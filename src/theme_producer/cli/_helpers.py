"""Shared CLI helpers: settings, engine resolution, requests, image names."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn

import typer
from oci_runtime import engine_qualified_image

from theme_producer.adapters.projections.registry import (
    default_format_names,
    projections_for_formats,
)
from theme_producer.domain.engines import EngineDefinition
from theme_producer.domain.generation import (
    EngineInfo,
    EngineNotRegisteredError,
    GenerationRequest,
)
from theme_producer.domain.settings import (
    AppSettings,
    ContainerEngine,
    RuntimeMode,
)
from theme_producer.factory import (
    CliDependencies,
    create_container_runtime,
)
from theme_producer.factory import (
    resolve_templates_dir as _resolve_templates_dir,
)
from theme_producer.ports.container_runtime import ContainerRuntimePort
from theme_producer.ports.output import OutputPort
from theme_producer.ports.theme_engine import ThemeEnginePort


def selected(ctx: typer.Context, key: str, command_value: Any) -> Any:
    """Command option wins over the global callback value."""
    if command_value is not None:
        return command_value
    return (ctx.obj or {}).get(key)


def resolve_templates_dir(
    deps: CliDependencies,
    templates_dir: Path | str | None = None,
) -> Path:
    """Re-export the factory resolver for command modules."""
    return _resolve_templates_dir(deps, templates_dir)


def resolve_settings(
    deps: CliDependencies,
    ctx: typer.Context,
    *,
    config_path: Path | None = None,
    runtime: RuntimeMode | None = None,
    container_engine: ContainerEngine | None = None,
) -> AppSettings:
    """Resolve settings with THEME/CLI overrides and the 5-strategy chain."""
    effective_config = selected(ctx, "config_path", config_path)
    effective_runtime = selected(ctx, "runtime", runtime)
    effective_container = selected(ctx, "container_engine", container_engine)

    overrides = dict((ctx.obj or {}).get("cli_overrides", {}))
    if effective_runtime is not None:
        overrides["runtime.mode"] = RuntimeMode(effective_runtime).value
    if effective_container is not None:
        overrides["container.engine"] = ContainerEngine(effective_container).value

    return deps.config_resolver.resolve(
        explicit_path=str(effective_config) if effective_config is not None else None,
        cli_overrides=overrides,
    )


def load_catalog(deps: CliDependencies) -> dict[str, EngineDefinition]:
    return deps.engine_catalog_loader.load()


def resolve_engine_name(
    requested: str | None,
    settings: AppSettings,
    catalog: dict[str, EngineDefinition],
) -> str:
    name = (requested or settings.generation.engine or "").strip()
    if not name:
        raise EngineNotRegisteredError("no engine selected and settings define no default")
    if name not in catalog:
        known = ", ".join(sorted(catalog)) or "none"
        raise EngineNotRegisteredError(
            f"engine {name!r} is not in the engine catalog; known engines: {known}"
        )
    return name


def resolve_formats(
    requested: list[str] | tuple[str, ...] | None,
    settings: AppSettings,
) -> tuple[str, ...]:
    """Resolve the ``--format`` list, defaulting to all non-dev projections."""
    if requested:
        formats = tuple(str(item).strip() for item in requested if str(item).strip())
    elif settings.output.default_formats:
        formats = tuple(str(item) for item in settings.output.default_formats)
    else:
        formats = default_format_names()
    projections_for_formats(formats)  # fail early with a typed, clear error
    return formats


def build_request(
    *,
    image_path: Path,
    engine: str,
    params: dict[str, Any],
    formats: tuple[str, ...],
    output_dir: Path,
    settings: AppSettings,
    dry_run: bool = False,
) -> GenerationRequest:
    return GenerationRequest(
        image_path=image_path,
        engine=engine,
        params=params,
        formats=formats,
        output_dir=output_dir,
        overwrite=settings.output.overwrite,
        runtime=settings.runtime.mode,
        dry_run=dry_run,
    )


def output_adapter(deps: CliDependencies) -> OutputPort:
    if deps.output_adapter is None:
        raise RuntimeError("CLI dependencies have no output adapter")
    return deps.output_adapter


def fail(deps: CliDependencies, exc: BaseException) -> NoReturn:
    """Render a typed error and exit non-zero."""
    if deps.output_adapter is not None:
        deps.output_adapter.error(exc)
    else:  # pragma: no cover - only an un-wired test dependency reaches this
        typer.echo(f"error: {type(exc).__name__}: {exc}", err=True)
    raise typer.Exit(code=1)


def container_runtime_for(deps: CliDependencies, settings: AppSettings) -> ContainerRuntimePort:
    if deps.container_runtime is not None:
        return deps.container_runtime
    return create_container_runtime(settings.container.engine)


def base_image_name(
    settings: AppSettings,
    container_engine: ContainerEngine | str | None = None,
) -> str:
    engine = container_engine or settings.container.engine
    engine_value = engine.value if isinstance(engine, ContainerEngine) else str(engine)
    return engine_qualified_image(
        f"{settings.container.image_prefix}-base",
        engine_value,
        settings.container.image_tag,
    )


def engine_image_name(
    settings: AppSettings,
    theme_engine: str,
    container_engine: ContainerEngine | str | None = None,
) -> str:
    engine = container_engine or settings.container.engine
    engine_value = engine.value if isinstance(engine, ContainerEngine) else str(engine)
    return engine_qualified_image(
        f"{settings.container.image_prefix}-{theme_engine}",
        engine_value,
        settings.container.image_tag,
    )


def parameter_rows(definition: EngineDefinition) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "name": parameter.name,
            "type": parameter.param_type,
            "default": parameter.default,
            "choices": list(parameter.choices) if parameter.choices else None,
            "description": parameter.description,
            "required": parameter.required,
        }
        for parameter in definition.parameters
    )


def engine_infos(
    catalog: dict[str, EngineDefinition],
    registry: dict[str, ThemeEnginePort],
    *,
    settings: AppSettings | None = None,
    runtime: ContainerRuntimePort | None = None,
) -> list[EngineInfo]:
    infos: list[EngineInfo] = []
    for name in sorted(catalog):
        definition = catalog[name]
        implementation = registry.get(name)
        available = bool(implementation and implementation.is_available())
        image: str | None = None
        image_available: bool | None = None
        if settings is not None and runtime is not None:
            image = engine_image_name(settings, name)
            try:
                image_available = bool(runtime.image_exists(image))
            except Exception:
                image_available = False
        infos.append(
            EngineInfo(
                name=name,
                display_name=definition.display_name,
                description=definition.description,
                min_version=definition.min_version,
                available=available,
                image=image,
                image_available=image_available,
                parameters=parameter_rows(definition),
            )
        )
    return infos


def serialize_settings(settings: AppSettings) -> dict[str, Any]:
    """Convert AppSettings to a JSON-safe nested dict (enums/paths unwrapped)."""

    def convert(value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            return {field.name: convert(getattr(value, field.name)) for field in fields(value)}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, tuple | list):
            return [convert(item) for item in value]
        if isinstance(value, Mapping):
            return {str(key): convert(item) for key, item in value.items()}
        return value

    result = convert(settings)
    assert isinstance(result, dict)
    return result
