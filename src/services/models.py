"""Pydantic models for AI service requests and responses.

Defines the structured data types used for schema mapping,
pre-flight sanitization, and data quality reporting.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.constants import DEFAULT_TARGET_DIALECT


class ColumnMapping(BaseModel):
    """Mapping of a single column from source to target, including optional transform."""

    source_name: str
    source_type: str
    target_name: str
    target_type: str
    nullable: bool = True
    is_primary_key: bool = False
    default: str | None = None
    transform: str | None = Field(
        default=None,
        description="Optional transformation expression (e.g. 'CAST(value AS INTEGER)')",
    )


class TableMapping(BaseModel):
    """Mapping of a single table with all its column mappings."""

    source_table: str
    target_table: str
    columns: list[ColumnMapping]


class SchemaMapping(BaseModel):
    """Full schema mapping result from AI, including all tables and warnings."""

    tables: list[TableMapping]
    warnings: list[str] = Field(default_factory=list)
    target_dialect: str = DEFAULT_TARGET_DIALECT

    def to_ddl(self) -> str:
        """Generate CREATE TABLE DDL statements for the target database.

        Produces one CREATE TABLE per mapped table with column definitions,
        NOT NULL constraints, DEFAULT values, and PRIMARY KEY declarations.

        Returns:
            DDL string with statements separated by blank lines.
        """
        statements: list[str] = []
        for table in self.tables:
            col_defs: list[str] = []
            pk_cols: list[str] = []
            for col in table.columns:
                parts = [f'"{col.target_name}"', col.target_type]
                if not col.nullable:
                    parts.append("NOT NULL")
                if col.default is not None:
                    parts.append(f"DEFAULT {col.default}")
                col_defs.append("  " + " ".join(parts))
                if col.is_primary_key:
                    pk_cols.append(f'"{col.target_name}"')
            if pk_cols:
                col_defs.append("  PRIMARY KEY (" + ", ".join(pk_cols) + ")")
            stmt = (
                f'CREATE TABLE "{table.target_table}" (\n'
                + ",\n".join(col_defs)
                + "\n);"
            )
            statements.append(stmt)
        return "\n\n".join(statements)


class ColumnStats(BaseModel):
    """Statistical metadata about a source column for pre-flight sanitization."""

    table: str
    column: str
    target_type: str
    sample_values: list[str]
    null_count: int
    total_rows: int
    distinct_count: int | None = None


class DataIssue(BaseModel):
    """A single data quality issue detected during pre-flight sanitization."""

    table: str
    column: str
    issue_type: str
    description: str
    suggested_fix: str


class SanitizationReport(BaseModel):
    """Result of the pre-flight data sanitization check."""

    issues: list[DataIssue] = Field(default_factory=list)
    is_clean: bool = True
