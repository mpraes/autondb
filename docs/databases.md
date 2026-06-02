# Supported Databases

AutonDB supports PostgreSQL, MySQL, and SQLite as both source and target.

| Database | Driver | Bulk strategy | Constraints toggle |
|----------|--------|--------------|--------------------|
| SQLite | `aiosqlite` | Batch INSERT + `executemany` | Not supported (no-op) |
| PostgreSQL | `asyncpg` | `copy_records_to_table` | `session_replication_role` |
| MySQL | `aiomysql` | Batch `executemany` | `FOREIGN_KEY_CHECKS` |

## IDatabase Interface

All connectors implement the `IDatabase` abstract base (`src/databases/idatabase.py`):

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection or pool |
| `disconnect()` | Close connection or pool |
| `get_schema()` | Return list of `TableSchema` (DDL metadata) |
| `stream_data(table, batch_size)` | Async iterator yielding row batches |
| `bulk_insert(table, columns, rows)` | Insert a batch of rows |
| `execute_ddl(ddl)` | Execute a DDL statement (CREATE TABLE, etc.) |
| `get_row_count(table)` | Return total row count for a table |
| `disable_constraints()` | Disable FK constraints for bulk insert speed |
| `enable_constraints()` | Re-enable FK constraints after migration |

### Additional methods

- **`PostgresDB.copy_to_table()`** — high-performance COPY protocol, available but not yet wired into MigrationEngine (currently uses `bulk_insert`)

## Per-Database Details

### SQLite (`sqlite_db.py`)

- File-based — no connection string parsing, just a file path
- No constraint toggling (no-op for `disable_constraints` / `enable_constraints`)
- Uses `aiosqlite` for async I/O

### PostgreSQL (`postgres_db.py`)

- Connection string format: `postgres://user:pass@host:port/dbname`
- Constraint toggling via `SET session_replication_role = 'replica'` / `RESET`
- `copy_records_to_table` available for maximum bulk throughput (not yet used by engine)
- Uses `asyncpg` connection pool

### MySQL (`mysql_db.py`)

- Connection string format: `mysql://user:pass@host:port/dbname`
- Constraint toggling via `SET FOREIGN_KEY_CHECKS = 0` / `1`
- No native COPY equivalent — `aiomysql` batch inserts are the performance path
- Uses `aiomysql` connection pool
