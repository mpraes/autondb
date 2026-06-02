from __future__ import annotations

from collections.abc import AsyncIterator

import aiosqlite

from src.constants import DEFAULT_BATCH_SIZE
from src.databases.identifier import validate_identifier
from src.databases.idatabase import ColumnSchema, IDatabase, Row, TableSchema

_SQLITE_TYPE_MAP: dict[str, str] = {
    "INTEGER": "INTEGER",
    "TEXT": "TEXT",
    "REAL": "REAL",
    "BLOB": "BLOB",
    "NUMERIC": "NUMERIC",
}


class SQLiteDB(IDatabase):
    """Async SQLite connector using aiosqlite.

    Designed for source and target operations. SQLite does not support
    disabling/enabling FK constraints dynamically, so those remain no-ops.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteDB: not connected. Call connect() first.")
        return self._conn

    async def get_schema(self) -> list[TableSchema]:
        conn = self._require_conn()

        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row["name"] for row in await cursor.fetchall()]

        result: list[TableSchema] = []
        for table_name in tables:
            validate_identifier(table_name)
            cursor = await conn.execute(f'PRAGMA table_info("{table_name}")')
            columns_raw = await cursor.fetchall()
            columns: list[ColumnSchema] = []
            for col in columns_raw:
                columns.append(
                    ColumnSchema(
                        name=col["name"],
                        type=_SQLITE_TYPE_MAP.get(
                            col["type"].upper(), col["type"].upper()
                        ),
                        nullable=col["notnull"] == 0,
                        default=col["dflt_value"],
                        is_primary_key=col["pk"] > 0,
                    )
                )
            result.append(TableSchema(name=table_name, columns=columns))
        return result

    async def stream_data(
        self, table: str, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> AsyncIterator[list[Row]]:
        conn = self._require_conn()
        validate_identifier(table)

        cursor = await conn.execute(f'SELECT * FROM "{table}"')
        batch: list[Row] = []
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                batch.append(Row(table=table, values=dict(row)))
            yield batch
            batch = []

    async def bulk_insert(self, table: str, rows: list[Row]) -> None:
        conn = self._require_conn()
        validate_identifier(table)

        if not rows:
            return

        columns = list(rows[0].values.keys())
        for c in columns:
            validate_identifier(c)
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(f'"{c}"' for c in columns)
        sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'

        values = [tuple(r.values[c] for c in columns) for r in rows]
        await conn.executemany(sql, values)
        await conn.commit()

    async def execute_ddl(self, ddl: str) -> None:
        conn = self._require_conn()

        for stmt in ddl.split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(stmt)
        await conn.commit()

    async def get_row_count(self, table: str) -> int:
        conn = self._require_conn()
        validate_identifier(table)

        cursor = await conn.execute(f'SELECT COUNT(*) FROM "{table}"')
        row = await cursor.fetchone()
        return row[0] if row else 0
