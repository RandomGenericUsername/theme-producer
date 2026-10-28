"""``tpr uninstall`` — remove the base and per-engine images."""

from __future__ import annotations

from pathlib import Path

import typer

from theme_producer.cli._helpers import (
    base_image_name,
    container_runtime_for,
    engine_image_name,
    fail,
    load_catalog,
    output_adapter,
    resolve_settings,
)
from theme_producer.cli.options import CONFIG_OPT, ENGINE_OPT
from theme_producer.domain.generation import EngineNotRegisteredError
from theme_producer.domain.settings import ContainerEngine
from theme_producer.factory import CliDependencies


def _targets(
    requested: list[str],
    deps: CliDependencies,
    catalog: dict[str, object],
) -> list[str]:
    names = list(dict.fromkeys(requested)) if requested else sorted(deps.engine_registry)
    if not names:  # pragma: no cover - production always registers matugen
        names = sorted(catalog)
    for name in names:
        if name not in catalog:
            known = ", ".join(sorted(catalog)) or "none"
            raise EngineNotRegisteredError(
                f"engine {name!r} is not in the engine catalog; known engines: {known}"
            )
    return names


def uninstall(
    ctx: typer.Context,
    engines: list[str] = typer.Option(  # noqa: B008
        [], "--engine", help="Engine image(s) to remove (default: all registered engines)"
    ),
    container_engine: ContainerEngine | None = ENGINE_OPT,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Print planned removals without removing"
    ),
    config_path: Path | None = CONFIG_OPT,
) -> None:
    deps: CliDependencies = ctx.obj["deps"]
    try:
        settings = resolve_settings(
            deps, ctx, config_path=config_path, container_engine=container_engine
        )
        catalog = load_catalog(deps)
        targets = _targets(engines, deps, catalog)
        effective_engine = settings.container.engine
        images = [
            ("base", base_image_name(settings, effective_engine)),
            *[(name, engine_image_name(settings, name, effective_engine)) for name in targets],
        ]
        if not yes:
            typer.confirm(f"Remove {len(images)} image(s)?", abort=True)

        if dry_run:
            output_adapter(deps).uninstall_result(
                [
                    {"engine": name, "image": image, "status": "would-remove"}
                    for name, image in images
                ]
            )
            return

        runtime = container_runtime_for(deps, settings)
        results = []
        for name, image in images:
            runtime.remove_image(image, force=False)
            results.append({"engine": name, "image": image, "status": "removed"})
        output_adapter(deps).uninstall_result(results)
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
