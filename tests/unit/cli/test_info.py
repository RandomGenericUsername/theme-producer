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
    assert payload["settings"]["output"]["default_mode"] == "dark"
    assert payload["settings"]["output"]["smart_threshold"] == 0.5
    assert payload["scheme_policy"]["profile"] == "balanced"
    assert payload["scheme_policy"]["loaded"] is True
    assert payload["scheme_policy"]["profile_found"] is True
    assert payload["scheme_policy"]["catalog_path"].endswith("scheme-policies.yaml")
    assert payload["scheme_policy"]["error"] is None


def test_info_reports_applied_overrides(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THEME__OUTPUT__OVERWRITE", "true")
    monkeypatch.setenv("THEME__OUTPUT__DEFAULT_MODE", "smart")
    monkeypatch.setenv("THEME__OUTPUT__SMART_THRESHOLD", "0.8")

    result = invoke(runner, make_deps(fake_engine), ["info"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    overrides = {override["field_path"]: override for override in payload["applied_overrides"]}
    assert overrides["output.overwrite"]["raw_value"] == "true"
    assert overrides["output.overwrite"]["source"] == "env"
    assert payload["settings"]["output"]["overwrite"] is True
    assert overrides["output.default_mode"]["source"] == "env"
    assert overrides["output.smart_threshold"]["coerced_value"] == 0.8
    assert payload["settings"]["output"]["default_mode"] == "smart"
    assert payload["settings"]["output"]["smart_threshold"] == 0.8


def test_info_reports_a_custom_policy_catalog_and_profile(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = tmp_path / "custom-policies.yaml"
    catalog.write_text(
        """
version: 1
default: custom
policies:
  custom:
    default: scheme-neutral
    rules:
      - when: { contrast: { gte: 0.4 } }
        variant: scheme-vibrant
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("THEME_SCHEME_POLICIES_CONFIG_FILE_PATH", str(catalog))
    monkeypatch.setenv("THEME__GENERATION__SCHEME_POLICY", "custom")

    result = invoke(runner, make_deps(fake_engine), ["info"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["settings"]["generation"]["scheme_policy"] == "custom"
    assert payload["scheme_policy"] == {
        "profile": "custom",
        "catalog_path": str(catalog.resolve()),
        "loaded": True,
        "profile_found": True,
        "error": None,
    }


def test_info_reports_an_unknown_profile_without_failing(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THEME__GENERATION__SCHEME_POLICY", "missing")

    result = invoke(runner, make_deps(fake_engine), ["info"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    report = payload["scheme_policy"]
    assert report["profile"] == "missing"
    assert report["loaded"] is True
    assert report["profile_found"] is False
    assert "unknown scheme policy" in report["error"]
