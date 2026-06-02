"""Databases package — connectors, factory, and identifier validation."""

from src.databases.factory import DIALECTS, build_db
from src.databases.identifier import validate_identifier
from src.databases.idatabase import ColumnSchema, IDatabase, Row, TableSchema
from src.databases.mysql_db import MySQLDB
from src.databases.postgres_db import PostgresDB
from src.databases.sqlite_db import SQLiteDB

__all__ = [
    "ColumnSchema",
    "DIALECTS",
    "IDatabase",
    "MySQLDB",
    "PostgresDB",
    "Row",
    "SQLiteDB",
    "TableSchema",
    "build_db",
    "validate_identifier",
]
