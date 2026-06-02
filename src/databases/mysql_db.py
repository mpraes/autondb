from __future__ import annotations

from collections.abc import AsyncIterator

import aiomysql

from src.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_POOL_MIN_SIZE,
    DEFAULT_POOL_MAX_SIZE,
)
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


def _validate_identifier(name: str) -> str:
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Invalid SQL identifier: '{name}'")
    return name


class MySQLDB(IDatabase):
    """Async MySQL connector using aiomysql.

    Supports constraint toggling (disable/enable FK checks) and
    optimized batch inserts.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        self._pool = await aiomysql.create_pool(
            self._dsn,
            minsize=DEFAULT_POOL_MIN_SIZE,
            maxsize=DEFAULT_POOL_MAX_SIZE,
            autocommit=True,
        )

    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    def _require_pool(self) -> aiomysql.Pool:
        if self._pool is None:
            raise RuntimeError("MySQLDB: not connected. Call connect() first.")
        return self._pool

    async def get_schema(self) -> list[TableSchema]:
        pool = self._require_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
                )
                tables = [row[0] for row in await cur.fetchall()]

            result: list[TableSchema] = []
            for table_name in tables:
                _validate_identifier(table_name)
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
        self, table: str, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> AsyncIterator[list[Row]]:
        pool = self._require_pool()
        _validate_identifier(table)

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(f"SELECT * FROM `{table}`")
                while True:
                    rows = await cur.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [Row(table=table, values=dict(r)) for r in rows]

    async def bulk_insert(self, table: str, rows: list[Row]) -> None:
        pool = self._require_pool()
        _validate_identifier(table)

        if not rows:
            return

        columns = list(rows[0].values.keys())
        for c in columns:
            _validate_identifier(c)
        col_names = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join("%s" for _ in columns)
        sql = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"

        values = [tuple(r.values[c] for c in columns) for r in rows]

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(sql, values)

    async def execute_ddl(self, ddl: str) -> None:
        pool = self._require_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                for stmt in ddl.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await cur.execute(stmt)

    async def get_row_count(self, table: str) -> int:
        pool = self._require_pool()
        _validate_identifier(table)

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                row = await cur.fetchone()
                return row[0] if row else 0

    async def disable_constraints(self) -> None:
        pool = self._require_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET FOREIGN_KEY_CHECKS = 0")

    async def enable_constraints(self) -> None:
        pool = self._require_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET FOREIGN_KEY_CHECKS = 1")
