"""Domain exceptions for the Theme model."""

from __future__ import annotations

__all__ = ["ThemeValidationError"]


class ThemeValidationError(ValueError):
    """Raised when Theme domain data violates an invariant.

    The message names the offending field and value so callers can surface a
    useful error without inspecting the exception type hierarchy.
    """
