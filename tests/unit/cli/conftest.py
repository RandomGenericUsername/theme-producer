from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from theme_producer.adapters.engines_catalog_loader import YamlEngineCatalogLoader
from theme_producer.adapters.jinja_renderer import JinjaThemeRenderer
from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.adapters.settings.config_resolver import AssembledConfigResolver
from theme_producer.adapters.template_dir_resolver import TemplateDirResolver
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.models import Theme
from theme_producer.factory import CliDependencies
from theme_producer.ports.container_runtime import ContainerResult

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


class FakeEngine:
    """Catalog-compatible engine that never touches a binary."""

    name = "matugen"

    def __init__(self, *, available: bool = True, theme: Theme | None = None) -> None:
        self.available = available
        self.theme = theme or load_theme()
        self.calls: list[tuple[ThemeRequest, EngineConfig]] = []

    def is_available(self) -> bool:
        return self.available

    def generate(self, request: ThemeRequest, config: EngineConfig) -> Theme:
        self.calls.append((request, config))
        return self.theme


class FakeContainerRuntime:
    """Minimal :class:`ContainerRuntimePort` used by install/uninstall tests."""

    def __init__(
        self,
        *,
        images: set[str] | None = None,
        run_stdout: str | None = None,
        run_return_code: int = 0,
    ) -> None:
        self.images = set(images or ())
        self.run_stdout = run_stdout
        self.run_return_code = run_return_code
        self.builds: list[dict[str, Any]] = []
        self.removed: list[str] = []
        self.runs: list[dict[str, Any]] = []

    def run(
        self,
        image: str,
        command: list[str],
        mounts: list[Any],
        timeout: int,
        environment: Mapping[str, str] | None = None,
        memory_limit: str | None = None,
    ) -> ContainerResult:
        self.runs.append(
            {
                "image": image,
                "command": list(command),
                "mounts": list(mounts),
                "timeout": timeout,
                "environment": dict(environment or {}),
                "memory_limit": memory_limit,
            }
        )
        return ContainerResult(
            return_code=self.run_return_code,
            stdout=self.run_stdout or "",
            stderr="",
        )

    def image_exists(self, image: str) -> bool:
        return image in self.images

    def pull_image(self, image: str) -> None:
        self.images.add(image)

    def build_image(
        self,
        dockerfile: Path,
        context: Path,
        image_name: str,
        timeout: int | None = 600,
        build_args: Mapping[str, str] | None = None,
        labels: Mapping[str, str] | None = None,
    ) -> str:
        self.builds.append(
            {
                "dockerfile": Path(dockerfile),
                "context": Path(context),
                "image": image_name,
                "timeout": timeout,
                "build_args": dict(build_args or {}),
                "labels": dict(labels or {}),
            }
        )
        self.images.add(image_name)
        return image_name

    def remove_image(self, image: str, force: bool = False) -> None:
        self.removed.append(image)
        self.images.discard(image)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def theme() -> Theme:
    return load_theme()


@pytest.fixture
def fake_engine(theme: Theme) -> FakeEngine:
    return FakeEngine(theme=theme)


def make_deps(
    engine: FakeEngine | None = None,
    *,
    container_runtime: FakeContainerRuntime | None = None,
) -> CliDependencies:
    return CliDependencies(
        config_resolver=AssembledConfigResolver(),
        engine_catalog_loader=YamlEngineCatalogLoader(),
        engine_registry={"matugen": engine or FakeEngine()},
        template_dir_resolver=TemplateDirResolver(),
        template_renderer=JinjaThemeRenderer(),
        projection_registry=ProjectionRegistry(),
        container_runtime=container_runtime,
    )


def invoke(
    runner: CliRunner,
    deps: CliDependencies,
    args: list[str],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("theme_producer.cli.main.build_deps", lambda: deps)
    from theme_producer.cli.main import app

    return runner.invoke(app, args)


def make_image(path: Path) -> Path:
    path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return path


def dumped_theme() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))
