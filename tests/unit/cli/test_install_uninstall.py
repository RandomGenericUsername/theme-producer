from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeContainerRuntime, FakeEngine, invoke, make_deps

BASE_IMAGE = "tpr-base-podman:latest"
MATUGEN_IMAGE = "tpr-matugen-podman:latest"


def _fake_dockerfiles(tmp_path: Path) -> Path:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (docker_dir / "Dockerfile.base").write_text("FROM scratch\n", encoding="utf-8")
    (docker_dir / "Dockerfile.matugen").write_text(
        "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\n", encoding="utf-8"
    )
    return docker_dir


def test_install_dry_run_plans_base_then_engine_without_building(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeContainerRuntime()
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(runner, deps, ["install", "--dry-run"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [item["image"] for item in payload["results"]] == [BASE_IMAGE, MATUGEN_IMAGE]
    assert {item["status"] for item in payload["results"]} == {"would-build"}
    assert runtime.builds == []


def test_install_builds_base_first_then_engine(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_dir = _fake_dockerfiles(tmp_path)
    monkeypatch.setattr(
        "theme_producer.cli.install_cmd.dockerfile_path",
        lambda name: docker_dir / f"Dockerfile.{name}",
    )
    runtime = FakeContainerRuntime()
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(runner, deps, ["install"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    assert [build["image"] for build in runtime.builds] == [BASE_IMAGE, MATUGEN_IMAGE]
    assert runtime.builds[1]["build_args"] == {"BASE_IMAGE": BASE_IMAGE}
    assert runtime.builds[0]["dockerfile"].name == "Dockerfile.base"
    assert runtime.builds[1]["dockerfile"].name == "Dockerfile.matugen"


def test_install_missing_engine_dockerfile_is_clear(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (docker_dir / "Dockerfile.base").write_text("FROM scratch\n", encoding="utf-8")
    monkeypatch.setattr(
        "theme_producer.cli.install_cmd.dockerfile_path",
        lambda name: docker_dir / f"Dockerfile.{name}",
    )
    runtime = FakeContainerRuntime()
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(runner, deps, ["install"], monkeypatch)

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "DockerfileNotFoundError"
    assert "Dockerfile.matugen not found (REQ-011)" in payload["error"]["message"]
    assert runtime.builds == []


def test_install_without_any_dockerfiles_fails_clearly(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    monkeypatch.setattr(
        "theme_producer.cli.install_cmd.dockerfile_path",
        lambda name: docker_dir / f"Dockerfile.{name}",
    )
    runtime = FakeContainerRuntime()
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(runner, deps, ["install"], monkeypatch)

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert "Dockerfile.base not found (REQ-011)" in payload["error"]["message"]
    assert runtime.builds == []


def test_uninstall_removes_base_and_engine_images(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeContainerRuntime(images={BASE_IMAGE, MATUGEN_IMAGE})
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(runner, deps, ["uninstall", "--yes"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    assert runtime.removed == [BASE_IMAGE, MATUGEN_IMAGE]


def test_uninstall_dry_run_does_not_remove(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeContainerRuntime(images={BASE_IMAGE, MATUGEN_IMAGE})
    deps = make_deps(fake_engine, container_runtime=runtime)

    result = invoke(
        runner,
        deps,
        ["uninstall", "--dry-run", "--yes"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [item["image"] for item in payload["results"]] == [BASE_IMAGE, MATUGEN_IMAGE]
    assert {item["status"] for item in payload["results"]} == {"would-remove"}
    assert runtime.removed == []
