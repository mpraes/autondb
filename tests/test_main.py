from __future__ import annotations

import pytest

from src.main import parse_args


class TestParseArgs:
    def test_required_args(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
            ]
        )
        assert args.source_dsn == "./db.sqlite"
        assert args.source_dialect == "sqlite"
        assert args.target_dsn == "postgres://user:pass@host/db"
        assert args.target_dialect == "postgresql"

    def test_default_batch_size(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
            ]
        )
        assert args.batch_size == 1000

    def test_custom_batch_size(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
                "--batch-size",
                "5000",
            ]
        )
        assert args.batch_size == 5000

    def test_auto_approve_flag(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
                "--auto-approve",
            ]
        )
        assert args.auto_approve is True

    def test_auto_approve_default(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
            ]
        )
        assert args.auto_approve is False

    def test_invalid_dialect_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(
                [
                    "--source-dsn",
                    "./db.sqlite",
                    "--source-dialect",
                    "oracle",
                    "--target-dsn",
                    "postgres://user:pass@host/db",
                    "--target-dialect",
                    "postgresql",
                ]
            )

    def test_missing_required_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args([])

    def test_ai_provider_and_model(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
                "--ai-provider",
                "groq",
                "--ai-model",
                "llama-3.3-70b-versatile",
            ]
        )
        assert args.ai_provider == "groq"
        assert args.ai_model == "llama-3.3-70b-versatile"

    def test_ai_provider_default_none(self) -> None:
        args = parse_args(
            [
                "--source-dsn",
                "./db.sqlite",
                "--source-dialect",
                "sqlite",
                "--target-dsn",
                "postgres://user:pass@host/db",
                "--target-dialect",
                "postgresql",
            ]
        )
        assert args.ai_provider is None
        assert args.ai_model is None
