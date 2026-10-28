"""End-to-end CLI generate with the real projection registry and a fake engine.

No matugen binary is required: the engine boundary is faked, while settings,
the catalog, templates, Jinja rendering, and canonical theme.json are real.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_image
from theme_producer.domain.models import Theme


def test_local_generate_writes_theme_json_and_all_eight_projections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from theme_producer.factory import create_dependencies

    runner = CliRunner()
    deps = create_dependencies()
    deps.engine_registry = {"matugen": FakeEngine()}
    image = make_image(tmp_path / "wallpaper.png")
    output = tmp_path / "output"

    result = invoke(
        runner,
        deps,
        ["generate", str(image), "-o", str(output)],
        monkeypatch,
    )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    expected = {
        "theme.json",
        "colors.gtk.css",
        "colors.adw.css",
        "colors.yaml",
        "colors.rasi",
        "colors.conf",
        "colors.btop.theme",
        "colors.kitty",
        "colors.sequences",
    }
    assert {path.name for path in output.iterdir()} == expected
    assert len(payload["output_files"]) == 9

    theme_payload = json.loads((output / "theme.json").read_text(encoding="utf-8"))
    assert Theme.from_dict(theme_payload).SCHEMA_VERSION == "1"

    assert (output / "colors.yaml").read_text(encoding="utf-8").startswith("# colors.yaml")
    assert "background" in (output / "colors.gtk.css").read_text(encoding="utf-8")
    assert "@define-color" in (output / "colors.rasi").read_text(encoding="utf-8")
    assert "$background" in (output / "colors.conf").read_text(encoding="utf-8")
    assert "theme[main_bg]" in (output / "colors.btop.theme").read_text(encoding="utf-8")
    assert "background " in (output / "colors.kitty").read_text(encoding="utf-8")
    assert (output / "colors.sequences").read_bytes().startswith(b"\x1b]4;0;")
    assert not (output / "theme.html").exists()  # dev-only preview is opt-in
