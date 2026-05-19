import json

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai

from graph.builder import build_graph

load_dotenv()
client = genai.Client()
graph = build_graph(client)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.get("/")
def read_root():
    return {"status": "success", "message": "canvas2code AI backend is live!"}


@app.post("/generate")
async def generate_code(file: UploadFile = File(...), framework: str = Form(...)):
    image_bytes = await file.read()
    mime_type = file.content_type

    async def event_stream():
        try:
            yield _sse({"type": "status", "message": "Preparing image..."})
            yield _sse({"type": "status", "message": "Calling Gemini..."})

            result = await graph.ainvoke(
                {
                    "image_bytes": image_bytes,
                    "framework": framework,
                    "generated_code": None,
                    "error": None,
                },
                config={"configurable": {"mime_type": mime_type}},
            )

            if result.get("error"):
                yield _sse({"type": "error", "message": result["error"]})
            elif result.get("generated_code"):
                yield _sse({"type": "code", "content": result["generated_code"]})
            else:
                yield _sse({"type": "error", "message": "No output produced."})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
