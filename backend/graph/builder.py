import asyncio
from operator import add, or_
from typing import Annotated, Dict, List, Optional, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from playwright.async_api import Browser

from providers import PROVIDERS
from providers.judge import JudgeProvider
from rendering import render_code_to_screenshot

JUDGE = JudgeProvider()
MAX_ITERATIONS = 3


class Message(TypedDict):
    role: str
    content: str


class Judgment(TypedDict):
    score: float
    critique: str
    needs_refinement: bool
    iteration: int


class GraphState(TypedDict):
    image_bytes: Optional[bytes]
    framework: str
    generated_code: Optional[str]
    error: Optional[str]
    messages: Annotated[List[Message], add]
    current_code: Optional[str]
    outputs: Annotated[Dict[str, str], or_]
    errors: Annotated[Dict[str, str], or_]
    rendered_screenshots: Annotated[Dict[str, bytes], or_]
    judgments: Annotated[Dict[str, Judgment], or_]
    iteration_count: Annotated[Dict[str, int], or_]
    llm_call_count: Annotated[int, add]
    selected_provider: Optional[str]


INITIAL_PROMPT = """
You are an expert frontend developer. Look at this uploaded sketch or wireframe.
Write a complete, working {framework} component using Tailwind CSS that perfectly matches the sketch.
Make it look modern and professional.
Return ONLY the raw code, ready to be rendered. Do not include markdown formatting like ```javascript.
"""

REFINE_PROMPT = """
You are an expert frontend developer iterating on a {framework} component.

Current code:
{current_code}

The user wants the following change:
{latest_message}

Return ONLY the updated raw code. No markdown fences, no explanations.
"""

REFINE_WITH_CRITIQUE_PROMPT = """
You are an expert frontend developer iterating on a {framework} component based on visual feedback.

Your previous code did not fully match the original sketch. A vision judge gave this critique:
{critique}

Your previous code:
{previous_code}

Look at the original sketch again. Address the critique. Return the updated {framework} component code using Tailwind CSS.
Return ONLY the raw code, no markdown fences, no explanations.
"""


def _make_provider_node(provider_name: str):
    provider = PROVIDERS[provider_name]

    async def node(state: GraphState, config: RunnableConfig) -> dict:
        try:
            prompt = INITIAL_PROMPT.format(framework=state["framework"])
            code = await provider.generate(
                state.get("image_bytes"), state["framework"], prompt
            )
            return {"outputs": {provider_name: code}, "llm_call_count": 1}
        except Exception as e:
            return {"errors": {provider_name: str(e)}, "llm_call_count": 1}

    return node


async def generate_code(state: GraphState, config: RunnableConfig) -> dict:
    return {}


async def merge_node(state: GraphState, config: RunnableConfig) -> dict:
    return {}


def _make_render_all_node(browser: Browser):
    async def render_all(state: GraphState, config: RunnableConfig) -> dict:
        outputs = state.get("outputs") or {}
        if not outputs:
            return {}

        framework = state["framework"]

        async def render_one(provider: str, code: str):
            try:
                png = await render_code_to_screenshot(
                    code=code, framework=framework, browser=browser
                )
                return provider, png, None
            except Exception as e:
                return provider, None, f"Rendering failed: {e}"

        results = await asyncio.gather(
            *[render_one(p, c) for p, c in outputs.items()]
        )
        screenshots = {p: png for p, png, _ in results if png is not None}
        errors = {p: err for p, _, err in results if err is not None}

        update: dict = {}
        if screenshots:
            update["rendered_screenshots"] = screenshots
        if errors:
            update["errors"] = errors
        return update

    return render_all


async def judge_outputs(state: GraphState, config: RunnableConfig) -> dict:
    screenshots = state.get("rendered_screenshots") or {}
    if not screenshots:
        return {}

    image_bytes = state["image_bytes"]
    framework = state["framework"]

    async def judge_one(provider: str, screenshot: bytes):
        try:
            j = await JUDGE.judge(
                original_sketch=image_bytes,
                rendered_screenshot=screenshot,
                framework=framework,
            )
            j["iteration"] = 0
            return provider, j, None
        except Exception as e:
            return provider, None, str(e)

    results = await asyncio.gather(
        *[judge_one(p, s) for p, s in screenshots.items()]
    )

    judgments: Dict[str, Judgment] = {}
    iteration_cap: Dict[str, int] = {}
    for provider, j, err in results:
        if j is not None:
            judgments[provider] = j
        if err is not None:
            iteration_cap[provider] = MAX_ITERATIONS

    update: dict = {"llm_call_count": len(screenshots)}
    if judgments:
        update["judgments"] = judgments
    if iteration_cap:
        update["iteration_count"] = iteration_cap
    return update


