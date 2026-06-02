from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the raw text response."""

    @abstractmethod
    async def complete_json(self, system: str, user: str) -> dict:
        """Send a prompt requesting JSON and return the parsed dict."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""
