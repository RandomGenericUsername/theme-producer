from __future__ import annotations

import colorsys
import json
from dataclasses import replace
from pathlib import Path

import pytest

from theme_producer.domain.ansi import (
    ANSI_BRIGHT_LIGHTNESS,
    ANSI_COLOR_COUNT,
    ANSI_HUE_ANCHORS,
    ANSI_NORMAL_LIGHTNESS,
    ANSI_SATURATION_FALLBACK,
    ANSI_SATURATION_MAX,
    ANSI_SATURATION_MIN,
    ANSI_SLOT_ROLES,
    ansi_palette,
)
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"

#: (slot, low, high) hue windows. Red wraps through 0 degrees.
HUE_WINDOWS = (
    (1, 340.0, 30.0),
    (2, 120.0, 170.0),
    (3, 70.0, 110.0),
    (4, 240.0, 280.0),
    (5, 300.0, 340.0),
    (6, 180.0, 220.0),
)


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def hls(color: Color) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*(channel / 255.0 for channel in color.rgb))


def hue_degrees(color: Color) -> float:
    return hls(color)[0] * 360.0


def in_window(hue: float, low: float, high: float) -> bool:
    if low <= high:
        return low <= hue <= high
    return hue >= low or hue <= high


def mutate_role(theme: Theme, role_name: str, hex_value: str) -> Theme:
    role = MaterialRole(role_name)
    roles = dict(theme.dark.roles)
    roles[role] = Color.from_hex(hex_value)
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def low_chroma_theme() -> Theme:
    """The fixture's near-achromatic primary with distinct low-chroma anchors.

    The canonical fixture's surface/on-surface-variant/outline-variant roles all
    happen to be ``#000000``; distinct anchor tones keep the 16-slot assertion
    about the ANSI recipe rather than about that fixture coincidence.
    """
    theme = load_theme()
    roles = dict(theme.dark.roles)
    roles[MaterialRole.SURFACE] = Color.from_hex("#17130f")
    roles[MaterialRole.ON_SURFACE_VARIANT] = Color.from_hex("#6f675e")
    roles[MaterialRole.OUTLINE_VARIANT] = Color.from_hex("#857c72")
    roles[MaterialRole.ON_SURFACE] = Color.from_hex("#ece5dc")
    roles[MaterialRole.PRIMARY] = Color.from_hex("#2b2723")
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def test_recipe_metadata_is_pinned() -> None:
    assert dict(ANSI_SLOT_ROLES) == {
        0: MaterialRole.SURFACE,
        7: MaterialRole.ON_SURFACE_VARIANT,
        8: MaterialRole.OUTLINE_VARIANT,
        15: MaterialRole.ON_SURFACE,
    }
    # Slots 1..6 in standard ANSI order: red, green, yellow, blue, magenta, cyan.
    assert dict(ANSI_HUE_ANCHORS) == {
        1: 25.0,
        2: 145.0,
        3: 90.0,
        4: 260.0,
        5: 330.0,
        6: 200.0,
    }
    assert ANSI_NORMAL_LIGHTNESS[ModeName.DARK] == pytest.approx(0.55)
    assert ANSI_NORMAL_LIGHTNESS[ModeName.LIGHT] == pytest.approx(0.45)
    assert ANSI_BRIGHT_LIGHTNESS[ModeName.DARK] == pytest.approx(0.72)
    assert ANSI_BRIGHT_LIGHTNESS[ModeName.LIGHT] == pytest.approx(0.60)
    assert ANSI_SATURATION_MIN == pytest.approx(0.45)
    assert ANSI_SATURATION_MAX == pytest.approx(0.85)
    assert ANSI_SATURATION_FALLBACK == pytest.approx(0.60)


def test_palette_has_sixteen_colors_and_is_deterministic() -> None:
    theme = load_theme()

    first = ansi_palette(theme)
    second = ansi_palette(theme)

    assert len(first) == ANSI_COLOR_COUNT
    assert all(isinstance(color, Color) for color in first)
    assert first == second