def _make_refine_loop_node(browser: Browser):
    async def refine_loop(state: GraphState, config: RunnableConfig) -> dict:
        outputs = state.get("outputs") or {}
        judgments = state.get("judgments") or {}
        iteration_counts = state.get("iteration_count") or {}

        pending = [
            p
            for p in outputs
            if judgments.get(p, {}).get("needs_refinement")
            and iteration_counts.get(p, 0) < MAX_ITERATIONS
        ]
        if not pending:
            return {}

        framework = state["framework"]
        image_bytes = state["image_bytes"]

        async def refine_one(provider_name: str):
            provider = PROVIDERS[provider_name]
            old_code = outputs[provider_name]
            old_judgment = judgments[provider_name]
            old_score = old_judgment["score"]
            current_iter = iteration_counts.get(provider_name, 0)
            new_iter = current_iter + 1

            try:
                prompt = REFINE_WITH_CRITIQUE_PROMPT.format(
                    framework=framework,
                    previous_code=old_code,
                    critique=old_judgment["critique"],
                )
                new_code = await provider.generate(image_bytes, framework, prompt)
                new_screenshot = await render_code_to_screenshot(
                    code=new_code, framework=framework, browser=browser
                )
                new_judgment = await JUDGE.judge(
                    original_sketch=image_bytes,
                    rendered_screenshot=new_screenshot,
                    framework=framework,
                )
                new_judgment["iteration"] = new_iter

                if new_judgment["score"] < old_score:
                    new_judgment["needs_refinement"] = False
                    return {
                        "provider": provider_name,
                        "kept_old": True,
                        "judgment": new_judgment,
                        "iteration": MAX_ITERATIONS,
                        "llm_calls": 2,
                    }

                return {
                    "provider": provider_name,
                    "code": new_code,
                    "screenshot": new_screenshot,
                    "judgment": new_judgment,
                    "iteration": new_iter,
                    "llm_calls": 2,
                }
            except Exception as e:
                return {
                    "provider": provider_name,
                    "error": str(e),
                    "iteration": MAX_ITERATIONS,
                    "llm_calls": 1,
                }

        results = await asyncio.gather(*[refine_one(p) for p in pending])

        outputs_update: Dict[str, str] = {}
        screenshots_update: Dict[str, bytes] = {}
        judgments_update: Dict[str, Judgment] = {}
        iterations_update: Dict[str, int] = {}
        total_calls = 0

        for r in results:
            p = r["provider"]
            total_calls += r.get("llm_calls", 0)
            iterations_update[p] = r["iteration"]

            if r.get("error"):
                continue
            if r.get("kept_old"):
                judgments_update[p] = r["judgment"]
                continue
            outputs_update[p] = r["code"]
            screenshots_update[p] = r["screenshot"]
            judgments_update[p] = r["judgment"]

        update: dict = {"llm_call_count": total_calls}
        if outputs_update:
            update["outputs"] = outputs_update
        if screenshots_update:
            update["rendered_screenshots"] = screenshots_update
        if judgments_update:
            update["judgments"] = judgments_update
        if iterations_update:
            update["iteration_count"] = iterations_update
        return update

    return refine_loop


async def refine_code(state: GraphState, config: RunnableConfig) -> dict:
    try:
        provider_name = state.get("selected_provider")
        if not provider_name or provider_name not in PROVIDERS:
            return {"error": "No valid provider selected. Call /select-winner first."}
        provider = PROVIDERS[provider_name]

        messages = state.get("messages") or []
        latest_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            None,
        )
        if not latest_user:
            return {"error": "No user message found for refinement."}

        prompt = REFINE_PROMPT.format(
            framework=state["framework"],
            current_code=state.get("current_code") or "",
            latest_message=latest_user,
        )
        refined = await provider.generate(None, state["framework"], prompt)
        return {
            "current_code": refined,
            "messages": [{"role": "assistant", "content": "Code updated."}],
            "llm_call_count": 1,
        }
    except Exception as e:
        return {"error": str(e), "llm_call_count": 1}


def _route(state: GraphState) -> str:
    if state.get("current_code") and state.get("selected_provider"):
        return "refine_code"
    return "generate_code"


def _should_continue(state: GraphState) -> str:
    outputs = state.get("outputs") or {}
    judgments = state.get("judgments") or {}
    iteration_counts = state.get("iteration_count") or {}
    for p in outputs:
        j = judgments.get(p)
        if (
            j
            and j.get("needs_refinement")
            and iteration_counts.get(p, 0) < MAX_ITERATIONS
        ):
            return "refine_loop"
    return END


def build_graph(checkpointer: BaseCheckpointSaver, browser: Browser):
    workflow = StateGraph(GraphState)

    workflow.add_node("generate_code", generate_code)
    workflow.add_node("gemini_generate", _make_provider_node("gemini"))
    workflow.add_node("groq_generate", _make_provider_node("groq"))
    workflow.add_node("openrouter_generate", _make_provider_node("openrouter"))
    workflow.add_node("merge_node", merge_node)
    workflow.add_node("render_all", _make_render_all_node(browser))
    workflow.add_node("judge_outputs", judge_outputs)
    workflow.add_node("refine_loop", _make_refine_loop_node(browser))
    workflow.add_node("refine_code", refine_code)

    workflow.set_conditional_entry_point(
        _route,
        {
            "generate_code": "generate_code",
            "refine_code": "refine_code",
        },
    )

    workflow.add_edge("generate_code", "gemini_generate")
    workflow.add_edge("generate_code", "groq_generate")
    workflow.add_edge("generate_code", "openrouter_generate")

    workflow.add_edge("gemini_generate", "merge_node")
    workflow.add_edge("groq_generate", "merge_node")
    workflow.add_edge("openrouter_generate", "merge_node")

    workflow.add_edge("merge_node", "render_all")
    workflow.add_edge("render_all", "judge_outputs")

    workflow.add_conditional_edges(
        "judge_outputs",
        _should_continue,
        {"refine_loop": "refine_loop", END: END},
    )
    workflow.add_conditional_edges(
        "refine_loop",
        _should_continue,
        {"refine_loop": "refine_loop", END: END},
    )

    workflow.add_edge("refine_code", END)

    return workflow.compile(checkpointer=checkpointer)
