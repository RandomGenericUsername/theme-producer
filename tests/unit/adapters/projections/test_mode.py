"""Projection-mode selection (REQ-017).

Dark is the byte-compatible default; light renders the matching
``theme.json.modes.light`` roles/palettes into the same eight consumer files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from theme_producer.adapters.projections.registry import (
    RUNTIME_PROJECTIONS,
    ProjectionRegistry,
)
from theme_producer.adapters.theme_json import ThemeJsonWriter
from theme_producer.domain.ansi import ansi_palette
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Theme
from theme_producer.domain.services import LEGACY_COLOR_ORDER

TESTS_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = TESTS_ROOT / "fixtures" / "theme.json"
GOLDEN_DIR = TESTS_ROOT / "fixtures" / "projections"

CSS_DEFINE = re.compile(r"^@define-color ([A-Za-z0-9_-]+) (#[0-9a-f]{6});$")
KITTY_LINE = re.compile(r"^(?P<key>[a-z0-9_]+) (?P<hex>#[0-9a-f]{6})$")


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def parse_css(text: str) -> dict[str, str]:
    defines: dict[str, str] = {}
    for line in text.splitlines():
        match = CSS_DEFINE.fullmatch(line)
        if match:
            defines[match.group(1)] = match.group(2)
    return defines


def parse_yaml(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    colors: list[str] = []
    in_colors = False
    for line in text.splitlines():
        if line == "colors:":
            in_colors = True
            continue
        if not line or line.startswith("#"):
            continue
        if in_colors:
            colors.append(line.split('"')[1])
            continue
        key, _, value = line.partition(": ")
        values[key] = value.strip('"')
    return values, colors


def parse_kitty(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = KITTY_LINE.fullmatch(line)
        assert match is not None, f"invalid kitty line: {line!r}"
        values[match.group("key")] = match.group("hex")
    return values


@pytest.mark.parametrize(
    "projection",
    RUNTIME_PROJECTIONS,
    ids=[projection.name for projection in RUNTIME_PROJECTIONS],
)
def test_dark_default_matches_the_existing_consumer_golden(
    tmp_path: Path, projection
) -> None:
    output = ProjectionRegistry().render(projection, load_theme(), tmp_path)
    golden = GOLDEN_DIR / projection.filename

    assert output.read_bytes() == golden.read_bytes()


def test_theme_json_always_carries_both_modes(tmp_path: Path) -> None:
    theme = load_theme()
    output = ThemeJsonWriter().write(theme, tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert set(payload["modes"]) == {"dark", "light"}
    assert payload["modes"] == theme.to_dict()["modes"]


def test_light_projection_uses_light_roles_and_palettes(tmp_path: Path) -> None:
    theme = load_theme()
    light = theme.light
    rendered = {
        path.name: path.read_text(encoding="utf-8")
        for path in ProjectionRegistry().render_runtime(
            theme, tmp_path, mode=ModeName.LIGHT
        ).values()
    }

    yaml_values, yaml_colors = parse_yaml(rendered["colors.yaml"])
    assert yaml_values["background"] == light.roles[MaterialRole.SURFACE].hex
    assert yaml_values["surface"] == light.roles[MaterialRole.SURFACE].hex
    assert yaml_values["foreground"] == light.roles[MaterialRole.ON_SURFACE].hex
    assert yaml_values["cursor"] == light.roles[MaterialRole.ON_SURFACE].hex
    assert yaml_values["accent"] == light.roles[MaterialRole.PRIMARY].hex
    assert yaml_colors == [light.roles[role].hex for role in LEGACY_COLOR_ORDER]

    gtk = parse_css(rendered["colors.gtk.css"])
    for name, role in (
        ("background", MaterialRole.SURFACE),
        ("foreground", MaterialRole.ON_SURFACE),
        ("accent", MaterialRole.PRIMARY),
        ("error", MaterialRole.ERROR),
        ("warning", MaterialRole.TERTIARY),
    ):
        assert gtk[name] == light.roles[role].hex
    for index, role in enumerate(LEGACY_COLOR_ORDER):
        assert gtk[f"color_{index:02d}"] == light.roles[role].hex

    palette = ansi_palette(theme, ModeName.LIGHT)
    kitty = parse_kitty(rendered["colors.kitty"])
    assert kitty["background"] == light.roles[MaterialRole.SURFACE].hex
    assert kitty["foreground"] == light.roles[MaterialRole.ON_SURFACE].hex
    assert kitty["cursor"] == light.roles[MaterialRole.ON_SURFACE].hex
    assert kitty["selection_background"] == light.roles[MaterialRole.SURFACE].hex
    assert kitty["selection_foreground"] == light.roles[MaterialRole.ON_SURFACE].hex
    for index, color in enumerate(palette):
        assert kitty[f"color{index}"] == color.hex


def test_light_and_dark_projection_outputs_differ(tmp_path: Path) -> None:
    theme = load_theme()
    registry = ProjectionRegistry()

    dark = registry.render("gtk", theme, tmp_path / "dark")
    light = registry.render("gtk", theme, tmp_path / "light", mode="light")

    assert dark.read_bytes() != light.read_bytes()
