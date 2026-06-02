# AutonDB — Agent Guide

## What This Project Is

AutonDB is an AI-assisted database migration tool for small/medium databases (PostgreSQL, MySQL, SQLite). It uses multi-provider AI (OpenAI, Groq, OpenRouter, Anthropic Claude, or a built-in Synthetic mock) to perform smart schema mapping and pre-flight data sanitization, then executes high-speed async migrations with post-migration integrity auditing.

**Project language**: Python. All documentation and code are in English.

## Current State

The project has completed **all 4 Epics** (DB connectors, AI brain, MigrationEngine, Tauri desktop). The app is ready for end-to-end testing.

## Documentation Map

| Doc | Content |
|-----|---------|
| [README.md](../README.md) | Minimal overview, installation, quick links |
| [docs/quick-start.md](quick-start.md) | CLI, Desktop App, Python Library usage |
| [docs/architecture.md](architecture.md) | Project structure, control flow, diagrams, design decisions |
| [docs/development.md](development.md) | Dev setup, commands, dependencies, build philosophy |
| [docs/ai-providers.md](ai-providers.md) | AI providers, configuration, privacy |
| [docs/databases.md](databases.md) | Supported databases, IDatabase interface |
| [docs/contributing.md](contributing.md) | Contributing workflow, CI, code conventions |
| [docs/releases.md](releases.md) | Release process, checklist |

| [CHANGELOG.md](../CHANGELOG.md) | Version history |

## Essential Commands

All commands are available via the Makefile. Run `make` to see available targets.

| Make target | What it does |
|---|---|
| `make install` | Install/sync runtime deps |
| `make install-dev` | Install runtime + dev deps |
| `make test` | Run test suite (`uv run pytest tests/ -v`) |
| `make lint` | Lint + format check (`ruff check` + `ruff format --check`) |
| `make run-migrate` | Run a migration (requires env vars) |
| `make build-sidecar` | Build Python sidecar binary |
| `make tauri-dev` | Run Tauri in dev mode |
| `make tauri-build` | Build Tauri desktop app |
| `make clean` | Remove caches and build artifacts |

- **Python version**: 3.13 (pinned in `.python-version`)

## Conventions

- **Async-first**: all database operations use `async/await` patterns
- **Environment variable for secrets**: API keys read from .env / env vars, not hardcoded (see `.env.example`)
- **Structured AI output**: prompts must request JSON responses; validate with Pydantic
- **Story-driven development**: implement features in logical order
- **Constants over magic values**: use `src/constants.py` for numeric/string defaults

## Mandatory Rules

These rules are **non-negotiable**. Any code that violates them must be fixed before merging.

1. **Zero dead imports** — every `import` statement in the codebase must be referenced in the file body. If an import is only needed for type hints, use `from __future__ import annotations` and keep the import at the top. Run `make lint` before committing.

2. **Zero code duplication** — if the same function, dict, or logic block appears in 2+ files, extract it to a shared module. Current shared modules:
   - `src/constants.py` — numeric/string defaults
   - `src/databases/factory.py` — `DIALECTS` dict + `build_db()`
   - `src/databases/identifier.py` — `validate_identifier()`
   - `src/services/providers/_json_utils.py` — `extract_json()`
   - `src/services/providers/__init__.py` — `PROVIDER_ENV_KEYS` + `create_provider()`
   - If you're about to copy-paste a function, stop and extract it first.

3. **All numeric/string defaults are named constants** — no magic values in code. If a number or string appears in more than one place, or represents a tunable parameter (batch size, pool size, max tokens, timeouts, conversion factors), it **must** live in `src/constants.py` and be imported by name.

4. **SQL identifiers must be validated** — every table name, column name, or other SQL identifier that originates from user input or external data **must** pass through `validate_identifier()` (from `src/databases/identifier.py`) before being interpolated into SQL strings. Parameterized queries (`$1`, `%s`, `?`) are for values; identifiers must be validated separately. Never duplicate this function — import it from `identifier.py`.

5. **`load_dotenv()` called exactly once** — only in `src/services/providers/__init__.py`. Never call it in other modules. If you need env vars earlier, restructure the import order instead.

5b. **Provider→env var mapping is centralized** — `PROVIDER_ENV_KEYS` in `src/services/providers/__init__.py` is the single source of truth for which env var holds each provider's API key. Never duplicate this mapping.

6. **Never swallow exceptions silently** — `except Exception: pass` is forbidden. At minimum, log the exception with `logging.warning(..., exc_info=True)`. If the exception is truly expected and harmless, add a comment explaining why.

7. **No imports inside method bodies** — all imports belong at the top of the file. The only exception is legitimate lazy imports that prevent circular dependencies, which must be documented with a comment.

8. **Connector guard pattern: `_require_conn()`/`_require_pool()`** — instead of calling `_assert_connected()` followed by `assert self._conn is not None`, use the `_require_conn()`/`_require_pool()` method that returns the typed connection object directly. This eliminates the redundant assert and makes the code both safer and cleaner.

9. **Test coverage is mandatory for new code** — every new function, class, or branch must have a corresponding test. Areas currently lacking coverage (must be addressed before adding more features):
   - `src/bridge.py` — `analyze()` and `migrate()` async functions
   - `src/main.py` — `run_migration()` async function
   - `PostgresDB.copy_to_table()` — currently untested dead code
   - SQLite integration test using `:memory:` DB

   Recently covered:
   - `src/main.py` — `parse_args()`
   - `src/services/providers/` — `create_provider()` error paths
   - `AIService.from_env()` — fallback logic from env vars
   - `src/databases/identifier.py` — `validate_identifier()`

10. **Documentation must reflect reality** — when changing code behavior, update `AGENTS.md` and `CHANGELOG.md` accordingly. Stale documentation is a bug. In particular:
    - If you add a new module, add it to the Architecture tree in `docs/architecture.md`
    - If you change an interface, update the `IDatabase interface` list in `docs/databases.md`
    - If you change control flow, update the Control Flow section in `docs/architecture.md`
    - If you add a dependency, add it to the Dependencies table in `docs/development.md`

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
