import asyncio
from typing import Optional, TypedDict

from google import genai
from google.genai import types
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph


class GraphState(TypedDict):
    image_bytes: bytes
    framework: str
    generated_code: Optional[str]
    error: Optional[str]


def _make_generate_code_node(client: genai.Client):
    async def generate_code(state: GraphState, config: RunnableConfig) -> dict:
        try:
            mime_type = config["configurable"]["mime_type"]
            prompt = f"""
        You are an expert frontend developer. Look at this uploaded sketch or wireframe.
        Write a complete, working {state['framework']} component using Tailwind CSS that perfectly matches the sketch.
        Make it look modern and professional.
        Return ONLY the raw code, ready to be rendered. Do not include markdown formatting like ```javascript.
        """
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=state["image_bytes"], mime_type=mime_type
                    ),
                ],
            )
            return {"generated_code": response.text}
        except Exception as e:
            return {"error": str(e)}

    return generate_code


def build_graph(client: genai.Client):
    workflow = StateGraph(GraphState)
    workflow.add_node("generate_code", _make_generate_code_node(client))
    workflow.set_entry_point("generate_code")
    workflow.add_edge("generate_code", END)
    return workflow.compile()
