from __future__ import annotations

from collections.abc import Callable

from src.constants import DEFAULT_BATCH_SIZE
from src.databases.idatabase import IDatabase, Row
from src.engine.integrity_audit import IntegrityAuditReport, run_integrity_audit
from src.engine.kpi_tracker import KPITracker
from src.services.models import ColumnMapping, SchemaMapping, TableMapping


class MigrationError(Exception):
    pass


class MigrationEngine:
    """Main orchestrator that executes the async migration pipeline.

    Receives an approved schema mapping, streams data from source,
    applies column transforms, and bulk-inserts into the target.
    """

    def __init__(
        self,
        source: IDatabase,
        target: IDatabase,
        mapping: SchemaMapping,
        batch_size: int = DEFAULT_BATCH_SIZE,
        on_progress: Callable[[KPITracker], None] | None = None,
    ) -> None:
        self._source = source
        self._target = target
        self._mapping = mapping
        self._batch_size = batch_size
        self._kpi = KPITracker()
        self._on_progress = on_progress

    @property
    def kpi(self) -> KPITracker:
        return self._kpi

    async def run(self) -> IntegrityAuditReport:
        """Execute the full migration pipeline.

        Steps:
        1. Estimate total rows from source
        2. Disable constraints on target
        3. Create target tables from mapping DDL
        4. Stream, transform, and insert data per table
        5. Enable constraints on target
        6. Run integrity audit
        """
        table_names = [t.source_table for t in self._mapping.tables]
        self._kpi.total_rows = await self._estimate_total_rows(table_names)

        try:
            self._kpi.start()
            await self._target.disable_constraints()
            await self._create_target_tables()
            await self._migrate_data()
            await self._target.enable_constraints()
        except Exception as exc:
            try:
                await self._target.enable_constraints()
            except Exception:
                import logging

                logging.getLogger(__name__).warning(
                    "Failed to re-enable constraints after error", exc_info=True
                )
            raise MigrationError(f"Migration failed: {exc}") from exc
        finally:
            self._kpi.stop()

        return await run_integrity_audit(self._source, self._target, table_names)

    async def _estimate_total_rows(self, table_names: list[str]) -> int:
        total = 0
        for table in table_names:
            total += await self._source.get_row_count(table)
        return total

    async def _create_target_tables(self) -> None:
        ddl = self._mapping.to_ddl()
        if not ddl:
            return
        await self._target.execute_ddl(ddl)

    async def _migrate_data(self) -> None:
        for table_mapping in self._mapping.tables:
            await self._migrate_table(table_mapping)

    async def _migrate_table(self, table_mapping: TableMapping) -> None:
        source_table = table_mapping.source_table
        target_table = table_mapping.target_table
        column_map = {col.source_name: col for col in table_mapping.columns}

        async for batch in self._source.stream_data(source_table, self._batch_size):
            transformed = self._transform_batch(batch, target_table, column_map)
            await self._target.bulk_insert(target_table, transformed)

            byte_size = sum(len(str(r.values).encode("utf-8")) for r in transformed)
            self._kpi.add_rows(len(transformed), byte_size)

            if self._on_progress:
                self._on_progress(self._kpi)

    @staticmethod
    def _transform_batch(
        batch: list[Row],
        target_table: str,
        column_map: dict[str, ColumnMapping],
    ) -> list[Row]:

        transformed: list[Row] = []
        for row in batch:
            new_values: dict[str, object] = {}
            for source_name, value in row.values.items():
                col = column_map.get(source_name)
                if col is None:
                    continue
                target_name = col.target_name
                if col.transform and value is not None:
                    new_values[target_name] = _apply_transform(value, col.transform)
                else:
                    new_values[target_name] = value
            transformed.append(Row(table=target_table, values=new_values))
        return transformed


def _apply_transform(value: object, transform_expr: str) -> object:
    """Apply a simple transform expression to a value.

    Supports CAST-style expressions like 'CAST(value AS INTEGER)'.
    The word 'value' is replaced with the actual value.
    For non-CAST transforms, returns the original value (actual SQL
    transforms happen at the DB level during DDL execution).
    """
    expr = transform_expr.strip()
    upper = expr.upper()
    if upper.startswith("CAST("):
        try:
            type_part = upper.rsplit("AS", 1)[-1].rstrip(")").strip()
            if type_part in ("INTEGER", "INT", "BIGINT", "SMALLINT"):
                return int(value)
            if type_part in (
                "REAL",
                "FLOAT",
                "DOUBLE",
                "DOUBLE PRECISION",
                "NUMERIC",
                "DECIMAL",
            ):
                return float(value)
            if type_part in ("TEXT", "VARCHAR", "CHAR", "VARCHAR(255)"):
                return str(value)
        except (ValueError, TypeError):
            return value
    return value
