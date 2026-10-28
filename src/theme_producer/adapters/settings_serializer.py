"""Serialize an :class:`AppSettings` value back to TOML.

Two consumers share this: ``tpr dump-config`` and the container processor's
temporary settings file. The output is deterministic, uses only TOML data
types, and can be re-read by ``tomllib`` / the settings assembler.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from theme_producer.domain.settings import (
    AppSettings,
    ContainerEngine,
    RuntimeMode,
    Verbosity,
)

__all__ = ["SettingsSerializer", "serialize_settings", "to_toml"]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"cannot serialize non-finite float {value!r}")
        return repr(value)
    if isinstance(value, Path):
        return f'"{_escape(str(value))}"'
    if isinstance(value, RuntimeMode | ContainerEngine):
        return f'"{_escape(str(value.value))}"'
    if isinstance(value, Verbosity):
        return str(value.value)
    return f'"{_escape(str(value))}"'


def _toml_array(values: tuple[Any, ...] | list[Any]) -> str:
    return "[" + ", ".join(_toml_value(value) for value in values) + "]"


def _write_params(lines: list[str], params: Mapping[str, Any]) -> None:
    if not params:
        lines.append("default_params = {}")
        return
    lines.append("")
    lines.append("[generation.default_params]")
    for key in sorted(params):
        lines.append(f"{_toml_string_key(key)} = {_toml_value(params[key])}")


def _toml_string_key(key: str) -> str:
    if key and all(character.isalnum() or character in "-_" for character in key):
        return key
    return f'"{_escape(key)}"'


def serialize_settings(
    settings: AppSettings,
    *,
    runtime_mode: RuntimeMode | str | None = None,
) -> str:
    """Return canonical TOML for ``settings``.

    ``runtime_mode`` overrides the serialized runtime (the container processor
    forces ``local`` for the inner invocation).
    """
    runtime = settings.runtime.mode if runtime_mode is None else RuntimeMode(runtime_mode)
    lines: list[str] = [
        "[output]",
        f"directory = {_toml_value(settings.output.directory)}",
        f"default_formats = {_toml_array(list(settings.output.default_formats))}",
        f"overwrite = {_toml_value(settings.output.overwrite)}",
        f"verbosity = {_toml_value(settings.output.verbosity.value)}",
        f"apply_to_terminal = {_toml_value(settings.output.apply_to_terminal)}",
        "",
        "[generation]",
        f"engine = {_toml_value(settings.generation.engine)}",
    ]
    _write_params(lines, settings.generation.default_params)
    lines.extend(
        [
            "",
            "[templates]",
            f"directory = {_toml_value(settings.templates.directory)}",
            "",
            "[runtime]",
            f"mode = {_toml_value(runtime)}",
            "",
            "[container]",
            f"engine = {_toml_value(settings.container.engine)}",
            f"image_prefix = {_toml_value(settings.container.image_prefix)}",
            f"image_tag = {_toml_value(settings.container.image_tag)}",
            f"timeout_seconds = {_toml_value(settings.container.timeout_seconds)}",
            f"memory_limit = {_toml_value(settings.container.memory_limit)}",
            "",
        ]
    )
    return "\n".join(lines)


class SettingsSerializer:
    """Small object wrapper so adapters can depend on one callable."""

    def to_toml(
        self,
        settings: AppSettings,
        *,
        runtime_mode: RuntimeMode | str | None = None,
    ) -> str:
        return serialize_settings(settings, runtime_mode=runtime_mode)


def to_toml(settings: AppSettings) -> str:
    """Convenience alias for the default serialization."""
    return serialize_settings(settings)
