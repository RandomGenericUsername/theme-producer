from __future__ import annotations

import os
from pathlib import Path

_HERMETIC_XDG_VARS = (
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_STATE_HOME",
)
_HERMETIC_HOST_ONLY_VARS = (
    "THEME_CONFIG_FILE_PATH",
    "THEME_TEMPLATES_TEMPLATES_DIR",
)


def test_hermetic_environment_canary() -> None:
    """Fail if the autouse fixture is bypassed and the host environment is reachable."""
    home = Path(os.environ["HOME"])
    root = home.parent
    assert home.name == "home"
    assert Path.home() == home
    assert Path.cwd().is_relative_to(root)
    assert Path.cwd() != home

    for name in _HERMETIC_XDG_VARS:
        value = Path(os.environ[name])
        assert value.is_relative_to(root), f"{name}={value} is outside {root}"
        assert value.is_dir(), f"{name}={value} is not a directory"

    for name in _HERMETIC_HOST_ONLY_VARS:
        assert name not in os.environ, f"{name} leaked from the host environment"

    leaked = [name for name in os.environ if name.startswith("DOTFILES_")]
    assert not leaked, f"DOTFILES_* leaked from the host environment: {leaked}"

    assert os.environ["NO_COLOR"] == "1"
    assert os.environ["COLUMNS"] == "200"
