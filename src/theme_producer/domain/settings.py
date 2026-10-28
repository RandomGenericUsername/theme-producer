"""Settings domain model.

Pure, frozen data returned by the settings resolver. The enums live here rather
than in ``domain.enums`` so this ticket stays independent of REQ-005's domain
work; they describe settings values, not theme colours.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any


class RuntimeMode(Enum):
    LOCAL = "local"
    CONTAINER = "container"


class ContainerEngine(Enum):
    DOCKER = "docker"
    PODMAN = "podman"


class Verbosity(Enum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    DEBUG = 3


@dataclass(frozen=True)
class OutputSettings:
    directory: Path
    default_formats: tuple[str, ...]
    overwrite: bool
    verbosity: Verbosity = Verbosity.NORMAL
    # Apply the generated ANSI sequences to the controlling terminal after a
    # successful generate, but only when sequences were produced and stdout is
    # a real TTY.
    apply_to_terminal: bool = True


@dataclass(frozen=True)
class GenerationSettings:
    engine: str
    default_params: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_params", MappingProxyType(self.default_params))


@dataclass(frozen=True)
class TemplatesSettings:
    # Empty means "resolve the templates directory with TemplateDirResolver".
    directory: str = ""


@dataclass(frozen=True)
class RuntimeSettings:
    mode: RuntimeMode


@dataclass(frozen=True)
class ContainerSettings:
    engine: ContainerEngine = ContainerEngine.PODMAN
    image_prefix: str = "tpr"
    image_tag: str = "latest"
    timeout_seconds: int = 300
    memory_limit: str = "512m"


@dataclass(frozen=True)
class AppliedOverride:
    field_path: str
    raw_value: str
    coerced_value: Any
    source: str


@dataclass(frozen=True)
class ConfigResolverResult:
    resolved_path: Path
    applied_overrides: tuple[AppliedOverride, ...]


@dataclass(frozen=True)
class AppSettings:
    output: OutputSettings
    generation: GenerationSettings
    templates: TemplatesSettings
    runtime: RuntimeSettings
    container: ContainerSettings
