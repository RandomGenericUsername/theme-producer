"""``tpr version`` — print the package version."""

from __future__ import annotations

import typer

from theme_producer.adapters.version_provider import get_version

__all__ = ["version"]


def version() -> None:
    typer.echo(get_version())
