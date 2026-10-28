"""The `tpr` Typer application.

The harness ticket exposes only `version` and `--version`; the rest of the CLI
surface arrives with REQ-010.
"""

from __future__ import annotations

import typer

from theme_producer import __version__

app = typer.Typer(
    name="tpr",
    help="Theme Producer — turn a wallpaper, seed color, or JSON into a Material You theme.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if not value:
        return
    typer.echo(__version__)
    raise typer.Exit()


@app.callback()
def main_callback(
    show_version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the package version and exit.",
    ),
) -> None:
    """Theme Producer."""


@app.command(help="Show the installed package version")
def version() -> None:
    typer.echo(__version__)
