"""cli-output presentation adapters for the theme producer.

Every adapter renders the same projected object; only the presentation differs.
JSON is the machine contract and is also the default format. The projectors in
this module are pure functions over domain/result objects.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Mapping
from typing import Any

from cli_output.adapters.factory import create_renderer
from cli_output.domain.enums import OutputFormat
from cli_output.domain.views import CustomView, ErrorView, MessageView
from rich.console import Console
from rich.table import Table
from rich.text import Text

from theme_producer.domain.enums import ModeName
from theme_producer.domain.generation import GenerationResult
from theme_producer.domain.models import Theme
from theme_producer.domain.settings import Verbosity

__all__ = [
    "JsonOutput",
    "OutputAdapterBase",
    "PlainOutput",
    "RichOutput",
    "project_config_info",
    "project_engines",
    "project_error",
    "project_install_like",
    "project_result",
    "project_theme",
]


def _role_rows(theme: Theme) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for role, color in theme.dark.roles.items():
        rows.append((role.value, color.hex, theme.light.roles[role].hex))
    return rows


def _palette_rows(theme: Theme) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for name, palette in theme.dark.palettes.items():
        rows.append(
            (
                name.value,
                " ".join(f"{tone}:{palette.tones[tone].hex}" for tone in sorted(palette.tones)),
            )
        )
    return rows


def _theme_rich(theme: Theme) -> Callable[[Console], None]:
    def render(console: Console) -> None:
        console.print()
        console.print(Text("Theme", style="bold"))
        console.print(
            f"scheme: {theme.scheme}  contrast: {theme.contrast}  "
            f"engine: {theme.generator.engine} {theme.generator.engine_version}"
        )
        console.print()
        role_table = Table(title="Roles (dark / light)", box=None)
        role_table.add_column("Role", style="cyan")
        role_table.add_column("Dark")
        role_table.add_column("Light")
        for role, dark, light in _role_rows(theme):
            role_table.add_row(role, dark, light)
        console.print(role_table)
        console.print()
        palette_table = Table(title="Tonal palettes", box=None)
        palette_table.add_column("Palette", style="cyan")
        palette_table.add_column("Tones")
        for name, tones in _palette_rows(theme):
            palette_table.add_row(name, tones)
        console.print(palette_table)
        console.print()

    return render


def _theme_plain(theme: Theme) -> list[str]:
    lines = [
        f"scheme: {theme.scheme}",
        f"contrast: {theme.contrast}",
        f"engine: {theme.generator.engine} {theme.generator.engine_version}",
        "roles:",
    ]
    for role, dark, light in _role_rows(theme):
        lines.append(f"  {role}: dark={dark} light={light}")
    lines.append("palettes:")
    for name, tones in _palette_rows(theme):
        lines.append(f"  {name}: {tones}")
    return lines


def project_result(result: GenerationResult) -> CustomView:
    """Project a generation result into JSON object + human views."""
    obj = result.to_dict()
    lines = [
        "Success" if result.success else "Failure",
        f"Command: {result.command}",
        f"Engine: {result.engine}",
        f"Mode: {result.mode.value}",
        f"Duration: {result.duration:.2f}s",
    ]
    if result.scheme is not None:
        lines.append(f"Scheme: {result.scheme.variant.value}")
        if result.scheme.smart:
            lines.append(f"Scheme profile: {result.scheme.profile}")
            if result.scheme.metrics is not None:
                metrics = result.scheme.metrics
                lines.append(
                    "Metrics: "
                    f"saturation={metrics.saturation:.3f} "
                    f"colorfulness={metrics.colorfulness:.3f} "
                    f"lightness={metrics.lightness:.3f} "
                    f"contrast={metrics.contrast:.3f} "
                    f"hue_diversity={metrics.hue_diversity:.3f}"
                )
    if result.plan is not None:
        lines.append(f"Plan: {result.plan}")
        lines.append(
            "Projections: " + (", ".join(result.projections) if result.projections else "none")
        )
    if result.theme is not None:
        lines.extend(_theme_plain(result.theme))
    if result.output_files:
        lines.append("Output files:")
        lines.extend(f"  {path}" for path in result.output_files)

    def rich(console: Console) -> None:
        console.print()
        console.print(
            Text(
                "Success" if result.success else "Failure",
                style="bold green" if result.success else "bold red",
            )
        )
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        table.add_row("Command", result.command)
        table.add_row("Engine", result.engine)
        table.add_row("Mode", result.mode.value)
        table.add_row("Duration", f"{result.duration:.2f}s")
        if result.scheme is not None:
            table.add_row("Scheme", result.scheme.variant.value)
            if result.scheme.smart:
                table.add_row("Scheme profile", str(result.scheme.profile))
                if result.scheme.metrics is not None:
                    metrics = result.scheme.metrics
                    table.add_row(
                        "Metrics",
                        f"saturation={metrics.saturation:.3f} "
                        f"colorfulness={metrics.colorfulness:.3f} "
                        f"lightness={metrics.lightness:.3f} "
                        f"contrast={metrics.contrast:.3f} "
                        f"hue_diversity={metrics.hue_diversity:.3f}",
                    )
        console.print(table)
        if result.plan is not None:
            console.print()
            console.print(Text("Plan", style="bold"))
            console.print(result.plan)
            console.print(
                "Projections: " + (", ".join(result.projections) if result.projections else "none")
            )
        if result.theme is not None:
            _theme_rich(result.theme)(console)
        if result.output_files:
            console.print(Text("Output files:", style="bold"))
            for path in result.output_files:
                console.print(f"  {path}")
        console.print()

    return CustomView(plain="\n".join(lines), object=obj, rich=rich)


def project_theme(
    theme: Theme,
    *,
    engine: str,
    mode: ModeName | str = ModeName.DARK,
) -> CustomView:
    """Project a display-only Theme (the ``show`` verb)."""
    result = GenerationResult(command="show", engine=engine, theme=theme, mode=mode)
    return project_result(result)


def _error_details(exc: BaseException) -> dict[str, str]:
    details: dict[str, str] = {}
    for attribute in ("key", "field_path", "reason", "path", "image", "engine"):
        value = getattr(exc, attribute, None)
        if value is not None:
            details[attribute] = str(value)
    extra_details = getattr(exc, "details", None)
    if isinstance(extra_details, Mapping):
        for key, value in extra_details.items():
            details[str(key)] = str(value)
    return details


def project_error(exc: BaseException) -> dict[str, Any]:
    """The stable JSON error contract."""
    error: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
    }
    details = _error_details(exc)
    if details:
        error["details"] = details
    return {"success": False, "error": error}


def project_config_info(payload: Mapping[str, Any]) -> CustomView:
    obj: dict[str, Any] = {"success": True, "command": "info", **dict(payload)}
    lines = [
        f"settings: {payload.get('settings_path')}",
        f"templates: {payload.get('templates_path')}",
        f"scheme_type: {payload.get('scheme_type')}",
        "scheme_policy: "
        f"{(payload.get('scheme_policy') or {}).get('profile')} "
        f"(loaded={(payload.get('scheme_policy') or {}).get('loaded')}, "
        f"path={(payload.get('scheme_policy') or {}).get('catalog_path')})",
        "engines:",
    ]
    for engine in payload.get("engines", []):
        available = "available" if engine.get("available") else "unavailable"
        lines.append(f"  {engine.get('name')}: {available}")
    lines.append("formats: " + ", ".join(payload.get("formats", [])))
    overrides = payload.get("applied_overrides", [])
    lines.append("overrides:")
    if overrides:
        for override in overrides:
            lines.append(f"  {override.get('field_path')}={override.get('raw_value')}")
    else:
        lines.append("  none")

    def rich(console: Console) -> None:
        console.print()
        console.print(Text("Configuration", style="bold"))
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        table.add_row("settings", str(payload.get("settings_path")))
        table.add_row("templates", str(payload.get("templates_path")))
        table.add_row("scheme_type", str(payload.get("scheme_type")))
        table.add_row("scheme_policy", str((payload.get("scheme_policy") or {}).get("profile")))
        table.add_row("formats", ", ".join(payload.get("formats", [])))
        console.print(table)
        engine_table = Table(title="Engines", box=None)
        engine_table.add_column("Engine", style="cyan")
        engine_table.add_column("Available")
        for engine in payload.get("engines", []):
            engine_table.add_row(
                str(engine.get("name")), "yes" if engine.get("available") else "no"
            )
        console.print(engine_table)
        if overrides:
            console.print(Text("Applied overrides", style="bold"))
            for override in overrides:
                console.print(
                    f"  {override.get('field_path')}={override.get('raw_value')} "
                    f"({override.get('source')})"
                )
        console.print()

    return CustomView(plain="\n".join(lines), object=obj, rich=rich)


def project_engines(
    engines: list[dict[str, Any]],
    *,
    runtime: str,
    container_engine: str | None,
) -> CustomView:
    obj = {
        "success": True,
        "command": "list-engines",
        "runtime": runtime,
        "container_engine": container_engine,
        "engines": engines,
    }
    lines: list[str] = []
    for engine in engines:
        lines.append(f"{engine['name']} - {engine.get('description', '')}")
        lines.append(f"  Available: {'yes' if engine.get('available') else 'no'}")
        if engine.get("image") is not None:
            lines.append(
                f"  Image: {engine['image']} "
                f"({'present' if engine.get('image_available') else 'missing'})"
            )
        parameters = engine.get("parameters") or []
        if parameters:
            lines.append("  Parameters:")
            for parameter in parameters:
                choices = (
                    f", choices: {', '.join(parameter['choices'])}"
                    if parameter.get("choices")
                    else ""
                )
                lines.append(
                    f"    {parameter['name']} ({parameter.get('type')}, "
                    f"default: {parameter.get('default')}{choices})"
                )

    def rich(console: Console) -> None:
        console.print()
        table = Table(title="Engines", box=None)
        table.add_column("Engine", style="cyan")
        table.add_column("Description")
        table.add_column("Available")
        table.add_column("Image")
        for engine in engines:
            image = engine.get("image")
            if image is None:
                image_state = "-"
            else:
                image_state = "present" if engine.get("image_available") else "missing"
            table.add_row(
                str(engine.get("name")),
                str(engine.get("description", "")),
                "yes" if engine.get("available") else "no",
                image_state,
            )
        console.print(table)
        console.print()

    return CustomView(plain="\n".join(lines), object=obj, rich=rich)


def project_install_like(title: str, results: list[dict[str, Any]]) -> CustomView:
    obj = {"success": True, "command": title, "results": results}
    lines = [
        f"{item.get('engine')}: {item.get('image')} [{item.get('status')}]" for item in results
    ]

    def rich(console: Console) -> None:
        table = Table(title=f"{title.title()} results", box=None)
        table.add_column("Engine", style="cyan")
        table.add_column("Image")
        table.add_column("Status")
        for item in results:
            table.add_row(str(item.get("engine")), str(item.get("image")), str(item.get("status")))
        console.print()
        console.print(table)
        console.print()

    return CustomView(plain="\n".join(lines), object=obj, rich=rich)


class OutputAdapterBase:
    """Shared renderer plumbing for the three output formats."""

    _default_format: OutputFormat

    def __init__(
        self,
        verbosity: Verbosity = Verbosity.NORMAL,
        renderer: Any | None = None,
    ) -> None:
        self._verbosity = verbosity
        self._renderer = renderer or create_renderer(self._default_format)

    @property
    def output_format(self) -> OutputFormat:
        """The format this adapter renders."""
        return self._default_format

    def process_result(self, result: GenerationResult) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(project_result(result))

    def theme_display(self, theme: Theme, *, engine: str) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(project_theme(theme, engine=engine))

    def config_info(self, payload: Mapping[str, Any]) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(project_config_info(payload))

    def engines_catalog(
        self,
        engines: list[dict[str, Any]],
        *,
        runtime: str,
        container_engine: str | None,
    ) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(
            project_engines(engines, runtime=runtime, container_engine=container_engine)
        )

    def install_result(self, results: list[dict[str, Any]]) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(project_install_like("install", results))

    def uninstall_result(self, results: list[dict[str, Any]]) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(project_install_like("uninstall", results))

    def version_info(self, version: str) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.custom(
            CustomView(
                plain=f"theme-producer {version}",
                object={"version": version},
                rich=f"[bold]theme-producer[/bold] v{version}",
            )
        )

    def message(self, text: str) -> None:
        if self._verbosity is Verbosity.QUIET:
            return
        self._renderer.message(MessageView(text=text))

    def error(self, exc: BaseException) -> None:
        payload = project_error(exc)
        details = payload["error"].get("details", {})
        if self._default_format is OutputFormat.JSON:
            # The JSON contract is a stable object, not cli-output's ErrorView.
            json.dump(payload, sys.stderr, indent=2)
            sys.stderr.write("\n")
            return
        self._renderer.error(
            ErrorView(
                kind=str(payload["error"]["type"]),
                message=str(payload["error"]["message"]),
                details={str(k): str(v) for k, v in details.items()},
            )
        )


# Imported last so the base class exists before subclasses import it.
from theme_producer.adapters.output.json_output import JsonOutput  # noqa: E402
from theme_producer.adapters.output.plain_output import PlainOutput  # noqa: E402
from theme_producer.adapters.output.rich_output import RichOutput  # noqa: E402
