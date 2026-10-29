"""Composition root for the CLI, adapters, and processors.

Commands depend on this module (or on a test-provided :class:`CliDependencies`)
instead of branching on runtime/engine names themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cli_output.adapters.factory import create_renderer
from cli_output.domain.enums import OutputFormat as SharedOutputFormat

from theme_producer.adapters.container_processor import ContainerProcessor
from theme_producer.adapters.dry_run_processor import DryRunProcessor
from theme_producer.adapters.engines.matugen import MatugenEngine
from theme_producer.adapters.engines.native import NativeEngine
from theme_producer.adapters.engines_catalog_loader import YamlEngineCatalogLoader
from theme_producer.adapters.image_metrics import PillowImageMetrics
from theme_producer.adapters.jinja_renderer import JinjaThemeRenderer
from theme_producer.adapters.local_processor import LocalProcessor
from theme_producer.adapters.oci_container_runtime import OciContainerRuntimeAdapter
from theme_producer.adapters.output import JsonOutput, PlainOutput, RichOutput
from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.adapters.scheme_policy_catalog_loader import YamlSchemePolicyCatalogLoader
from theme_producer.adapters.settings.config_resolver import AssembledConfigResolver
from theme_producer.adapters.template_dir_resolver import TemplateDirResolver
from theme_producer.domain.generation import (
    ContainerRuntimeUnavailableError,
    GenerationRequest,
)
from theme_producer.domain.settings import AppSettings, ContainerEngine, RuntimeMode, Verbosity
from theme_producer.ports.container_runtime import ContainerRuntimePort
from theme_producer.ports.image_metrics import ImageMetricsPort
from theme_producer.ports.output import OutputPort
from theme_producer.ports.processor import ProcessorPort
from theme_producer.ports.theme_engine import ThemeEnginePort

__all__ = [
    "CliDependencies",
    "create_container_processor",
    "create_container_runtime",
    "create_dependencies",
    "create_dry_run_processor",
    "create_engine_registry",
    "create_local_processor",
    "create_output_adapter",
    "create_processor",
    "create_projection_registry",
    "resolve_templates_dir",
]


@dataclass
class CliDependencies:
    """Everything a CLI invocation needs, injectable in tests."""

    config_resolver: AssembledConfigResolver
    engine_catalog_loader: YamlEngineCatalogLoader
    scheme_policy_catalog_loader: YamlSchemePolicyCatalogLoader = field(
        default_factory=YamlSchemePolicyCatalogLoader
    )
    image_metrics: ImageMetricsPort = field(default_factory=PillowImageMetrics)
    engine_registry: dict[str, ThemeEnginePort] = field(default_factory=dict)
    template_dir_resolver: TemplateDirResolver = field(default_factory=TemplateDirResolver)
    template_renderer: JinjaThemeRenderer = field(default_factory=JinjaThemeRenderer)
    projection_registry: ProjectionRegistry = field(default_factory=ProjectionRegistry)
    output_adapter: OutputPort | None = None
    container_runtime: ContainerRuntimePort | None = None
    processor: ProcessorPort | None = None


def create_engine_registry() -> dict[str, ThemeEnginePort]:
    """Return the engines implemented in this package.

    Both engines are behind the same port and each reports its own host
    availability, so ``list-engines`` stays honest when one binary is absent.
    """
    return {"matugen": MatugenEngine(), "native": NativeEngine()}


def create_engine_catalog_loader() -> YamlEngineCatalogLoader:
    return YamlEngineCatalogLoader()


def create_projection_registry(
    templates_dir: Path | None = None,
) -> ProjectionRegistry:
    return ProjectionRegistry(templates_dir=Path(templates_dir) if templates_dir else None)


def resolve_templates_dir(
    deps: CliDependencies,
    templates_dir: Path | str | None = None,
) -> Path:
    return deps.template_dir_resolver.resolve(
        explicit_dir=Path(templates_dir) if templates_dir is not None else None
    )


def create_output_adapter(
    fmt: SharedOutputFormat,
    verbosity: Verbosity = Verbosity.NORMAL,
) -> OutputPort:
    """Build the cli-output-backed adapter for ``fmt``."""
    renderer = create_renderer(SharedOutputFormat(fmt.value))
    if fmt is SharedOutputFormat.RICH:
        return RichOutput(verbosity=verbosity, renderer=renderer)
    if fmt is SharedOutputFormat.PLAIN:
        return PlainOutput(verbosity=verbosity, renderer=renderer)
    return JsonOutput(verbosity=verbosity, renderer=renderer)


def create_container_runtime(
    engine: ContainerEngine | str = ContainerEngine.PODMAN,
) -> ContainerRuntimePort:
    """Create an oci-runtime adapter for ``engine`` (docker or podman)."""
    from oci_runtime.domain.enums import RuntimeKind
    from oci_runtime.domain.types import RuntimePreference
    from oci_runtime.factory import RuntimeFactory

    container_engine = engine if isinstance(engine, ContainerEngine) else ContainerEngine(engine)
    kind = RuntimeKind.DOCKER if container_engine is ContainerEngine.DOCKER else RuntimeKind.PODMAN
    try:
        runtime_engine = RuntimeFactory().create(
            RuntimePreference(kind=kind, binary=container_engine.value)
        )
    except Exception as exc:
        raise ContainerRuntimeUnavailableError(
            f"container runtime {container_engine.value!r} is unavailable: {exc}"
        ) from exc
    return OciContainerRuntimeAdapter(runtime_engine)


def create_local_processor(
    deps: CliDependencies,
    *,
    templates_dir: Path | None = None,
) -> LocalProcessor:
    projection_registry = create_projection_registry(
        templates_dir if templates_dir is not None else None
    )
    return LocalProcessor(deps.engine_registry, projection_registry)


def create_container_processor(
    deps: CliDependencies,
    settings: AppSettings,
    *,
    templates_dir: Path | None = None,
) -> ContainerProcessor:
    resolved = templates_dir if templates_dir is not None else resolve_templates_dir(deps)
    runtime = deps.container_runtime or create_container_runtime(settings.container.engine)
    return ContainerProcessor(runtime, resolved)


def create_dry_run_processor(
    deps: CliDependencies,
    *,
    templates_dir: Path | None = None,
) -> DryRunProcessor:
    projection_registry = create_projection_registry(
        templates_dir if templates_dir is not None else None
    )
    return DryRunProcessor(deps.engine_registry, projection_registry)


def create_processor(
    deps: CliDependencies,
    request: GenerationRequest,
    settings: AppSettings,
    *,
    templates_dir: Path | None = None,
) -> ProcessorPort:
    """Select dry-run > container > local for one request."""
    if deps.processor is not None:
        return deps.processor
    if request.dry_run:
        return create_dry_run_processor(deps, templates_dir=templates_dir)
    if request.runtime is RuntimeMode.CONTAINER:
        return create_container_processor(deps, settings, templates_dir=templates_dir)
    return create_local_processor(deps, templates_dir=templates_dir)


def create_dependencies() -> CliDependencies:
    """Production wiring for every CLI verb."""
    template_dir_resolver = TemplateDirResolver()
    return CliDependencies(
        config_resolver=AssembledConfigResolver(),
        engine_catalog_loader=create_engine_catalog_loader(),
        scheme_policy_catalog_loader=YamlSchemePolicyCatalogLoader(),
        engine_registry=create_engine_registry(),
        template_dir_resolver=template_dir_resolver,
        template_renderer=JinjaThemeRenderer(resolver=template_dir_resolver),
        projection_registry=ProjectionRegistry(),
    )
