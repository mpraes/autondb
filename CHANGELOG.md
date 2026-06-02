# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Extract `_validate_identifier()` from 3 duplicated copies into shared `src/databases/identifier.py`
- Move `import logging` from inside method body to top-level in `migration.py`
- Move `import json` from inside method body to top-level in `synthetic.py`
- Replace duplicated provider→env-var dict in `bridge.py` with shared `PROVIDER_ENV_KEYS` constant
- Replace hardcoded `"postgresql"` default in `SchemaMapping.target_dialect` with `DEFAULT_TARGET_DIALECT` constant
- Improve combobox contrast in desktop UI (darker background, white bold text, custom SVG arrow)
- Two-column layout for config screen (Origin/Destination side-by-side, AI/Options side-by-side)

### Added

- `src/databases/identifier.py` — shared `validate_identifier()` module
- `DEFAULT_TARGET_DIALECT` constant in `src/constants.py`
- `PROVIDER_ENV_KEYS` mapping in `src/services/providers/__init__.py`
- `validate_identifier` export in `src/databases/__init__.py`
- Test suite for `validate_identifier()` (`tests/test_identifier.py`)
- Test suite for `create_provider()` error paths (`tests/test_create_provider.py`)
- Test suite for `parse_args()` (`tests/test_main.py`)
- Test suite for `AIService.from_env()` (`tests/test_ai_service.py`)
- `setup-macos.sh` — one-command dev setup for macOS (Homebrew)
- `setup-windows.ps1` — one-command dev setup for Windows (winget)
- `setup-linux.sh` rewritten to install ALL dev deps (Rust, Node, Python, uv), not just system libs
- `.github/workflows/release.yml` — CI pipeline: build sidecar once per arch → Tauri packages → publish CLI binaries
- `make setup-macos` and `make setup-windows` Make targets
- Installation instructions for end users (`.msi`, `.dmg`, `.deb`, `.AppImage`) in README
- Releasing section in README with `git tag` workflow
- Build philosophy section in README documenting one-binary-many-packages architecture

### Fixed

- Remove unused `Manager` import in `src-tauri/src/lib.rs` (Rust warning)
- Fix syntax error in `sqlite_db.py` from misplaced parenthesis

## [0.1.0] - 2025-06-01

### Added

- Core migration engine with async streaming, constraint toggling, and integrity audit
- AI-powered schema mapping with multi-provider support (OpenAI, Groq, OpenRouter, Anthropic, Synthetic)
- Pre-flight data sanitization via statistical metadata analysis
- Real-time KPI tracker (rows/s, MB/s, ETA)
- Post-migration integrity audit (row count comparison)
- Database connectors: SQLite (aiosqlite), PostgreSQL (asyncpg), MySQL (aiomysql)
- CLI entry point with `--source-dsn`, `--target-dsn`, `--auto-approve` flags
- Tauri 2 desktop app with 3-screen wizard (Config → Preview → Dashboard)
- Python sidecar bridge (JSON-over-stdout protocol)
- PyInstaller spec for standalone binary (`autondb-core`)
- Dark-themed UI with KPI cards, progress bar, and toast notifications
- Shared constants in `src/constants.py` (batch size, pool sizes, max tokens, etc.)
- DB factory with `DIALECTS` registry and `build_db()`
- JSON extraction utility (`extract_json()`) stripping markdown fences
- Pydantic models for schema mapping, sanitization reports
- Test suite (62 tests across 5 files)
- `build-core.sh` for one-command sidecar build
- `setup-linux.sh` for Linux system dependencies
- Makefile with all common targets

[unreleased]: https://github.com/renan/autondb/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/renan/autondb/releases/tag/v0.1.0
