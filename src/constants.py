"""Shared numeric and string constants used across the AutonDB codebase.

All tunable parameters (batch sizes, pool sizes, max tokens, conversion
factors, default dialects, etc.) live here so they are never duplicated
as magic values in other modules.
"""

from __future__ import annotations

DEFAULT_BATCH_SIZE = 1000
DEFAULT_POOL_MIN_SIZE = 2
DEFAULT_POOL_MAX_SIZE = 10
DEFAULT_AI_MAX_TOKENS = 4096
DEFAULT_AI_PROVIDER = "openai"
DEFAULT_AI_MODEL = "gpt-4o"
DEFAULT_TARGET_DIALECT = "postgresql"
BYTES_PER_MB = 1024 * 1024
