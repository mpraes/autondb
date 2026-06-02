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

## Installation (End User)

Download the latest release for your platform from [GitHub Releases](https://github.com/renan/autondb/releases):

| Platform | Format | Install |
|----------|--------|---------|
| **Windows** | `.msi` | Double-click to install |
| **macOS** | `.dmg` | Open, drag to Applications |
| **Linux (Debian/Ubuntu)** | `.deb` | `sudo dpkg -i autondb_*_amd64.deb` |
| **Linux (any)** | `.AppImage` | `chmod +x autondb_*_amd64.AppImage && ./autondb_*_amd64.AppImage` |

No Rust, Node.js, or Python required — the app is self-contained.

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

## Development Setup

One command installs all dependencies (Rust, Node.js, Python, uv, system libs):

| Platform | Command |
|----------|---------|
| **Linux (Debian/Ubuntu)** | `./setup-linux.sh` |
| **macOS** | `./setup-macos.sh` |
| **Windows** | `.\setup-windows.ps1` |

Or via Make:

```bash
make setup-linux     # Debian/Ubuntu
make setup-macos     # macOS
make setup-windows   # Windows (PowerShell)
```

After setup, build and run:

```bash
./build-core.sh    # Build Python sidecar binary
npx tauri dev      # Run in dev mode
npx tauri build    # Build production app
```

### Requirements (if not using setup scripts)

- **Python** 3.13+ (managed by `uv`)
- **Rust** 1.77+ (for Tauri desktop builds only)
- **Node.js** 22+ (for Tauri CLI only)
- **System libs** (Linux only): `libgtk-3-dev`, `libwebkit2gtk-4.1-dev`, `libdbus-1-dev`, `libayatana-appindicator3-dev` — run `./setup-linux.sh`

## Build Philosophy: One Binary, Many Packages

The Python core is compiled **once per target architecture** into a standalone binary via PyInstaller. That same binary is then re-packaged into every distribution format — it is never rebuilt:

```
autondb-core (PyInstaller)          ← built ONCE per arch
  ├── dist/autondb-core             ← standalone CLI binary
  ├── src-tauri/binaries/           ← Tauri sidecar (same binary, renamed)
  │   ├── .deb                      ← Debian package (Linux)
  │   ├── .AppImage                 ← portable app (Linux)
  │   ├── .msi                      ← Windows installer
  │   └── .dmg                      ← macOS disk image
  └── importable as Python module   ← library mode
```

**CI pipeline** (`.github/workflows/release.yml`) enforces this:

1. **`build-sidecar`** — PyInstaller compiles `autondb-core` once per architecture (4 targets). Artifact is uploaded.
2. **`build-tauri`** — downloads the pre-built sidecar (no rebuild), then Tauri compiles the Rust shell and packages it into `.deb` + `.AppImage` / `.msi` / `.dmg`.
3. **`publish-cli`** — uploads the standalone CLI binaries to the same GitHub Release.

This means the exact same `autondb-core` binary inside the `.deb` is also available as a standalone CLI download.

**Supported architectures:**

| Architecture | Binary name |
|-------------|-------------|
| Linux x86_64 | `autondb-core-x86_64-unknown-linux-gnu` |
| macOS Apple Silicon | `autondb-core-aarch64-apple-darwin` |
| macOS Intel | `autondb-core-x86_64-apple-darwin` |
| Windows x86_64 | `autondb-core-x86_64-pc-windows-msvc.exe` |

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
├── constants.py              # Shared magic-value constants
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
    ├── factory.py            # DIALECTS registry + build_db()
    ├── identifier.py         # Shared validate_identifier() for SQL injection guard
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

## Releasing

Push a tag and GitHub Actions builds installers for all platforms automatically:

```bash
git tag v0.1.0
git push origin v0.1.0
```

This triggers `.github/workflows/release.yml` which produces:
- Windows `.msi`
- macOS `.dmg`
- Linux `.deb` + `.AppImage`

All artifacts are published to the GitHub Release page.

## Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install runtime deps |
| `make install-dev` | Install runtime + dev deps |
| `make test` | Run test suite |
| `make lint` | Lint + format check |
| `make tauri-dev` | Run Tauri in dev mode |
| `make tauri-build` | Build Tauri desktop app |
| `make build-sidecar` | Build Python sidecar binary |

## License

MIT
