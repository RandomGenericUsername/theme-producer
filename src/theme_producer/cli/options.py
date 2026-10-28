"""Shared Typer option definitions.

Options are declared here once and reused on both the global callback and the
verbs, so ``tpr --config X generate`` and ``tpr generate --config X`` both work
(Click parses a global option before the verb and a command option after it).
"""

from __future__ import annotations

from pathlib import Path

import typer

from theme_producer.domain.settings import ContainerEngine, RuntimeMode

CONFIG_OPT: Path | None = typer.Option(
    None,
    "--config",
    help="Path to settings.toml",
    file_okay=True,
    dir_okay=False,
    readable=True,
    resolve_path=True,
)

TEMPLATES_DIR_OPT: Path | None = typer.Option(
    None,
    "--templates-dir",
    help="Directory containing the .j2 projection templates",
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
)

RUNTIME_OPT: RuntimeMode | None = typer.Option(
    None,
    "--runtime",
    "-r",
    help="Execution runtime: local or container",
    case_sensitive=False,
)

ENGINE_OPT: ContainerEngine | None = typer.Option(
    None,
    "--container-engine",
    help="Container engine: docker or podman",
    case_sensitive=False,
)

PROJECTION_MODE_OPT: str | None = typer.Option(
    None,
    "--mode",
    help=(
        "Output projection mode: dark, light, or smart (default: "
        "settings.output.default_mode, packaged dark). Selects the mode rendered into the "
        "consumer files; theme.json always carries both. Smart picks light when the source's "
        "mean relative luminance >= the smart threshold. Distinct from `--param mode=...`, "
        "which sets the engine's default mode."
    ),
    case_sensitive=False,
)

SMART_THRESHOLD_OPT: float | None = typer.Option(
    None,
    "--smart-threshold",
    help=(
        "Luminance threshold in [0, 1] for --mode smart (default: "
        "settings.output.smart_threshold, packaged 0.5)."
    ),
)
