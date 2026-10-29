"""Dry-run processor: resolve and print the plan without running anything."""

from __future__ import annotations

import shlex
import time
from collections.abc import Mapping
from pathlib import Path

from theme_producer.adapters.projections.registry import (
    ProjectionRegistry,
    default_format_names,
    projections_for_formats,
)
from theme_producer.domain.generation import (
    EngineNotRegisteredError,
    GenerationError,
    GenerationRequest,
    GenerationResult,
)
from theme_producer.domain.settings import AppSettings, RuntimeMode
from theme_producer.ports.theme_engine import ThemeEnginePort

__all__ = ["DryRunProcessor"]


class DryRunProcessor:
    """Build the exact command/projection plan; never calls the engine."""

    def __init__(
        self,
        engine_registry: Mapping[str, ThemeEnginePort],
        projection_registry: ProjectionRegistry,
    ) -> None:
        self._engine_registry = dict(engine_registry)
        self._projection_registry = projection_registry

    @staticmethod
    def _formats(request: GenerationRequest) -> tuple[str, ...]:
        return request.formats or default_format_names()

    def _validate(self, request: GenerationRequest) -> None:
        if request.engine not in self._engine_registry:
            known = ", ".join(sorted(self._engine_registry)) or "none"
            raise EngineNotRegisteredError(
                f"engine {request.engine!r} is not registered on this host; "
                f"registered engines: {known}"
            )
        image = Path(request.image_path).expanduser()
        if not image.is_file():
            raise GenerationError(f"input image not found: {image}")
        # Raises UnknownFormatError before printing a misleading plan.
        projections_for_formats(self._formats(request))

    def _build_plan(
        self, request: GenerationRequest, settings: AppSettings, subcommand: str
    ) -> str:
        command = [
            "tpr",
            subcommand,
            str(request.image_path),
            "--engine",
            request.engine,
            "--runtime",
            request.runtime.value,
        ]
        if request.runtime is RuntimeMode.CONTAINER:
            command.extend(["--container-engine", settings.container.engine.value])
        command.extend(["--mode", request.mode.value])
        for key in sorted(request.params):
            command.extend(["--param", f"{key}={request.params[key]}"])
        if subcommand == "generate":
            for output_format in self._formats(request):
                command.extend(["--format", output_format])
            command.extend(["-o", str(request.output_dir)])
        return shlex.join(command)

    def _process(self, request: GenerationRequest, settings: AppSettings, subcommand: str):
        started = time.monotonic()
        self._validate(request)
        projections = projections_for_formats(self._formats(request))
        plan = self._build_plan(request, settings, subcommand)
        return GenerationResult(
            command=subcommand,
            engine=request.engine,
            theme=None,
            output_files=(),
            duration=time.monotonic() - started,
            plan=plan,
            projections=tuple(projection.filename for projection in projections),
            mode=request.mode,
            scheme=request.scheme,
        )

    def process_generate(
        self, request: GenerationRequest, settings: AppSettings
    ) -> GenerationResult:
        return self._process(request, settings, "generate")

    def process_show(self, request: GenerationRequest, settings: AppSettings) -> GenerationResult:
        return self._process(request, settings, "show")
