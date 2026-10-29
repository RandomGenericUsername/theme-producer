"""CLI integration for the ``scheme-smart`` pseudo-variant (REQ-021).

The engine boundary is faked; the metrics adapter, policy catalog, settings
resolution, and processors are real. Synthetic images keep the suite hermetic.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import (
    FakeContainerRuntime,
    FakeEngine,
    invoke,
    load_theme,
    make_deps,
    make_image,
    make_solid_image,
)
from theme_producer.cli._scheme import resolve_scheme, theme_request_for
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.exceptions import InvalidImageMetricsError
from theme_producer.domain.models import Theme

#: A solid red image measures saturation 1.0, colorfulness ~0.336, contrast 0.
RED = (255, 0, 0)


class EchoSchemeEngine(FakeEngine):
    """Fake engine that records the concrete scheme in the returned Theme."""

    def generate(self, request: ThemeRequest, config: EngineConfig) -> Theme:
        self.calls.append((request, config))
        return replace(self.theme, scheme=str(config.params["scheme_type"]))


class CapturingRuntime(FakeContainerRuntime):
    """Fake runtime that also keeps the mounted inner settings file."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.settings_text: str | None = None

    def run(self, image, command, mounts, timeout, environment=None, memory_limit=None):
        for mount in mounts:
            if mount.target == "/tpr-config/settings.toml":
                self.settings_text = mount.source.read_text(encoding="utf-8")
        return super().run(image, command, mounts, timeout, environment, memory_limit)


def _engine_calls(engine: FakeEngine) -> list[tuple[ThemeRequest, EngineConfig]]:
    return list(engine.calls)


def _forbid_policy_load(monkeypatch: pytest.MonkeyPatch, deps) -> None:
    def _explode(*_args, **_kwargs):
        raise AssertionError("the scheme-policy catalog must not be loaded")

    monkeypatch.setattr(deps.scheme_policy_catalog_loader, "load", _explode)


