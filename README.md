# AutonDB

AI-assisted database migration tool for small/medium databases (PostgreSQL, MySQL, SQLite). It uses AI to perform smart schema mapping and pre-flight data sanitization, then executes high-speed async migrations with post-migration integrity auditing.

## Three Ways to Run

Pick the one that fits your workflow:

| Path | Best for | What you get |
|------|----------|--------------|
| **Standalone CLI** | Servers, CI/CD, scripting | Single Python entry point, no GUI |
| **Desktop App** | Everyday use, non-technical users | Native window with 3-step wizard |
| **Python Library** | Custom integrations, automation | Import `MigrationEngine` directly |

All three share the same compiled core binary — build it once, repackage everywhere.

## Quick Start

### 1. Standalone CLI

```bash
# Install
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

**CLI flags:**

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

### 2. Desktop App (Tauri)

A native desktop app with a visual 3-step wizard: **Configure → Preview → Migrate**.

```bash
# One-time: install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# One-time: install Linux system dependencies
./setup-linux.sh

# Build the Python sidecar binary (once per architecture)
./build-core.sh

# Run in dev mode
npx tauri dev

# Build production app
npx tauri build
```

The desktop app features:
- **Config screen** — paste connection strings, pick AI provider, enter API key
- **Preview screen** — visual table-by-table mapping with types, transforms, warnings, and DDL
- **Dashboard** — real-time KPI gauges (rows/s, MB/s, ETA), progress bar, integrity report

### 3. Python Library

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

## Build Philosophy: One Binary, Many Packages

The Python core is compiled **once per target architecture** into a standalone binary via PyInstaller. That same binary is then re-packaged into every distribution format:

```
autondb-core (PyInstaller)
  ├── used directly as CLI (standalone binary)
  ├── bundled as Tauri sidecar (desktop app)
  └── importable as Python module (library mode)
```

**Supported architectures:**

| Architecture | Binary name |
|-------------|-------------|
| Linux x86_64 | `autondb-core-x86_64-unknown-linux-gnu` |
| macOS Apple Silicon | `autondb-core-aarch64-apple-darwin` |
| macOS Intel | `autondb-core-x86_64-apple-darwin` |
| Windows x86_64 | `autondb-core-x86_64-pc-windows-msvc.exe` |

**Build the core binary:**

```bash
uv sync --group dev
uv run pyinstaller autondb-core.spec --noconfirm --clean
```

The output lands in `dist/autondb-core`. To bundle it for Tauri:

```bash
./build-core.sh
```

This compiles the binary and copies it to `src-tauri/binaries/` with the correct platform-specific name.

## AI Configuration

AutonDB never sends raw data to AI providers — only schema (DDL) and statistical metadata. Set your API key via environment variable or `.env` file:

```bash
# .env
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

**Supported providers:**

| Provider | Env var for key | Default model |
|----------|-----------------|---------------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| OpenRouter | `OPENROUTER_API_KEY` | `openai/gpt-4o` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Synthetic | — (no key needed) | — (mock for testing) |

## Supported Databases

| Database | Driver | Bulk strategy | Constraints toggle |
|----------|--------|--------------|--------------------|
| SQLite | `aiosqlite` | Batch INSERT + `executemany` | Not supported (no-op) |
| PostgreSQL | `asyncpg` | `copy_records_to_table` | `session_replication_role` |
| MySQL | `aiomysql` | Batch `executemany` | `FOREIGN_KEY_CHECKS` |

## Architecture

```
src/
├── main.py                  # CLI entry point
├── bridge.py                 # Tauri sidecar bridge (JSON-over-stdout)
├── engine/
│   ├── migration.py          # MigrationEngine — orchestrator
│   ├── kpi_tracker.py        # KPITracker — rows/s, MB/s, ETA
│   └── integrity_audit.py    # Post-migration COUNT audit
├── services/
│   ├── ai_service.py         # AIService — multi-provider orchestrator
│   ├── models.py             # Pydantic models
│   ├── prompts.py            # Prompt templates
│   └── providers/            # AI provider implementations
│       ├── openai_compat.py  # OpenAI, Groq, OpenRouter
│       ├── anthropic_provider.py
│       └── synthetic.py      # Mock for testing
└── databases/
    ├── idatabase.py          # IDatabase abstract base
    ├── sqlite_db.py
    ├── postgres_db.py
    └── mysql_db.py

src-tauri/                    # Tauri 2 desktop app (Rust)
ui/                           # Frontend (vanilla HTML/CSS/JS)
```

**Control flow:**

1. User provides source & target connection strings + AI config
2. Source DB streams schema → AI maps types to target dialect
3. AI samples metadata → validates compatibility (Pre-Flight Sanitizer)
4. User approves the mapping
5. MigrationEngine disables constraints, streams data, re-enables constraints
6. KPITracker reports rows/s, MB/s, ETA in real time
7. Integrity audit: COUNT per table, source vs target

## Development

```bash
# Install dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Run linter / type check (if configured)
# Build sidecar + desktop app
./build-core.sh && npx tauri dev
```

## Requirements

- **Python** 3.13+ (managed by `uv`)
- **Rust** 1.77+ (for Tauri desktop builds only)
- **Node.js** 18+ (for Tauri CLI only)
- **System libs** (Linux only): `libgtk-3-dev`, `libwebkit2gtk-4.1-dev`, `libdbus-1-dev`, `libappindicator3-dev` — run `./setup-linux.sh`

## License

MIT
