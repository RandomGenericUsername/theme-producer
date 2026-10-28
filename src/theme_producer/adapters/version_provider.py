"""Resolve the installed package version with an in-tree fallback.

Editable installs and ``uv run`` both expose metadata, but a source tree used
without installation still needs ``tpr --version`` to work. The fallback keeps
the package's declared ``__version__`` authoritative in that case.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

from theme_producer import __version__

__all__ = ["get_version"]

_DISTRIBUTION_NAME = "theme-producer"


def get_version() -> str:
    """Return the installed distribution version, or ``__version__``."""
    try:
        return _distribution_version(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return __version__
