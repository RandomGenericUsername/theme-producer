from __future__ import annotations

import os
from pathlib import Path

# Output determinism: Typer reads these at import time, and a CI runner exports
# GITHUB_ACTIONS (Typer then forces a terminal) plus a narrow width, so Rich
# wraps and interleaves ANSI inside a value assertion. Pin them before the CLI
# modules are imported; the hermetic fixture re-asserts them per test so a test
# cannot leak a host value either.
os.environ["_TYPER_FORCE_DISABLE_TERMINAL"] = "1"
os.environ["NO_COLOR"] = "1"
os.environ["COLUMNS"] = "200"
os.environ["TERMINAL_WIDTH"] = "200"
os.environ.pop("FORCE_COLOR", None)

import pytest

_HERMETIC_XDG_VARS = (
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_STATE_HOME",
)
_HERMETIC_HOST_ONLY_VARS = (
    "THEME_CONFIG_FILE_PATH",
    "THEME_TEMPLATES_TEMPLATES_DIR",
    "THEME_SCHEME_POLICIES_CONFIG_FILE_PATH",
)


@pytest.fixture(autouse=True)
def _hermetic_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test off the host HOME/XDG/dotfiles config."""
    root = tmp_path / "hermetic"
    home = root / "home"
    work = root / "work" / "a" / "b" / "c"
    home.mkdir(parents=True)
    work.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    for name in _HERMETIC_XDG_VARS:
        path = root / name.lower()
        path.mkdir(parents=True)
        monkeypatch.setenv(name, str(path))
    for name in _HERMETIC_HOST_ONLY_VARS:
        monkeypatch.delenv(name, raising=False)
    # Every DOTFILES_* variable is host state, whichever one a future adapter
    # reads; delete the whole namespace rather than an allow-list.
    for name in list(os.environ):
        if name.startswith("DOTFILES_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(work)
