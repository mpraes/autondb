from __future__ import annotations

import json
import re

from anthropic import AsyncAnthropic

from src.services.providers.base import AIProvider


def _extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text.strip())


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
            max_tokens=4096,
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
            max_tokens=4096,
            system=system_enforced,
            messages=[{"role": "user", "content": user}],
        )
        raw = response.content[0].text
        return _extract_json(raw)
