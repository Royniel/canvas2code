import base64
import os
from typing import Optional

from openai import AsyncOpenAI

from usage import current_node_type, current_thread_id, tracker

from ._mime import detect_mime


class GroqProvider:
    name = "groq"
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, model: Optional[str] = None):
        self._client: Optional[AsyncOpenAI] = None
        self._model = model or os.environ.get(
        "GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
        )

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is not set")
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

        usage = getattr(response, "usage", None)
        await tracker.log_usage(
            provider=self.name,
            model=self._model,
            node_type=current_node_type.get(),
            usage_dict={
                "input_tokens": (
                    getattr(usage, "prompt_tokens", 0) if usage else 0
                ),
                "output_tokens": (
                    getattr(usage, "completion_tokens", 0) if usage else 0
                ),
            },
            thread_id=current_thread_id.get(),
        )

        return response.choices[0].message.content or ""
