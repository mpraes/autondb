# AutonDB

AI-assisted database migration tool for PostgreSQL, MySQL, and SQLite. Smart schema mapping via AI, pre-flight data sanitization, high-speed async migrations, and post-migration integrity auditing.

## Installation

Download the latest release from [GitHub Releases](https://github.com/renan/autondb/releases):

| Platform | Format | Install |
|----------|--------|---------|
| Windows | `.msi` | Double-click to install |
| macOS | `.dmg` | Open, drag to Applications |
| Linux (Debian/Ubuntu) | `.deb` | `sudo dpkg -i autondb_*_amd64.deb` |
| Linux (any) | `.AppImage` | `chmod +x && ./autondb_*_amd64.AppImage` |

No Rust, Node.js, or Python required — the app is self-contained.

## Quick Start

```bash
# CLI
uv run src/main.py \
  --source-dsn ./old.db --source-dialect sqlite \
  --target-dsn "postgres://user:pass@localhost/newdb" --target-dialect postgresql \
  --ai-provider openai --auto-approve
```

→ Full examples for [CLI, Desktop App, and Python Library](docs/quick-start.md)

## AI Configuration

Set your API key via `.env` or environment variable. AI never touches raw data — only schema and statistical metadata.

| Provider | Env var | Default model |
|----------|---------|---------------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| OpenRouter | `OPENROUTER_API_KEY` | `openai/gpt-4o` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Synthetic | — | Mock for testing |

→ [docs/ai-providers.md](docs/ai-providers.md) for details

## Contributing

1. Fork → branch from `main`
2. Write tests for new code
3. Run `make lint && make test`
4. Open a PR — CI (lint + tests) must pass

→ [docs/contributing.md](docs/contributing.md) for the full guide

## Documentation

| Doc | Content |
|-----|---------|
| [docs/quick-start.md](docs/quick-start.md) | CLI, Desktop App, Python Library usage |
| [docs/architecture.md](docs/architecture.md) | Architecture, control flow, diagrams |
| [docs/development.md](docs/development.md) | Dev setup, build, commands |
| [docs/ai-providers.md](docs/ai-providers.md) | AI providers, configuration, privacy |
| [docs/databases.md](docs/databases.md) | Supported databases, connectors |
| [docs/contributing.md](docs/contributing.md) | Contributing guide, CI, releases |
| [docs/releases.md](docs/releases.md) | Release process, checklist |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## License

[MIT](LICENSE) — Copyright (c) 2025 mpraes
