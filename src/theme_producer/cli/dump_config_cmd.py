"""``tpr dump-config`` — serialize resolved settings as TOML."""

from __future__ import annotations

from pathlib import Path

import typer

from theme_producer.adapters.settings_serializer import SettingsSerializer
from theme_producer.cli._helpers import fail, output_adapter, resolve_settings
from theme_producer.cli.options import CONFIG_OPT
from theme_producer.domain.generation import OutputWriteError
from theme_producer.factory import CliDependencies


def dump_config(
    ctx: typer.Context,
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write to this file (or directory/settings.toml)"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", "-w", help="Replace an existing settings file"
    ),
    config_path: Path | None = CONFIG_OPT,
) -> None:
    deps: CliDependencies = ctx.obj["deps"]
    try:
        settings = resolve_settings(deps, ctx, config_path=config_path)
        content = SettingsSerializer().to_toml(settings)

        if output is None:
            typer.echo(content, nl=False)
            return

        target = output if output.suffix == ".toml" else output / "settings.toml"
        if target.exists() and not overwrite:
            raise OutputWriteError(
                f"{target} already exists; pass --overwrite to replace it",
                details={"path": str(target)},
            )
        try:
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise OutputWriteError(
                f"cannot write {target}: {exc}", details={"path": str(target)}
            ) from exc
        output_adapter(deps).message(f"Configuration written to {target.resolve()}")
    except typer.Exit:
        raise
    except Exception as exc:
        fail(deps, exc)
