"""Domain exceptions for the Theme model and the engine boundary."""

from __future__ import annotations

__all__ = [
    "EngineConfigError",
    "EngineExecutionError",
    "EngineNotAvailableError",
    "EngineParseError",
    "InvalidImageMetricsError",
    "InvalidSchemePolicyCatalogError",
    "InvalidSchemeRuleError",
    "SchemePolicyError",
    "ThemeValidationError",
    "UnknownSchemePolicyError",
]


class ThemeValidationError(ValueError):
    """Raised when Theme domain data violates an invariant.

    The message names the offending field and value so callers can surface a
    useful error without inspecting the exception type hierarchy.
    """


class EngineConfigError(ValueError):
    """Raised when an engine request, catalog entry, or parameter is invalid."""

    def __init__(self, key: str, reason: str | None = None) -> None:
        if reason is None:
            reason = key
            key = "engine"
        self.key = key
        self.reason = reason
        super().__init__(f"Engine config error for {key}: {reason}")


class EngineNotAvailableError(RuntimeError):
    """Raised when the engine executable cannot be found."""

    def __init__(self, engine: str, hint: str = "") -> None:
        self.engine = engine
        self.hint = hint
        message = f"Engine {engine!r} is not available"
        if hint:
            message = f"{message}. Hint: {hint}"
        super().__init__(message)


class EngineExecutionError(RuntimeError):
    """Raised when an engine process fails, times out, or cannot be spawned."""

    def __init__(
        self,
        engine: str,
        message: str,
        *,
        stderr: str = "",
        returncode: int | None = None,
    ) -> None:
        self.engine = engine
        self.message = message
        self.stderr = stderr
        self.returncode = returncode
        suffix = f" (exit {returncode})" if returncode is not None else ""
        if stderr.strip():
            suffix = f"{suffix}: {stderr.strip()}"
        super().__init__(f"Engine {engine!r} failed: {message}{suffix}")


class EngineParseError(ValueError):
    """Raised when engine output does not match the expected Theme shape."""

    def __init__(self, engine: str, message: str) -> None:
        self.engine = engine
        self.message = message
        super().__init__(f"Engine {engine!r} produced unparseable output: {message}")


class SchemePolicyError(ValueError):
    """Base class for invalid scheme-policy data or resolution requests.

    Messages name the offending field and value so callers can surface a
    useful error without inspecting the exception hierarchy.
    """


class InvalidImageMetricsError(SchemePolicyError):
    """Raised when an image metric is missing, unknown, or outside ``[0, 1]``."""


class InvalidSchemeRuleError(SchemePolicyError):
    """Raised when a condition, rule, or scheme policy violates an invariant."""


class InvalidSchemePolicyCatalogError(SchemePolicyError):
    """Raised when a scheme-policy catalog is malformed or unsupported."""


class UnknownSchemePolicyError(SchemePolicyError):
    """Raised when a policy name is not present in the catalog."""
