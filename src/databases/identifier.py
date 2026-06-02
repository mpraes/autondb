from __future__ import annotations

import re

_INVALID_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_identifier(name: str) -> str:
    """Validate a SQL identifier to prevent injection.

    Only allows alphanumeric characters and underscores.
    Must not be empty.

    Raises:
        ValueError: If the identifier is invalid.
    """
    if not name or not _INVALID_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: '{name}'")
    return name
