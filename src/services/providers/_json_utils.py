"""Shared JSON extraction utility for AI provider responses.

Strips markdown code fences (```json ... ```) that some models wrap
around their JSON output before parsing.
"""

from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    """Extract and parse JSON from a model response that may be wrapped in markdown fences.

    If the text contains a ```json or ``` code fence, extracts the inner
    content. Otherwise, parses the entire text as JSON.

    Args:
        text: Raw response text from an AI model.

    Returns:
        Parsed JSON as a dict.

    Raises:
        json.JSONDecodeError: If the text is not valid JSON.
    """
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text.strip())
