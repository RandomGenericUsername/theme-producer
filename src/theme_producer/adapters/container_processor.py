"""Container processor: run the same CLI inside the pinned engine image."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from oci_runtime import engine_qualified_image

from theme_producer.adapters.projections.registry import default_format_names
from theme_producer.adapters.settings_serializer import SettingsSerializer
from theme_producer.domain.generation import (
    ContainerImageNotFoundError,
    GenerationError,
    GenerationRequest,
    GenerationResult,
)
from theme_producer.domain.models import Theme
from theme_producer.domain.settings import AppSettings
from theme_producer.ports.container_runtime import ContainerMount, ContainerRuntimePort

__all__ = ["ContainerProcessor"]

logger = logging.getLogger(__name__)

_CONTAINER_ENV = {
    "HOME": "/tmp",
    "XDG_CONFIG_HOME": "/tmp/.config",
    "XDG_CACHE_HOME": "/tmp/.cache",
    "THEME_CONFIG_FILE_PATH": "/tpr-config/settings.toml",
    "THEME_TEMPLATES_TEMPLATES_DIR": "/templates",
    "THEME__RUNTIME__MODE": "local",
}

_CONTAINER_OUTPUT = "/output"


class ContainerProcessor:
    """Execute ``tpr`` inside the engine image with four bind mounts.

    There is deliberately no host cache: the inner process runs with a fresh
    temp settings file and the same templates directory the local processor
    would use.
    """

    def __init__(
        self,
        container_runtime: ContainerRuntimePort,
        templates_dir: Path,
        settings_serializer: SettingsSerializer | None = None,
    ) -> None:
        self._runtime = container_runtime
        self._templates_dir = Path(templates_dir)
        self._serializer = settings_serializer or SettingsSerializer()

    @staticmethod
    def _formats(request: GenerationRequest) -> tuple[str, ...]:
        return request.formats or default_format_names()

    @staticmethod
    def _image(settings: AppSettings, engine: str) -> str:
        prefix = settings.container.image_prefix
        return engine_qualified_image(
            f"{prefix}-{engine}",
            settings.container.engine.value,
            settings.container.image_tag,
        )

    def _write_settings(self, settings: AppSettings) -> Path:
        content = self._serializer.to_toml(settings, runtime_mode="local")
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".toml", mode="w", encoding="utf-8"
        ) as handle:
            handle.write(content)
            path = Path(handle.name)
        try:
            os.chmod(path, 0o644)
        except OSError:  # pragma: no cover - best effort for rootless runtimes
            logger.warning("could not chmod temporary settings file %s", path)
        return path

    def _run(
        self,
        *,
        image: str,
        command: list[str],
        mounts: list[ContainerMount],
        settings: AppSettings,
    ):
        return self._runtime.run(
            image=image,
            command=command,
            mounts=mounts,
            timeout=settings.container.timeout_seconds,
            environment=_CONTAINER_ENV,
            memory_limit=settings.container.memory_limit,
        )

    def _decode(self, stdout: str, image: str, stderr: str) -> dict[str, Any]:
        if not stdout.strip():
            raise GenerationError(
                f"container image {image!r} produced no JSON output", details={"stderr": stderr}
            )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise GenerationError(
                f"container image {image!r} produced invalid JSON: {exc}",
                details={"stderr": stderr},
            ) from exc
        if not isinstance(payload, dict):
            raise GenerationError(f"container image {image!r} produced a non-object JSON payload")
        return payload

    @staticmethod
    def _theme_from(payload: dict[str, Any]) -> Theme | None:
        raw = payload.get("theme")
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise GenerationError("container output 'theme' is not an object")
        try:
            return Theme.from_dict(raw)
        except Exception as exc:
            raise GenerationError(f"container output theme is invalid: {exc}") from exc

    def _generate_command(self, request: GenerationRequest) -> list[str]:
        command = [
            "tpr",
            "--output-format",
            "json",
            "generate",
            f"/input/{Path(request.image_path).name}",
            "--engine",
            request.engine,
            "--runtime",
            "local",
            "--no-summary",
            "-o",
            _CONTAINER_OUTPUT,
        ]
        for key in sorted(request.params):
            command.extend(["--param", f"{key}={request.params[key]}"])
        for output_format in self._formats(request):
            command.extend(["--format", output_format])
        return command

    def _show_command(self, request: GenerationRequest) -> list[str]:
        command = [
            "tpr",
            "--output-format",
            "json",
            "show",
            f"/input/{Path(request.image_path).name}",
            "--engine",
            request.engine,
        ]
        for key in sorted(request.params):
            command.extend(["--param", f"{key}={request.params[key]}"])
        return command

    def _preflight_image(self, request: GenerationRequest, settings: AppSettings) -> str:
        image = self._image(settings, request.engine)
        if not self._runtime.image_exists(image):
            raise ContainerImageNotFoundError(
                f"engine image {image!r} not found; run `tpr install --engine {request.engine}`",
                details={"image": image, "engine": request.engine},
            )
        input_path = Path(request.image_path).expanduser()
        if not input_path.is_file():
            raise GenerationError(f"input image not found: {input_path}")
        if input_path.resolve().parent == Path("/"):
            raise GenerationError("refusing to bind-mount the filesystem root as /input")
        return image

    def process_generate(
        self, request: GenerationRequest, settings: AppSettings
    ) -> GenerationResult:
        started = time.monotonic()
        temp_settings: Path | None = None
        try:
            image = self._preflight_image(request, settings)
            input_path = Path(request.image_path).expanduser()
            output_dir = Path(request.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
            temp_settings = self._write_settings(settings)

            mounts = [
                ContainerMount(input_path.resolve().parent, "/input", read_only=True),
                ContainerMount(output_dir, _CONTAINER_OUTPUT, read_only=False),
                ContainerMount(temp_settings, "/tpr-config/settings.toml", read_only=True),
                ContainerMount(self._templates_dir, "/templates", read_only=True),
            ]
            command = self._generate_command(request)
            result = self._run(image=image, command=command, mounts=mounts, settings=settings)
            if result.return_code != 0:
                raise GenerationError(
                    f"container generate failed with exit {result.return_code}",
                    details={"stderr": result.stderr, "image": image},
                )
            payload = self._decode(result.stdout, image, result.stderr)

            raw_files = payload.get("output_files") or []
            output_files: list[Path] = []
            for raw_path in raw_files:
                text = str(raw_path)
                if text.startswith(_CONTAINER_OUTPUT):
                    text = str(output_dir) + text[len(_CONTAINER_OUTPUT) :]
                output_files.append(Path(text))
            if not output_files:
                output_files = sorted(path for path in output_dir.iterdir() if path.is_file())

            return GenerationResult(
                command="generate",
                engine=request.engine,
                theme=self._theme_from(payload),
                output_files=tuple(output_files),
                duration=time.monotonic() - started,
                stderr=result.stderr,
            )
        finally:
            if temp_settings is not None:
                temp_settings.unlink(missing_ok=True)

    def process_show(self, request: GenerationRequest, settings: AppSettings) -> GenerationResult:
        started = time.monotonic()
        temp_settings: Path | None = None
        try:
            image = self._preflight_image(request, settings)
            input_path = Path(request.image_path).expanduser()
            temp_settings = self._write_settings(settings)
            mounts = [
                ContainerMount(input_path.resolve().parent, "/input", read_only=True),
                ContainerMount(temp_settings, "/tpr-config/settings.toml", read_only=True),
                ContainerMount(self._templates_dir, "/templates", read_only=True),
            ]
            result = self._run(
                image=image,
                command=self._show_command(request),
                mounts=mounts,
                settings=settings,
            )
            if result.return_code != 0:
                raise GenerationError(
                    f"container show failed with exit {result.return_code}",
                    details={"stderr": result.stderr, "image": image},
                )
            payload = self._decode(result.stdout, image, result.stderr)
            return GenerationResult(
                command="show",
                engine=request.engine,
                theme=self._theme_from(payload),
                output_files=(),
                duration=time.monotonic() - started,
                stderr=result.stderr,
            )
        finally:
            if temp_settings is not None:
                temp_settings.unlink(missing_ok=True)
