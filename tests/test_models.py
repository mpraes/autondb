from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.services.models import (
    ColumnMapping,
    ColumnStats,
    DataIssue,
    SanitizationReport,
    SchemaMapping,
    TableMapping,
)


class TestColumnMapping:
    def test_minimal_fields(self) -> None:
        m = ColumnMapping(
            source_name="id",
            source_type="INTEGER",
            target_name="id",
            target_type="SERIAL",
        )
        assert m.nullable is True
        assert m.is_primary_key is False
        assert m.default is None
        assert m.transform is None

    def test_full_fields(self) -> None:
        m = ColumnMapping(
            source_name="name",
            source_type="TEXT",
            target_name="name",
            target_type="VARCHAR(255)",
            nullable=False,
            is_primary_key=False,
            default="'unknown'",
            transform="CAST(name AS VARCHAR(255))",
        )
        assert m.nullable is False
        assert m.transform == "CAST(name AS VARCHAR(255))"


class TestTableMapping:
    def test_basic(self) -> None:
        t = TableMapping(
            source_table="users",
            target_table="users",
            columns=[
                ColumnMapping(
                    source_name="id",
                    source_type="INTEGER",
                    target_name="id",
                    target_type="SERIAL",
                    nullable=False,
                    is_primary_key=True,
                ),
            ],
        )
        assert len(t.columns) == 1
        assert t.columns[0].target_type == "SERIAL"


class TestSchemaMapping:
    def test_to_ddl_basic(self) -> None:
        mapping = SchemaMapping(
            tables=[
                TableMapping(
                    source_table="users",
                    target_table="users",
                    columns=[
                        ColumnMapping(
                            source_name="id",
                            source_type="INTEGER",
                            target_name="id",
                            target_type="SERIAL",
                            nullable=False,
                            is_primary_key=True,
                        ),
                        ColumnMapping(
                            source_name="email",
                            source_type="TEXT",
                            target_name="email",
                            target_type="VARCHAR(255)",
                            nullable=False,
                        ),
                    ],
                )
            ],
            warnings=["SQLite TEXT may contain heterogeneous types"],
            target_dialect="postgresql",
        )
        ddl = mapping.to_ddl()
        assert 'CREATE TABLE "users"' in ddl
        assert '"id" SERIAL' in ddl
        assert '"email" VARCHAR(255) NOT NULL' in ddl
        assert "PRIMARY KEY" in ddl

    def test_to_ddl_with_defaults(self) -> None:
        mapping = SchemaMapping(
            tables=[
                TableMapping(
                    source_table="orders",
                    target_table="orders",
                    columns=[
                        ColumnMapping(
                            source_name="status",
                            source_type="TEXT",
                            target_name="status",
                            target_type="VARCHAR(50)",
                            default="'pending'",
                        ),
                    ],
                )
            ],
        )
        ddl = mapping.to_ddl()
        assert "DEFAULT 'pending'" in ddl

    def test_empty_warnings(self) -> None:
        mapping = SchemaMapping(tables=[], warnings=[])
        assert mapping.warnings == []
        assert mapping.to_ddl() == ""


class TestColumnStats:
    def test_basic(self) -> None:
        s = ColumnStats(
            table="users",
            column="email",
            target_type="VARCHAR(255)",
            sample_values=["a@b.com", "c@d.com"],
            null_count=0,
            total_rows=100,
        )
        assert s.distinct_count is None

    def test_with_distinct(self) -> None:
        s = ColumnStats(
            table="users",
            column="role",
            target_type="VARCHAR(50)",
            sample_values=["admin", "user"],
            null_count=0,
            total_rows=50,
            distinct_count=2,
        )
        assert s.distinct_count == 2


class TestDataIssue:
    def test_basic(self) -> None:
        issue = DataIssue(
            table="orders",
            column="order_date",
            issue_type="type_mismatch",
            description="Contains text 'N/A' in date column",
            suggested_fix="UPDATE orders SET order_date = NULL WHERE order_date = 'N/A'",
        )
        assert issue.issue_type == "type_mismatch"


class TestSanitizationReport:
    def test_clean(self) -> None:
        report = SanitizationReport(issues=[], is_clean=True)
        assert report.is_clean is True
        assert len(report.issues) == 0

    def test_with_issues(self) -> None:
        report = SanitizationReport(
            issues=[
                DataIssue(
                    table="t",
                    column="c",
                    issue_type="type_mismatch",
                    description="bad data",
                    suggested_fix="fix it",
                )
            ],
            is_clean=False,
        )
        assert report.is_clean is False
        assert len(report.issues) == 1
