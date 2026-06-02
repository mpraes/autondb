# AutonDB — Agent Guide

## What This Project Is

AutonDB is an AI-assisted database migration tool for small/medium databases (PostgreSQL, MySQL, SQLite). It uses OpenAI to perform smart schema mapping and pre-flight data sanitization, then executes high-speed async migrations with post-migration integrity auditing.

**Project language**: Python, Portuguese (backlog/docs are in Portuguese; code is in English).

## Current State

The project has completed **Epic 1** (DB connectors), **Epic 2** (AI brain), and **Epic 3** (MigrationEngine). Implementation follows the stories in `docs/BACKLOG.md` sequentially (Epic 1 → 2 → 3 → 4). Next up: Epic 4 (Tauri).

## Essential Commands

- **Install/sync deps**: `uv sync` (uses `uv.lock`, managed by `uv`)
- **Run**: `uv run src/main.py` (not yet functional)
- **Test**: `uv run pytest tests/ -v`
- **Python version**: 3.13 (pinned in `.python-version`)

## Architecture (Planned)

```
src/
├── main.py                  # CLI entry point
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
    ├── SQLiteDB   (aiosqlite)
    ├── PostgresDB (asyncpg)
    └── MySQLDB    (aiomysql)
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
- The `databases/` package dir is empty but must contain an `__init__.py` or be a proper Python package once connectors are added
- Epic 4 (Tauri) will introduce a `src-tauri/` directory at project root — don't confuse with `src/` Python source

## Implementation Priority

Per backlog, implement in this order:
1. **STORY-1.1**: Project structure (done)
2. **STORY-1.2**: `IDatabase` abstract base class (done)
3. **STORY-1.3–1.5**: SQLite, PostgreSQL, MySQL connectors (done)
4. **STORY-2.1–2.3**: AIService, prompt engineering, Pre-Flight Sanitizer (done)
5. **STORY-3.1–3.4**: MigrationEngine, constraint toggling, KPITracker, integrity audit (done)
6. **STORY-4.1–4.5**: Tauri desktop wrapper (separate concern, do last)
