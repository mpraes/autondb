# AutonDB — Agent Guide

## What This Project Is

AutonDB is an AI-assisted database migration tool for small/medium databases (PostgreSQL, MySQL, SQLite). It uses multi-provider AI (OpenAI, Groq, OpenRouter, Anthropic Claude, or a built-in Synthetic mock) to perform smart schema mapping and pre-flight data sanitization, then executes high-speed async migrations with post-migration integrity auditing.

**Project language**: Python, Portuguese (backlog/docs are in Portuguese; code is in English).

## Current State

The project has completed **all 4 Epics** (DB connectors, AI brain, MigrationEngine, Tauri desktop). All stories in `docs/BACKLOG.md` are done. The app is ready for end-to-end testing.

## Essential Commands

All commands are available via the Makefile. Run `make` to see available targets.

| Make target | What it does | Raw command |
|---|---|---|
| `make install` | Install/sync runtime deps | `uv sync` |
| `make install-dev` | Install runtime + dev deps | `uv sync --group dev` |
| `make test` | Run test suite | `uv run pytest tests/ -v` |
| `make lint` | Lint + format check | `ruff check` + `ruff format --check` |
| `make run-migrate` | Run a migration (requires env vars) | `uv run src/main.py ...` |
| `make build-sidecar` | Build Python sidecar binary | `./build-core.sh` |
| `make tauri-dev` | Run Tauri in dev mode | `npx tauri dev` |
| `make tauri-build` | Build Tauri desktop app | `npx tauri build` |
| `make setup-linux` | Install Linux system deps (first time) | `./setup-linux.sh` |
| `make clean` | Remove caches and build artifacts | — |

**Running a migration**:
```bash
make run-migrate SOURCE_DSN=/data/source.db SOURCE_DIALECT=sqlite TARGET_DSN=postgres://user:pass@host/db TARGET_DIALECT=postgresql
# Optional: EXTRA_ARGS="--auto-approve --batch-size 500"
```

- **Python version**: 3.13 (pinned in `.python-version`)

## Architecture

