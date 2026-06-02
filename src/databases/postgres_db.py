from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import asyncpg

from src.databases.idatabase import ColumnSchema, IDatabase, Row, TableSchema

_PG_TYPE_MAP: dict[str, str] = {
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "boolean": "BOOLEAN",
    "real": "FLOAT",
    "double precision": "DOUBLE PRECISION",
    "character varying": "VARCHAR",
    "character": "CHAR",
    "text": "TEXT",
    "date": "DATE",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMPTZ",
    "numeric": "NUMERIC",
    "bytea": "BYTEA",
    "uuid": "UUID",
    "json": "JSON",
    "jsonb": "JSONB",
    "serial": "SERIAL",
    "bigserial": "BIGSERIAL",
}


class PostgresDB(IDatabase):
    """Async PostgreSQL connector using asyncpg.

    Supports constraint toggling (disable/enable FKs) and high-performance
    copy_to_table for bulk data loading.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def get_schema(self) -> list[TableSchema]:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )

            result: list[TableSchema] = []
            for table_row in tables:
                table_name = table_row["table_name"]
                columns_raw = await conn.fetch(
                    "SELECT column_name, data_type, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = $1 "
                    "ORDER BY ordinal_position",
                    table_name,
                )
                pk_cols = await conn.fetch(
                    "SELECT a.attname "
                    "FROM pg_index i "
                    "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                    "WHERE i.indrelid = $1::regclass AND i.indisprimary",
                    f"public.{table_name}",
                )
                pk_names = {r["attname"] for r in pk_cols}

                columns: list[ColumnSchema] = []
                for col in columns_raw:
                    columns.append(
                        ColumnSchema(
                            name=col["column_name"],
                            type=_PG_TYPE_MAP.get(col["data_type"], col["data_type"].upper()),
                            nullable=col["is_nullable"] == "YES",
                            default=col["column_default"],
                            is_primary_key=col["column_name"] in pk_names,
                        )
                    )
                result.append(TableSchema(name=table_name, columns=columns))
            return result

    async def stream_data(
        self, table: str, batch_size: int = 1000
    ) -> AsyncIterator[list[Row]]:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            cursor = await conn.cursor(f'SELECT * FROM "{table}"')
            while True:
                rows = await cursor.fetch(batch_size)
                if not rows:
                    break
                yield [
                    Row(table=table, values=dict(r))
                    for r in rows
                ]

    async def bulk_insert(self, table: str, rows: list[Row]) -> None:
        self._assert_connected()
        assert self._pool is not None

        if not rows:
            return

        columns = list(rows[0].values.keys())
        col_names = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    sql,
                    [tuple(r.values[c] for c in columns) for r in rows],
                )

    async def execute_ddl(self, ddl: str) -> None:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            for stmt in ddl.split(";"):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(stmt)

    async def copy_to_table(self, table: str, columns: list[str], data: list[tuple[Any, ...]]) -> None:
        """High-performance bulk load using PostgreSQL COPY protocol.

        This is significantly faster than row-by-row INSERT for large datasets.

        Args:
            table: Target table name.
            columns: Column names in order.
            data: List of tuples matching column order.
        """
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            await conn.copy_records_to_table(
                table,
                records=data,
                columns=columns,
            )

    async def get_row_count(self, table: str) -> int:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(f'SELECT COUNT(*) AS cnt FROM "{table}"')
            return row["cnt"] if row else 0

    async def disable_constraints(self) -> None:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            await conn.execute("SET session_replication_role = 'replica'")

    async def enable_constraints(self) -> None:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            await conn.execute("SET session_replication_role = 'origin'")

    def _assert_connected(self) -> None:
        if self._pool is None:
            raise RuntimeError("PostgresDB: not connected. Call connect() first.")
