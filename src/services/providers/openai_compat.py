from __future__ import annotations

from openai import AsyncOpenAI

from src.services.providers._json_utils import extract_json
from src.services.providers.base import AIProvider


class OpenAICompatProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider_label: str = "openai",
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._label = provider_label

    @property
    def provider_name(self) -> str:
        return self._label

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    async def complete_json(self, system: str, user: str) -> dict:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return extract_json(raw)
