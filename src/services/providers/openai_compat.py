from __future__ import annotations

from openai import AsyncOpenAI

from src.services.providers._json_utils import extract_json
from src.services.providers.base import AIProvider


class OpenAICompatProvider(AIProvider):
    """AI provider for OpenAI-compatible APIs (OpenAI, Groq, OpenRouter).

    Uses the OpenAI Python client with configurable base_url to support
    multiple providers that share the same chat completions API.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider_label: str = "openai",
    ) -> None:
        """Initialize the OpenAI-compatible provider.

        Args:
            api_key: API key for authentication.
            model: Model identifier (e.g. 'gpt-4o', 'llama-3.3-70b-versatile').
            base_url: Optional override for the API base URL.
            provider_label: Human-readable provider name for logging.
        """
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._label = provider_label

    @property
    def provider_name(self) -> str:
        """Return the provider label (e.g. 'openai', 'groq', 'openrouter')."""
        return self._label

    async def complete(self, system: str, user: str) -> str:
        """Send a chat completion prompt and return the raw text response."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    async def complete_json(self, system: str, user: str) -> dict:
        """Send a chat completion prompt with JSON response format and return parsed dict."""
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
