from __future__ import annotations

import os
from pathlib import Path

import pytest

from theme_producer.adapters.template_dir_resolver import TemplateDirResolver

_PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "src" / "theme_producer"
_DEFAULT_TEMPLATES_DIR = _PACKAGE_ROOT / "defaults" / "templates"


@pytest.fixture(autouse=True)
def _clean_templates_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THEME_TEMPLATES_TEMPLATES_DIR", raising=False)
    for name in list(os.environ):
        if name.startswith("THEME_TEMPLATES__"):
            monkeypatch.delenv(name, raising=False)


def test_explicit_directory_beats_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = tmp_path / "explicit-templates"
    explicit.mkdir()
    env_dir = tmp_path / "env-templates"
    env_dir.mkdir()
    monkeypatch.setenv("THEME_TEMPLATES_TEMPLATES_DIR", str(env_dir))

    result = TemplateDirResolver().resolve(explicit_dir=explicit)

    assert result == explicit.resolve()


def test_env_var_takes_second_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    templates_dir = tmp_path / "custom-templates"
    templates_dir.mkdir()
    monkeypatch.setenv("THEME_TEMPLATES_TEMPLATES_DIR", str(templates_dir))

    result = TemplateDirResolver().resolve()

    assert result == templates_dir.resolve()


def test_directory_traversal_finds_templates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    working_dir = tmp_path / "level0" / "level1"
    working_dir.mkdir(parents=True)
    monkeypatch.chdir(working_dir)

    result = TemplateDirResolver().resolve()

    assert result == templates_dir.resolve()


def test_directory_traversal_stops_after_three_levels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    working_dir = tmp_path / "level0" / "level1" / "level2" / "level3"
    working_dir.mkdir(parents=True)
    monkeypatch.chdir(working_dir)

    result = TemplateDirResolver().resolve()

    assert result == _DEFAULT_TEMPLATES_DIR.resolve()


def test_xdg_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xdg_config = tmp_path / "xdg-config"
    templates_dir = xdg_config / "theme-producer" / "templates"
    templates_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

    result = TemplateDirResolver().resolve()

    assert result == templates_dir.resolve()


def test_package_defaults_fallback() -> None:
    result = TemplateDirResolver().resolve()

    assert result == _DEFAULT_TEMPLATES_DIR.resolve()
    assert result.is_dir()


def test_missing_explicit_directory_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_dir = tmp_path / "env-templates"
    env_dir.mkdir()
    monkeypatch.setenv("THEME_TEMPLATES_TEMPLATES_DIR", str(env_dir))

    result = TemplateDirResolver().resolve(explicit_dir=tmp_path / "does-not-exist")

    assert result == env_dir.resolve()
