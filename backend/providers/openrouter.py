import base64
import os
from typing import Optional

from openai import AsyncOpenAI

from ._mime import detect_mime


class OpenRouterProvider:
    name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, model: Optional[str] = None):
        self._client: Optional[AsyncOpenAI] = None
        self._model = model or os.environ.get(
            "OPENROUTER_MODEL", "qwen/qwen-2-vl-72b-instruct"
        )

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise RuntimeError("OPENROUTER_API_KEY is not set")
            self._client = AsyncOpenAI(base_url=self.BASE_URL, api_key=api_key)
        return self._client

    async def generate(
        self,
        image_bytes: Optional[bytes],
        framework: str,
        prompt: str,
    ) -> str:
        content: list = [{"type": "text", "text": prompt}]
        if image_bytes:
            mime_type = detect_mime(image_bytes)
            b64 = base64.b64encode(image_bytes).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                }
            )
        response = await self.client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content or ""
