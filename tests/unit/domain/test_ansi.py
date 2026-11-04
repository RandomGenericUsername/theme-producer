from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from theme_producer.domain import ansi as ansi_module
from theme_producer.domain.ansi import ANSI_COLOR_COUNT, ANSI_SLOT_ROLES, ansi_palette
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme
from theme_producer.domain.services import LEGACY_COLOR_ORDER

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"

EXPECTED_SLOT_ROLES = {
    0: MaterialRole.SURFACE,
    1: MaterialRole.ERROR,
    2: MaterialRole.TERTIARY,
    3: MaterialRole.SECONDARY,
    4: MaterialRole.PRIMARY,
    5: MaterialRole.SURFACE_VARIANT,
    6: MaterialRole.OUTLINE_VARIANT,
    7: MaterialRole.ON_SURFACE,
    8: MaterialRole.OUTLINE,
    9: MaterialRole.ERROR_CONTAINER,
    10: MaterialRole.TERTIARY_CONTAINER,
    11: MaterialRole.SECONDARY_CONTAINER,
    12: MaterialRole.PRIMARY_CONTAINER,
    13: MaterialRole.SURFACE_CONTAINER,
    14: MaterialRole.SURFACE_CONTAINER_HIGH,
    15: MaterialRole.ON_SURFACE_VARIANT,
}

BRIGHT_CONTAINER_ROLES = {
    9: MaterialRole.ERROR_CONTAINER,
    10: MaterialRole.TERTIARY_CONTAINER,
    11: MaterialRole.SECONDARY_CONTAINER,
    12: MaterialRole.PRIMARY_CONTAINER,
    13: MaterialRole.SURFACE_CONTAINER,
    14: MaterialRole.SURFACE_CONTAINER_HIGH,
}

RETIRED_HUE_RECIPE_SYMBOLS = (
    "ANSI_BRIGHT_OFFSET",
    "ANSI_BRIGHT_LIGHTNESS",
    "ANSI_HUE_ANCHORS",
    "ANSI_HUE_FAMILY_BOUND",
    "ANSI_HUE_TINT_MAX",
    "ANSI_HUE_TINT_STEP",
    "ANSI_MIN_HUE_SEPARATION",
    "ANSI_NORMAL_LIGHTNESS",
    "ANSI_SATURATION_FALLBACK",
    "ANSI_SATURATION_MAX",
    "ANSI_SATURATION_MIN",
    "_hue_color",
    "_primary_hls",
    "_tinted_hue",
    "_tinted_hues",
)


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def mode_for(theme: Theme, mode_name: ModeName) -> Mode:
    return theme.dark if mode_name is ModeName.DARK else theme.light


def mutate_role(theme: Theme, role: MaterialRole, hex_value: str) -> Theme:
    roles = dict(theme.dark.roles)
    roles[role] = Color.from_hex(hex_value)
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def test_slot_role_table_covers_all_sixteen_slots_explicitly() -> None:
    assert ANSI_COLOR_COUNT == 16
    assert tuple(sorted(ANSI_SLOT_ROLES)) == tuple(range(ANSI_COLOR_COUNT))
    assert dict(ANSI_SLOT_ROLES) == EXPECTED_SLOT_ROLES


def test_slot_role_table_uses_the_canonical_legacy_order() -> None:
    assert tuple(ANSI_SLOT_ROLES[index] for index in range(16)) == LEGACY_COLOR_ORDER


@pytest.mark.parametrize("mode_name", [ModeName.DARK, ModeName.LIGHT])
def test_every_slot_is_its_material_role(mode_name: ModeName) -> None:
    theme = load_theme()
    mode = mode_for(theme, mode_name)
    palette = ansi_palette(theme, mode_name)

    assert len(palette) == ANSI_COLOR_COUNT
    for slot, role in EXPECTED_SLOT_ROLES.items():
        assert palette[slot] == mode.roles[role], slot
        assert palette[slot] in mode.roles.values(), slot


@pytest.mark.parametrize("slot", range(16))
def test_mutating_a_mapped_role_changes_its_slot(slot: int) -> None:
    theme = load_theme()
    role = EXPECTED_SLOT_ROLES[slot]
    mutated_color = Color.from_hex("#010203")
    before = ansi_palette(theme)
    after = ansi_palette(mutate_role(theme, role, mutated_color.hex))

    assert after[slot] == mutated_color
    assert after[slot] != before[slot]


def test_bright_slots_are_their_container_roles() -> None:
    theme = load_theme()
    palette = ansi_palette(theme)

    for slot, role in BRIGHT_CONTAINER_ROLES.items():
        assert palette[slot] == theme.dark.roles[role], slot
        assert EXPECTED_SLOT_ROLES[slot] == role


def test_dark_and_light_tables_select_their_own_mode() -> None:
    theme = load_theme()
    dark = ansi_palette(theme, ModeName.DARK)
    light = ansi_palette(theme, ModeName.LIGHT)

    assert dark == tuple(theme.dark.roles[role] for role in LEGACY_COLOR_ORDER)
    assert light == tuple(theme.light.roles[role] for role in LEGACY_COLOR_ORDER)
    assert dark != light


def test_a_dark_mutation_does_not_leak_into_the_light_table() -> None:
    theme = load_theme()
    before = ansi_palette(theme, ModeName.LIGHT)
    mutated = mutate_role(theme, MaterialRole.PRIMARY, "#010203")

    assert ansi_palette(mutated, ModeName.LIGHT) == before
    assert ansi_palette(mutated, ModeName.DARK) != ansi_palette(theme, ModeName.DARK)


def test_palette_is_deterministic() -> None:
    theme = load_theme()

    assert ansi_palette(theme) == ansi_palette(theme)


def test_no_generated_hue_recipe_remains() -> None:
    for symbol in RETIRED_HUE_RECIPE_SYMBOLS:
        assert not hasattr(ansi_module, symbol), symbol
    assert not hasattr(ansi_module, "colorsys")


def test_unrelated_role_mutation_does_not_change_ansi() -> None:
    theme = load_theme()
    mutated = mutate_role(theme, MaterialRole.INVERSE_PRIMARY, "#123456")

    assert ansi_palette(mutated) == ansi_palette(theme)
