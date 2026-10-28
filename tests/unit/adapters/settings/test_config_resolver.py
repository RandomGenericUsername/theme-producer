from __future__ import annotations

from pathlib import Path

import pytest

from theme_producer.adapters.settings.config_resolver import AssembledConfigResolver
from theme_producer.adapters.settings.errors import ConfigResolutionError
from theme_producer.adapters.settings.schema import CoreSettingsSchema
from theme_producer.domain.settings import (
    AppSettings,
    ContainerEngine,
    ContainerSettings,
    GenerationSettings,
    OutputSettings,
    RuntimeMode,
    RuntimeSettings,
    TemplatesSettings,
    Verbosity,
)


def _write_config(path: Path, directory: str = "/tmp/base") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[output]\ndirectory = "{directory}"\n'
        '[generation]\nengine = "matugen"\n'
        '[runtime]\nmode = "local"\n'
        '[container]\nengine = "docker"\n'
    )
    return path


def test_resolve_returns_domain_settings(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")

    settings = AssembledConfigResolver().resolve(explicit_path=str(config))

    assert isinstance(settings, AppSettings)
    assert isinstance(settings.output, OutputSettings)
    assert isinstance(settings.generation, GenerationSettings)
    assert isinstance(settings.templates, TemplatesSettings)
    assert isinstance(settings.runtime, RuntimeSettings)
    assert isinstance(settings.container, ContainerSettings)
    assert settings.output.directory == Path("/tmp/base")
    assert settings.generation.engine == "matugen"
    assert settings.runtime.mode is RuntimeMode.LOCAL
    assert settings.container.engine is ContainerEngine.DOCKER
    assert settings.output.verbosity is Verbosity.NORMAL


def test_last_result_reports_path_and_applied_overrides(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    resolver = AssembledConfigResolver()

    settings = resolver.resolve(
        explicit_path=str(config),
        cli_overrides={"runtime.mode": "container", "output.overwrite": "true"},
    )

    assert settings.runtime.mode is RuntimeMode.CONTAINER
    assert settings.output.overwrite is True
    assert resolver.last_result is not None
    assert resolver.last_result.resolved_path == config.resolve()
    applied = {override.field_path: override for override in resolver.last_result.applied_overrides}
    assert applied["runtime.mode"].raw_value == "container"
    assert applied["runtime.mode"].coerced_value == "container"
    assert applied["runtime.mode"].source == "cli"
    assert applied["output.overwrite"].coerced_value is True


def test_cli_overrides_beat_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _write_config(tmp_path / "settings.toml")
    monkeypatch.setenv("THEME__RUNTIME__MODE", "container")

    settings = AssembledConfigResolver().resolve(
        explicit_path=str(config),
        cli_overrides={"runtime.mode": "local"},
    )

    assert settings.runtime.mode is RuntimeMode.LOCAL


@pytest.mark.parametrize(
    ("env_var", "value", "assertion"),
    [
        (
            "THEME__OUTPUT__DIRECTORY",
            "/custom/out",
            lambda s: s.output.directory == Path("/custom/out"),
        ),
        (
            "THEME__OUTPUT__DEFAULT_FORMATS",
            "json,yaml",
            lambda s: s.output.default_formats == ("json", "yaml"),
        ),
        ("THEME__OUTPUT__OVERWRITE", "true", lambda s: s.output.overwrite is True),
        ("THEME__OUTPUT__VERBOSITY", "3", lambda s: s.output.verbosity is Verbosity.DEBUG),
        (
            "THEME__OUTPUT__APPLY_TO_TERMINAL",
            "false",
            lambda s: s.output.apply_to_terminal is False,
        ),
        ("THEME__GENERATION__ENGINE", "native", lambda s: s.generation.engine == "native"),
        (
            "THEME__GENERATION__DEFAULT_PARAMS",
            "a:one;b:two",
            lambda s: dict(s.generation.default_params) == {"a": "one", "b": "two"},
        ),
        (
            "THEME__TEMPLATES__DIRECTORY",
            "/custom/templates",
            lambda s: s.templates.directory == "/custom/templates",
        ),
        ("THEME__RUNTIME__MODE", "container", lambda s: s.runtime.mode is RuntimeMode.CONTAINER),
        (
            "THEME__CONTAINER__ENGINE",
            "podman",
            lambda s: s.container.engine is ContainerEngine.PODMAN,
        ),
        ("THEME__CONTAINER__IMAGE_PREFIX", "myapp", lambda s: s.container.image_prefix == "myapp"),
        ("THEME__CONTAINER__IMAGE_TAG", "v1", lambda s: s.container.image_tag == "v1"),
        ("THEME__CONTAINER__TIMEOUT_SECONDS", "42", lambda s: s.container.timeout_seconds == 42),
        ("THEME__CONTAINER__MEMORY_LIMIT", "2G", lambda s: s.container.memory_limit == "2g"),
    ],
)
def test_every_scalar_env_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    value: str,
    assertion: object,
) -> None:
    config = _write_config(tmp_path / "settings.toml")
    monkeypatch.setenv(env_var, value)

    settings = AssembledConfigResolver().resolve(explicit_path=str(config))

    assert callable(assertion)
    assert assertion(settings)  # type: ignore[operator]


def test_resolver_uses_theme_schema_and_policy() -> None:
    from unittest.mock import create_autospec

    from config_assembler_engine.application.use_cases import AssembleConfiguration
    from config_assembler_engine.domain.models import (
        AppliedOverride as EngineAppliedOverride,
    )
    from config_assembler_engine.domain.models import (
        AssemblyResult,
        OverrideSource,
        PathSource,
        ResolvedPath,
    )

    mock_assembler = create_autospec(AssembleConfiguration, instance=True)
    mock_assembler.execute.return_value = AssemblyResult(
        config=CoreSettingsSchema(output={"directory": "/tmp/out"}),
        resolved_path=ResolvedPath(Path("/tmp/settings.toml"), PathSource.CLI_PATH),
        applied_overrides=[
            EngineAppliedOverride("runtime.mode", "container", "container", OverrideSource.CLI)
        ],
    )
    resolver = AssembledConfigResolver(assembler=mock_assembler)
    resolver.resolve()

    _, kwargs = mock_assembler.execute.call_args
    assert kwargs["schema"] is CoreSettingsSchema
    assert kwargs["policy"].env_prefix == "THEME"
    rule_paths = {rule.field_path for rule in kwargs["rules"]}
    assert rule_paths == {
        "output.directory",
        "output.default_formats",
        "output.overwrite",
        "output.verbosity",
        "output.apply_to_terminal",
        "generation.engine",
        "generation.default_params",
        "templates.directory",
        "runtime.mode",
        "container.engine",
        "container.image_prefix",
        "container.image_tag",
        "container.timeout_seconds",
        "container.memory_limit",
    }
    assert resolver.last_result is not None
    assert resolver.last_result.applied_overrides[0].source == "cli"


def test_malformed_toml_raises_config_resolution_error(tmp_path: Path) -> None:
    malformed = tmp_path / "settings.toml"
    malformed.write_text("{{{ not valid toml }}}")

    resolver = AssembledConfigResolver()
    with pytest.raises(ConfigResolutionError) as excinfo:
        resolver.resolve(explicit_path=str(malformed))

    assert excinfo.value.key == "settings.toml"
    assert excinfo.value.source is not None
    assert "Failed to parse TOML" in excinfo.value.reason


def test_invalid_runtime_mode_is_reported_with_field_key(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    config.write_text(config.read_text().replace('mode = "local"', 'mode = "hybrid"'))

    with pytest.raises(ConfigResolutionError) as excinfo:
        AssembledConfigResolver().resolve(explicit_path=str(config))

    assert excinfo.value.key == "runtime.mode"
    assert "Invalid runtime mode 'hybrid'" in excinfo.value.reason
    assert excinfo.value.source is not None


def test_invalid_container_engine_is_reported_with_field_key(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    config.write_text(config.read_text().replace('engine = "docker"', 'engine = "containerd"'))

    with pytest.raises(ConfigResolutionError) as excinfo:
        AssembledConfigResolver().resolve(explicit_path=str(config))

    assert excinfo.value.key == "container.engine"
    assert "Invalid container engine 'containerd'" in excinfo.value.reason


def test_invalid_memory_limit_is_reported_with_field_key(tmp_path: Path) -> None:
    config = tmp_path / "settings.toml"
    config.write_text(
        '[output]\ndirectory = "/tmp/out"\n'
        '[runtime]\nmode = "local"\n'
        '[container]\nengine = "docker"\nmemory_limit = "512mb"\n'
    )

    with pytest.raises(ConfigResolutionError) as excinfo:
        AssembledConfigResolver().resolve(explicit_path=str(config))

    assert excinfo.value.key == "container.memory_limit"
    assert "Invalid memory limit '512mb'" in excinfo.value.reason


def test_invalid_env_override_is_wrapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _write_config(tmp_path / "settings.toml")
    monkeypatch.setenv("THEME__CONTAINER__ENGINE", "containerd")

    with pytest.raises(ConfigResolutionError) as excinfo:
        AssembledConfigResolver().resolve(explicit_path=str(config))

    assert excinfo.value.key == "container.engine"
    assert "Invalid container engine 'containerd'" in excinfo.value.reason
