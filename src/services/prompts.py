"""Prompt templates for AI schema mapping and pre-flight sanitization.

Builds system and user prompts that instruct the AI model to produce
structured JSON responses matching the Pydantic model schemas.
"""

from __future__ import annotations

import json

from src.databases.idatabase import TableSchema
from src.services.models import ColumnStats, SchemaMapping


def build_schema_mapping_prompt(
    source_schema: list[TableSchema],
    source_dialect: str,
    target_dialect: str,
) -> tuple[str, str]:
    """Build system and user prompts for AI schema mapping.

    The system prompt defines the AI role, mapping rules, and the expected
    JSON schema. The user prompt provides the source DDL and target dialect.

    Args:
        source_schema: List of TableSchema from the source database.
        source_dialect: Source database dialect (e.g. 'sqlite').
        target_dialect: Target database dialect (e.g. 'postgresql').

    Returns:
        Tuple of (system_prompt, user_prompt) strings.
    """
    schema_ddl = _schema_to_readable_ddl(source_schema)

    system = (
        "You are a senior database migration expert. "
        "Your job is to map column types from one database dialect to another, "
        "preserving semantics and choosing the most appropriate target type.\n\n"
        "Rules:\n"
        "1. Choose the target type that best preserves the source type's semantics.\n"
        "2. Preserve column names unless they collide with reserved keywords in the "
        "target dialect — in that case, append '_col' to the name.\n"
        "3. Preserve table names following the same rule.\n"
        "4. If a type has no direct equivalent, pick the safest wider type.\n"
        "5. Set 'transform' to a SQL expression only when a data transformation is "
        "needed during migration (e.g., CAST, date format change).\n"
        "6. Add any compatibility concerns to the 'warnings' list.\n"
        "7. You MUST respond with valid JSON matching the schema below — no markdown.\n\n"
        "JSON schema:\n" + json.dumps(SchemaMapping.model_json_schema(), indent=2)
    )

    user = (
        f"Map the following {source_dialect} schema to {target_dialect}.\n\n"
        f"Source DDL:\n{schema_ddl}\n\n"
        f"Target dialect: {target_dialect}\n\n"
        "Respond with a JSON object matching the schema provided."
    )

    return system, user


def build_sanitization_prompt(
    column_stats: list[ColumnStats],
    target_dialect: str,
) -> tuple[str, str]:
    """Build system and user prompts for pre-flight data sanitization.

    The system prompt defines the AI role, detection rules, and the expected
    JSON schema. The user prompt provides column statistical metadata.

    Args:
        column_stats: List of ColumnStats with sampling metadata.
        target_dialect: Target database dialect.

    Returns:
        Tuple of (system_prompt, user_prompt) strings.
    """
    stats_payload = json.dumps(
        [s.model_dump() for s in column_stats], indent=2, default=str
    )

    system = (
        "You are a data quality analyst specializing in database migrations. "
        "You receive statistical metadata about source columns (sample values, "
        "null counts, distinct counts) and must detect data that is incompatible "
        "with the mapped target column types.\n\n"
        "IMPORTANT: You never receive raw personal data — only statistical metadata "
        "and small value samples for type-compatibility analysis.\n\n"
        "Rules:\n"
        "1. Detect values that cannot be cast to the target type "
        "(e.g., text in DATE columns, letters in INTEGER columns).\n"
        "2. Detect encoding issues (e.g., non-UTF8 characters for TEXT columns).\n"
        "3. Detect values that exceed the target type's range or length.\n"
        "4. For each issue, provide a concrete suggested_fix SQL expression or "
        "migration step.\n"
        "5. If no issues are found, return an empty issues list and is_clean=true.\n"
        "6. You MUST respond with valid JSON — no markdown.\n\n"
        "JSON schema:\n"
        + json.dumps(
            {
                "type": "object",
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "table": {"type": "string"},
                                "column": {"type": "string"},
                                "issue_type": {"type": "string"},
                                "description": {"type": "string"},
                                "suggested_fix": {"type": "string"},
                            },
                            "required": [
                                "table",
                                "column",
                                "issue_type",
                                "description",
                                "suggested_fix",
                            ],
                        },
                    },
                    "is_clean": {"type": "boolean"},
                },
                "required": ["issues", "is_clean"],
            },
            indent=2,
        )
    )

    user = (
        f"Analyze the following column statistics from a source database "
        f"being migrated to {target_dialect}. Detect any data that is "
        f"incompatible with the mapped target types.\n\n"
        f"Column statistics:\n{stats_payload}\n\n"
        f"Target dialect: {target_dialect}\n\n"
        "Respond with a JSON object matching the schema provided."
    )

    return system, user


def _schema_to_readable_ddl(schema: list[TableSchema]) -> str:
    """Convert a list of TableSchema into a human-readable DDL representation.

    Used as input for AI prompts — provides table and column definitions
    in a compact, parseable format.

    Args:
        schema: List of TableSchema objects.

    Returns:
        Formatted DDL string.
    """
    lines: list[str] = []
    for table in schema:
        lines.append(f"TABLE {table.name} (")
        for col in table.columns:
            parts = [f"  {col.name}", col.type]
            if not col.nullable:
                parts.append("NOT NULL")
            if col.is_primary_key:
                parts.append("PRIMARY KEY")
            if col.default is not None:
                parts.append(f"DEFAULT {col.default}")
            lines.append("  " + " ".join(parts) + ",")
        lines.append(")")
        lines.append("")
    return "\n".join(lines)
