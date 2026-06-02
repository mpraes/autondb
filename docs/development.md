# Development

## Setup

One command installs all dependencies (Rust, Node.js, Python, uv, system libs):

| Platform | Command |
|----------|---------|
| Linux (Debian/Ubuntu) | `./setup-linux.sh` or `make setup-linux` |
| macOS | `./setup-macos.sh` or `make setup-macos` |
| Windows | `.\setup-windows.ps1` or `make setup-windows` |

### Requirements (if not using setup scripts)

- **Python** 3.13+ (managed by `uv`, pinned in `.python-version`)
- **Rust** 1.77+ (for Tauri desktop builds only)
- **Node.js** 22+ (for Tauri CLI only)
- **System libs** (Linux only): `libgtk-3-dev`, `libwebkit2gtk-4.1-dev`, `libdbus-1-dev`, `libayatana-appindicator3-dev` — run `./setup-linux.sh`

## Commands

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
| `make clean` | Remove caches and build artifacts | — |

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

### Dev dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `ruff` | Linter + formatter |
| `pyinstaller` | Build standalone binary |

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

### Build steps

```bash
./build-core.sh    # Build Python sidecar binary
npx tauri dev      # Run in dev mode
npx tauri build    # Build production app
```

### CI pipeline (release)

`.github/workflows/release.yml` enforces the one-binary-many-packages approach:

1. **`build-sidecar`** — PyInstaller compiles `autondb-core` once per architecture (4 targets). Artifact is uploaded.
2. **`build-tauri`** — downloads the pre-built sidecar (no rebuild), then Tauri compiles the Rust shell and packages it into `.deb` + `.AppImage` / `.msi` / `.dmg`.
3. **`publish-cli`** — uploads the standalone CLI binaries to the same GitHub Release.

This means the exact same `autondb-core` binary inside the `.deb` is also available as a standalone CLI download.

### Supported architectures

| Architecture | Binary name |
|-------------|-------------|
| Linux x86_64 | `autondb-core-x86_64-unknown-linux-gnu` |
| macOS Apple Silicon | `autondb-core-aarch64-apple-darwin` |
| macOS Intel | `autondb-core-x86_64-apple-darwin` |
| Windows x86_64 | `autondb-core-x86_64-pc-windows-msvc.exe` |
