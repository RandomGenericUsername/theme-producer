from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps


def test_dump_config_prints_resolved_toml(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(runner, make_deps(fake_engine), ["dump-config"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = tomllib.loads(result.stdout)
    assert payload["runtime"]["mode"] == "local"
    assert payload["generation"]["engine"] == "matugen"
    assert payload["container"]["engine"] == "podman"


def test_dump_config_writes_a_file_and_refuses_overwrite(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "settings.toml"
    deps = make_deps(fake_engine)

    first = invoke(
        runner,
        deps,
        ["dump-config", "--output", str(target)],
        monkeypatch,
    )
    assert first.exit_code == 0, first.stderr
    assert tomllib.loads(target.read_text(encoding="utf-8"))["runtime"]["mode"] == "local"

    second = invoke(
        runner,
        deps,
        ["dump-config", "--output", str(target)],
        monkeypatch,
    )
    assert second.exit_code == 1
    error = json.loads(second.stderr)
    assert error["error"]["type"] == "OutputWriteError"
    assert "--overwrite" in error["error"]["message"]

    third = invoke(
        runner,
        deps,
        ["dump-config", "--output", str(target), "--overwrite"],
        monkeypatch,
    )
    assert third.exit_code == 0, third.stderr


def test_dump_config_directory_output_appends_settings_toml(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "config"

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["dump-config", "--output", str(target)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert (target / "settings.toml").is_file()
