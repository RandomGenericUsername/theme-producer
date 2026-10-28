from __future__ import annotations

from pathlib import Path

import pytest

from theme_producer.adapters.settings.config_resolver import AssembledConfigResolver
from theme_producer.adapters.settings.errors import ConfigResolutionError
from theme_producer.adapters.settings.schema import CoreSettingsSchema
from theme_producer.adapters.version_provider import get_version
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
    assert settings.output.default_mode == "dark"
    assert settings.output.smart_threshold == 0.5
    assert settings.generation.scheme_policy == "balanced"


def test_empty_image_tag_resolves_to_version_pin(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    config.write_text(config.read_text() + 'image_tag = ""\n', encoding="utf-8")

    settings = AssembledConfigResolver().resolve(explicit_path=str(config))

    assert settings.container.image_tag == f"v{get_version()}"


def test_explicit_image_tag_is_kept(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    config.write_text(config.read_text() + 'image_tag = "v9.9.9"\n', encoding="utf-8")

    settings = AssembledConfigResolver().resolve(explicit_path=str(config))

    assert settings.container.image_tag == "v9.9.9"


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
        (
            "THEME__OUTPUT__DEFAULT_MODE",
            "smart",
            lambda s: s.output.default_mode == "smart",
        ),
        (
            "THEME__OUTPUT__SMART_THRESHOLD",
            "0.8",
            lambda s: s.output.smart_threshold == 0.8,
        ),
        ("THEME__GENERATION__ENGINE", "native", lambda s: s.generation.engine == "native"),
        (
            "THEME__GENERATION__DEFAULT_PARAMS",
            "a:one;b:two",
            lambda s: dict(s.generation.default_params) == {"a": "one", "b": "two"},
        ),
        (
            "THEME__GENERATION__SCHEME_POLICY",
            "vivid",
            lambda s: s.generation.scheme_policy == "vivid",
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
        "output.default_mode",
        "output.smart_threshold",
        "generation.engine",
        "generation.default_params",
        "generation.scheme_policy",
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


def test_cli_overrides_output_default_mode_and_threshold(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    resolver = AssembledConfigResolver()

    settings = resolver.resolve(
        explicit_path=str(config),
        cli_overrides={
            "output.default_mode": "smart",
            "output.smart_threshold": "0.75",
        },
    )

    assert settings.output.default_mode == "smart"
    assert settings.output.smart_threshold == 0.75
    assert resolver.last_result is not None
    applied = {override.field_path: override for override in resolver.last_result.applied_overrides}
    assert applied["output.default_mode"].source == "cli"
    assert applied["output.smart_threshold"].coerced_value == 0.75


def test_cli_overrides_generation_scheme_policy(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "settings.toml")
    resolver = AssembledConfigResolver()

    settings = resolver.resolve(
        explicit_path=str(config),
        cli_overrides={"generation.scheme_policy": "source-faithful"},
    )

    assert settings.generation.scheme_policy == "source-faithful"
    assert resolver.last_result is not None
    applied = {override.field_path: override for override in resolver.last_result.applied_overrides}
    assert applied["generation.scheme_policy"].source == "cli"
    assert applied["generation.scheme_policy"].coerced_value == "source-faithful"


@pytest.mark.parametrize(
    ("field_path", "value", "key", "match"),
    [
        ("output.default_mode", "sepia", "output.default_mode", "Invalid output default mode"),
        ("output.smart_threshold", "1.5", "output.smart_threshold", "smart threshold"),
        ("output.smart_threshold", "-0.1", "output.smart_threshold", "smart threshold"),
        (
            "generation.scheme_policy",
            "   ",
            "generation.scheme_policy",
            "scheme_policy must be a non-empty",
        ),
    ],
)
def test_invalid_projection_settings_are_reported_with_field_key(
    tmp_path: Path,
    field_path: str,
    value: str,
    key: str,
    match: str,
) -> None:
    config = _write_config(tmp_path / "settings.toml")

    with pytest.raises(ConfigResolutionError, match=match) as excinfo:
        AssembledConfigResolver().resolve(
            explicit_path=str(config), cli_overrides={field_path: value}
        )

    assert excinfo.value.key == key
