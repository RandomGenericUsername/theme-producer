"""BUG-003: legacy token compatibility for AGS (GTK CSS) and rofi (rasi).

CSG remains the runtime reference until the dotfiles wiring ticket proves that
tpr can replace it, so both artifacts must stay drop-in compatible:

* AGS styles consume ``@color_foreground`` / ``@color_background``.
* rofi consumes zero-padded ``@color01``/``@color04``/``@color07``/``@color10``.

The aliases are additive: the vocabulary names, every Material role, and
``color_00..15`` stay unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Theme
from theme_producer.domain.services import LEGACY_COLOR_ORDER

TESTS_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = TESTS_ROOT / "fixtures" / "theme.json"

CSS_DEFINE = re.compile(r"^@define-color ([A-Za-z0-9_-]+) (#[0-9a-f]{6});$")
RASI_POSITIONAL = re.compile(r"^color\d{2}$")

SEMANTIC_NAMES = (
    "background",
    "foreground",
    "accent",
    "accent-muted",
    "surface",
    "on_surface",
    "error",
    "warning",
)

GTK_COMPAT_ALIASES = ("color_background", "color_foreground", "color_cursor")
GTK_POSITIONAL_ALIASES = tuple(f"color_{index:02d}" for index in range(16))
RASI_POSITIONAL_ALIASES = tuple(f"color{index:02d}" for index in range(16))


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def parse_defines(text: str) -> dict[str, str]:
    defines: dict[str, str] = {}
    for line in text.splitlines():
        match = CSS_DEFINE.fullmatch(line)
        if match:
            defines[match.group(1)] = match.group(2)
    return defines


def render_defines(projection: str, mode: ModeName, tmp_path: Path) -> dict[str, str]:
    theme = load_theme()
    output = ProjectionRegistry().render(
        projection, theme, tmp_path / mode.value, mode=mode
    )
    return parse_defines(output.read_text(encoding="utf-8"))


def roles_for(theme: Theme, mode: ModeName):
    return theme.dark.roles if mode is ModeName.DARK else theme.light.roles


@pytest.mark.parametrize("mode", [ModeName.DARK, ModeName.LIGHT], ids=["dark", "light"])
def test_gtk_has_exactly_the_csg_compatibility_alias_set(
    tmp_path: Path, mode: ModeName
) -> None:
    defines = render_defines("gtk", mode, tmp_path)
    roles = roles_for(load_theme(), mode)

    aliases = {name for name in defines if name.startswith("color_")}
    assert aliases == set(GTK_COMPAT_ALIASES) | set(GTK_POSITIONAL_ALIASES)

    assert defines["color_background"] == roles[MaterialRole.SURFACE].hex
    assert defines["color_foreground"] == roles[MaterialRole.ON_SURFACE].hex
    assert defines["color_cursor"] == roles[MaterialRole.ON_SURFACE].hex
    for index, role in enumerate(LEGACY_COLOR_ORDER):
        assert defines[f"color_{index:02d}"] == roles[role].hex


@pytest.mark.parametrize("mode", [ModeName.DARK, ModeName.LIGHT], ids=["dark", "light"])
def test_rasi_has_zero_padded_positional_and_semantic_aliases(
    tmp_path: Path, mode: ModeName
) -> None:
    defines = render_defines("rasi", mode, tmp_path)
    roles = roles_for(load_theme(), mode)

    positional = {name for name in defines if RASI_POSITIONAL.fullmatch(name)}
    assert positional == set(RASI_POSITIONAL_ALIASES)
    for index in range(10):
        assert f"color{index}" not in defines
    for index, role in enumerate(LEGACY_COLOR_ORDER):
        assert defines[f"color{index:02d}"] == roles[role].hex

    for name in SEMANTIC_NAMES:
        assert name in defines
    # rasi keeps its shape: only the positional aliases are zero-padded.
    assert "color_background" not in defines
    assert "color_foreground" not in defines
    assert "color_cursor" not in defines


def test_light_mode_carries_the_same_aliases_with_light_values(tmp_path: Path) -> None:
    theme = load_theme()
    registry = ProjectionRegistry()

    dark_gtk = parse_defines(
        registry.render("gtk", theme, tmp_path / "dark-gtk").read_text(encoding="utf-8")
    )
    light_gtk = parse_defines(
        registry.render(
            "gtk", theme, tmp_path / "light-gtk", mode=ModeName.LIGHT
        ).read_text(encoding="utf-8")
    )
    assert set(light_gtk) == set(dark_gtk)
    assert light_gtk["color_background"] == theme.light.roles[MaterialRole.SURFACE].hex
    assert light_gtk["color_foreground"] == theme.light.roles[MaterialRole.ON_SURFACE].hex
    assert light_gtk["color_cursor"] == theme.light.roles[MaterialRole.ON_SURFACE].hex
    assert light_gtk["color_background"] != dark_gtk["color_background"]

    dark_rasi = parse_defines(
        registry.render("rasi", theme, tmp_path / "dark-rasi").read_text(encoding="utf-8")
    )
    light_rasi = parse_defines(
        registry.render(
            "rasi", theme, tmp_path / "light-rasi", mode=ModeName.LIGHT
        ).read_text(encoding="utf-8")
    )
    assert set(light_rasi) == set(dark_rasi)
    assert light_rasi["color04"] == theme.light.roles[LEGACY_COLOR_ORDER[4]].hex
    assert light_rasi["color00"] != dark_rasi["color00"]
