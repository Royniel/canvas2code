import asyncio
import json
from typing import Optional, TypedDict

from google import genai
from google.genai import types
from pydantic import BaseModel

from usage import current_thread_id, tracker

from ._mime import detect_mime


class _JudgmentSchema(BaseModel):
    score: float
    critique: str
    needs_refinement: bool


class Judgment(TypedDict):
    score: float
    critique: str
    needs_refinement: bool


JUDGE_PROMPT = """You are evaluating a frontend code rendering against the original UI sketch.

Compare structure, layout, key UI elements, typography hierarchy, and overall faithfulness to the sketch.
- DO NOT penalize for exact color matching or fonts — sketches are imprecise on those.
- DO penalize for missing elements, wrong layout, incorrect proportions, alignment issues, wrong number of items.

Framework: {framework}

Score this rendering on a 0.0 to 1.0 scale of visual fidelity.
Provide concrete, actionable critique (1-3 sentences).
Mark needs_refinement=true if the score is below 0.75."""


class JudgeProvider:
    name = "judge"

    def __init__(self, model: str = "gemini-2.5-flash"):
        self._client: Optional[genai.Client] = None
        self._model = model

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client()
        return self._client

    async def judge(
        self,
        original_sketch: bytes,
        rendered_screenshot: bytes,
        framework: str,
    ) -> Judgment:
        prompt = JUDGE_PROMPT.format(framework=framework)
        contents = [
            prompt,
            "Original sketch:",
            types.Part.from_bytes(
                data=original_sketch,
                mime_type=detect_mime(original_sketch),
            ),
            "Current rendering:",
            types.Part.from_bytes(
                data=rendered_screenshot,
                mime_type="image/png",
            ),
        ]
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_JudgmentSchema,
            ),
        )

        usage = getattr(response, "usage_metadata", None)
        await tracker.log_usage(
            provider=self.name,
            model=self._model,
            node_type="judge",
            usage_dict={
                "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
            },
            thread_id=current_thread_id.get(),
        )

        text = response.text or "{}"
        try:
            parsed = _JudgmentSchema.model_validate_json(text)
        except Exception:
            try:
                data = json.loads(text)
                parsed = _JudgmentSchema(
                    score=float(data.get("score", 0.0)),
                    critique=str(data.get("critique", "")),
                    needs_refinement=bool(data.get("needs_refinement", False)),
                )
            except Exception:
                parsed = _JudgmentSchema(
                    score=0.0,
                    critique="Judge response could not be parsed.",
                    needs_refinement=False,
                )

        score = max(0.0, min(1.0, parsed.score))
        return {
            "score": score,
            "critique": parsed.critique,
            "needs_refinement": parsed.needs_refinement,
        }
