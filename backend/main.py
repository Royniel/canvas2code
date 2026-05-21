import base64
import json
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from playwright.async_api import async_playwright
from pydantic import BaseModel

from graph.builder import MAX_ITERATIONS, build_graph

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("canvas2code")

runtime = {"graph": None}

PROVIDER_NODE_MAP = {
    "gemini_generate": "gemini",
    "groq_generate": "groq",
    "openrouter_generate": "openrouter",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.environ["DATABASE_URL"]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            async with AsyncPostgresSaver.from_conn_string(db_url) as saver:
                await saver.setup()
                runtime["graph"] = build_graph(saver, browser)
                yield
                runtime["graph"] = None
        finally:
            await browser.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefineRequest(BaseModel):
    thread_id: str
    message: str


class SelectWinnerRequest(BaseModel):
    thread_id: str
    provider: str


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _emit_judgment(provider: str, judgment: dict) -> list:
    """Build SSE events for a single judgment result."""
    events = [
        _sse(
            {
                "type": "judgment",
                "provider": provider,
                "score": judgment["score"],
                "critique": judgment["critique"],
                "iteration": judgment["iteration"],
            }
        )
    ]
    needs = judgment.get("needs_refinement") and judgment["iteration"] < MAX_ITERATIONS
    events.append(
        _sse(
            {
                "type": "provider_status",
                "provider": provider,
                "status": "refining" if needs else "done",
            }
        )
    )
    return events


@app.get("/")
def read_root():
    return {"status": "success", "message": "canvas2code AI backend is live!"}


@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    framework: str = Form(...),
    thread_id: str = Form(...),
):
    image_bytes = await file.read()

    async def event_stream():
        total_llm_calls = 0
        try:
            yield _sse({"type": "status", "message": "Starting comparison..."})
            for p in ("gemini", "groq", "openrouter"):
                yield _sse(
                    {
                        "type": "provider_status",
                        "provider": p,
                        "status": "generating",
                    }
                )

            graph = runtime["graph"]
            initial_state = {
                "image_bytes": image_bytes,
                "framework": framework,
                "generated_code": None,
                "error": None,
                "current_code": None,
                "selected_provider": None,
                "outputs": {},
                "errors": {},
                "rendered_screenshots": {},
                "judgments": {},
                "iteration_count": {},
                "llm_call_count": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Generate {framework} code from this sketch.",
                    }
                ],
            }
            config = {"configurable": {"thread_id": thread_id}}

            async for chunk in graph.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                for node_name, node_output in chunk.items():
                    out = node_output or {}
                    total_llm_calls += out.get("llm_call_count", 0)

                    if node_name in PROVIDER_NODE_MAP:
                        provider = PROVIDER_NODE_MAP[node_name]
                        out_errors = out.get("errors", {})
                        out_outputs = out.get("outputs", {})
                        if provider in out_errors:
                            yield _sse(
                                {
                                    "type": "provider_error",
                                    "provider": provider,
                                    "message": out_errors[provider],
                                    "stage": "generation",
                                }
                            )
                            yield _sse(
                                {
                                    "type": "provider_status",
                                    "provider": provider,
                                    "status": "error",
                                }
                            )
                        elif provider in out_outputs:
                            yield _sse(
                                {
                                    "type": "provider_code",
                                    "provider": provider,
                                    "content": out_outputs[provider],
                                }
                            )
                            yield _sse(
                                {
                                    "type": "provider_status",
                                    "provider": provider,
                                    "status": "rendering",
                                }
                            )

                    elif node_name == "render_all":
                        screenshots = out.get("rendered_screenshots", {})
                        render_errors = out.get("errors", {})
                        for provider, png in screenshots.items():
                            yield _sse(
                                {
                                    "type": "provider_screenshot",
                                    "provider": provider,
                                    "image_base64": base64.b64encode(png).decode(
                                        "ascii"
                                    ),
                                }
                            )
                            yield _sse(
                                {
                                    "type": "provider_status",
                                    "provider": provider,
                                    "status": "judging",
                                }
                            )
                        for provider, err in render_errors.items():
                            yield _sse(
                                {
                                    "type": "provider_error",
                                    "provider": provider,
                                    "message": err,
                                    "stage": "rendering",
                                }
                            )
                            yield _sse(
                                {
                                    "type": "provider_status",
                                    "provider": provider,
                                    "status": "done",
                                }
                            )

                    elif node_name == "judge_outputs":
                        judgments = out.get("judgments", {})
                        for provider, j in judgments.items():
                            for ev in _emit_judgment(provider, j):
                                yield ev

                    elif node_name == "refine_loop":
                        new_outputs = out.get("outputs", {}) or {}
                        new_screenshots = out.get("rendered_screenshots", {}) or {}
                        new_judgments = out.get("judgments", {}) or {}
                        new_iterations = out.get("iteration_count", {}) or {}

                        for provider, iter_num in new_iterations.items():
                            if iter_num <= MAX_ITERATIONS:
                                yield _sse(
                                    {
                                        "type": "refining",
                                        "provider": provider,
                                        "iteration": iter_num,
                                    }
                                )

                        for provider, code in new_outputs.items():
                            yield _sse(
                                {
                                    "type": "provider_code",
                                    "provider": provider,
                                    "content": code,
                                }
                            )

                        for provider, png in new_screenshots.items():
                            yield _sse(
                                {
                                    "type": "provider_screenshot",
                                    "provider": provider,
                                    "image_base64": base64.b64encode(png).decode(
                                        "ascii"
                                    ),
                                }
                            )

                        for provider, j in new_judgments.items():
                            for ev in _emit_judgment(provider, j):
                                yield ev

            logger.info(
                "Generation complete: thread=%s framework=%s total_llm_calls=%d",
                thread_id,
                framework,
                total_llm_calls,
            )
            yield _sse(
                {
                    "type": "status",
                    "message": f"Comparison complete ({total_llm_calls} LLM calls)",
                }
            )
        except Exception as e:
            logger.exception("Generate failed for thread %s", thread_id)
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/select-winner")
async def select_winner(req: SelectWinnerRequest):
    graph = runtime["graph"]
    config = {"configurable": {"thread_id": req.thread_id}}
    snapshot = await graph.aget_state(config)
    outputs = (snapshot.values or {}).get("outputs", {})

    if req.provider not in outputs:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{req.provider}' has no output for thread '{req.thread_id}'.",
        )

    await graph.aupdate_state(
        config,
        {
            "selected_provider": req.provider,
            "current_code": outputs[req.provider],
        },
    )
    return {"status": "ok", "selected_provider": req.provider}


@app.post("/refine")
async def refine(req: RefineRequest):
    async def event_stream():
        try:
            yield _sse({"type": "status", "message": "Refining code..."})

            graph = runtime["graph"]
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": req.message}]},
                config={"configurable": {"thread_id": req.thread_id}},
            )

            if result.get("error"):
                yield _sse({"type": "error", "message": result["error"]})
            elif result.get("current_code"):
                yield _sse({"type": "code", "content": result["current_code"]})
            else:
                yield _sse({"type": "error", "message": "No output produced."})
        except Exception as e:
            logger.exception("Refine failed for thread %s", req.thread_id)
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
