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
        """Open an async SQLite connection and set Row as the row factory."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

    async def disconnect(self) -> None:
        """Close the SQLite connection if active."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _require_conn(self) -> aiosqlite.Connection:
        """Return the active connection or raise RuntimeError if not connected."""
        if self._conn is None:
            raise RuntimeError("SQLiteDB: not connected. Call connect() first.")
        return self._conn

    async def get_schema(self) -> list[TableSchema]:
        """Read all non-system tables and their columns from SQLite metadata.

        Uses sqlite_master and PRAGMA table_info to build TableSchema objects.

        Returns:
            List of TableSchema for each user table.
        """
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
        """Yield batches of rows from the given SQLite table.

        Args:
            table: Table name to read from.
            batch_size: Number of rows per yielded batch.

        Yields:
            Lists of Row objects, each containing column name-value pairs.
        """
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
        """Insert a batch of rows into a SQLite table using executemany.

        Args:
            table: Target table name.
            rows: List of Row objects to insert.
        """
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
        """Execute DDL statements split on semicolons."""
        conn = self._require_conn()

        for stmt in ddl.split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(stmt)
        await conn.commit()

    async def get_row_count(self, table: str) -> int:
        """Return the total row count for a SQLite table."""
        conn = self._require_conn()
        validate_identifier(table)

        cursor = await conn.execute(f'SELECT COUNT(*) FROM "{table}"')
        row = await cursor.fetchone()
        return row[0] if row else 0
