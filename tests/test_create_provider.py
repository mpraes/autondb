from __future__ import annotations

import os

import pytest

from src.services.providers import PROVIDER_ENV_KEYS, create_provider
from src.services.providers.base import AIProvider
from src.services.providers.openai_compat import OpenAICompatProvider
from src.services.providers.anthropic_provider import AnthropicProvider
from src.services.providers.synthetic import SyntheticProvider


class TestCreateProvider:
    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown AI provider"):
            create_provider("nonexistent")

    def test_openai_missing_key_raises(self) -> None:
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                create_provider("openai")
        finally:
            if original is not None:
                os.environ["OPENAI_API_KEY"] = original

    def test_groq_missing_key_raises(self) -> None:
        original = os.environ.pop("GROQ_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                create_provider("groq")
        finally:
            if original is not None:
                os.environ["GROQ_API_KEY"] = original

    def test_openrouter_missing_key_raises(self) -> None:
        original = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                create_provider("openrouter")
        finally:
            if original is not None:
                os.environ["OPENROUTER_API_KEY"] = original

    def test_anthropic_missing_key_raises(self) -> None:
        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                create_provider("anthropic")
        finally:
            if original is not None:
                os.environ["ANTHROPIC_API_KEY"] = original

    def test_openai_returns_correct_provider(self) -> None:
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = create_provider("openai")
        assert isinstance(provider, OpenAICompatProvider)
        assert isinstance(provider, AIProvider)

    def test_groq_returns_correct_provider(self) -> None:
        os.environ["GROQ_API_KEY"] = "test-key"
        provider = create_provider("groq")
        assert isinstance(provider, OpenAICompatProvider)
        assert isinstance(provider, AIProvider)

    def test_anthropic_returns_correct_provider(self) -> None:
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        provider = create_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)
        assert isinstance(provider, AIProvider)

    def test_synthetic_returns_correct_provider(self) -> None:
        provider = create_provider("synthetic")
        assert isinstance(provider, SyntheticProvider)
        assert isinstance(provider, AIProvider)

    def test_provider_name_case_insensitive(self) -> None:
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = create_provider("OpenAI")
        assert isinstance(provider, OpenAICompatProvider)

    def test_model_override(self) -> None:
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = create_provider("openai", model="gpt-3.5-turbo")
        assert provider._model == "gpt-3.5-turbo"


class TestProviderEnvKeys:
    def test_contains_all_providers(self) -> None:
        assert "openai" in PROVIDER_ENV_KEYS
        assert "groq" in PROVIDER_ENV_KEYS
        assert "openrouter" in PROVIDER_ENV_KEYS
        assert "anthropic" in PROVIDER_ENV_KEYS

    def test_values_are_env_var_names(self) -> None:
        for key in PROVIDER_ENV_KEYS.values():
            assert key.isupper()
            assert "_API_KEY" in key
