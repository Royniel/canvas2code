import asyncio
from typing import Optional

from google import genai
from google.genai import types

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
        return response.text or ""
