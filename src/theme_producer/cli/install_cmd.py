"""``tpr install`` — build the base image then one image per engine."""

from __future__ import annotations

from pathlib import Path

import typer
from oci_runtime import resolve_build_context
from oci_runtime.domain.exceptions import SourceRootNotFoundError

from theme_producer.adapters.docker import dockerfile_path
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
from theme_producer.domain.generation import (
    DockerfileNotFoundError,
    EngineNotRegisteredError,
    GenerationError,
)
from theme_producer.domain.settings import ContainerEngine
from theme_producer.factory import CliDependencies

_SOURCE_ROOT_ENV = "THEME_PRODUCER_SOURCE_ROOT"


def _target_engines(
    requested: list[str],
    deps: CliDependencies,
    catalog: dict[str, object],
) -> list[str]:
    if requested:
        names = list(dict.fromkeys(requested))
    elif deps.engine_registry:
        names = sorted(deps.engine_registry)
    else:  # pragma: no cover - production always registers matugen
        names = sorted(catalog)
    for name in names:
        if name not in catalog:
            known = ", ".join(sorted(catalog)) or "none"
            raise EngineNotRegisteredError(
                f"engine {name!r} is not in the engine catalog; known engines: {known}"
            )
    return names


def _dockerfile(name: str) -> Path:
    return dockerfile_path(name)


def _require_dockerfile(name: str) -> Path:
    path = _dockerfile(name)
    if not path.is_file():
        raise DockerfileNotFoundError(f"Dockerfile.{name} not found (REQ-011)")
    return path


def _project_root() -> Path:
    try:
        return resolve_build_context(
            package="theme-producer",
            env_var=_SOURCE_ROOT_ENV,
            import_name="theme_producer",
        ).root
    except SourceRootNotFoundError as exc:
        raise GenerationError(
            f"cannot locate the source checkout used as the build context: {exc}"
        ) from exc


def install(
    ctx: typer.Context,
    engines: list[str] = typer.Option(  # noqa: B008
        [], "--engine", help="Engine(s) to build (default: all registered engines)"
    ),
    container_engine: ContainerEngine | None = ENGINE_OPT,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Print planned images without building"
    ),
    config_path: Path | None = CONFIG_OPT,
) -> None:
    deps: CliDependencies = ctx.obj["deps"]
    try:
        settings = resolve_settings(
            deps, ctx, config_path=config_path, container_engine=container_engine
        )
        catalog = load_catalog(deps)
        targets = _target_engines(engines, deps, catalog)
        effective_engine = settings.container.engine
        base_image = base_image_name(settings, effective_engine)

        if dry_run:
            results = [
                {"engine": "base", "image": base_image, "status": "would-build"},
                *[
                    {
                        "engine": name,
                        "image": engine_image_name(settings, name, effective_engine),
                        "status": "would-build",
                    }
                    for name in targets
                ],
            ]
            output_adapter(deps).install_result(results)
            return

        # Resolve every required Dockerfile before the first build so a missing
        # engine file cannot leave a freshly built base image behind.
        base_dockerfile = _require_dockerfile("base")
        engine_dockerfiles = {name: _require_dockerfile(name) for name in targets}
        project_root = _project_root()
        runtime = container_runtime_for(deps, settings)

        results = []
        runtime.build_image(base_dockerfile, project_root, base_image)
        results.append({"engine": "base", "image": base_image, "status": "built"})
        for name in targets:
            image = engine_image_name(settings, name, effective_engine)
            runtime.build_image(
                engine_dockerfiles[name],
                project_root,
                image,
                build_args={"BASE_IMAGE": base_image},
            )
            results.append({"engine": name, "image": image, "status": "built"})
        output_adapter(deps).install_result(results)
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
