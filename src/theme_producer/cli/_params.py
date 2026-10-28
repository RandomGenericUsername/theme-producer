"""``--param`` parsing, coercion, and catalog-driven resolution (AD-7)."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import Any

from config_assembler_engine.adapters.type_coercer import PydanticTypeCoercer
from config_assembler_engine.domain.models import OverrideSource, OverrideValue
from config_assembler_engine.errors import OverrideCoercionError

from theme_producer.domain.engine_params import ParameterResolutionService
from theme_producer.domain.engines import EngineDefinition
from theme_producer.domain.exceptions import EngineConfigError

__all__ = ["coerce_params", "parse_params", "resolve_engine_params"]

_TYPE_MAP: dict[str, type] = {"str": str, "int": int, "float": float}


def parse_params(raw: list[str]) -> dict[str, str]:
    """Parse repeated ``K=V`` flags, dropping malformed entries.

    The value keeps everything after the first ``=`` (so ``k=a=b`` is valid),
    and the last occurrence of a key wins.
    """
    result: dict[str, str] = {}
    for entry in raw:
        if "=" not in entry:
            print(
                f"Warning: ignoring malformed parameter {entry!r} (expected key=value)",
                file=sys.stderr,
            )
            continue
        key, _, value = entry.partition("=")
        key = key.strip()
        if not key:
            print(
                f"Warning: ignoring malformed parameter with empty key {entry!r}",
                file=sys.stderr,
            )
            continue
        result[key] = value.strip()
    return result


def coerce_params(
    definition: EngineDefinition,
    overrides: Mapping[str, Any],
) -> dict[str, Any]:
    """Coerce raw override strings using the catalog parameter types."""
    definitions = {parameter.name: parameter for parameter in definition.parameters}
    coercer = PydanticTypeCoercer()
    coerced: dict[str, Any] = {}
    for name, value in overrides.items():
        parameter = definitions.get(name)
        if parameter is None:
            # Leave it for ParameterResolutionService to report as unknown.
            coerced[name] = value
            continue
        try:
            coerced[name] = coercer.coerce(
                OverrideValue(
                    field_path=name,
                    raw_value=str(value),
                    source=OverrideSource.CLI,
                ),
                _TYPE_MAP[parameter.param_type],
            )
        except OverrideCoercionError as exc:
            raise EngineConfigError(
                name,
                f"expected {parameter.param_type}; got {value!r}",
            ) from exc
    return coerced


def resolve_engine_params(
    definition: EngineDefinition,
    defaults: Mapping[str, Any] | None,
    overrides: Mapping[str, str] | None,
) -> dict[str, Any]:
    """Merge catalog/CLI overrides, coerce them, then resolve defaults/choices."""
    merged = {**(defaults or {}), **(overrides or {})}
    coerced = coerce_params(definition, merged)
    return ParameterResolutionService.resolve_all(definition.parameters, coerced)
