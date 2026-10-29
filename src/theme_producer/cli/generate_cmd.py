"""``tpr generate`` — engine → Theme → theme.json + projections."""

from __future__ import annotations

from dataclasses import replace
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
from theme_producer.cli._scheme import apply_scheme_resolution
from theme_producer.cli.options import (
    CONFIG_OPT,
    ENGINE_OPT,
    POLICIES_FILE_OPT,
    PROJECTION_MODE_OPT,
    RUNTIME_OPT,
    SCHEME_POLICY_OPT,
    SMART_THRESHOLD_OPT,
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
    mode: str | None = PROJECTION_MODE_OPT,
    smart_threshold: float | None = SMART_THRESHOLD_OPT,
    scheme_policy: str | None = SCHEME_POLICY_OPT,
    policies_file: Path | None = POLICIES_FILE_OPT,
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
            extra_overrides=(
                {"generation.scheme_policy": scheme_policy} if scheme_policy is not None else None
            ),
        )
        catalog = load_catalog(deps)
        engine_name = resolve_engine_name(engine, settings, catalog)
        definition = catalog[engine_name]

        raw_params = parse_params(param)
        scheme, params_with_scheme = apply_scheme_resolution(
            deps,
            image_path=image,
            definition=definition,
            settings_scheme_type=settings.generation.scheme_type,
            profile=settings.generation.scheme_policy,
            policies_file=str(policies_file) if policies_file is not None else None,
            params=raw_params,
        )
        # The container inner command must also read a concrete variant from its
        # temporary settings file, never the pseudo-value.
        settings = replace(
            settings,
            generation=replace(
                settings.generation,
                scheme_type=scheme.variant.value,
            ),
        )
        resolved_params = resolve_engine_params(
            definition, settings.generation.default_params, params_with_scheme
        )
        resolved_formats = resolve_formats(formats, settings)
        resolved_output = Path(output_dir) if output_dir is not None else settings.output.directory
        effective_templates = selected(ctx, "templates_dir", templates_dir)
        if effective_templates is None and settings.templates.directory:
            effective_templates = settings.templates.directory

        effective_mode = mode if mode is not None else settings.output.default_mode
        effective_threshold = (
            smart_threshold if smart_threshold is not None else settings.output.smart_threshold
        )
        request = build_request(
            image_path=image,
            engine=engine_name,
            params=resolved_params,
            formats=resolved_formats,
            output_dir=resolved_output,
            settings=settings,
            dry_run=dry_run,
            mode=effective_mode,
            smart_threshold=effective_threshold,
            scheme=scheme,
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
