from __future__ import annotations

import pytest

from src.databases.identifier import validate_identifier


class TestValidateIdentifier:
    def test_valid_simple(self) -> None:
        assert validate_identifier("users") == "users"

    def test_valid_with_underscore(self) -> None:
        assert validate_identifier("user_id") == "user_id"

    def test_valid_with_digits(self) -> None:
        assert validate_identifier("table1") == "table1"

    def test_valid_starts_with_underscore(self) -> None:
        assert validate_identifier("_private") == "_private"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier("")

    def test_spaces_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier("user name")

    def test_special_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier("drop;table")

    def test_hyphen_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier("col-name")

    def test_dot_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier("schema.table")

    def test_sql_injection_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier("users; DROP TABLE users")
