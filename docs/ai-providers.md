# AI Providers

AutonDB uses AI to perform schema mapping and pre-flight data sanitization. AI never touches raw data — only schema (DDL) and statistical metadata are sent to the provider.

## Configuration

Set your API key via environment variable or `.env` file:

```bash
# .env
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

Or pass via CLI flags:

```bash
uv run src/main.py --ai-provider openai --ai-model gpt-4o ...
```

## Supported Providers

| Provider | Env var for key | Default model | Notes |
|----------|-----------------|---------------|-------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` | Primary provider |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | OpenAI-compatible API |
| OpenRouter | `OPENROUTER_API_KEY` | `openai/gpt-4o` | OpenAI-compatible API |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | Native Anthropic API |
| Synthetic | — (no key needed) | — (mock) | For testing only |

## Privacy

- **Schema only** — the AI receives table names, column names, and type definitions (DDL)
- **Statistical metadata only** — the pre-flight sanitizer sends sample values, null counts, and distinct counts — never full rows
- **No PII** — raw data is never sent to any AI provider
- **User control** — all AI calls can be reviewed before proceeding via the approval step

## Architecture

All providers implement the `AIProvider` abstract base (`src/services/providers/base.py`):

- `complete(prompt)` — plain text completion (defined but not used in production)
- `complete_json(prompt)` — structured JSON completion (used by AIService)

The provider factory in `src/services/providers/__init__.py` maps provider names to implementations and loads API keys from the environment. Runtime switching is available via `ai_service.set_provider()`.

The `PROVIDER_ENV_KEYS` dict centralizes the mapping of provider names to API key env vars — used by both `create_provider()` and the Tauri bridge.
