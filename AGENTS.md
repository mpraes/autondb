# AutonDB — Agent Guide

## What This Project Is

AutonDB is an AI-assisted database migration tool for small/medium databases (PostgreSQL, MySQL, SQLite). It uses OpenAI to perform smart schema mapping and pre-flight data sanitization, then executes high-speed async migrations with post-migration integrity auditing.

**Project language**: Python, Portuguese (backlog/docs are in Portuguese; code is in English).

## Current State

The project has completed **all 4 Epics** (DB connectors, AI brain, MigrationEngine, Tauri desktop). All stories in `docs/BACKLOG.md` are done. The app is ready for end-to-end testing.

## Essential Commands

- **Install/sync deps**: `uv sync` (uses `uv.lock`, managed by `uv`)
- **Install dev deps**: `uv sync --group dev`
- **Run CLI**: `uv run src/main.py --source-dsn ... --source-dialect ... --target-dsn ... --target-dialect ...`
- **Test**: `uv run pytest tests/ -v`
- **Build Python sidecar**: `./build-core.sh`
- **Run Tauri dev**: `npx tauri dev`
- **Build Tauri app**: `npx tauri build`
- **Linux setup (first time)**: `./setup-linux.sh`
- **Python version**: 3.13 (pinned in `.python-version`)

## Architecture (Planned)

```
src/
├── main.py                  # CLI entry point
├── bridge.py                 # Tauri sidecar bridge (JSON-over-stdout)
├── engine/
│   ├── __init__.py           # Package exports
│   ├── migration.py          # MigrationEngine — orchestrator
│   ├── kpi_tracker.py        # KPITracker — real-time rows/s, MB/s, ETA
│   └── integrity_audit.py    # Post-migration COUNT audit
├── services/
│   ├── __init__.py           # Package exports
│   ├── ai_service.py         # AIService — multi-provider orchestrator
│   ├── models.py             # Pydantic models (SchemaMapping, SanitizationReport, etc.)
│   ├── prompts.py            # Prompt templates for schema mapping & sanitization
│   └── providers/            # AI provider implementations
│       ├── __init__.py       # Provider factory + registry
│       ├── base.py           # AIProvider abstract base
│       ├── openai_compat.py  # OpenAI, Groq, OpenRouter (all OpenAI-compatible)
│       ├── anthropic_provider.py  # Anthropic Claude
│       └── synthetic.py      # Mock provider for testing
└── databases/               # Database connectors
    ├── __init__.py
    ├── idatabase.py         # IDatabase abstract base
    ├── sqlite_db.py         # SQLiteDB   (aiosqlite)
    ├── postgres_db.py       # PostgresDB (asyncpg)
    └── mysql_db.py          # MySQLDB    (aiomysql)

src-tauri/                    # Tauri 2 desktop app
├── Cargo.toml                # Rust deps (tauri, serde, dirs)
├── tauri.conf.json           # App config, sidecar binary path
├── src/
│   ├── main.rs               # Rust entry
│   └── lib.rs                # Tauri commands: analyze_schema, start_migration, download_audit_pdf
├── capabilities/default.json # Permission config
└── binaries/                 # PyInstaller sidecar (autondb-core)

ui/                           # Frontend (vanilla HTML/CSS/JS)
├── index.html                # 3 screens: config, preview, dashboard
├── css/style.css             # Dark theme, KPI cards, progress bar
└── js/app.js                 # Tauri API integration, event listeners
```

### Control Flow

1. User provides source & target connection strings + AI provider config (env var / .env)
2. Source DB connector streams schema (DDL) → AIService maps types to target dialect (returns structured JSON)
3. AIService samples data (first ~1000 rows stats) and validates compatibility (Pre-Flight Sanitizer)
4. User approves the AI-generated mapping
5. MigrationEngine disables FK constraints & indexes on target, streams data async from source → target, re-enables constraints
6. KPITracker reports rows/s, MB/s, ETA in real time
7. Post-migration integrity audit: COUNT per table, source vs target

### Key Design Decisions

- **All I/O is async** — every DB connector uses async drivers (aiosqlite, asyncpg, aiomysql)
- **AI never touches raw data** — only schema (DDL) and statistical metadata are sent to OpenAI
- **Constraints disabled during migration** — FKs and indexes dropped before bulk insert, recreated after, for speed
- **`IDatabase` interface** — all connectors implement `connect()`, `get_schema()`, `stream_data()`, `bulk_insert()`, `execute_ddl()`, `get_row_count()`, `disable_constraints()`, `enable_constraints()`
- **Pydantic models** — used for structured validation (dependency already in `pyproject.toml`)
- **Multi-provider AI** — supports OpenAI, Groq, OpenRouter, Anthropic Claude, and Synthetic (mock) via `providers/` subpackage. Runtime switching via `ai_service.set_provider()`.

## Dependencies

| Package | Purpose |
|---------|---------|
| `aiosqlite` | Async SQLite connector |
| `asyncpg` | Async PostgreSQL connector (prefer `copy_to_table` for bulk perf) |
| `aiomysql` | Async MySQL connector (batch inserts) |
| `openai` | OpenAI-compatible API client (works for OpenAI, Groq, OpenRouter) |
| `anthropic` | Anthropic Claude API client |
| `pydantic` | Data validation and structured models |
| `python-dotenv` | Load .env files for API keys |

## Conventions

- **Async-first**: all database operations use `async/await` patterns
- **Environment variable for secrets**: API keys read from .env / env vars, not hardcoded (see `.env.example`)
- **Structured AI output**: prompts must request JSON responses; validate with Pydantic
- **Story-driven development**: implement stories in order from `docs/BACKLOG.md`

## Gotchas

- `asyncpg` uses `copy_to_table` for maximum bulk insert throughput — not raw INSERT statements
- MySQL has no native `COPY` equivalent; `aiomysql` batch inserts are the performance path
- SQLite is file-based — no connection string parsing needed, just a file path
- **Tauri on Linux requires system packages**: run `./setup-linux.sh` first (installs libgtk-3-dev, libwebkit2gtk-4.1-dev, etc.)
- **Tauri sidecar**: the Python bridge binary (`autondb-core`) is built via PyInstaller (`./build-core.sh`) and placed in `src-tauri/binaries/`
- **Bridge protocol**: Python bridge outputs one JSON event per line to stdout; the Rust backend parses and emits Tauri events
- The `src-tauri/` directory is the Tauri project root — don't confuse with `src/` Python source

## Implementation Priority

Per backlog, implement in this order:
1. **STORY-1.1**: Project structure (done)
2. **STORY-1.2**: `IDatabase` abstract base class (done)
3. **STORY-1.3–1.5**: SQLite, PostgreSQL, MySQL connectors (done)
4. **STORY-2.1–2.3**: AIService, prompt engineering, Pre-Flight Sanitizer (done)
5. **STORY-3.1–3.4**: MigrationEngine, constraint toggling, KPITracker, integrity audit (done)
6. **STORY-4.1–4.5**: Tauri desktop wrapper, PyInstaller sidecar, UI screens (done)
