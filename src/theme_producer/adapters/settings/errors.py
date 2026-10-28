"""Settings adapter errors.

Deliberately self-contained: REQ-005 owns ``domain.exceptions``, so this
adapter exposes the error the settings resolver raises without importing it.
"""

from __future__ import annotations

from typing import Any


class ConfigResolutionError(Exception):
    """Raised when settings or a resolved path cannot be assembled."""

    def __init__(self, key: str, reason: str, source: Any = None) -> None:
        self.key = key
        self.reason = reason
        self.source = source
        super().__init__(f"Config resolution failed for {key}: {reason}")
