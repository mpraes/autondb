"""AI service — high-level interface for schema mapping and data sanitization.

Wraps an AIProvider and exposes map_schema() and sanitize_preflight()
methods that build prompts, call the provider, and validate responses.
"""

from __future__ import annotations

import os

from src.constants import DEFAULT_AI_PROVIDER, DEFAULT_AI_MODEL
from src.databases.idatabase import TableSchema
from src.services.models import (
    ColumnStats,
    SanitizationReport,
    SchemaMapping,
)
from src.services.prompts import build_sanitization_prompt, build_schema_mapping_prompt
from src.services.providers import create_provider
from src.services.providers.base import AIProvider


class AIServiceError(Exception):
    pass


class AIService:
    """High-level AI service for schema mapping and data sanitization.

    Wraps an AIProvider and exposes map_schema() and sanitize_preflight()
    methods that build prompts, call the provider, and validate responses.
    """

    def __init__(
        self,
        provider: AIProvider,
        provider_name: str = DEFAULT_AI_PROVIDER,
        model: str = DEFAULT_AI_MODEL,
    ) -> None:
        """Initialize AIService with a specific provider and model.

        Args:
            provider: An AIProvider instance to delegate calls to.
            provider_name: Human-readable provider label (e.g. 'openai').
            model: Model identifier (e.g. 'gpt-4o').
        """
        self._provider = provider
        self._provider_name = provider_name
        self._model = model

    @classmethod
    def from_env(
        cls,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> AIService:
        """Create an AIService from environment variables.

        Falls back to AI_PROVIDER and AI_MODEL env vars, then to defaults.

        Args:
            provider_name: Optional provider override (e.g. 'anthropic').
            model: Optional model override (e.g. 'claude-sonnet-4-20250514').

        Returns:
            A configured AIService instance.
        """
        provider_name = (
            provider_name or os.getenv("AI_PROVIDER", DEFAULT_AI_PROVIDER)
        ).lower()
        model = model or os.getenv("AI_MODEL")
        provider = create_provider(provider_name, model)
        effective_model = model or getattr(provider, "_model", provider_name)
        return cls(
            provider=provider, provider_name=provider_name, model=effective_model
        )

    def set_provider(self, provider_name: str, model: str | None = None) -> None:
        """Switch the AI provider at runtime.

        Args:
            provider_name: Name of the new provider (e.g. 'groq').
            model: Optional model override for the new provider.
        """
        new_provider = create_provider(provider_name, model)
        self._provider = new_provider
        self._provider_name = provider_name
        self._model = model or provider_name

    @property
    def provider_name(self) -> str:
        """Name of the current AI provider."""
        return self._provider_name

    @property
    def model(self) -> str:
        """Model identifier currently in use."""
        return self._model

    async def map_schema(
        self,
        source_schema: list[TableSchema],
        source_dialect: str,
        target_dialect: str,
    ) -> SchemaMapping:
        """Use AI to map source schema types to the target dialect.

        Sends DDL metadata to the AI provider and returns a validated
        SchemaMapping with per-column type mappings, transforms, and warnings.

        Args:
            source_schema: List of TableSchema from the source database.
            source_dialect: Source database dialect (e.g. 'sqlite').
            target_dialect: Target database dialect (e.g. 'postgresql').

        Returns:
            A SchemaMapping with tables, columns, warnings, and DDL.

        Raises:
            AIServiceError: If the AI call or response validation fails.
        """
        system, user = build_schema_mapping_prompt(
            source_schema, source_dialect, target_dialect
        )
        try:
            raw = await self._provider.complete_json(system, user)
        except Exception as exc:
            raise AIServiceError(
                f"AI provider '{self._provider_name}' failed: {exc}"
            ) from exc

        try:
            mapping = SchemaMapping.model_validate(raw)
        except Exception as exc:
            raise AIServiceError(
                f"AI response failed schema validation: {exc}\nRaw: {raw}"
            ) from exc

        mapping.target_dialect = target_dialect
        return mapping

    async def sanitize_preflight(
        self,
        column_stats: list[ColumnStats],
        target_dialect: str,
    ) -> SanitizationReport:
        """Run pre-flight data sanitization check via AI.

        Sends statistical metadata (sample values, null counts, distinct
        counts) to the AI provider to detect data incompatible with the
        target column types.

        Args:
            column_stats: List of ColumnStats with sampling metadata.
            target_dialect: Target database dialect.

        Returns:
            A SanitizationReport listing detected issues or confirming clean data.

        Raises:
            AIServiceError: If the AI call or response validation fails.
        """
        system, user = build_sanitization_prompt(column_stats, target_dialect)
        try:
            raw = await self._provider.complete_json(system, user)
        except Exception as exc:
            raise AIServiceError(
                f"AI provider '{self._provider_name}' failed: {exc}"
            ) from exc

        try:
            report = SanitizationReport.model_validate(raw)
        except Exception as exc:
            raise AIServiceError(
                f"AI response failed sanitization validation: {exc}\nRaw: {raw}"
            ) from exc

        return report
