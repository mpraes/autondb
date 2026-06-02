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
    def __init__(
        self,
        provider: AIProvider,
        provider_name: str = DEFAULT_AI_PROVIDER,
        model: str = DEFAULT_AI_MODEL,
    ) -> None:
        self._provider = provider
        self._provider_name = provider_name
        self._model = model

    @classmethod
    def from_env(
        cls,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> AIService:
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
        new_provider = create_provider(provider_name, model)
        self._provider = new_provider
        self._provider_name = provider_name
        self._model = model or provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    async def map_schema(
        self,
        source_schema: list[TableSchema],
        source_dialect: str,
        target_dialect: str,
    ) -> SchemaMapping:
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
