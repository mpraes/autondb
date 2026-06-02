# AutonDB - Architecture

> Standalone files: [class_diagram.mermaid](./class_diagram.mermaid) | [sequence_diagram.mermaid](./sequence_diagram.mermaid) | [component_diagram.mermaid](./component_diagram.mermaid)
>
> Open `.mermaid` files directly in VSCode with the Mermaid extension for preview.

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

## Sequence Diagram - Migration Flow

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
