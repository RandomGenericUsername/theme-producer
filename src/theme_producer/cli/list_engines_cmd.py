"""``tpr list-engines`` — catalog entries + host/image availability."""

from __future__ import annotations

from pathlib import Path

import typer

from theme_producer.cli._helpers import (
    container_runtime_for,
    engine_infos,
    fail,
    load_catalog,
    output_adapter,
    resolve_settings,
    selected,
)
from theme_producer.cli.options import CONFIG_OPT, ENGINE_OPT, RUNTIME_OPT
from theme_producer.domain.settings import ContainerEngine, RuntimeMode
from theme_producer.factory import CliDependencies


def list_engines(
    ctx: typer.Context,
    runtime: RuntimeMode | None = RUNTIME_OPT,
    container_engine: ContainerEngine | None = ENGINE_OPT,
    config_path: Path | None = CONFIG_OPT,
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
        output_adapter(deps).engines_catalog(
            [info.to_dict() for info in infos],
            runtime=RuntimeMode(effective_runtime).value,
            container_engine=settings.container.engine.value,
        )
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
