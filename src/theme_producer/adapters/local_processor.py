"""Local processor: run the engine on this host and render projections."""

from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path

from theme_producer.adapters.projections.registry import (
    ProjectionRegistry,
    default_format_names,
    projections_for_formats,
)
from theme_producer.adapters.theme_json import ThemeJsonWriter
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.exceptions import EngineConfigError
from theme_producer.domain.generation import (
    EngineNotRegisteredError,
    EngineUnavailableError,
    GenerationRequest,
    GenerationResult,
)
from theme_producer.domain.models import Theme
from theme_producer.domain.settings import AppSettings
from theme_producer.ports.theme_engine import ThemeEnginePort

__all__ = ["LocalProcessor"]


class LocalProcessor:
    """Generate a Theme locally, writing ``theme.json`` plus projections."""

    def __init__(
        self,
        engine_registry: Mapping[str, ThemeEnginePort],
        projection_registry: ProjectionRegistry,
        theme_writer: ThemeJsonWriter | None = None,
    ) -> None:
        self._engine_registry = dict(engine_registry)
        self._projection_registry = projection_registry
        self._theme_writer = theme_writer or ThemeJsonWriter()

    def _engine(self, name: str) -> ThemeEnginePort:
        try:
            engine = self._engine_registry[name]
        except KeyError:
            known = ", ".join(sorted(self._engine_registry)) or "none"
            raise EngineNotRegisteredError(
                f"engine {name!r} is not registered on this host; registered engines: {known}"
            ) from None
        if not engine.is_available():
            raise EngineUnavailableError(
                f"engine {name!r} is not available on this host; "
                f"run `tpr install --engine {name}` and use `--runtime container`, "
                "or install the engine binary"
            )
        return engine

    @staticmethod
    def _theme_request(request: GenerationRequest) -> ThemeRequest:
        return ThemeRequest(
            source_kind="image",
            image_path=Path(request.image_path).expanduser(),
        )

    @staticmethod
    def _engine_config(request: GenerationRequest) -> EngineConfig:
        timeout_value = request.params.get("timeout", 300)
        try:
            timeout = int(timeout_value)
        except (TypeError, ValueError) as exc:
            raise EngineConfigError("timeout", f"must be an int; got {timeout_value!r}") from exc
        return EngineConfig(
            engine=request.engine,
            params=dict(request.params),
            timeout=max(1, timeout),
        )

    @staticmethod
    def _formats(request: GenerationRequest) -> tuple[str, ...]:
        return request.formats or default_format_names()

    def _generate(self, request: GenerationRequest) -> tuple[Theme, float]:
        engine = self._engine(request.engine)
        started = time.monotonic()
        theme = engine.generate(self._theme_request(request), self._engine_config(request))
        return theme, time.monotonic() - started

    def process_generate(
        self, request: GenerationRequest, settings: AppSettings
    ) -> GenerationResult:
        theme, duration = self._generate(request)
        output_dir = Path(request.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True, mode=0o755)

        files: list[Path] = [self._theme_writer.write(theme, output_dir)]
        for projection in projections_for_formats(self._formats(request)):
            destination = output_dir / projection.filename
            if destination.exists() and not request.overwrite:
                continue
            files.append(self._projection_registry.render(projection, theme, output_dir))

        return GenerationResult(
            command="generate",
            engine=request.engine,
            theme=theme,
            output_files=tuple(files),
            duration=duration,
        )

    def process_show(self, request: GenerationRequest, settings: AppSettings) -> GenerationResult:
        theme, duration = self._generate(request)
        return GenerationResult(
            command="show",
            engine=request.engine,
            theme=theme,
            output_files=(),
            duration=duration,
        )
