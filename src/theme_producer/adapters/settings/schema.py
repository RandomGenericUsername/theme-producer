"""Pydantic boundary schema for ``settings.toml``.

The assembler validates TOML and override values through these models; the
resolver then converts the validated model into the pure domain dataclasses.
Keep this layer free of I/O.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from theme_producer.domain.generation import InvalidSmartThresholdError
from theme_producer.domain.settings import ContainerEngine, RuntimeMode
from theme_producer.domain.smart_mode import ProjectionMode, validate_threshold

_MEMORY_LIMIT_PATTERN = re.compile(r"^\d+[kKmMgGtT]?$")
_PROJECTION_MODES = {mode.value for mode in ProjectionMode}


class OutputSettingsSchema(BaseModel):
    directory: Path
    default_formats: list[str] = Field(default_factory=list)
    overwrite: bool = False
    verbosity: int = Field(default=1, ge=0, le=3)
    apply_to_terminal: bool = True
    default_mode: str = "dark"
    smart_threshold: float = 0.5

    @field_validator("directory", mode="before")
    @classmethod
    def _validate_directory_not_empty(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("directory must not be empty")
        return value

    @field_validator("default_mode", mode="before")
    @classmethod
    def _validate_default_mode(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError(
                f"Invalid output default mode {value!r} — must be dark, light, or smart"
            )
        normalized = value.strip().lower()
        if normalized not in _PROJECTION_MODES:
            raise ValueError(
                f"Invalid output default mode '{value}' — must be one of: "
                f"{', '.join(sorted(_PROJECTION_MODES))}"
            )
        return normalized

    @field_validator("smart_threshold", mode="before")
    @classmethod
    def _validate_smart_threshold(cls, value: object) -> float:
        try:
            return validate_threshold(value)
        except InvalidSmartThresholdError as exc:
            raise ValueError(str(exc)) from exc


class GenerationSettingsSchema(BaseModel):
    engine: str = "matugen"
    default_params: dict[str, Any] = Field(default_factory=dict)
    scheme_policy: str = "balanced"

    @field_validator("engine")
    @classmethod
    def _validate_engine_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("engine must not be empty")
        return value

    @field_validator("scheme_policy")
    @classmethod
    def _validate_scheme_policy_not_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("scheme_policy must be a non-empty profile name")
        return value


class TemplatesSettingsSchema(BaseModel):
    # Empty means "resolve the templates directory with TemplateDirResolver".
    directory: str = ""


class RuntimeSettingsSchema(BaseModel):
    mode: str = "local"

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        valid = {member.value for member in RuntimeMode}
        if value not in valid:
            raise ValueError(
                f"Invalid runtime mode '{value}' — must be one of: {', '.join(sorted(valid))}"
            )
        return value


class ContainerSettingsSchema(BaseModel):
    engine: str = "podman"

    @field_validator("engine")
    @classmethod
    def _validate_engine(cls, value: str) -> str:
        valid = {member.value for member in ContainerEngine}
        if value not in valid:
            raise ValueError(
                f"Invalid container engine '{value}' — must be one of: {', '.join(sorted(valid))}"
            )
        return value

    @field_validator("memory_limit")
    @classmethod
    def _validate_memory_limit(cls, value: str) -> str:
        if not _MEMORY_LIMIT_PATTERN.match(value):
            raise ValueError(
                f"Invalid memory limit '{value}' — must be a number optionally followed by k/m/g/t"
            )
        return value.lower()

    @field_validator("timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: int) -> int:
        if value < 0:
            raise ValueError(f"Timeout must be non-negative, got {value}")
        return value

    image_prefix: str = "tpr"
    # Empty means "resolve to v<package version>" in the config resolver.
    image_tag: str = ""
    timeout_seconds: int = 300
    memory_limit: str = "512m"


class CoreSettingsSchema(BaseModel):
    output: OutputSettingsSchema
    generation: GenerationSettingsSchema = Field(default_factory=GenerationSettingsSchema)
    templates: TemplatesSettingsSchema = Field(default_factory=TemplatesSettingsSchema)
    runtime: RuntimeSettingsSchema = Field(default_factory=RuntimeSettingsSchema)
    container: ContainerSettingsSchema = Field(default_factory=ContainerSettingsSchema)
