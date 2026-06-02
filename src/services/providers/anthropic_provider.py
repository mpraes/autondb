from __future__ import annotations

from anthropic import AsyncAnthropic

from src.constants import DEFAULT_AI_MAX_TOKENS
from src.services.providers._json_utils import extract_json
from src.services.providers.base import AIProvider


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=DEFAULT_AI_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    async def complete_json(self, system: str, user: str) -> dict:
        system_enforced = (
            system
            + "\n\nYou MUST respond with valid JSON only. No markdown, no commentary."
        )
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=DEFAULT_AI_MAX_TOKENS,
            system=system_enforced,
            messages=[{"role": "user", "content": user}],
        )
        raw = response.content[0].text
        return extract_json(raw)
