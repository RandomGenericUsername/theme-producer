"""``tpr generate`` — engine → Theme → theme.json + projections."""

from __future__ import annotations

from pathlib import Path

import typer

from theme_producer.cli._helpers import (
    build_request,
    fail,
    load_catalog,
    output_adapter,
    resolve_engine_name,
    resolve_formats,
    resolve_settings,
    selected,
)
from theme_producer.cli._params import parse_params, resolve_engine_params
from theme_producer.cli.options import (
    CONFIG_OPT,
    ENGINE_OPT,
    PROJECTION_MODE_OPT,
    RUNTIME_OPT,
    TEMPLATES_DIR_OPT,
)
from theme_producer.domain.settings import ContainerEngine, RuntimeMode
from theme_producer.factory import CliDependencies, create_processor


def generate(
    ctx: typer.Context,
    image: Path = typer.Argument(..., help="Input wallpaper image"),
    engine: str | None = typer.Option(
        None, "--engine", help="Theme engine (default: settings.generation.engine)"
    ),
    formats: list[str] = typer.Option(  # noqa: B008
        [],
        "--format",
        "-f",
        help="Output format(s): yaml, conf, gtk.css, adw.css, sequences, rasi, "
        "kitty, btop.theme, html, json",
    ),
    param: list[str] = typer.Option(  # noqa: B008
        [], "--param", help="Engine parameter override K=V"
    ),
    mode: str = PROJECTION_MODE_OPT,
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Print the resolved plan without generating"
    ),
    runtime: RuntimeMode | None = RUNTIME_OPT,
    container_engine: ContainerEngine | None = ENGINE_OPT,
    config_path: Path | None = CONFIG_OPT,
    templates_dir: Path | None = TEMPLATES_DIR_OPT,
    no_summary: bool = typer.Option(False, "--no-summary", hidden=True),
) -> None:
    deps: CliDependencies = ctx.obj["deps"]
    del no_summary  # accepted for the inner container invocation; JSON is already the shape
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

        raw_params = parse_params(param)
        resolved_params = resolve_engine_params(
            definition, settings.generation.default_params, raw_params
        )
        resolved_formats = resolve_formats(formats, settings)
        resolved_output = Path(output_dir) if output_dir is not None else settings.output.directory
        effective_templates = selected(ctx, "templates_dir", templates_dir)
        if effective_templates is None and settings.templates.directory:
            effective_templates = settings.templates.directory

        request = build_request(
            image_path=image,
            engine=engine_name,
            params=resolved_params,
            formats=resolved_formats,
            output_dir=resolved_output,
            settings=settings,
            dry_run=dry_run,
            mode=mode,
        )
        processor = create_processor(
            deps,
            request,
            settings,
            templates_dir=Path(effective_templates) if effective_templates else None,
        )
        result = processor.process_generate(request, settings)

        # The terminal apply is intentionally a no-op in the producer: writing to
        # the live TTY belongs to the dotfiles runtime, not this CLI (REQ-010).
        _ = settings.output.apply_to_terminal

        output_adapter(deps).process_result(result)
        if not result.success:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
