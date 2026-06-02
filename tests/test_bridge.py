from __future__ import annotations

import json
import subprocess
import sys

import pytest

from src.bridge import _emit, _build_db
from src.databases.sqlite_db import SQLiteDB
from src.databases.postgres_db import PostgresDB
from src.databases.mysql_db import MySQLDB


class TestBridgeHelpers:
    def test_build_db_sqlite(self) -> None:
        db = _build_db("sqlite", "/tmp/test.db")
        assert isinstance(db, SQLiteDB)

    def test_build_db_postgresql(self) -> None:
        db = _build_db("postgresql", "postgres://user:pass@localhost/db")
        assert isinstance(db, PostgresDB)

    def test_build_db_mysql(self) -> None:
        db = _build_db("mysql", "mysql://user:pass@localhost/db")
        assert isinstance(db, MySQLDB)

    def test_build_db_invalid(self) -> None:
        with pytest.raises(ValueError, match="Unsupported dialect"):
            _build_db("oracle", "oracle://host/db")

    def test_emit_writes_json_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        _emit("test_event", {"key": "value", "num": 42})
        captured = capsys.readouterr()
        line = captured.out.strip()
        parsed = json.loads(line)
        assert parsed["event"] == "test_event"
        assert parsed["payload"]["key"] == "value"
        assert parsed["payload"]["num"] == 42

    def test_emit_with_non_serializable(self, capsys: pytest.CaptureFixture[str]) -> None:
        from datetime import datetime

        dt = datetime(2024, 1, 15, 12, 0, 0)
        _emit("date_event", {"ts": dt})
        captured = capsys.readouterr()
        line = captured.out.strip()
        parsed = json.loads(line)
        assert "2024" in parsed["payload"]["ts"]


class TestBridgeCLI:
    def test_invalid_args_exits(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "src.bridge"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_unknown_command_exits(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "src.bridge", "unknown", "{}"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
