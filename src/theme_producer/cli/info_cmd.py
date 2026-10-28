"""``tpr info`` — resolved settings, templates, engines, formats, overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from theme_producer.adapters.projections.registry import known_format_names
from theme_producer.cli._helpers import (
    container_runtime_for,
    engine_infos,
    fail,
    load_catalog,
    output_adapter,
    resolve_settings,
    resolve_templates_dir,
    selected,
    serialize_settings,
)
from theme_producer.cli.options import CONFIG_OPT, ENGINE_OPT, RUNTIME_OPT, TEMPLATES_DIR_OPT
from theme_producer.domain.exceptions import SchemePolicyError
from theme_producer.domain.settings import ContainerEngine, RuntimeMode
from theme_producer.factory import CliDependencies


def info(
    ctx: typer.Context,
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
        effective_templates = selected(ctx, "templates_dir", templates_dir)
        if effective_templates is None and settings.templates.directory:
            effective_templates = settings.templates.directory
        templates_path = resolve_templates_dir(deps, effective_templates)
        effective_runtime = selected(ctx, "runtime", runtime) or settings.runtime.mode
        runtime_adapter = None
        if RuntimeMode(effective_runtime) is RuntimeMode.CONTAINER:
            runtime_adapter = container_runtime_for(deps, settings)

        infos = engine_infos(
            catalog,
            deps.engine_registry,
            settings=settings if runtime_adapter is not None else None,
            runtime=runtime_adapter,
        )
        last_result = deps.config_resolver.last_result
        applied = (
            [
                {
                    "field_path": override.field_path,
                    "raw_value": override.raw_value,
                    "coerced_value": override.coerced_value,
                    "source": override.source,
                }
                for override in last_result.applied_overrides
            ]
            if last_result is not None
            else []
        )
        policy_report = _scheme_policy_report(deps, settings.generation.scheme_policy)
        payload = {
            "settings_path": (str(last_result.resolved_path) if last_result is not None else None),
            "templates_path": str(templates_path),
            "runtime": RuntimeMode(effective_runtime).value,
            "container_engine": settings.container.engine.value,
            "scheme_policy": policy_report,
            "engines": [info.to_dict() for info in infos],
            "formats": list(known_format_names()),
            "applied_overrides": applied,
            "settings": serialize_settings(settings),
        }
        output_adapter(deps).config_info(payload)
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)


def _scheme_policy_report(deps: CliDependencies, profile: str) -> dict[str, Any]:
    """Report the resolved catalog path, selected profile, and load outcome.

    ``info`` is diagnostic: a broken catalog or an unknown profile is reported
    in the payload instead of aborting the command, so the user can see the
    resolved path alongside the error.
    """
    report: dict[str, Any] = {
        "profile": profile,
        "catalog_path": None,
        "loaded": False,
        "profile_found": None,
        "error": None,
    }
    loader = deps.scheme_policy_catalog_loader
    try:
        catalog = loader.load()
    except SchemePolicyError as exc:
        report["error"] = str(exc)
        if loader.last_source_path is not None:
            report["catalog_path"] = str(loader.last_source_path)
        return report

    report["loaded"] = True
    if loader.last_source_path is not None:
        report["catalog_path"] = str(loader.last_source_path)
    try:
        catalog.select(profile)
    except SchemePolicyError as exc:
        report["profile_found"] = False
        report["error"] = str(exc)
    else:
        report["profile_found"] = True
    return report
