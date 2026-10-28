from __future__ import annotations

from typer.testing import CliRunner

from theme_producer import __version__
from theme_producer.cli.main import app

runner = CliRunner()


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == __version__


def test_version_option_prints_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == __version__
