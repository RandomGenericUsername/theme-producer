"""``tpr show`` — re-extract a Theme for display without writing files."""

from __future__ import annotations

from pathlib import Path

import typer

from theme_producer.cli._helpers import (
    build_request,
    fail,
    load_catalog,
    output_adapter,
    resolve_engine_name,
    resolve_settings,
    selected,
)
from theme_producer.cli._params import parse_params, resolve_engine_params
from theme_producer.cli.options import (
    CONFIG_OPT,
    ENGINE_OPT,
    PROJECTION_MODE_OPT,
    RUNTIME_OPT,
    SMART_THRESHOLD_OPT,
    TEMPLATES_DIR_OPT,
)
from theme_producer.domain.settings import ContainerEngine, RuntimeMode
from theme_producer.factory import CliDependencies, create_processor


def show(
    ctx: typer.Context,
    image: Path = typer.Argument(..., help="Input wallpaper image"),
    engine: str | None = typer.Option(
        None, "--engine", help="Theme engine (default: settings.generation.engine)"
    ),
    param: list[str] = typer.Option(  # noqa: B008
        [], "--param", help="Engine parameter override K=V"
    ),
    mode: str | None = PROJECTION_MODE_OPT,
    smart_threshold: float | None = SMART_THRESHOLD_OPT,
    runtime: RuntimeMode | None = RUNTIME_OPT,
    container_engine: ContainerEngine | None = ENGINE_OPT,
    config_path: Path | None = CONFIG_OPT,
    templates_dir: Path | None = TEMPLATES_DIR_OPT,
) -> None:
    deps: CliDependencies = ctx.obj["deps"]
    try:
        settings = resolve_settings(
            deps,
            ctx,
            config_path=config_path,
            runtime=runtime,
            container_engine=container_engine,
        )
        catalog = load_catalog(deps)
        engine_name = resolve_engine_name(engine, settings, catalog)
        definition = catalog[engine_name]
        resolved_params = resolve_engine_params(
            definition, settings.generation.default_params, parse_params(param)
        )
        effective_templates = selected(ctx, "templates_dir", templates_dir)
        if effective_templates is None and settings.templates.directory:
            effective_templates = settings.templates.directory
        effective_mode = mode if mode is not None else settings.output.default_mode
        effective_threshold = (
            smart_threshold
            if smart_threshold is not None
            else settings.output.smart_threshold
        )
        request = build_request(
            image_path=image,
            engine=engine_name,
            params=resolved_params,
            formats=(),
            output_dir=settings.output.directory,
            settings=settings,
            mode=effective_mode,
            smart_threshold=effective_threshold,
        )
        processor = create_processor(
            deps,
            request,
            settings,
            templates_dir=Path(effective_templates) if effective_templates else None,
        )
        result = processor.process_show(request, settings)
        output_adapter(deps).process_result(result)
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
