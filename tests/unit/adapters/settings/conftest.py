from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clean_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A host ``THEME__*`` variable must never change a test result."""
    monkeypatch.delenv("THEME_CONFIG_FILE_PATH", raising=False)
    monkeypatch.delenv("THEME_TEMPLATES_TEMPLATES_DIR", raising=False)
    for name in list(os.environ):
        if name.startswith("THEME__"):
            monkeypatch.delenv(name, raising=False)
