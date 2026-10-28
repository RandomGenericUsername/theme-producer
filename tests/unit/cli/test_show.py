from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps, make_image


def test_show_generates_theme_and_writes_nothing(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"
    config = tmp_path / "settings.toml"
    config.write_text(f'[output]\ndirectory = "{output}"\n', encoding="utf-8")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["show", str(image), "--config", str(config)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["command"] == "show"
    assert payload["engine"] == "matugen"
    assert payload["output_files"] == []
    assert payload["theme"]["modes"]["dark"]["roles"]
    assert payload["theme"]["modes"]["dark"]["palettes"]["primary"]["40"]
    assert not output.exists()
    assert len(fake_engine.calls) == 1


def test_show_reports_engine_unavailable_as_typed_error(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = FakeEngine(available=False)
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(engine),
        ["show", str(image)],
        monkeypatch,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "EngineUnavailableError"
    assert not engine.calls


def test_show_mode_light_returns_and_displays_the_selected_mode(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["show", str(image), "--mode", "light"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "light"
    assert set(payload["theme"]["modes"]) == {"dark", "light"}
    assert len(fake_engine.calls) == 1


def test_show_invalid_mode_is_a_typed_error(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["show", str(image), "--mode", "sepia"],
        monkeypatch,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "UnknownModeError"
    assert not fake_engine.calls
