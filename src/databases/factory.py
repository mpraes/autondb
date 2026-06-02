from __future__ import annotations

from src.databases.idatabase import IDatabase
from src.databases.mysql_db import MySQLDB
from src.databases.postgres_db import PostgresDB
from src.databases.sqlite_db import SQLiteDB

DIALECTS = {
    "sqlite": lambda dsn: SQLiteDB(dsn),
    "postgresql": lambda dsn: PostgresDB(dsn),
    "mysql": lambda dsn: MySQLDB(dsn),
}


def build_db(dialect: str, dsn: str) -> IDatabase:
    factory = DIALECTS.get(dialect)
    if factory is None:
        raise ValueError(
            f"Unsupported dialect: '{dialect}'. "
            f"Supported: {', '.join(sorted(DIALECTS))}"
        )
    return factory(dsn)
