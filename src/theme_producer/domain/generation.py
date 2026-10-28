"""Generation request/result value objects shared by the CLI and processors.

This module is deliberately free of I/O. It describes *what* to generate and
*what happened*, plus the typed errors the processor adapters raise. The
canonical theme object lives in :mod:`theme_producer.domain.models` and is never
duplicated here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from theme_producer.domain.models import Theme
from theme_producer.domain.settings import AppliedOverride, RuntimeMode

__all__ = [
    "AppliedOverride",
    "ContainerImageNotFoundError",
    "ContainerRuntimeError",
    "ContainerRuntimeUnavailableError",
    "DockerfileNotFoundError",
    "EngineInfo",
    "EngineNotRegisteredError",
    "EngineUnavailableError",
    "GenerationError",
    "GenerationRequest",
    "GenerationResult",
    "OutputWriteError",
    "UnknownFormatError",
]


class GenerationError(RuntimeError):
    """Base class for typed, user-facing generation/CLI failures.

    ``type`` is intentionally the concrete class name: the JSON error contract
    exposes a stable ``error.type`` string without leaking tracebacks.
    """

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.message = message
        self.details: dict[str, Any] = dict(details or {})
        super().__init__(message)

    @property
    def type(self) -> str:
        """The stable error type used by the JSON contract."""
        return type(self).__name__


class UnknownFormatError(GenerationError):
    """Raised when ``--format`` names a format with no projection."""


class EngineNotRegisteredError(GenerationError):
    """Raised when the selected engine has no implementation on this host."""


class EngineUnavailableError(GenerationError):
    """Raised when an engine is registered but cannot run here."""


class ContainerRuntimeUnavailableError(GenerationError):
    """Raised when the configured container engine cannot be created."""


class ContainerRuntimeError(GenerationError):
    """Raised when an oci-runtime operation fails."""


class ContainerImageNotFoundError(GenerationError):
    """Raised when the requested engine/base image has not been built."""


class DockerfileNotFoundError(GenerationError):
    """Raised when a Dockerfile required for an image build is absent."""


class OutputWriteError(GenerationError):
    """Raised when a generated/config artifact cannot be written."""


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Everything a processor needs for one ``generate``/``show`` run."""

    image_path: Path
    engine: str
    params: Mapping[str, Any] = field(default_factory=dict)
    formats: tuple[str, ...] = ()
    output_dir: Path = Path(".")
    overwrite: bool = False
    runtime: RuntimeMode = RuntimeMode.LOCAL
    dry_run: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "image_path", Path(self.image_path))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        object.__setattr__(self, "params", dict(self.params))
        object.__setattr__(self, "formats", tuple(self.formats))
        if isinstance(self.runtime, str):
            object.__setattr__(self, "runtime", RuntimeMode(self.runtime))


@dataclass(frozen=True, slots=True)
class EngineInfo:
    """One catalog entry enriched with host/image availability."""

    name: str
    display_name: str
    description: str
    min_version: str
    available: bool
    image: str | None = None
    image_available: bool | None = None
    parameters: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "min_version": self.min_version,
            "available": self.available,
            "image": self.image,
            "image_available": self.image_available,
            "parameters": [dict(parameter) for parameter in self.parameters],
        }


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """The machine-readable outcome of one CLI verb."""

    command: str
    engine: str
    success: bool = True
    theme: Theme | None = None
    output_files: tuple[Path, ...] = ()
    duration: float = 0.0
    plan: str | None = None
    projections: tuple[str, ...] = ()
    stderr: str = ""
    return_code: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": self.success,
            "command": self.command,
            "engine": self.engine,
            "theme": self.theme.to_dict() if self.theme is not None else None,
            "output_files": [str(path) for path in self.output_files],
            "duration": round(self.duration, 6),
        }
        if self.plan is not None:
            payload["plan"] = self.plan
            payload["projections"] = list(self.projections)
        if self.stderr:
            payload["stderr"] = self.stderr
        if self.return_code:
            payload["return_code"] = self.return_code
        return payload
