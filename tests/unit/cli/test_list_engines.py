from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeContainerRuntime, FakeEngine, invoke, make_deps
from theme_producer.adapters.version_provider import get_version

MATUGEN_IMAGE = f"tpr-matugen-podman:v{get_version()}"


def test_list_engines_shows_catalog_and_native_unavailable(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(runner, make_deps(fake_engine), ["list-engines"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["command"] == "list-engines"
    engines = {engine["name"]: engine for engine in payload["engines"]}
    assert set(engines) == {"matugen", "native"}
    assert engines["matugen"]["available"] is True
    assert engines["native"]["available"] is False
    assert engines["matugen"]["image"] is None


def test_list_engines_container_mode_reports_image_presence(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeContainerRuntime(images={MATUGEN_IMAGE})
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(
        runner,
        deps,
        ["--runtime", "container", "list-engines"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    engines = {engine["name"]: engine for engine in payload["engines"]}
    assert payload["runtime"] == "container"
    assert engines["matugen"]["image"] == MATUGEN_IMAGE
    assert engines["matugen"]["image_available"] is True
    assert engines["native"]["image_available"] is False
