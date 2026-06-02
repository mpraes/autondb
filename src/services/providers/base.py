"""Abstract base class for all AI providers.

Every provider must implement complete() and complete_json().
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract interface for AI completion providers."""

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a prompt and return the raw text response.

        Args:
            system: System prompt defining the AI role and rules.
            user: User prompt with the specific request.

        Returns:
            Raw text response from the AI model.
        """

    @abstractmethod
    async def complete_json(self, system: str, user: str) -> dict:
        """Send a prompt requesting JSON and return the parsed dict.

        Args:
            system: System prompt defining the AI role, rules, and JSON schema.
            user: User prompt with the specific request.

        Returns:
            Parsed JSON dict from the AI response.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g. 'openai', 'anthropic')."""
