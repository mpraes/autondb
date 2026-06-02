from __future__ import annotations

import argparse
import asyncio

from src.constants import DEFAULT_BATCH_SIZE
from src.databases.factory import DIALECTS, build_db
from src.engine.migration import MigrationEngine
from src.services.ai_service import AIService


async def run_migration(args: argparse.Namespace) -> None:
    source = build_db(args.source_dialect, args.source_dsn)
    target = build_db(args.target_dialect, args.target_dsn)

    ai = AIService.from_env(provider_name=args.ai_provider, model=args.ai_model)

    try:
        await source.connect()
        await target.connect()

        schema = await source.get_schema()
        mapping = await ai.map_schema(schema, args.source_dialect, args.target_dialect)

        print("=== Schema Mapping ===")
        for table in mapping.tables:
            print(f"\nTable: {table.source_table} → {table.target_table}")
            for col in table.columns:
                transform = f"  [transform: {col.transform}]" if col.transform else ""
                print(
                    f"  {col.source_name} ({col.source_type}) → {col.target_name} ({col.target_type}){transform}"
                )

        if mapping.warnings:
            print("\n=== Warnings ===")
            for w in mapping.warnings:
                print(f"  ⚠  {w}")

        print(f"\n=== Target DDL ({mapping.target_dialect}) ===")
        print(mapping.to_ddl())

        if not args.auto_approve:
            answer = input("\nProceed with migration? [y/N] ").strip().lower()
            if answer not in ("y", "yes"):
                print("Migration cancelled.")
                return

        engine = MigrationEngine(
            source=source,
            target=target,
            mapping=mapping,
            batch_size=args.batch_size,
            on_progress=lambda kpi: print(
                f"\r  {kpi.format_snapshot()}", end="", flush=True
            ),
        )

        print("\n=== Starting Migration ===")
        audit = await engine.run()
        print()

        print(audit.summary())
        if not audit.all_match:
            print(
                "\nSome tables have row count mismatches — manual review recommended."
            )

    finally:
        await source.disconnect()
        await target.disconnect()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="autondb",
        description="AI-assisted database migration tool",
    )
    parser.add_argument(
        "--source-dsn",
        required=True,
        help="Source database connection string or file path",
    )
    parser.add_argument(
        "--source-dialect",
        required=True,
        choices=sorted(DIALECTS),
        help="Source database dialect",
    )
    parser.add_argument(
        "--target-dsn",
        required=True,
        help="Target database connection string or file path",
    )
    parser.add_argument(
        "--target-dialect",
        required=True,
        choices=sorted(DIALECTS),
        help="Target database dialect",
    )
    parser.add_argument(
        "--ai-provider",
        default=None,
        help="AI provider (openai, groq, openrouter, anthropic, synthetic)",
    )
    parser.add_argument(
        "--ai-model",
        default=None,
        help="AI model name (overrides default for provider)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows per batch during migration (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip approval prompt and start migration automatically",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    asyncio.run(run_migration(args))


if __name__ == "__main__":
    main()
