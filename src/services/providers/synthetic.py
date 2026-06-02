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

    def __init__(
        self,
        schema_response: dict | None = None,
        sanitization_response: dict | None = None,
    ) -> None:
        self._schema_response = schema_response or self._SCHEMA_MAPPING_RESPONSE
        self._sanitization_response = (
            sanitization_response or self._SANITIZATION_RESPONSE
        )

    @property
    def provider_name(self) -> str:
        return "synthetic"

    async def complete(self, system: str, user: str) -> str:
        import json

        response = self._select_response(system, user)
        return json.dumps(response)

    async def complete_json(self, system: str, user: str) -> dict:
        return self._select_response(system, user)

    def _select_response(self, system: str, user: str) -> dict:
        if self._is_schema_request(system, user):
            return self._schema_response
        return self._sanitization_response

    @staticmethod
    def _is_schema_request(system: str, user: str) -> bool:
        combined = f"{system} {user}".lower()
        return "schema" in combined or "mapping" in combined or "ddl" in combined
