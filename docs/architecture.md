# Architecture

> Diagrams: [class_diagram.mermaid](./class_diagram.mermaid) | [sequence_diagram.mermaid](./sequence_diagram.mermaid) | [component_diagram.mermaid](./component_diagram.mermaid)
>
> Open `.mermaid` files in VSCode with the Mermaid extension for preview.

## Project Structure

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
    ├── identifier.py         # Shared validate_identifier() for SQL injection guard
    ├── idatabase.py          # IDatabase abstract base
    ├── sqlite_db.py          # SQLiteDB   (aiosqlite)
    ├── postgres_db.py        # PostgresDB (asyncpg)
    └── mysql_db.py           # MySQLDB    (aiomysql)

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

## Control Flow

1. User provides source & target connection strings + AI provider config (env var / .env)
2. Source DB connector streams schema (DDL) → AIService maps types to target dialect (returns structured JSON)
3. Caller collects column statistical metadata (sample values, null counts, distinct counts) → AIService validates compatibility (Pre-Flight Sanitizer)
4. User approves the AI-generated mapping
5. MigrationEngine disables FK constraints on target (`SET session_replication_role` / `SET FOREIGN_KEY_CHECKS`), streams data async from source → target, re-enables constraints
6. KPITracker reports rows/s, MB/s, ETA in real time
7. Post-migration integrity audit: COUNT per table, source vs target

## Key Design Decisions

- **All I/O is async** — every DB connector uses async drivers (aiosqlite, asyncpg, aiomysql)
- **AI never touches raw data** — only schema (DDL) and statistical metadata are sent to the AI provider
- **Constraints disabled during migration** — FKs are disabled via session-level flags before bulk insert, and re-enabled after, for speed. Indexes are not dropped/recreated.
- **`IDatabase` interface** — all connectors implement `connect()`, `disconnect()`, `get_schema()`, `stream_data()`, `bulk_insert()`, `execute_ddl()`, `get_row_count()`, `disable_constraints()`, `enable_constraints()`
- **`PostgresDB.copy_to_table()`** — available as an additional method for high-performance COPY protocol, but not yet wired into MigrationEngine (currently uses bulk INSERT)
- **Pydantic models** — used for structured validation (dependency already in `pyproject.toml`)
- **Multi-provider AI** — supports OpenAI, Groq, OpenRouter, Anthropic Claude, and Synthetic (mock) via `providers/` subpackage. Runtime switching via `ai_service.set_provider()`.
- **Shared constants** — magic values (batch size, pool sizes, max tokens, MB conversion, default target dialect) live in `src/constants.py` and are imported everywhere
- **DB factory** — `src/databases/factory.py` centralizes `DIALECTS` and `build_db()`, used by both CLI and bridge
- **JSON extraction** — shared `extract_json()` in `providers/_json_utils.py` strips markdown fences, used by OpenAI and Anthropic providers
- **Identifier validation** — `validate_identifier()` in `src/databases/identifier.py` guards against SQL injection in table/column names across all DB connectors
- **Provider env key mapping** — `PROVIDER_ENV_KEYS` in `src/services/providers/__init__.py` centralizes the mapping of provider names to API key env vars, used by both `create_provider()` and the Tauri bridge

## Class Diagram

```mermaid
classDiagram
    class CLI {
        +main None
        +parse_args Namespace
        +run_migration MigrationConfig
    }
    class IDatabase {
        <<abstract>>
        +connect None
        +disconnect None
        +get_schema list
        +stream_data AsyncIterator
        +bulk_insert None
        +get_row_count int
        +disable_constraints None
        +enable_constraints None
    }
    class SQLiteDB {
        -_conn Connection
        -_db_path str
        +connect None
        +disconnect None
        +get_schema list
        +stream_data AsyncIterator
        +bulk_insert None
    }
    class PostgresDB {
        -_pool Pool
        -_dsn str
        +connect None
        +disconnect None
        +get_schema list
        +stream_data AsyncIterator
        +bulk_insert None
        +copy_to_table None
        +disable_constraints None
        +enable_constraints None
    }
    class MySQLDB {
        -_pool Pool
        -_dsn str
        +connect None
        +disconnect None
        +get_schema list
        +stream_data AsyncIterator
        +bulk_insert None
        +disable_constraints None
        +enable_constraints None
    }
    class AIService {
        -_client AsyncOpenAI
        -_model str
        +init None
        +map_schema SchemaMapping
        +sanitize_preflight SanitizationReport
    }
    class SchemaMapping {
        +tables list
        +warnings list
        +to_ddl str
    }
    class TableMapping {
        +source_table str
        +target_table str
        +columns list
    }
    class ColumnMapping {
        +source_name str
        +source_type str
        +target_name str
        +target_type str
        +transform Optional
    }
    class ColumnStats {
        +table str
        +column str
        +sample_values list
        +null_count int
        +total_rows int
    }
    class SanitizationReport {
        +issues list
        +is_clean bool
    }
    class DataIssue {
        +table str
        +column str
        +issue_type str
        +description str
        +suggested_fix str
    }
    class MigrationEngine {
        -_source IDatabase
        -_target IDatabase
        -_ai AIService
        -_kpi KPITracker
        +init None
        +run MigrationResult
    }
    class KPITracker {
        -_start_time float
        -_rows_processed int
        -_bytes_processed int
        +increment_rows None
        +increment_bytes None
        +get_rows_per_sec float
        +get_bytes_per_sec float
        +get_eta float
        +snapshot KPISnapshot
    }
    class KPISnapshot {
        +rows_per_sec float
        +bytes_per_sec float
        +eta_seconds float
        +rows_processed int
        +elapsed_seconds float
    }
    class AuditReport {
        +table_counts dict
        +is_valid bool
        +mismatches list
    }
    class SourceTargetCount {
        +source_count int
        +target_count int
        +matches bool
    }
    class MigrationResult {
        +audit AuditReport
        +kpi_final KPISnapshot
        +success bool
        +errors list
    }
    class MigrationConfig {
        +source_dsn str
        +source_dialect str
        +target_dsn str
        +target_dialect str
        +openai_api_key str
        +openai_model str
        +batch_size int
    }
    IDatabase <|-- SQLiteDB
    IDatabase <|-- PostgresDB
    IDatabase <|-- MySQLDB
    AIService *-- SchemaMapping
    SchemaMapping *-- TableMapping
    TableMapping *-- ColumnMapping
    AIService ..> ColumnStats : uses as input
    AIService *-- SanitizationReport
    SanitizationReport *-- DataIssue
    MigrationEngine *-- KPITracker
    MigrationEngine --> AuditReport : produces
    MigrationEngine --> MigrationResult : produces
    KPITracker *-- KPISnapshot
    AuditReport *-- SourceTargetCount
    CLI --> MigrationConfig : creates
    CLI --> MigrationEngine : instantiates
    MigrationEngine --> IDatabase : uses
    MigrationEngine --> AIService : uses
    MigrationEngine --> KPITracker : uses
```

