from __future__ import annotations

from src.services.providers.base import AIProvider


class SyntheticProvider(AIProvider):
    _SCHEMA_MAPPING_RESPONSE = {
        "tables": [
            {
                "source_table": "example_table",
                "target_table": "example_table",
                "columns": [
                    {
                        "source_name": "id",
                        "source_type": "INTEGER",
                        "target_name": "id",
                        "target_type": "SERIAL",
                        "nullable": False,
                        "is_primary_key": True,
                        "default": None,
                        "transform": None,
                    }
                ],
            }
        ],
        "warnings": [],
    }

    _SANITIZATION_RESPONSE = {
        "issues": [],
        "is_clean": True,
    }

    def __init__(self, schema_response: dict | None = None) -> None:
        self._schema_response = schema_response or self._SCHEMA_MAPPING_RESPONSE

    @property
    def provider_name(self) -> str:
        return "synthetic"

    async def complete(self, system: str, user: str) -> str:
        import json

        if "schema" in user.lower() or "mapping" in system.lower():
            return json.dumps(self._schema_response)
        return json.dumps(self._SANITIZATION_RESPONSE)

    async def complete_json(self, system: str, user: str) -> dict:
        if "schema" in user.lower() or "mapping" in system.lower():
            return self._schema_response
        return self._SANITIZATION_RESPONSE
