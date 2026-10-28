from __future__ import annotations

from pathlib import Path

import pytest

import theme_producer
from theme_producer.adapters.settings.config_resolver import AssembledConfigResolver
from theme_producer.adapters.version_provider import get_version
from theme_producer.domain.settings import ContainerEngine, RuntimeMode

_DEFAULT_SETTINGS = Path(theme_producer.__file__).resolve().parent / "defaults" / "settings.toml"


def _write_config(
    path: Path,
    directory: str,
    *,
    runtime_mode: str = "local",
    container_engine: str = "docker",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[output]\ndirectory = "{directory}"\n'
        '[generation]\nengine = "matugen"\n'
        f'[runtime]\nmode = "{runtime_mode}"\n'
        f'[container]\nengine = "{container_engine}"\n'
    )
    return path


def test_cli_path_prevails_over_env_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_config(tmp_path / "env_settings.toml", "/prio/env")
    cli_path = _write_config(tmp_path / "cli_settings.toml", "/prio/cli")

    monkeypatch.setenv("THEME_CONFIG_FILE_PATH", str(env_path))
    resolver = AssembledConfigResolver()
    settings = resolver.resolve(explicit_path=str(cli_path))

    assert settings.output.directory == Path("/prio/cli")
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == cli_path.resolve()


def test_env_path_takes_second_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_config(tmp_path / "env_settings.toml", "/prio/env")

    monkeypatch.setenv("THEME_CONFIG_FILE_PATH", str(env_path))
    resolver = AssembledConfigResolver()
    settings = resolver.resolve()

    assert settings.output.directory == Path("/prio/env")
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == env_path.resolve()


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_directory_traversal_finds_settings_at_supported_depth(
    depth: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write_config(tmp_path / "settings.toml", f"/prio/depth{depth}")
    working_dir = tmp_path.joinpath(*(f"level{level}" for level in range(depth)))
    working_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(working_dir)
    resolver = AssembledConfigResolver()
    settings = resolver.resolve()

    assert settings.output.directory == Path(f"/prio/depth{depth}")
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == config_file.resolve()


def test_directory_traversal_depth_4_falls_through_to_xdg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deep_dir = tmp_path / "level0" / "level1" / "level2" / "level3"
    deep_dir.mkdir(parents=True)
    _write_config(tmp_path / "settings.toml", "/prio/depth4-ignored")

    xdg_home = tmp_path / "xdg"
    xdg_file = _write_config(xdg_home / "theme-producer" / "settings.toml", "/prio/xdg")

    monkeypatch.chdir(deep_dir)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    resolver = AssembledConfigResolver()
    settings = resolver.resolve()

    assert settings.output.directory == Path("/prio/xdg")
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == xdg_file.resolve()


def test_xdg_resolves_with_custom_xdg_config_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    xdg_home = tmp_path / "xdg"
    config_file = _write_config(xdg_home / "theme-producer" / "settings.toml", "/prio/xdg-custom")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    resolver = AssembledConfigResolver()
    settings = resolver.resolve()

    assert settings.output.directory == Path("/prio/xdg-custom")
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == config_file.resolve()


def test_xdg_resolves_standard_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xdg_home = tmp_path / ".config"
    config_file = _write_config(xdg_home / "theme-producer" / "settings.toml", "/prio/xdg-standard")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    resolver = AssembledConfigResolver()
    settings = resolver.resolve()

    assert settings.output.directory == Path("/prio/xdg-standard")
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == config_file.resolve()


def test_package_default_fallback_when_no_file_found() -> None:
    resolver = AssembledConfigResolver()
    settings = resolver.resolve()

    assert settings.generation.engine == "matugen"
    assert settings.output.directory == Path("/tmp/theme-producer")
    assert settings.output.default_mode == "dark"
    assert settings.output.smart_threshold == 0.5
    assert settings.runtime.mode is RuntimeMode.LOCAL
    assert settings.container.engine is ContainerEngine.PODMAN
    assert settings.container.image_tag == f"v{get_version()}"
    assert settings.templates.directory == ""
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == _DEFAULT_SETTINGS.resolve()
    assert resolver.last_result.applied_overrides == ()