def test_explicit_real_scheme_type_bypasses_the_policy(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    deps = make_deps(fake_engine)
    _forbid_policy_load(monkeypatch, deps)

    result = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--param",
            "scheme_type=scheme-content",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-content"
    assert json.loads(result.stdout)["scheme"]["requested"] == "scheme-content"
    assert json.loads(result.stdout)["scheme"]["smart"] is False


def test_default_scheme_type_is_still_tonal_spot(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    deps = make_deps(fake_engine)
    _forbid_policy_load(monkeypatch, deps)

    result = invoke(
        runner, deps, ["generate", str(image), "-o", str(tmp_path / "out")], monkeypatch
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-tonal-spot"


def test_settings_scheme_type_selects_the_variant(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    config = tmp_path / "settings.toml"
    config.write_text(
        f'[output]\ndirectory = "{tmp_path / "out"}"\n'
        '[generation]\nscheme_type = "scheme-expressive"\n',
        encoding="utf-8",
    )
    deps = make_deps(fake_engine)
    _forbid_policy_load(monkeypatch, deps)

    result = invoke(runner, deps, ["generate", str(image), "--config", str(config)], monkeypatch)

    assert result.exit_code == 0, result.stderr
    _request, engine_config = _engine_calls(fake_engine)[0]
    assert engine_config.params["scheme_type"] == "scheme-expressive"


def test_env_scheme_type_smart_runs_the_policy(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    monkeypatch.setenv("THEME__GENERATION__SCHEME_TYPE", "scheme-smart")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-vibrant"
    scheme = json.loads(result.stdout)["scheme"]
    assert scheme["requested"] == "scheme-smart"
    assert scheme["variant"] == "scheme-vibrant"
    assert scheme["profile"] == "balanced"
    assert scheme["metrics"]["saturation"] == pytest.approx(1.0)


def test_scheme_policy_alone_does_not_enable_smart(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    deps = make_deps(fake_engine)
    _forbid_policy_load(monkeypatch, deps)

    result = invoke(
        runner,
        deps,
        ["generate", str(image), "--scheme-policy", "muted", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-tonal-spot"
    assert json.loads(result.stdout)["scheme"]["smart"] is False


@pytest.mark.parametrize("engine_name", ["matugen", "native"])
def test_smart_is_accepted_by_both_engines_and_forwards_the_concrete_variant(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    engine_name: str,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    deps = make_deps(fake_engine)
    deps.engine_registry[engine_name] = fake_engine

    result = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--engine",
            engine_name,
            "--param",
            "scheme_type=scheme-smart",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-vibrant"
    assert "scheme-smart" not in config.params.values()


def test_scheme_policy_selects_a_different_variant(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    deps = make_deps(fake_engine)

    for profile, expected in (
        ("balanced", "scheme-vibrant"),
        ("muted", "scheme-tonal-spot"),
        ("source-faithful", "scheme-content"),
    ):
        fake_engine.calls.clear()
        result = invoke(
            runner,
            deps,
            [
                "generate",
                str(image),
                "--param",
                "scheme_type=scheme-smart",
                "--scheme-policy",
                profile,
                "-o",
                str(tmp_path / profile),
            ],
            monkeypatch,
        )
        assert result.exit_code == 0, result.stderr
        _request, config = _engine_calls(fake_engine)[0]
        assert config.params["scheme_type"] == expected, profile
        assert json.loads(result.stdout)["scheme"]["profile"] == profile


def test_policies_file_override_selects_the_custom_catalog(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    catalog = tmp_path / "custom-policies.yaml"
    catalog.write_text(
        """
version: 1
default: force-neutral
policies:
  force-neutral:
    default: scheme-neutral
    rules:
      - when: { contrast: { gte: 0.0 } }
        variant: scheme-neutral
""",
        encoding="utf-8",
    )

    result = invoke(
        runner,
        make_deps(fake_engine),
        [
            "generate",
            str(image),
            "--policies-file",
            str(catalog),
            "--scheme-policy",
            "force-neutral",
            "--param",
            "scheme_type=scheme-smart",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-neutral"
    payload = json.loads(result.stdout)
    assert payload["scheme"]["catalog_path"] == str(catalog.resolve())
    assert payload["scheme"]["profile"] == "force-neutral"


def test_cli_scheme_policy_beats_env(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    monkeypatch.setenv("THEME__GENERATION__SCHEME_POLICY", "muted")
    monkeypatch.setenv("THEME__GENERATION__SCHEME_TYPE", "scheme-smart")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--scheme-policy", "source-faithful", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-content"
    assert json.loads(result.stdout)["scheme"]["profile"] == "source-faithful"


def test_cli_param_scheme_type_beats_env_smart(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    monkeypatch.setenv("THEME__GENERATION__SCHEME_TYPE", "scheme-smart")
    deps = make_deps(fake_engine)
    _forbid_policy_load(monkeypatch, deps)

    result = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--param",
            "scheme_type=scheme-monochrome",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-monochrome"


def test_dry_run_reports_metrics_profile_and_variant(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        [
            "generate",
            str(image),
            "--param",
            "scheme_type=scheme-smart",
            "--scheme-policy",
            "balanced",
            "--format",
            "yaml",
            "--dry-run",
            "-o",
            str(output),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["scheme"]["requested"] == "scheme-smart"
    assert payload["scheme"]["variant"] == "scheme-vibrant"
    assert payload["scheme"]["profile"] == "balanced"
    assert payload["scheme"]["metrics"]["saturation"] == pytest.approx(1.0)
    assert payload["scheme"]["metrics"]["colorfulness"] == pytest.approx(0.335, abs=1e-3)
    assert "--param scheme_type=scheme-vibrant" in payload["plan"]
    assert "scheme-smart" not in payload["plan"]
    assert not fake_engine.calls
    assert not output.exists()


def test_container_receives_only_the_concrete_variant(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)
    output = tmp_path / "out"
    runtime = CapturingRuntime(
        images={"tpr-matugen-podman:latest"},
        run_stdout=json.dumps(
            {
                "success": True,
                "command": "generate",
                "engine": "matugen",
                "theme": load_theme().to_dict(),
                "output_files": ["/output/theme.json"],
                "duration": 0.1,
            }
        ),
    )
    config = tmp_path / "settings.toml"
    config.write_text(
        f'[output]\ndirectory = "{output}"\n'
        '[generation]\nscheme_type = "scheme-smart"\n'
        '[runtime]\nmode = "container"\n'
        '[container]\nengine = "podman"\nimage_tag = "latest"\n',
        encoding="utf-8",
    )

    result = invoke(
        runner,
        make_deps(fake_engine, container_runtime=runtime),
        ["generate", str(image), "--config", str(config)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    command = runtime.runs[0]["command"]
    param_values = [command[i + 1] for i, item in enumerate(command) if item == "--param"]
    assert "scheme_type=scheme-vibrant" in param_values
    assert not any("scheme-smart" in value for value in param_values)
    assert runtime.settings_text is not None
    assert 'scheme_type = "scheme-vibrant"' in runtime.settings_text
    assert "scheme-smart" not in runtime.settings_text


def test_theme_json_records_the_concrete_variant(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = EchoSchemeEngine()
    image = make_solid_image(tmp_path / "red.png", RED)
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(engine),
        [
            "generate",
            str(image),
            "--param",
            "scheme_type=scheme-smart",
            "--format",
            "json",
            "-o",
            str(output),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    theme_payload = json.loads((output / "theme.json").read_text(encoding="utf-8"))
    assert theme_payload["scheme"] == "scheme-vibrant"
    assert json.loads(result.stdout)["theme"]["scheme"] == "scheme-vibrant"


def test_show_uses_the_same_smart_path(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "red.png", RED)

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["show", str(image), "--param", "scheme_type=scheme-smart", "--scheme-policy", "muted"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = _engine_calls(fake_engine)[0]
    assert config.params["scheme_type"] == "scheme-tonal-spot"
    payload = json.loads(result.stdout)
    assert payload["scheme"]["smart"] is True
    assert payload["scheme"]["profile"] == "muted"


def test_color_source_uses_the_same_metrics_port(
    fake_engine: FakeEngine,
    tmp_path: Path,
) -> None:
    deps = make_deps(fake_engine)
    resolution = resolve_scheme(
        deps,
        request=theme_request_for(tmp_path / "unused.png", seed_color="#ff0000"),
        requested="scheme-smart",
        profile="balanced",
        policies_file=None,
    )

    assert resolution.metrics is not None
    assert resolution.metrics.saturation == pytest.approx(1.0)
    assert resolution.metrics.colorfulness == 0.0
    # balanced's first rule sees colorfulness < 0.08.
    assert resolution.variant.value == "scheme-monochrome"


def test_json_source_with_smart_raises_the_typed_metrics_error(
    fake_engine: FakeEngine,
    tmp_path: Path,
) -> None:
    deps = make_deps(fake_engine)
    source = tmp_path / "theme.json"
    source.write_text("{}", encoding="utf-8")

    with pytest.raises(InvalidImageMetricsError, match="json request has no measurable source"):
        resolve_scheme(
            deps,
            request=ThemeRequest(source_kind="json", json_path=source),
            requested="scheme-smart",
            profile="balanced",
            policies_file=None,
        )
