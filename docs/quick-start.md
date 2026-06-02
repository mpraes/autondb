# Quick Start

AutonDB can be used in three ways — all share the same core engine.

## 1. Standalone CLI

```bash
# Install deps
uv sync

# Run a migration
uv run src/main.py \
  --source-dsn ./old.db \
  --source-dialect sqlite \
  --target-dsn "postgres://user:pass@localhost/newdb" \
  --target-dialect postgresql \
  --ai-provider openai \
  --auto-approve
```

The CLI will:

1. Read the source schema
2. Ask your AI provider to map types to the target dialect
3. Print the mapping + generated DDL for review
4. Prompt for approval (or skip with `--auto-approve`)
5. Stream data with real-time KPIs
6. Run a post-migration integrity audit

### CLI flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--source-dsn` | Yes | — | Source connection string or file path |
| `--source-dialect` | Yes | — | `sqlite`, `postgresql`, or `mysql` |
| `--target-dsn` | Yes | — | Target connection string or file path |
| `--target-dialect` | Yes | — | `sqlite`, `postgresql`, or `mysql` |
| `--ai-provider` | No | env | `openai`, `groq`, `openrouter`, `anthropic`, `synthetic` |
| `--ai-model` | No | env | Model name (e.g. `gpt-4o`, `claude-sonnet-4-20250514`) |
| `--batch-size` | No | 1000 | Rows per batch during streaming |
| `--auto-approve` | No | false | Skip approval prompt |

Or via Make:

```bash
make run-migrate SOURCE_DSN=./old.db SOURCE_DIALECT=sqlite TARGET_DSN="postgres://user:pass@localhost/newdb" TARGET_DIALECT=postgresql
# Optional: EXTRA_ARGS="--auto-approve --batch-size 500"
```

## 2. Desktop App (Tauri)

A native desktop app with a visual 3-step wizard: **Configure → Preview → Migrate**.

- **Config screen** — paste connection strings, pick AI provider, enter API key
- **Preview screen** — visual table-by-table mapping with types, transforms, warnings, and DDL
- **Dashboard** — real-time KPI gauges (rows/s, MB/s, ETA), progress bar, integrity report

Download the installer from [GitHub Releases](https://github.com/renan/autondb/releases).

## 3. Python Library

Use the engine directly in your own code:

```python
import asyncio
from src.databases.sqlite_db import SQLiteDB
from src.databases.postgres_db import PostgresDB
from src.engine.migration import MigrationEngine
from src.services.ai_service import AIService
from src.services.models import SchemaMapping, TableMapping, ColumnMapping

async def migrate():
    source = SQLiteDB("./source.db")
    target = PostgresDB("postgres://user:pass@localhost/target")
    await source.connect()
    await target.connect()

    ai = AIService.from_env(provider_name="openai", model="gpt-4o")
    schema = await source.get_schema()
    mapping = await ai.map_schema(schema, "sqlite", "postgresql")

    engine = MigrationEngine(
        source=source,
        target=target,
        mapping=mapping,
        batch_size=2000,
        on_progress=lambda kpi: print(kpi.format_snapshot()),
    )
    report = await engine.run()
    print(report.summary())

    await source.disconnect()
    await target.disconnect()

asyncio.run(migrate())
```
