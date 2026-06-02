from __future__ import annotations

from src.services.providers.base import AIProvider
from src.services.providers.synthetic import SyntheticProvider


def test_synthetic_is_ai_provider() -> None:
    assert isinstance(SyntheticProvider(), AIProvider)


def test_synthetic_provider_name() -> None:
    assert SyntheticProvider().provider_name == "synthetic"
