"""Pure engine-boundary domain objects.

A :class:`ThemeRequest` names exactly one source, an :class:`EngineConfig`
carries the selected engine plus its parameters, and the catalog objects
describe what an engine accepts. This module has no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from theme_producer.domain.enums import SourceKind
from theme_producer.domain.exceptions import EngineConfigError, ThemeValidationError

__all__ = [
    "KNOWN_ENGINE_NAMES",
    "PARAM_TYPES",
    "EngineConfig",
    "EngineDefinition",
    "EngineParameterDefinition",
    "ThemeRequest",
]

#: Parameter types the catalog schema and the parameter service understand.
PARAM_TYPES: frozenset[str] = frozenset({"float", "int", "str"})

#: Engines this package can describe. Unknown catalog entries are skipped.
KNOWN_ENGINE_NAMES: frozenset[str] = frozenset({"matugen", "native"})


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ThemeValidationError(f"{field_name} must be a non-empty string; got {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ThemeRequest:
    """Exactly one source for a Theme generation request."""

    source_kind: SourceKind | str
    image_path: Path | None = None
    color: str | None = None
    json_path: Path | None = None

    def __post_init__(self) -> None:
        try:
            kind = SourceKind(self.source_kind)
        except (TypeError, ValueError) as exc:
            raise ThemeValidationError(
                f"source_kind must be one of {[item.value for item in SourceKind]}; "
                f"got {self.source_kind!r}"
            ) from exc
        object.__setattr__(self, "source_kind", kind)

        if self.image_path is not None:
            object.__setattr__(self, "image_path", Path(self.image_path))
        if self.json_path is not None:
            object.__setattr__(self, "json_path", Path(self.json_path))

        provided = [
            name
            for name, value in (
                ("image_path", self.image_path),
                ("color", self.color),
                ("json_path", self.json_path),
            )
            if value is not None
        ]
        if len(provided) != 1:
            raise ThemeValidationError(
                "ThemeRequest requires exactly one source "
                f"(image_path, color, or json_path); got {provided or 'none'}"
            )

        expected = {
            SourceKind.IMAGE: "image_path",
            SourceKind.COLOR: "color",
            SourceKind.JSON: "json_path",
        }[kind]
        if provided[0] != expected:
            raise ThemeValidationError(
                f"source_kind {kind.value!r} requires {expected!r}; got {provided[0]!r}"
            )

        if kind is SourceKind.COLOR:
            _require_non_empty_string(self.color, "color")
            assert self.color is not None  # for type checkers
            object.__setattr__(self, "color", self.color.strip())
        elif kind is SourceKind.IMAGE:
            _require_non_empty_string(str(self.image_path), "image_path")
        else:
            _require_non_empty_string(str(self.json_path), "json_path")


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """The selected engine and the parameters to run it with."""

    engine: str
    params: dict[str, Any] = field(default_factory=dict)
    timeout: int = 300

    def __post_init__(self) -> None:
        _require_non_empty_string(self.engine, "engine")
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, int):
            raise EngineConfigError("timeout", f"must be an int; got {self.timeout!r}")
        if not isinstance(self.params, Mapping):
            raise EngineConfigError("params", f"must be a mapping; got {self.params!r}")
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))


@dataclass(frozen=True, slots=True)
class EngineParameterDefinition:
    """One catalog parameter: its type, default, and allowed values."""

    name: str
    param_type: str
    default: Any = None
    choices: tuple[str, ...] | None = None
    description: str = ""
    required: bool = False

    def __post_init__(self) -> None:
        _require_non_empty_string(self.name, "parameter name")
        if self.param_type not in PARAM_TYPES:
            raise EngineConfigError(
                self.name,
                f"param_type must be one of {sorted(PARAM_TYPES)}; got {self.param_type!r}",
            )
        if self.choices is not None:
            if not isinstance(self.choices, tuple | list):
                raise EngineConfigError(
                    self.name, f"choices must be a tuple of strings; got {self.choices!r}"
                )
            choices = tuple(self.choices)
            if not all(isinstance(choice, str) for choice in choices):
                raise EngineConfigError(self.name, f"choices must all be strings; got {choices!r}")
            object.__setattr__(self, "choices", choices)
        if not isinstance(self.required, bool):
            raise EngineConfigError(self.name, f"required must be a bool; got {self.required!r}")
        if not isinstance(self.description, str):
            raise EngineConfigError(
                self.name, f"description must be a string; got {self.description!r}"
            )


@dataclass(frozen=True, slots=True)
class EngineDefinition:
    """One engine catalog entry."""

    name: str
    display_name: str
    description: str
    parameters: tuple[EngineParameterDefinition, ...]
    min_version: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.name, "engine name")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            object.__setattr__(self, "display_name", self.name.title())
        if not isinstance(self.description, str):
            raise EngineConfigError(self.name, "description must be a string")
        if not isinstance(self.min_version, str) or not self.min_version.strip():
            raise EngineConfigError(self.name, "min_version must be a non-empty string")
        params = tuple(self.parameters)
        if not all(isinstance(param, EngineParameterDefinition) for param in params):
            raise EngineConfigError(
                self.name, "parameters must all be EngineParameterDefinition instances"
            )
        names = [param.name for param in params]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise EngineConfigError(self.name, f"duplicate parameter names: {duplicates}")
        object.__setattr__(self, "parameters", params)
