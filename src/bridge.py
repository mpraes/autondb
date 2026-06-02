"""AutonDB Tauri Bridge — JSON-over-stdout protocol for Tauri sidecar.

Usage:
    python -m src.bridge analyze <config_json>
    python -m src.bridge migrate <config_json> <mapping_json>

Outputs one JSON event per line to stdout. The Tauri Rust backend reads
these events and emits them as Tauri events to the frontend.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from src.databases.idatabase import IDatabase
from src.databases.mysql_db import MySQLDB
from src.databases.postgres_db import PostgresDB
from src.databases.sqlite_db import SQLiteDB
from src.engine.migration import MigrationEngine
from src.services.ai_service import AIService
from src.services.models import SchemaMapping

_DIALECTS = {
    "sqlite": lambda dsn: SQLiteDB(dsn),
    "postgresql": lambda dsn: PostgresDB(dsn),
    "mysql": lambda dsn: MySQLDB(dsn),
}


def _emit(event_type: str, payload: Any) -> None:
    line = json.dumps({"event": event_type, "payload": payload}, default=str)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _build_db(dialect: str, dsn: str) -> IDatabase:
    factory = _DIALECTS.get(dialect)
    if factory is None:
        raise ValueError(f"Unsupported dialect: '{dialect}'")
    return factory(dsn)


async def analyze(config: dict) -> None:
    source = _build_db(config["source_dialect"], config["source_dsn"])
    target = _build_db(config["target_dialect"], config["target_dsn"])

    import os
    os.environ["AI_PROVIDER"] = config.get("ai_provider", "openai")
    if config.get("ai_key"):
        key_env = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_var = key_env.get(config["ai_provider"], "OPENAI_API_KEY")
        os.environ[env_var] = config["ai_key"]

    ai = AIService.from_env(
        provider_name=config.get("ai_provider"),
        model=config.get("ai_model"),
    )

    try:
        await source.connect()
        await target.connect()
        schema = await source.get_schema()
        mapping = await ai.map_schema(
            schema, config["source_dialect"], config["target_dialect"]
        )
        _emit("analyze_result", {
            "tables": [t.model_dump() for t in mapping.tables],
            "warnings": mapping.warnings,
            "target_dialect": mapping.target_dialect,
            "ddl": mapping.to_ddl(),
        })
    finally:
        await source.disconnect()
        await target.disconnect()


async def migrate(config: dict, mapping_data: dict) -> None:
    source = _build_db(config["source_dialect"], config["source_dsn"])
    target = _build_db(config["target_dialect"], config["target_dsn"])

    mapping = SchemaMapping.model_validate(mapping_data)

    def on_progress(kpi):
        snap = kpi.snapshot()
        _emit("migration_progress", {
            "rows_processed": snap.rows_processed,
            "bytes_processed": snap.bytes_processed,
            "elapsed_seconds": snap.elapsed_seconds,
            "rows_per_second": snap.rows_per_second,
            "mb_per_second": snap.mb_per_second,
            "eta_seconds": snap.eta_seconds,
            "total_rows": kpi.total_rows or 0,
        })

    engine = MigrationEngine(
        source=source,
        target=target,
        mapping=mapping,
        batch_size=config.get("batch_size", 1000),
        on_progress=on_progress,
    )

    try:
        await source.connect()
        await target.connect()
        report = await engine.run()
        _emit("migration_complete", {
            "all_match": report.all_match,
            "total_source_rows": report.total_source_rows,
            "total_target_rows": report.total_target_rows,
            "summary": report.summary(),
            "tables": [
                {
                    "table": r.table,
                    "source_count": r.source_count,
                    "target_count": r.target_count,
                    "match": r.match,
                }
                for r in report.table_results
            ],
        })
    except Exception as exc:
        _emit("migration_error", str(exc))
    finally:
        await source.disconnect()
        await target.disconnect()


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m src.bridge <analyze|migrate> <config_json>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    config = json.loads(sys.argv[2])

    if command == "analyze":
        asyncio.run(analyze(config))
    elif command == "migrate":
        mapping_data = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        asyncio.run(migrate(config, mapping_data))
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
