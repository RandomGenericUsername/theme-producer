from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps


def test_dump_templates_uses_xdg_default(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(runner, make_deps(fake_engine), ["dump-templates"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    target = Path(os.environ["XDG_CONFIG_HOME"]) / "theme-producer" / "templates"
    assert sorted(path.name for path in target.glob("*.j2")) == sorted(
        [
            "colors.adw.css.j2",
            "colors.btop.theme.j2",
            "colors.conf.j2",
            "colors.gtk.css.j2",
            "colors.kitty.j2",
            "colors.rasi.j2",
            "colors.sequences.j2",
            "colors.yaml.j2",
            "theme.html.j2",
        ]
    )


def test_dump_templates_custom_output_and_overwrite_rules(
    runner: CliRunner,
    fake_engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "templates"
    deps = make_deps(fake_engine)

    first = invoke(
        runner,
        deps,
        ["dump-templates", "--output", str(target)],
        monkeypatch,
    )
    assert first.exit_code == 0, first.stderr
    existing = target / "colors.yaml.j2"
    existing.write_text("LOCAL EDIT", encoding="utf-8")

    second = invoke(
        runner,
        deps,
        ["dump-templates", "--output", str(target)],
        monkeypatch,
    )
    assert second.exit_code == 0, second.stderr
    assert existing.read_text(encoding="utf-8") == "LOCAL EDIT"
    assert "skipped" in json.loads(second.stdout)["message"]

    third = invoke(
        runner,
        deps,
        ["dump-templates", "--output", str(target), "--overwrite"],
        monkeypatch,
    )
    assert third.exit_code == 0, third.stderr
    assert "colors.yaml" in existing.read_text(encoding="utf-8")
