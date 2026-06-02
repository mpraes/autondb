from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import aiomysql

from src.databases.idatabase import ColumnSchema, IDatabase, Row, TableSchema

_MYSQL_TYPE_MAP: dict[str, str] = {
    "int": "INT",
    "bigint": "BIGINT",
    "tinyint": "TINYINT",
    "smallint": "SMALLINT",
    "mediumint": "MEDIUMINT",
    "float": "FLOAT",
    "double": "DOUBLE",
    "decimal": "DECIMAL",
    "varchar": "VARCHAR",
    "char": "CHAR",
    "text": "TEXT",
    "tinytext": "TINYTEXT",
    "mediumtext": "MEDIUMTEXT",
    "longtext": "LONGTEXT",
    "date": "DATE",
    "datetime": "DATETIME",
    "timestamp": "TIMESTAMP",
    "time": "TIME",
    "blob": "BLOB",
    "json": "JSON",
    "enum": "ENUM",
    "binary": "BINARY",
    "varbinary": "VARBINARY",
}


class MySQLDB(IDatabase):
    """Async MySQL connector using aiomysql.

    Supports constraint toggling (disable/enable FK checks) and
    optimized batch inserts.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        self._pool = await aiomysql.create_pool(self._dsn, minsize=2, maxsize=10, autocommit=True)

    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def get_schema(self) -> list[TableSchema]:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
                )
                tables = [row[0] for row in await cur.fetchall()]

            result: list[TableSchema] = []
            for table_name in tables:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                        "ORDER BY ORDINAL_POSITION",
                        (table_name,),
                    )
                    columns_raw = await cur.fetchall()

                columns: list[ColumnSchema] = []
                for col in columns_raw:
                    columns.append(
                        ColumnSchema(
                            name=col[0],
                            type=_MYSQL_TYPE_MAP.get(col[1], col[1].upper()),
                            nullable=col[2] == "YES",
                            default=col[3],
                            is_primary_key=col[4] == "PRI",
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
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(f'SELECT * FROM `{table}`')
                while True:
                    rows = await cur.fetchmany(batch_size)
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
        col_names = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join("%s" for _ in columns)
        sql = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"

        values = [tuple(r.values[c] for c in columns) for r in rows]

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(sql, values)

    async def execute_ddl(self, ddl: str) -> None:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                for stmt in ddl.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await cur.execute(stmt)

    async def get_row_count(self, table: str) -> int:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f'SELECT COUNT(*) FROM `{table}`')
                row = await cur.fetchone()
                return row[0] if row else 0

    async def disable_constraints(self) -> None:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET FOREIGN_KEY_CHECKS = 0")

    async def enable_constraints(self) -> None:
        self._assert_connected()
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    def _assert_connected(self) -> None:
        if self._pool is None:
            raise RuntimeError("MySQLDB: not connected. Call connect() first.")
