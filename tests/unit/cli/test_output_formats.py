from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps, make_image


def test_json_is_the_default_and_contains_no_ansi(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--format", "json", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert "\x1b" not in result.stdout
    assert json.loads(result.stdout)["success"] is True


def test_rich_output_renders_human_view(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(
        runner,
        make_deps(fake_engine),
        ["--output-format", "rich", "info"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert "Configuration" in result.stdout
    assert "Engines" in result.stdout


def test_plain_output_renders_human_view_without_ansi(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(
        runner,
        make_deps(fake_engine),
        ["--output-format", "plain", "info"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert "settings:" in result.stdout
    assert "formats:" in result.stdout
    assert "\x1b" not in result.stdout


def test_quiet_suppresses_success_output(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(
        runner,
        make_deps(fake_engine),
        ["--quiet", "info"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip() == ""


def test_json_error_contract_is_stable_and_ansi_free(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--format", "nope", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 1
    assert "\x1b" not in result.stderr
    payload = json.loads(result.stderr)
    assert set(payload) == {"success", "error"}
    assert payload["success"] is False
    assert set(payload["error"]) >= {"type", "message"}
