"""Pydantic boundary schema for ``engines.yaml``.

The assembler validates the catalog document through these models; the loader
then converts the validated shape into pure domain dataclasses. No I/O here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, RootModel, field_validator

from theme_producer.domain.engines import PARAM_TYPES

__all__ = [
    "EngineDefinitionSchema",
    "EngineParameterSchema",
    "EnginesCatalogSchema",
]


class EngineParameterSchema(BaseModel):
    name: str
    param_type: str
    default: Any = None
    choices: list[str] | None = None
    description: str = ""
    required: bool = False

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("parameter name must not be empty")
        return value

    @field_validator("param_type")
    @classmethod
    def _validate_param_type(cls, value: str) -> str:
        if value not in PARAM_TYPES:
            raise ValueError(
                f"Invalid param_type '{value}' — must be one of: {', '.join(sorted(PARAM_TYPES))}"
            )
        return value

    @field_validator("choices")
    @classmethod
    def _validate_choices(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and not all(isinstance(choice, str) for choice in value):
            raise ValueError("choices must be a list of strings")
        return value


class EngineDefinitionSchema(BaseModel):
    display_name: str = ""
    description: str = ""
    min_version: str = "0.0.0"
    parameters: list[EngineParameterSchema] = []


class EnginesCatalogSchema(RootModel[dict[str, EngineDefinitionSchema]]):
    pass
