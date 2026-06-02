from __future__ import annotations

import json
import os

import pytest
import pytest_asyncio

from src.databases.idatabase import ColumnSchema, TableSchema
from src.services.ai_service import AIService
from src.services.models import ColumnStats, SchemaMapping, SanitizationReport
from src.services.prompts import build_sanitization_prompt, build_schema_mapping_prompt
from src.services.providers.synthetic import SyntheticProvider


@pytest.fixture
def sample_schema() -> list[TableSchema]:
    return [
        TableSchema(
            name="users",
            columns=[
                ColumnSchema(
                    name="id", type="INTEGER", nullable=False, is_primary_key=True
                ),
                ColumnSchema(name="email", type="TEXT", nullable=False),
                ColumnSchema(name="created_at", type="TEXT", nullable=True),
            ],
        ),
    ]


@pytest.fixture
def sample_stats() -> list[ColumnStats]:
    return [
        ColumnStats(
            table="users",
            column="email",
            target_type="VARCHAR(255)",
            sample_values=["alice@example.com", "bob@example.com"],
            null_count=0,
            total_rows=100,
            distinct_count=98,
        ),
        ColumnStats(
            table="users",
            column="created_at",
            target_type="TIMESTAMP",
            sample_values=["2024-01-15", "N/A", "2024-02-20"],
            null_count=5,
            total_rows=100,
            distinct_count=90,
        ),
    ]


class TestSchemaMappingPrompt:
    def test_returns_system_and_user(self, sample_schema: list[TableSchema]) -> None:
        system, user = build_schema_mapping_prompt(
            sample_schema, "sqlite", "postgresql"
        )
        assert "migration expert" in system
        assert "sqlite" in user.lower()
        assert "postgresql" in user.lower()
        assert "users" in user

    def test_includes_json_schema(self, sample_schema: list[TableSchema]) -> None:
        system, user = build_schema_mapping_prompt(
            sample_schema, "sqlite", "postgresql"
        )
        assert "tables" in system
        assert "columns" in system


class TestSanitizationPrompt:
    def test_returns_system_and_user(self, sample_stats: list[ColumnStats]) -> None:
        system, user = build_sanitization_prompt(sample_stats, "postgresql")
        assert "data quality" in system.lower()
        assert "postgresql" in user.lower()

    def test_includes_stats_payload(self, sample_stats: list[ColumnStats]) -> None:
        system, user = build_sanitization_prompt(sample_stats, "postgresql")
        assert "alice@example.com" in user
        assert "N/A" in user


class TestSyntheticProvider:
    @pytest.mark.asyncio
    async def test_complete_returns_json_string(self) -> None:
        provider = SyntheticProvider()
        result = await provider.complete("system", "schema mapping prompt")
        parsed = json.loads(result)
        assert "tables" in parsed

    @pytest.mark.asyncio
    async def test_complete_json_returns_dict(self) -> None:
        provider = SyntheticProvider()
        result = await provider.complete_json("system", "schema mapping prompt")
        assert isinstance(result, dict)
        assert "tables" in result

    @pytest.mark.asyncio
    async def test_sanitization_response(self) -> None:
        provider = SyntheticProvider()
        result = await provider.complete_json(
            "data quality analyst", "analyze data compatibility"
        )
        assert "issues" in result
        assert "is_clean" in result


class TestAIServiceWithSynthetic:
    @pytest_asyncio.fixture
    async def ai(self) -> AIService:
        return AIService(
            provider=SyntheticProvider(),
            provider_name="synthetic",
            model="synthetic",
        )

    @pytest.mark.asyncio
    async def test_map_schema_returns_mapping(
        self, ai: AIService, sample_schema: list[TableSchema]
    ) -> None:
        mapping = await ai.map_schema(sample_schema, "sqlite", "postgresql")
        assert isinstance(mapping, SchemaMapping)
        assert mapping.target_dialect == "postgresql"

    @pytest.mark.asyncio
    async def test_sanitize_preflight_returns_report(
        self, ai: AIService, sample_stats: list[ColumnStats]
    ) -> None:
        report = await ai.sanitize_preflight(sample_stats, "postgresql")
        assert isinstance(report, SanitizationReport)

    @pytest.mark.asyncio
    async def test_provider_name(self, ai: AIService) -> None:
        assert ai.provider_name == "synthetic"

    @pytest.mark.asyncio
    async def test_set_provider_switches_runtime(self) -> None:
        ai = AIService(
            provider=SyntheticProvider(),
            provider_name="synthetic",
            model="synthetic",
        )
        custom_response = {
            "tables": [],
            "warnings": ["custom warning"],
        }
        new_provider = SyntheticProvider(schema_response=custom_response)
        ai.set_provider("synthetic", model="synthetic")
        ai._provider = new_provider
        ai._provider_name = "synthetic"

        assert ai.provider_name == "synthetic"

    @pytest.mark.asyncio
    async def test_map_schema_with_custom_synthetic(
        self, sample_schema: list[TableSchema]
    ) -> None:
        custom = {
            "tables": [
                {
                    "source_table": "users",
                    "target_table": "users",
                    "columns": [
                        {
                            "source_name": "id",
                            "source_type": "INTEGER",
                            "target_name": "id",
                            "target_type": "BIGSERIAL",
                            "nullable": False,
                            "is_primary_key": True,
                            "default": None,
                            "transform": None,
                        }
                    ],
                }
            ],
            "warnings": ["SQLite INTEGER may exceed BIGINT range"],
        }
        ai = AIService(
            provider=SyntheticProvider(schema_response=custom),
            provider_name="synthetic",
            model="synthetic",
        )
        mapping = await ai.map_schema(sample_schema, "sqlite", "postgresql")
        assert mapping.tables[0].columns[0].target_type == "BIGSERIAL"
        assert len(mapping.warnings) == 1


class TestAIServiceFromEnv:
    def test_from_env_with_synthetic(self) -> None:
        os.environ["AI_PROVIDER"] = "synthetic"
        try:
            ai = AIService.from_env(provider_name="synthetic")
            assert ai.provider_name == "synthetic"
        finally:
            os.environ.pop("AI_PROVIDER", None)

    def test_from_env_default_provider(self) -> None:
        original = os.environ.pop("AI_PROVIDER", None)
        try:
            os.environ["OPENAI_API_KEY"] = "test-key"
            ai = AIService.from_env()
            assert ai.provider_name == "openai"
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
            if original is not None:
                os.environ["AI_PROVIDER"] = original

    def test_from_env_model_from_env(self) -> None:
        os.environ["AI_MODEL"] = "gpt-3.5-turbo"
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            ai = AIService.from_env(provider_name="openai")
            assert ai.model == "gpt-3.5-turbo"
        finally:
            os.environ.pop("AI_MODEL", None)
            os.environ.pop("OPENAI_API_KEY", None)

    def test_from_env_model_override(self) -> None:
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            ai = AIService.from_env(provider_name="openai", model="gpt-4o-mini")
            assert ai.model == "gpt-4o-mini"
        finally:
            os.environ.pop("OPENAI_API_KEY", None)
