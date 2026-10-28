"""``tpr dump-templates`` — materialize the packaged template catalog."""

from __future__ import annotations

import os
import shutil
from importlib.resources import files as resource_files
from pathlib import Path

import typer

from theme_producer.cli._helpers import fail, output_adapter
from theme_producer.domain.generation import OutputWriteError
from theme_producer.factory import CliDependencies

_BUNDLED_TEMPLATES = "templates"


def default_templates_target() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home) if config_home else Path.home() / ".config"
    return root / "theme-producer" / "templates"


def dump_templates(
    ctx: typer.Context,
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Target directory (default: XDG config templates)"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", "-w", help="Replace existing template files"
    ),
) -> None:
    deps: CliDependencies = ctx.obj["deps"]
    try:
        target = Path(output) if output is not None else default_templates_target()
        try:
            bundled = resource_files("theme_producer").joinpath("defaults", _BUNDLED_TEMPLATES)
            entries = sorted(entry for entry in bundled.iterdir() if entry.name.endswith(".j2"))
        except (ModuleNotFoundError, OSError, TypeError) as exc:
            raise OutputWriteError(f"cannot find bundled templates: {exc}") from exc

        target.mkdir(parents=True, exist_ok=True, mode=0o755)
        copied = 0
        skipped = 0
        for entry in entries:
            destination = target / entry.name
            if destination.exists() and not overwrite:
                skipped += 1
                continue
            try:
                shutil.copy2(str(entry), str(destination))
            except OSError as exc:
                raise OutputWriteError(
                    f"cannot write {destination}: {exc}", details={"path": str(destination)}
                ) from exc
            copied += 1

        output_adapter(deps).message(
            f"Copied {copied} template(s) to {target.resolve()} "
            f"({skipped} existing file(s) skipped)"
        )
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
