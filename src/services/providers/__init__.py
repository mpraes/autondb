from __future__ import annotations

import os

from dotenv import load_dotenv

from src.services.providers.base import AIProvider
from src.services.providers.openai_compat import OpenAICompatProvider
from src.services.providers.anthropic_provider import AnthropicProvider
from src.services.providers.synthetic import SyntheticProvider

load_dotenv()

_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "openai/gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "synthetic": "synthetic",
}

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def create_provider(name: str, model: str | None = None) -> AIProvider:
    name = name.lower()
    model = model or _DEFAULT_MODELS.get(name, "gpt-4o")

    if name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return OpenAICompatProvider(api_key=api_key, model=model, provider_label="openai")

    if name == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        return OpenAICompatProvider(
            api_key=api_key,
            model=model,
            base_url=_GROQ_BASE_URL,
            provider_label="groq",
        )

    if name == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        return OpenAICompatProvider(
            api_key=api_key,
            model=model,
            base_url=_OPENROUTER_BASE_URL,
            provider_label="openrouter",
        )

    if name == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        return AnthropicProvider(api_key=api_key, model=model)

    if name == "synthetic":
        return SyntheticProvider()

    raise ValueError(
        f"Unknown AI provider: '{name}'. "
        f"Supported providers: {', '.join(sorted(_DEFAULT_MODELS))}"
    )


__all__ = [
    "AIProvider",
    "AnthropicProvider",
    "OpenAICompatProvider",
    "SyntheticProvider",
    "create_provider",
]
