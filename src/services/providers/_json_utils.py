from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text.strip())
