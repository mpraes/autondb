from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from src.databases.idatabase import ColumnSchema, IDatabase, Row, TableSchema
from src.engine.integrity_audit import (
    IntegrityAuditReport,
    TableAuditResult,
    run_integrity_audit,
)
from src.engine.kpi_tracker import KPISnapshot, KPITracker
from src.engine.migration import MigrationEngine, MigrationError, _apply_transform
from src.services.models import ColumnMapping, SchemaMapping, TableMapping


class InMemoryDB(IDatabase):
    """In-memory database for testing, no real DB required."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = tables or {}
        self._connected: bool = False
        self._constraints_disabled: bool = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def get_schema(self) -> list[TableSchema]:
        self._assert_connected()
        result: list[TableSchema] = []
        for table_name, rows in self._tables.items():
            if not rows:
                continue
            columns = [
                ColumnSchema(name=col, type="TEXT")
                for col in rows[0]
            ]
            result.append(TableSchema(name=table_name, columns=columns))
        return result

    async def stream_data(
        self, table: str, batch_size: int = 1000
    ) -> AsyncIterator[list[Row]]:
        self._assert_connected()
        rows = self._tables.get(table, [])
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            yield [Row(table=table, values=dict(r)) for r in batch]

    async def bulk_insert(self, table: str, rows: list[Row]) -> None:
        self._assert_connected()
        if table not in self._tables:
            self._tables[table] = []
        for r in rows:
            self._tables[table].append(dict(r.values))

    async def get_row_count(self, table: str) -> int:
        self._assert_connected()
        return len(self._tables.get(table, []))

    async def execute_ddl(self, ddl: str) -> None:
        self._assert_connected()

    async def disable_constraints(self) -> None:
        self._assert_connected()
        self._constraints_disabled = True

    async def enable_constraints(self) -> None:
        self._assert_connected()
        self._constraints_disabled = False

    def _assert_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("InMemoryDB: not connected")


class TestKPITracker:
    def test_initial_state(self) -> None:
        kpi = KPITracker()
        assert kpi.rows_processed == 0
        assert kpi.bytes_processed == 0
        assert kpi.total_rows is None
        assert not kpi.is_running

    def test_add_rows(self) -> None:
        kpi = KPITracker()
        kpi.add_rows(100, byte_size=500)
        assert kpi.rows_processed == 100
        assert kpi.bytes_processed == 500
        kpi.add_rows(50, byte_size=250)
        assert kpi.rows_processed == 150
        assert kpi.bytes_processed == 750

    def test_start_stop(self) -> None:
        kpi = KPITracker()
        kpi.start()
        assert kpi.is_running
        kpi.stop()
        assert not kpi.is_running

    def test_snapshot_before_start(self) -> None:
        kpi = KPITracker()
        snap = kpi.snapshot()
        assert snap.rows_processed == 0
        assert snap.elapsed_seconds == 0.0
        assert snap.rows_per_second == 0.0
        assert snap.eta_seconds is None

    def test_snapshot_with_progress(self) -> None:
        kpi = KPITracker(total_rows=1000)
        kpi.start()
        kpi.add_rows(500)
        snap = kpi.snapshot()
        assert snap.rows_processed == 500
        assert snap.elapsed_seconds > 0
        assert snap.rows_per_second > 0
        assert snap.eta_seconds is not None
        kpi.stop()

    def test_snapshot_eta_none_when_no_total(self) -> None:
        kpi = KPITracker()
        kpi.start()
        kpi.add_rows(100)
        snap = kpi.snapshot()
        assert snap.eta_seconds is None
        kpi.stop()

    def test_snapshot_eta_none_when_completed(self) -> None:
        kpi = KPITracker(total_rows=100)
        kpi.start()
        kpi.add_rows(100)
        snap = kpi.snapshot()
        assert snap.eta_seconds is None
        kpi.stop()

    def test_format_snapshot(self) -> None:
        kpi = KPITracker(total_rows=1000)
        kpi.start()
        kpi.add_rows(500)
        text = kpi.format_snapshot()
        assert "500 rows" in text
        kpi.stop()

    def test_format_snapshot_no_elapsed(self) -> None:
        kpi = KPITracker()
        kpi.add_rows(10)
        text = kpi.format_snapshot()
        assert "10 rows" in text

    def test_total_rows_setter(self) -> None:
        kpi = KPITracker()
        assert kpi.total_rows is None
        kpi.total_rows = 500
        assert kpi.total_rows == 500


class TestIntegrityAudit:
    @pytest.mark.asyncio
    async def test_all_match(self) -> None:
        source = InMemoryDB({"users": [{"id": 1}, {"id": 2}], "orders": [{"id": 1}]})
        target = InMemoryDB({"users": [{"id": 1}, {"id": 2}], "orders": [{"id": 1}]})
        await source.connect()
        await target.connect()

        report = await run_integrity_audit(source, target, ["users", "orders"])
        assert report.all_match is True
        assert len(report.table_results) == 2
        assert report.total_source_rows == 3
        assert report.total_target_rows == 3
        assert len(report.mismatched_tables) == 0

        await source.disconnect()
        await target.disconnect()

    @pytest.mark.asyncio
    async def test_mismatch(self) -> None:
        source = InMemoryDB({"users": [{"id": 1}, {"id": 2}]})
        target = InMemoryDB({"users": [{"id": 1}]})
        await source.connect()
        await target.connect()

        report = await run_integrity_audit(source, target, ["users"])
        assert report.all_match is False
        assert len(report.mismatched_tables) == 1
        assert report.mismatched_tables[0].discrepancy == 1

        await source.disconnect()
        await target.disconnect()

    def test_table_audit_result(self) -> None:
        r = TableAuditResult(table="test", source_count=10, target_count=10, match=True)
        assert r.discrepancy == 0

        r2 = TableAuditResult(table="test", source_count=10, target_count=8, match=False)
        assert r2.discrepancy == 2

    def test_report_summary_pass(self) -> None:
        report = IntegrityAuditReport(
            table_results=[
                TableAuditResult("a", 10, 10, True),
                TableAuditResult("b", 20, 20, True),
            ],
            all_match=True,
        )
        summary = report.summary()
        assert "PASS" in summary
        assert "a" in summary
        assert "b" in summary

    def test_report_summary_fail(self) -> None:
        report = IntegrityAuditReport(
            table_results=[
                TableAuditResult("a", 10, 10, True),
                TableAuditResult("b", 20, 18, False),
            ],
            all_match=False,
        )
        summary = report.summary()
        assert "FAIL" in summary
        assert "Mismatched tables: 1" in summary
        assert "Total discrepancy: 2" in summary


class TestMigrationEngine:
    @pytest.fixture
    def sample_mapping(self) -> SchemaMapping:
        return SchemaMapping(
            tables=[
                TableMapping(
                    source_table="users",
                    target_table="users",
                    columns=[
                        ColumnMapping(
                            source_name="id",
                            source_type="INTEGER",
                            target_name="id",
                            target_type="INTEGER",
                            nullable=False,
                            is_primary_key=True,
                        ),
                        ColumnMapping(
                            source_name="name",
                            source_type="TEXT",
                            target_name="name",
                            target_type="VARCHAR(255)",
                        ),
                    ],
                )
            ],
            target_dialect="sqlite",
        )

    @pytest.mark.asyncio
    async def test_full_migration(self, sample_mapping: SchemaMapping) -> None:
        source = InMemoryDB({
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Carol"},
            ]
        })
        target = InMemoryDB()
        await source.connect()
        await target.connect()

        engine = MigrationEngine(
            source=source,
            target=target,
            mapping=sample_mapping,
            batch_size=2,
        )

        report = await engine.run()

        assert report.all_match is True
        assert len(target._tables["users"]) == 3
        assert target._constraints_disabled is False

        await source.disconnect()
        await target.disconnect()

    @pytest.mark.asyncio
    async def test_kpi_tracking(self, sample_mapping: SchemaMapping) -> None:
        source = InMemoryDB({
            "users": [{"id": i, "name": f"user_{i}"} for i in range(5)]
        })
        target = InMemoryDB()
        await source.connect()
        await target.connect()

        progress_calls: list[str] = []

        engine = MigrationEngine(
            source=source,
            target=target,
            mapping=sample_mapping,
            batch_size=2,
            on_progress=lambda kpi: progress_calls.append(kpi.format_snapshot()),
        )

        await engine.run()

        assert engine.kpi.rows_processed == 5
        assert len(progress_calls) > 0
        assert not engine.kpi.is_running

        await source.disconnect()
        await target.disconnect()

    @pytest.mark.asyncio
    async def test_constraints_re_enabled_on_error(self, sample_mapping: SchemaMapping) -> None:
        source = InMemoryDB({"users": [{"id": 1, "name": "Alice"}]})
        target = InMemoryDB()
        await source.connect()
        await target.connect()

        original_bulk_insert = target.bulk_insert

        async def failing_bulk_insert(table: str, rows: list[Row]) -> None:
            raise RuntimeError("insert failed")

        target.bulk_insert = failing_bulk_insert

        engine = MigrationEngine(source=source, target=target, mapping=sample_mapping)

        with pytest.raises(MigrationError):
            await engine.run()

        assert target._constraints_disabled is False

        await source.disconnect()
        await target.disconnect()

    @pytest.mark.asyncio
    async def test_transform_batch(self) -> None:
        rows = [
            Row(table="t", values={"id": "1", "name": "Alice"}),
            Row(table="t", values={"id": "2", "name": "Bob"}),
        ]
        column_map = {
            "id": ColumnMapping(
                source_name="id",
                source_type="TEXT",
                target_name="id",
                target_type="INTEGER",
                transform="CAST(value AS INTEGER)",
            ),
            "name": ColumnMapping(
                source_name="name",
                source_type="TEXT",
                target_name="name",
                target_type="VARCHAR(255)",
            ),
        }
        result = MigrationEngine._transform_batch(rows, "users", column_map)
        assert result[0].values["id"] == 1
        assert result[0].values["name"] == "Alice"
        assert result[1].values["id"] == 2

    @pytest.mark.asyncio
    async def test_empty_source(self, sample_mapping: SchemaMapping) -> None:
        source = InMemoryDB({"users": []})
        target = InMemoryDB()
        await source.connect()
        await target.connect()

        engine = MigrationEngine(source=source, target=target, mapping=sample_mapping)
        report = await engine.run()

        assert report.all_match is True
        assert engine.kpi.rows_processed == 0

        await source.disconnect()
        await target.disconnect()


class TestApplyTransform:
    def test_cast_integer(self) -> None:
        assert _apply_transform("42", "CAST(value AS INTEGER)") == 42

    def test_cast_float(self) -> None:
        assert _apply_transform("3.14", "CAST(value AS REAL)") == 3.14

    def test_cast_text(self) -> None:
        assert _apply_transform(42, "CAST(value AS TEXT)") == "42"

    def test_invalid_cast_returns_original(self) -> None:
        assert _apply_transform("not_a_number", "CAST(value AS INTEGER)") == "not_a_number"

    def test_non_cast_returns_original(self) -> None:
        assert _apply_transform("hello", "UPPER(value)") == "hello"

    def test_none_value_returns_none(self) -> None:
        assert _apply_transform(None, "CAST(value AS INTEGER)") is None
