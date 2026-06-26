import asyncio
from typing import Optional

from google import genai
from google.genai import types

from usage import current_node_type, current_thread_id, tracker

from ._mime import detect_mime


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash"):
        self._client: Optional[genai.Client] = None
        self._model = model

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client()
        return self._client

    async def generate(
        self,
        image_bytes: Optional[bytes],
        framework: str,
        prompt: str,
    ) -> str:
        contents: list = [prompt]
        if image_bytes:
            contents.append(
                types.Part.from_bytes(
                    data=image_bytes, mime_type=detect_mime(image_bytes)
                )
            )
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self._model,
            contents=contents,
        )

        usage = getattr(response, "usage_metadata", None)
        await tracker.log_usage(
            provider=self.name,
            model=self._model,
            node_type=current_node_type.get(),
            usage_dict={
                "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
            },
            thread_id=current_thread_id.get(),
        )

        return response.text or ""