## Sequence Diagram — Migration Flow

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Engine as MigrationEngine
    participant Source as SourceDB
    participant AI as AIService
    participant Target as TargetDB
    participant KPI as KPITracker
    User->>CLI: run migration
    activate CLI
    CLI->>Engine: init source target ai
    activate Engine
    Note over Engine,AI: Phase 1 - Schema Mapping
    Engine->>Source: get_schema
    Source-->>Engine: DDL and TableSchema
    Engine->>AI: map_schema
    activate AI
    Note right of AI: DDL metadata only
    AI-->>Engine: SchemaMapping
    deactivate AI
    Engine-->>User: Display mapping for approval
    User->>Engine: Approve mapping
    Note over Engine,AI: Phase 2 - Pre-Flight Sanitization
    Engine->>Source: stream_data sample
    Source-->>Engine: ColumnStats
    Engine->>AI: sanitize_preflight
    activate AI
    Note right of AI: Metadata only no PII
    AI-->>Engine: SanitizationReport
    deactivate AI
    alt has data issues
        Engine-->>User: Display issues
        User->>Engine: Confirm proceed
    end
    Note over Engine,KPI: Phase 3 - Migration
    Engine->>Target: disable_constraints
    Note right of Target: Drop FKs and indexes
    Engine->>KPI: start tracking
    loop For each table
        Engine->>Source: stream_data
        activate Source
        loop Batch of rows
            Source-->>Engine: Row batch
            Engine->>KPI: increment_rows
            Engine->>Target: bulk_insert
            Target-->>Engine: ack
            Engine->>KPI: increment_bytes
        end
        deactivate Source
    end
    Engine->>Target: enable_constraints
    Note right of Target: Recreate FKs and indexes
    Engine->>KPI: snapshot
    KPI-->>Engine: KPISnapshot
    Note over Engine,Target: Phase 4 - Integrity Audit
    loop For each table
        Engine->>Source: get_row_count
        Source-->>Engine: source_count
        Engine->>Target: get_row_count
        Target-->>Engine: target_count
    end
    Engine->>Engine: Build AuditReport
    Engine-->>CLI: MigrationResult
    deactivate Engine
    CLI-->>User: Summary with AuditReport and KPI
    deactivate CLI
```

## Component Diagram

```mermaid
graph TB
    subgraph Core[AutonDB Core]
        CLI[CLI main.py]
        Engine[MigrationEngine engine/migration.py]
        AI[AIService services/ai_service.py]
        KPI[KPITracker engine/kpi.py]
        Audit[AuditReport Pydantic]
        Result[MigrationResult Pydantic]
        Schema[SchemaMapping Pydantic]
        SanReport[SanitizationReport Pydantic]
    end
    subgraph DB[Database Connectors databases]
        IDB[IDatabase abstract]
        SQLite[SQLiteDB aiosqlite]
        PG[PostgresDB asyncpg]
        MySQL[MySQLDB aiomysql]
    end
    OpenAI[OpenAI API]
    SourceDB[(Source DB)]
    TargetDB[(Target DB)]
    CLI -->|configures and runs| Engine
    Engine -->|reads source writes target| IDB
    Engine -->|schema mapping sanitization| AI
    Engine -->|tracks progress| KPI
    Engine -->|produces| Audit
    Engine -->|produces| Result
    IDB -.->|implements| SQLite
    IDB -.->|implements| PG
    IDB -.->|implements| MySQL
    AI -->|DDL and metadata only| OpenAI
    AI -->|produces| Schema
    AI -->|produces| SanReport
    SQLite -->|file-based| SourceDB
    PG -->|asyncpg pool| SourceDB
    PG -->|copy_to_table| TargetDB
    MySQL -->|batch inserts| TargetDB
```
