from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnSchema:
    name: str
    type: str
    nullable: bool = True
    default: str | None = None
    is_primary_key: bool = False


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: list[ColumnSchema]


@dataclass(frozen=True)
class Row:
    table: str
    values: dict[str, Any]


class IDatabase(ABC):
    """Abstract interface that all database connectors must implement.

    Defines the contract for connecting, reading schemas, streaming data,
    bulk inserting, and managing constraints during migration.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the database."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection and release resources."""

    @abstractmethod
    async def get_schema(self) -> list[TableSchema]:
        """Return the full schema of the database as a list of TableSchema."""

    @abstractmethod
    async def stream_data(self, table: str, batch_size: int = 1000) -> AsyncIterator[list[Row]]:
        """Yield batches of rows from the given table.

        Args:
            table: Name of the table to read.
            batch_size: Number of rows per batch.
        """

    @abstractmethod
    async def bulk_insert(self, table: str, rows: list[Row]) -> None:
        """Insert a batch of rows into the given table.

        Args:
            table: Target table name.
            rows: List of Row objects to insert.
        """

    @abstractmethod
    async def get_row_count(self, table: str) -> int:
        """Return the total row count for the given table."""

    async def disable_constraints(self) -> None:
        """Disable foreign keys and indexes on the target database.

        Default no-op — only some connectors support this (PostgreSQL, MySQL).
        """

    async def enable_constraints(self) -> None:
        """Re-enable foreign keys and indexes on the target database.

        Default no-op — only some connectors support this (PostgreSQL, MySQL).
        """
