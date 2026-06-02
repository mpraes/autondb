# Contributing

## Workflow

1. **Fork** the repository and create your branch from `main`
2. **Write tests** — every new function, class, or branch must have a corresponding test under `tests/`
3. **Run checks locally** before pushing:

```bash
make lint   # ruff check + ruff format --check
make test   # pytest tests/ -v
```

4. **Open a Pull Request** against `main`

## CI

Two GitHub Actions workflows run automatically:

### Tests (`.github/workflows/tests.yml`)

Runs on every push and PR to `main`:

| Job | What it does |
|-----|-------------|
| **lint** | `ruff check` + `ruff format --check` |
| **test** | `pytest tests/ -v` |

PRs must pass both jobs before merging.

### Release (`.github/workflows/release.yml`)

Runs on semver tag push (`v*.*.*`) or manual trigger:

1. Validates the tag and extracts the changelog
2. Builds the Python sidecar once per architecture
3. Packages the Tauri app for all platforms
4. Publishes installers + CLI binaries to a GitHub Release

→ See [docs/releases.md](releases.md) for the full release guide.

## Releasing

Releases are handled via semver tags:

```bash
# Update CHANGELOG.md, bump versions, then:
git tag v1.2.3
git push origin v1.2.3
```

This triggers the release pipeline. See [docs/releases.md](releases.md) for the complete checklist and process.

## Code Conventions

- **Async-first** — all database operations use `async/await`
- **Environment variables for secrets** — API keys from `.env` / env vars, never hardcoded
- **Structured AI output** — prompts request JSON; validate with Pydantic
- **Constants over magic values** — use `src/constants.py` for numeric/string defaults
- **SQL identifiers must be validated** — use `validate_identifier()` from `src/databases/identifier.py`
- **No code duplication** — extract shared logic to common modules
- **No silent exception swallowing** — at minimum `logging.warning(..., exc_info=True)`
