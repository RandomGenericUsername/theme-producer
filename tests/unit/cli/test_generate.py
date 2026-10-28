from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps, make_image
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
