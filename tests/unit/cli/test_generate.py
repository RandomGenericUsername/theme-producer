from __future__ import annotations

import json
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
from theme_producer.domain.models import Theme


def test_generate_writes_theme_json_and_selected_projections(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        [
            "generate",
            str(image),
            "--engine",
            "matugen",
            "--format",
            "yaml",
            "--format",
            "gtk.css",
            "-o",
            str(output),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["command"] == "generate"
    assert payload["engine"] == "matugen"
    assert payload["theme"]["schema_version"] == "1"
    assert payload["output_files"] == [
        str(output / "theme.json"),
        str(output / "colors.yaml"),
        str(output / "colors.gtk.css"),
    ]
    for name in ("theme.json", "colors.yaml", "colors.gtk.css"):
        assert (output / name).is_file()
    assert "background" in (output / "colors.yaml").read_text(encoding="utf-8")
    assert Theme.from_dict(payload["theme"]).dark.roles
    assert len(fake_engine.calls) == 1


def test_generate_defaults_to_all_non_dev_projections(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "-o", str(output)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["mode"] == "dark"
    files = sorted(path.name for path in output.iterdir())
    assert files == sorted(
        [
            "theme.json",
            "colors.gtk.css",
            "colors.adw.css",
            "colors.yaml",
            "colors.rasi",
            "colors.conf",
            "colors.btop.theme",
            "colors.kitty",
            "colors.sequences",
        ]
    )


def test_generate_json_format_writes_only_theme_json(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--format", "json", "-o", str(output)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert [path.name for path in output.iterdir()] == ["theme.json"]


def test_generate_unknown_format_is_a_typed_error(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
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
    payload = json.loads(result.stderr)
    assert payload["success"] is False
    assert payload["error"]["type"] == "UnknownFormatError"
    assert "known formats" in payload["error"]["message"]
    assert not fake_engine.calls


def test_generate_unknown_param_is_a_typed_error(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--param", "nope=1", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "EngineConfigError"
    assert "unknown parameter" in payload["error"]["message"].lower()
    assert not fake_engine.calls


def test_generate_coerces_params_and_validates_choices(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    deps = make_deps(fake_engine)

    result = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--param",
            "contrast=0.5",
            "--param",
            "source_color_index=2",
            "--param",
            "mode=light",
            "--param",
            "mode=dark",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )
    assert result.exit_code == 0, result.stderr
    _request, config = fake_engine.calls[0]
    assert config.params["contrast"] == 0.5
    assert isinstance(config.params["contrast"], float)
    assert config.params["source_color_index"] == 2
    assert isinstance(config.params["source_color_index"], int)
    assert config.params["mode"] == "dark"

    fake_engine.calls.clear()
    invalid = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--param",
            "mode=sideways",
            "-o",
            str(tmp_path / "out2"),
        ],
        monkeypatch,
    )
    assert invalid.exit_code == 1
    error = json.loads(invalid.stderr)
    assert error["error"]["type"] == "EngineConfigError"
    assert "invalid choice" in error["error"]["message"].lower()


def test_generate_rejects_native_scheme_smart_at_param_validation(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    deps = make_deps(fake_engine)
    deps.engine_registry["native"] = fake_engine

    result = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--engine",
            "native",
            "--param",
            "scheme_type=scheme-smart",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )

    assert result.exit_code == 1
    error = json.loads(result.stderr)
    assert error["error"]["type"] == "EngineConfigError"
    assert "invalid choice" in error["error"]["message"].lower()
    assert "scheme-smart" in error["error"]["message"]
    assert not fake_engine.calls


def test_generate_drops_malformed_params(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--param", "not-a-pair", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    _request, config = fake_engine.calls[0]
    assert "not-a-pair" not in config.params


def test_generate_dry_run_does_not_call_engine_or_write_files(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--format", "yaml", "--dry-run", "-o", str(output)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["plan"].startswith("tpr generate")
    assert payload["plan"].find("--engine matugen") > 0
    assert payload["projections"] == ["colors.yaml"]
    assert not fake_engine.calls
    assert not output.exists()


def test_generate_uses_settings_default_formats(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    config = tmp_path / "settings.toml"
    config.write_text(
        '[output]\ndirectory = "unused"\ndefault_formats = ["yaml"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--config", str(config), "-o", str(output)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert sorted(path.name for path in output.iterdir()) == [
        "colors.yaml",
        "theme.json",
    ]


def test_generate_mode_light_renders_light_roles_and_keeps_both_modes(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        [
            "generate",
            str(image),
            "--mode",
            "light",
            "--format",
            "yaml",
            "--format",
            "gtk.css",
            "--format",
            "kitty",
            "-o",
            str(output),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "light"

    theme_payload = json.loads((output / "theme.json").read_text(encoding="utf-8"))
    assert set(theme_payload["modes"]) == {"dark", "light"}
    light = theme_payload["modes"]["light"]["roles"]

    yaml_text = (output / "colors.yaml").read_text(encoding="utf-8")
    assert f'background: "{light["surface"]}"' in yaml_text
    assert f'foreground: "{light["on_surface"]}"' in yaml_text
    assert f'accent: "{light["primary"]}"' in yaml_text

    gtk_text = (output / "colors.gtk.css").read_text(encoding="utf-8")
    assert f"@define-color surface {light['surface']};" in gtk_text
    assert f"@define-color on_surface {light['on_surface']};" in gtk_text
    assert f"@define-color primary {light['primary']};" in gtk_text

    kitty_text = (output / "colors.kitty").read_text(encoding="utf-8")
    assert f"background {light['surface']}" in kitty_text
    assert f"foreground {light['on_surface']}" in kitty_text


def test_generate_invalid_mode_is_a_typed_error(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--mode", "sepia", "-o", str(tmp_path / "out")],
        monkeypatch,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "UnknownModeError"
    assert "dark, light" in payload["error"]["message"]
    assert not fake_engine.calls


def test_generate_dry_run_prints_the_selected_mode(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")

    result = invoke(
        runner,
        make_deps(fake_engine),
        [
            "generate",
            str(image),
            "--mode",
            "light",
            "--format",
            "yaml",
            "--dry-run",
            "-o",
            str(tmp_path / "out"),
        ],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "light"
    assert "--mode light" in payload["plan"]
    assert not fake_engine.calls


def test_generate_smart_bright_image_selects_light(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "bright.png", (240, 240, 240))
    output = tmp_path / "out"

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--mode", "smart", "--format", "yaml", "-o", str(output)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "light"
    theme_payload = json.loads((output / "theme.json").read_text(encoding="utf-8"))
    assert set(theme_payload["modes"]) == {"dark", "light"}
    light_surface = theme_payload["modes"]["light"]["roles"]["surface"]
    yaml_text = (output / "colors.yaml").read_text(encoding="utf-8")
    assert f'background: "{light_surface}"' in yaml_text


def test_generate_uses_output_default_mode_from_settings(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_image(tmp_path / "wall.png")
    config = tmp_path / "settings.toml"
    config.write_text(
        f'[output]\ndirectory = "{tmp_path / "out"}"\ndefault_mode = "light"\n',
        encoding="utf-8",
    )

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--config", str(config), "--format", "yaml"],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["mode"] == "light"


def test_generate_smart_dry_run_prints_concrete_mode(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bright = make_solid_image(tmp_path / "bright.png", (240, 240, 240))
    dark = make_solid_image(tmp_path / "dark.png", (10, 10, 10))
    deps = make_deps(fake_engine)

    bright_result = invoke(
        runner,
        deps,
        ["generate", str(bright), "--mode", "smart", "--format", "yaml", "--dry-run"],
        monkeypatch,
    )
    assert bright_result.exit_code == 0, bright_result.stderr
    bright_payload = json.loads(bright_result.stdout)
    assert bright_payload["mode"] == "light"
    assert "--mode light" in bright_payload["plan"]
    assert "--mode smart" not in bright_payload["plan"]

    dark_result = invoke(
        runner,
        deps,
        ["generate", str(dark), "--mode", "smart", "--format", "yaml", "--dry-run"],
        monkeypatch,
    )
    assert dark_result.exit_code == 0, dark_result.stderr
    dark_payload = json.loads(dark_result.stdout)
    assert dark_payload["mode"] == "dark"
    assert "--mode dark" in dark_payload["plan"]


def test_generate_smart_threshold_flips_the_decision(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mean relative luminance ~0.6.
    image = make_solid_image(tmp_path / "mean-06.png", (203, 203, 203))
    deps = make_deps(fake_engine)

    light = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--mode",
            "smart",
            "--smart-threshold",
            "0.5",
            "--format",
            "yaml",
            "--dry-run",
        ],
        monkeypatch,
    )
    assert light.exit_code == 0, light.stderr
    assert json.loads(light.stdout)["mode"] == "light"

    dark = invoke(
        runner,
        deps,
        [
            "generate",
            str(image),
            "--mode",
            "smart",
            "--smart-threshold",
            "0.8",
            "--format",
            "yaml",
            "--dry-run",
        ],
        monkeypatch,
    )
    assert dark.exit_code == 0, dark.stderr
    assert json.loads(dark.stdout)["mode"] == "dark"


def test_generate_invalid_smart_threshold_is_a_typed_error(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "bright.png", (240, 240, 240))

    result = invoke(
        runner,
        make_deps(fake_engine),
        ["generate", str(image), "--mode", "smart", "--smart-threshold", "1.5"],
        monkeypatch,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "InvalidSmartThresholdError"
    assert "[0, 1]" in payload["error"]["message"]
    assert not fake_engine.calls


def test_generate_smart_container_receives_the_concrete_mode(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = make_solid_image(tmp_path / "bright.png", (240, 240, 240))
    output = tmp_path / "out"
    runtime = FakeContainerRuntime(
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
        '[runtime]\nmode = "container"\n'
        '[container]\nengine = "podman"\nimage_tag = "latest"\n',
        encoding="utf-8",
    )

    result = invoke(
        runner,
        make_deps(fake_engine, container_runtime=runtime),
        ["generate", str(image), "--mode", "smart", "--config", str(config)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    command = runtime.runs[0]["command"]
    assert command[command.index("--mode") + 1] == "light"
    assert "smart" not in command