```
src/
├── constants.py              # Shared magic-value constants (batch size, pool sizes, etc.)
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
│       ├── __init__.py       # Provider factory + registry (load_dotenv here)
│       ├── base.py           # AIProvider abstract base
│       ├── _json_utils.py    # Shared JSON extraction (markdown fence stripping)
│       ├── openai_compat.py  # OpenAI, Groq, OpenRouter (all OpenAI-compatible)
│       ├── anthropic_provider.py  # Anthropic Claude
│       └── synthetic.py      # Mock provider for testing
└── databases/               # Database connectors
    ├── __init__.py
    ├── factory.py            # DIALECTS registry + build_db()
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
3. Caller collects column statistical metadata (sample values, null counts, distinct counts) → AIService validates compatibility (Pre-Flight Sanitizer)
4. User approves the AI-generated mapping
5. MigrationEngine disables FK constraints on target (SET session_replication_role / SET FOREIGN_KEY_CHECKS), streams data async from source → target, re-enables constraints
6. KPITracker reports rows/s, MB/s, ETA in real time
7. Post-migration integrity audit: COUNT per table, source vs target

### Key Design Decisions

- **All I/O is async** — every DB connector uses async drivers (aiosqlite, asyncpg, aiomysql)
- **AI never touches raw data** — only schema (DDL) and statistical metadata are sent to the AI provider
- **Constraints disabled during migration** — FKs are disabled via session-level flags before bulk insert, and re-enabled after, for speed. Indexes are not dropped/recreated.
- **`IDatabase` interface** — all connectors implement `connect()`, `disconnect()`, `get_schema()`, `stream_data()`, `bulk_insert()`, `execute_ddl()`, `get_row_count()`, `disable_constraints()`, `enable_constraints()`
- **`PostgresDB.copy_to_table()`** — available as an additional method for high-performance COPY protocol, but not yet wired into MigrationEngine (currently uses bulk INSERT)
- **Pydantic models** — used for structured validation (dependency already in `pyproject.toml`)
- **Multi-provider AI** — supports OpenAI, Groq, OpenRouter, Anthropic Claude, and Synthetic (mock) via `providers/` subpackage. Runtime switching via `ai_service.set_provider()`.
- **Shared constants** — magic values (batch size, pool sizes, max tokens, MB conversion) live in `src/constants.py` and are imported everywhere
- **DB factory** — `src/databases/factory.py` centralizes `DIALECTS` and `build_db()`, used by both CLI and bridge
- **JSON extraction** — shared `extract_json()` in `providers/_json_utils.py` strips markdown fences, used by OpenAI and Anthropic providers
- **Identifier validation** — `_validate_identifier()` guards against SQL injection in table/column names across all DB connectors
- **`load_dotenv()` called once** — only in `src/services/providers/__init__.py`, which is the module that reads API keys from env vars

## Dependencies

| Package | Purpose |
|---------|---------|
| `aiosqlite` | Async SQLite connector |
| `asyncpg` | Async PostgreSQL connector (supports `copy_to_table` for bulk perf) |
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
- **Constants over magic values**: use `src/constants.py` for numeric/string defaults

## Mandatory Rules

These rules are **non-negotiable**. Any code that violates them must be fixed before merging.

1. **Zero dead imports** — every `import` statement in the codebase must be referenced in the file body. If an import is only needed for type hints, use `from __future__ import annotations` and keep the import at the top. Run `make lint` before committing.

2. **Zero code duplication** — if the same function, dict, or logic block appears in 2+ files, extract it to a shared module. Current shared modules:
   - `src/constants.py` — numeric/string defaults
   - `src/databases/factory.py` — `DIALECTS` dict + `build_db()`
   - `src/services/providers/_json_utils.py` — `extract_json()`
   - If you're about to copy-paste a function, stop and extract it first.

3. **All numeric/string defaults are named constants** — no magic values in code. If a number or string appears in more than one place, or represents a tunable parameter (batch size, pool size, max tokens, timeouts, conversion factors), it **must** live in `src/constants.py` and be imported by name.

4. **SQL identifiers must be validated** — every table name, column name, or other SQL identifier that originates from user input or external data **must** pass through `_validate_identifier()` (defined in each connector) before being interpolated into SQL strings. Parameterized queries (`$1`, `%s`, `?`) are for values; identifiers must be validated separately.

5. **`load_dotenv()` called exactly once** — only in `src/services/providers/__init__.py`. Never call it in other modules. If you need env vars earlier, restructure the import order instead.

6. **Never swallow exceptions silently** — `except Exception: pass` is forbidden. At minimum, log the exception with `logging.warning(..., exc_info=True)`. If the exception is truly expected and harmless, add a comment explaining why.

7. **No imports inside method bodies** — all imports belong at the top of the file. The only exception is legitimate lazy imports that prevent circular dependencies, which must be documented with a comment.

8. **Connector guard pattern: `_require_conn()`/`_require_pool()`** — instead of calling `_assert_connected()` followed by `assert self._conn is not None`, use the `_require_conn()`/`_require_pool()` method that returns the typed connection object directly. This eliminates the redundant assert and makes the code both safer and cleaner.

9. **Test coverage is mandatory for new code** — every new function, class, or branch must have a corresponding test. Areas currently lacking coverage (must be addressed before adding more features):
   - `src/bridge.py` — `analyze()` and `migrate()` functions
   - `src/main.py` — `run_migration()` and `parse_args()`
   - `src/services/providers/` — `create_provider()` error paths (unknown provider, missing API key)
   - `AIService.from_env()` — fallback logic from env vars
   - `PostgresDB.copy_to_table()` — currently untested dead code
   - SQLite integration test using `:memory:` DB

10. **Documentation must reflect reality** — when changing code behavior, update `AGENTS.md` and `docs/BACKLOG.md` accordingly. Stale documentation is a bug. In particular:
    - If you add a new module, add it to the Architecture tree
    - If you change an interface, update the `IDatabase interface` list
    - If you change control flow, update the Control Flow section
    - If you add a dependency, add it to the Dependencies table

## Gotchas

- `asyncpg` supports `copy_to_table` for maximum bulk insert throughput — but MigrationEngine currently uses `bulk_insert` (INSERT statements). To enable COPY, wire `copy_to_table` into the engine's Postgres path.
- MySQL has no native `COPY` equivalent; `aiomysql` batch inserts are the performance path
- SQLite is file-based — no connection string parsing needed, just a file path
- **Tauri on Linux requires system packages**: run `./setup-linux.sh` first (installs libgtk-3-dev, libwebkit2gtk-4.1-dev, etc.)
- **Tauri sidecar**: the Python bridge binary (`autondb-core`) is built via PyInstaller (`./build-core.sh`) and placed in `src-tauri/binaries/`
- **Bridge protocol**: Python bridge outputs one JSON event per line to stdout; the Rust backend parses and emits Tauri events
- The `src-tauri/` directory is the Tauri project root — don't confuse with `src/` Python source
- **`AIProvider.complete()`** (non-JSON) is defined on the abstract base but never called in production — only `complete_json()` is used by AIService

## Implementation Priority

Per backlog, implement in this order:
1. **STORY-1.1**: Project structure (done)
2. **STORY-1.2**: `IDatabase` abstract base class (done)
3. **STORY-1.3–1.5**: SQLite, PostgreSQL, MySQL connectors (done)
4. **STORY-2.1–2.3**: AIService, prompt engineering, Pre-Flight Sanitizer (done)
5. **STORY-3.1–3.4**: MigrationEngine, constraint toggling, KPITracker, integrity audit (done)
6. **STORY-4.1–4.5**: Tauri desktop wrapper, PyInstaller sidecar, UI screens (done)
