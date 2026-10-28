"""Resolution of engine parameters from catalog defaults plus overrides.

The CLI coerces ``--param`` strings with ``PydanticTypeCoercer`` before calling
here (AD-7); this service owns defaults, choice validation, required-parameter
checks, and a final type check so the engine adapter receives clean values.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from theme_producer.domain.engines import EngineParameterDefinition
from theme_producer.domain.exceptions import EngineConfigError

__all__ = ["ParameterResolutionService"]


class ParameterResolutionService:
    """Resolve catalog parameter definitions against user overrides."""

    @staticmethod
    def resolve_all(
        parameters: tuple[EngineParameterDefinition, ...] | list[EngineParameterDefinition],
        overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        provided = dict(overrides or {})
        definitions = tuple(parameters)
        known = {param.name for param in definitions}
        unknown = sorted(set(provided) - known)
        if unknown:
            raise EngineConfigError(
                "params",
                f"unknown parameter(s) {unknown}; known parameters: {sorted(known)}",
            )

        resolved: dict[str, Any] = {}
        for param in definitions:
            if param.name in provided:
                value = provided[param.name]
            elif param.default is not None:
                value = param.default
            elif param.required:
                raise EngineConfigError(
                    param.name,
                    f"required parameter '{param.name}' has no default "
                    "and no override was provided",
                )
            else:
                value = None
            resolved[param.name] = _coerce(param, value)
        return resolved


def _coerce(param: EngineParameterDefinition, value: Any) -> Any:
    if value is None:
        if param.required:
            raise EngineConfigError(
                param.name,
                f"required parameter '{param.name}' cannot be None",
            )
        return None

    if param.param_type == "float":
        coerced = _as_float(param, value)
    elif param.param_type == "int":
        coerced = _as_int(param, value)
    else:
        coerced = _as_str(param, value)

    if param.choices is not None and coerced not in param.choices:
        raise EngineConfigError(
            param.name,
            f"invalid choice {coerced!r}; must be one of {list(param.choices)}",
        )
    return coerced


def _as_float(param: EngineParameterDefinition, value: Any) -> float:
    if isinstance(value, bool):
        raise EngineConfigError(param.name, f"expected a float; got {value!r}")
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError as exc:
            raise EngineConfigError(param.name, f"expected a float; got {value!r}") from exc
    else:
        raise EngineConfigError(param.name, f"expected a float; got {value!r}")
    if not math.isfinite(number):
        raise EngineConfigError(param.name, f"expected a finite float; got {value!r}")
    return number


def _as_int(param: EngineParameterDefinition, value: Any) -> int:
    if isinstance(value, bool):
        raise EngineConfigError(param.name, f"expected an int; got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise EngineConfigError(param.name, f"expected an int; got {value!r}")
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError as exc:
            raise EngineConfigError(param.name, f"expected an int; got {value!r}") from exc
    raise EngineConfigError(param.name, f"expected an int; got {value!r}")


def _as_str(param: EngineParameterDefinition, value: Any) -> str:
    if not isinstance(value, str):
        raise EngineConfigError(param.name, f"expected a string; got {value!r}")
    return value
