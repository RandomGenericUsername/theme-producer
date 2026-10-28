from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from tests.unit.cli.conftest import FakeEngine, invoke, make_deps
from theme_producer import __version__
from theme_producer.adapters.version_provider import get_version


def test_version_provider_falls_back_to_dunder_version() -> None:
    version = get_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert version == __version__


def test_version_command_prints_version_with_injected_deps(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(runner, make_deps(fake_engine), ["version"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip() == __version__


def test_version_global_flag_prints_version(
    runner: CliRunner,
    fake_engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = invoke(runner, make_deps(fake_engine), ["--version"], monkeypatch)

    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip() == __version__