def test_zero_seven_eight_fifteen_track_material_roles() -> None:
    theme = load_theme()
    palette = ansi_palette(theme)

    assert palette[0] == theme.dark.roles[MaterialRole.SURFACE]
    assert palette[7] == theme.dark.roles[MaterialRole.ON_SURFACE_VARIANT]
    assert palette[8] == theme.dark.roles[MaterialRole.OUTLINE_VARIANT]
    assert palette[15] == theme.dark.roles[MaterialRole.ON_SURFACE]


@pytest.mark.parametrize(("slot", "low", "high"), HUE_WINDOWS)
def test_chromatic_slots_fall_inside_their_hue_window(slot: int, low: float, high: float) -> None:
    palette = ansi_palette(load_theme())

    assert in_window(hue_degrees(palette[slot]), low, high)
    assert in_window(hue_degrees(palette[slot + 8]), low, high)


def test_bright_slots_are_brighter_than_normal_slots() -> None:
    palette = ansi_palette(load_theme())

    for slot in range(1, 7):
        normal = hls(palette[slot])
        bright = hls(palette[slot + 8])
        assert bright[1] > normal[1], slot
        # Same anchor: rounding permits a fraction of a degree of drift.
        delta = abs(bright[0] - normal[0]) * 360.0
        assert min(delta, 360.0 - delta) < 2.0, slot


def test_light_mode_uses_light_recipe_and_light_roles() -> None:
    theme = load_theme()
    palette = ansi_palette(theme, ModeName.LIGHT)

    assert palette[0] == theme.light.roles[MaterialRole.SURFACE]
    assert palette[15] == theme.light.roles[MaterialRole.ON_SURFACE]
    for slot in range(1, 7):
        normal_lightness = hls(palette[slot])[1]
        bright_lightness = hls(palette[slot + 8])[1]
        assert normal_lightness == pytest.approx(0.45, abs=0.01)
        assert bright_lightness == pytest.approx(0.60, abs=0.01)


def test_low_chroma_theme_still_yields_sixteen_distinct_colors() -> None:
    palette = ansi_palette(low_chroma_theme())

    assert len(set(palette)) == 16
    assert len(set(palette[1:7])) == 6
    assert len(set(palette[9:15])) == 6
    # Minimum saturation keeps the hue anchors separated even at low chroma.
    for slot in range(1, 7):
        assert hls(palette[slot])[2] >= ANSI_SATURATION_MIN - 0.01


def test_achromatic_primary_uses_saturation_fallback() -> None:
    theme = mutate_role(load_theme(), "primary", "#808080")
    palette = ansi_palette(theme)

    assert len(set(palette[1:7])) == 6
    for slot in range(1, 7):
        assert hls(palette[slot])[2] == pytest.approx(ANSI_SATURATION_FALLBACK, abs=0.01)


def test_primary_saturation_is_clamped_to_the_window() -> None:
    low = ansi_palette(mutate_role(load_theme(), "primary", "#26201a"))
    high = ansi_palette(mutate_role(load_theme(), "primary", "#ff0000"))

    for slot in range(1, 7):
        assert hls(low[slot])[2] == pytest.approx(ANSI_SATURATION_MIN, abs=0.01)
        assert hls(high[slot])[2] == pytest.approx(ANSI_SATURATION_MAX, abs=0.01)


def test_unrelated_role_mutation_does_not_change_ansi() -> None:
    theme = load_theme()
    mutated = mutate_role(theme, "inverse_primary", "#123456")

    assert ansi_palette(mutated) == ansi_palette(theme)


def test_primary_saturation_mutation_changes_ansi() -> None:
    theme = load_theme()
    desaturated = mutate_role(theme, "primary", "#2b2723")
    saturated = mutate_role(theme, "primary", "#ff0000")

    before = ansi_palette(desaturated)
    after = ansi_palette(saturated)

    assert before != after
    assert all(before[slot] != after[slot] for slot in range(1, 7))
