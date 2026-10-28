from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps
from theme_producer.adapters.version_provider import get_version


def test_info_reports_resolved_settings_templates_engines_formats(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "settings.toml"
    config.write_text(f'[output]\ndirectory = "{tmp_path / "out"}"\n', encoding="utf-8")

    result = invoke(runner, make_deps(fake_engine), ["info", "--config", str(config)], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["command"] == "info"
    assert payload["settings_path"] == str(config.resolve())
    assert Path(payload["templates_path"]).is_dir()
    engines = {engine["name"]: engine for engine in payload["engines"]}
    assert set(engines) == {"matugen", "native"}
    assert "json" in payload["formats"]
    assert "gtk.css" in payload["formats"]
    assert payload["applied_overrides"] == []
    assert payload["settings"]["runtime"]["mode"] == "local"
    assert payload["settings"]["container"]["image_tag"] == f"v{get_version()}"


def test_info_reports_applied_overrides(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THEME__OUTPUT__OVERWRITE", "true")

    result = invoke(runner, make_deps(fake_engine), ["info"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    overrides = {
        override["field_path"]: override for override in payload["applied_overrides"]
    }
    assert overrides["output.overwrite"]["raw_value"] == "true"
    assert overrides["output.overwrite"]["source"] == "env"
    assert payload["settings"]["output"]["overwrite"] is True
