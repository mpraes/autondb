"""Database connector factory and dialect registry.

Centralizes the DIALECTS dict and build_db() function used by both
the CLI and the Tauri bridge to instantiate database connectors.
"""

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
"""Registry mapping dialect names to their constructor callables."""


def build_db(dialect: str, dsn: str) -> IDatabase:
    """Instantiate and return a database connector for the given dialect.

    Args:
        dialect: Database dialect ('sqlite', 'postgresql', or 'mysql').
        dsn: Connection string or file path for the database.

    Returns:
        An IDatabase instance for the specified dialect.

    Raises:
        ValueError: If the dialect is not supported.
    """
    factory = DIALECTS.get(dialect)
    if factory is None:
        raise ValueError(
            f"Unsupported dialect: '{dialect}'. "
            f"Supported: {', '.join(sorted(DIALECTS))}"
        )
    return factory(dsn)
