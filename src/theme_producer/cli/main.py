"""The ``tpr`` Typer application and global flag wiring."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from cli_output.domain.enums import OutputFormat as SharedOutputFormat

from theme_producer.adapters.version_provider import get_version
from theme_producer.cli.dump_config_cmd import dump_config
from theme_producer.cli.dump_templates_cmd import dump_templates
from theme_producer.cli.generate_cmd import generate
from theme_producer.cli.info_cmd import info
from theme_producer.cli.install_cmd import install
from theme_producer.cli.list_engines_cmd import list_engines
from theme_producer.cli.options import CONFIG_OPT, ENGINE_OPT, RUNTIME_OPT, TEMPLATES_DIR_OPT
from theme_producer.cli.show_cmd import show
from theme_producer.cli.uninstall_cmd import uninstall
from theme_producer.cli.version_cmd import version
from theme_producer.domain.settings import ContainerEngine, RuntimeMode, Verbosity
from theme_producer.factory import CliDependencies, create_dependencies, create_output_adapter

app = typer.Typer(
    name="tpr",
    help=("Theme Producer — turn a wallpaper into a Material You Theme plus consumer projections."),
    no_args_is_help=True,
)


def build_deps() -> CliDependencies:
    """Composition root entry point (monkeypatched by CLI tests)."""
    return create_dependencies()


def _version_callback(value: bool) -> None:
    if not value:
        return
    typer.echo(get_version())
    raise typer.Exit()


@app.callback()
def main_callback(
    ctx: typer.Context,
    show_version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the package version and exit.",
    ),
    output_format: SharedOutputFormat = typer.Option(  # noqa: B008
        SharedOutputFormat.JSON,
        "--output-format",
        help="Output format: json, rich, or plain (default: json)",
        case_sensitive=False,
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (-v, -vv)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error output",
    ),
    config_path: Path | None = CONFIG_OPT,
    templates_dir: Path | None = TEMPLATES_DIR_OPT,
    runtime: RuntimeMode | None = RUNTIME_OPT,
    container_engine: ContainerEngine | None = ENGINE_OPT,
) -> None:
    """Theme Producer."""
    deps = build_deps()

    if quiet:
        verbosity = Verbosity.QUIET
    elif verbose > 0:
        verbosity = Verbosity.DEBUG if verbose > 1 else Verbosity.VERBOSE
    else:
        verbosity = Verbosity.NORMAL

    logging.basicConfig(
        level={
            Verbosity.QUIET: logging.ERROR,
            Verbosity.NORMAL: logging.WARNING,
            Verbosity.VERBOSE: logging.INFO,
            Verbosity.DEBUG: logging.DEBUG,
        }[verbosity],
        format="%(levelname)s: %(message)s",
    )

    cli_overrides: dict[str, str] = {}
    if quiet or verbose > 0:
        cli_overrides["output.verbosity"] = str(verbosity.value)

    deps.output_adapter = create_output_adapter(output_format, verbosity=verbosity)
    ctx.obj = {
        "deps": deps,
        "cli_overrides": cli_overrides,
        "verbosity": verbosity,
        "output_format": output_format,
        "config_path": config_path,
        "templates_dir": templates_dir,
        "runtime": runtime,
        "container_engine": container_engine,
    }


# Typer reads the function signatures, so each command is registered explicitly
# with its help text.
app.command(help="Generate a Theme and its projections from an image")(generate)
app.command(help="Show a Theme's roles and palettes without writing files")(show)
app.command(help="List engines, host availability, and container image presence")(list_engines)
app.command(help="Build the base image and one image per engine")(install)
app.command(help="Remove the base and per-engine images")(uninstall)
app.command(help="Show resolved settings, templates, engines, formats, and overrides")(info)
app.command(help="Print or write the resolved settings as TOML")(dump_config)
app.command(help="Copy the bundled projection templates to a local directory")(dump_templates)
app.command(help="Show the installed package version")(version)
