from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

import theme_producer.adapters.projections.btop as btop_module
from theme_producer.adapters.projections.btop import (
    BTOP_GRADIENTS,
    BTOP_KEY_ROLES,
    BTOP_KEY_SPECS,
    BTOP_KEYS,
    MIN_GRAPH_CONTRAST,
    BtopComponent,
    BtopIntent,
    BtopRow,
    build_btop_rows,
)
from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.domain.color_metrics import contrast_ratio, relative_luminance
from theme_producer.domain.enums import TONES, MaterialRole, ModeName, PaletteName
from theme_producer.domain.models import Color, Mode, Theme, TonalPalette

TESTS_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = TESTS_ROOT / "fixtures" / "theme.json"
LIGHT_GOLDEN = TESTS_ROOT / "fixtures" / "projections-light" / "colors.btop.theme"

# Independent copy of the documented btop key set: the guard must not pass just
# because the implementation's own tuple and mapping agree with each other.
DOCUMENTED_BTOP_KEYS = (
    "main_bg",
    "main_fg",
    "title",
    "hi_fg",
    "selected_bg",
    "selected_fg",
    "inactive_fg",
    "graph_text",
    "meter_bg",
    "proc_misc",
    "cpu_box",
    "mem_box",
    "net_box",
    "proc_box",
    "div_line",
    "proc_pause_bg",
    "proc_follow_bg",
    "proc_banner_bg",
    "proc_banner_fg",
    "followed_bg",
    "followed_fg",
    "temp_start",
    "temp_mid",
    "temp_end",
    "cpu_start",
    "cpu_mid",
    "cpu_end",
    "free_start",
    "free_mid",
    "free_end",
    "cached_start",
    "cached_mid",
    "cached_end",
    "available_start",
    "available_mid",
    "available_end",
    "used_start",
    "used_mid",
    "used_end",
    "download_start",
    "download_mid",
    "download_end",
    "upload_start",
    "upload_mid",
    "upload_end",
    "process_start",
    "process_mid",
    "process_end",
)

# Independent copy of the approved semantic component table.
EXPECTED_COMPONENT_KEYS = {
    BtopComponent.GLOBAL_CHROME: {
        "main_bg",
        "main_fg",
        "title",
        "hi_fg",
        "selected_bg",
        "selected_fg",
        "inactive_fg",
        "graph_text",
        "div_line",
    },
    BtopComponent.NETWORK_CHROME: {"net_box", "meter_bg"},
    BtopComponent.CPU_CHROME: {"cpu_box"},
    BtopComponent.MEMORY_CHROME: {"mem_box"},
    BtopComponent.PROCESS_CHROME: {"proc_box"},
    BtopComponent.NETWORK_DOWNLOAD: {"download_start", "download_mid", "download_end"},
    BtopComponent.NETWORK_UPLOAD: {"upload_start", "upload_mid", "upload_end"},
    BtopComponent.CPU_LOAD: {"cpu_start", "cpu_mid", "cpu_end"},
    BtopComponent.CPU_THERMAL_PRESSURE: {"temp_start", "temp_mid", "temp_end"},
    BtopComponent.MEMORY_USED: {"used_start", "used_mid", "used_end"},
    BtopComponent.MEMORY_CACHED: {"cached_start", "cached_mid", "cached_end"},
    BtopComponent.MEMORY_CAPACITY: {
        "free_start",
        "free_mid",
        "free_end",
        "available_start",
        "available_mid",
        "available_end",
    },
    BtopComponent.PROCESS_STATE: {
        "proc_misc",
        "proc_pause_bg",
        "proc_follow_bg",
        "proc_banner_bg",
        "proc_banner_fg",
        "followed_bg",
        "followed_fg",
        "process_start",
        "process_mid",
        "process_end",
    },
}

BTOP_LINE = re.compile(r'^theme\[([a-z0-9_]+)\]="(#[0-9a-f]{6})"$')


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def rows_by_key(mode: Mode) -> dict[str, BtopRow]:
    return {row.key: row for row in build_btop_rows(mode)}


def ratio(first: Color, second: Color) -> float:
    return contrast_ratio(relative_luminance(first), relative_luminance(second))


def test_documented_key_set_is_exactly_48_unique_keys() -> None:
    assert len(DOCUMENTED_BTOP_KEYS) == 48
    assert len(set(DOCUMENTED_BTOP_KEYS)) == 48
    assert BTOP_KEYS == DOCUMENTED_BTOP_KEYS


def test_semantic_contract_covers_exactly_the_documented_keys() -> None:
    assert set(BTOP_KEY_SPECS) == set(DOCUMENTED_BTOP_KEYS)
    assert len(BTOP_KEY_SPECS) == 48
    assert set(BTOP_KEY_ROLES) == set(DOCUMENTED_BTOP_KEYS)
    for spec in BTOP_KEY_SPECS.values():
        assert isinstance(spec.component, BtopComponent)
        assert isinstance(spec.intent, BtopIntent)
        assert isinstance(spec.family, PaletteName)
        if spec.is_gradient:
            assert spec.role is None
        else:
            assert spec.role is not None


def test_component_table_matches_the_approved_semantics() -> None:
    actual: dict[BtopComponent, set[str]] = {component: set() for component in BtopComponent}
    for key, spec in BTOP_KEY_SPECS.items():
        actual[spec.component].add(key)

    assert actual == EXPECTED_COMPONENT_KEYS
    assert set().union(*EXPECTED_COMPONENT_KEYS.values()) == set(DOCUMENTED_BTOP_KEYS)


def test_semantic_families_are_pinned() -> None:
    assert BTOP_KEY_SPECS["download_end"].family is PaletteName.PRIMARY
    assert BTOP_KEY_SPECS["upload_end"].family is PaletteName.TERTIARY
    assert BTOP_KEY_SPECS["cpu_end"].family is PaletteName.PRIMARY
    assert BTOP_KEY_SPECS["temp_start"].family is PaletteName.TERTIARY
    assert BTOP_KEY_SPECS["temp_mid"].family is PaletteName.TERTIARY
    assert BTOP_KEY_SPECS["temp_end"].family is PaletteName.ERROR
    assert BTOP_KEY_SPECS["used_start"].family is PaletteName.SECONDARY
    assert BTOP_KEY_SPECS["used_mid"].family is PaletteName.TERTIARY
    assert BTOP_KEY_SPECS["used_end"].family is PaletteName.TERTIARY
    assert BTOP_KEY_SPECS["free_end"].family is PaletteName.NEUTRAL_VARIANT
    assert BTOP_KEY_SPECS["available_end"].family is PaletteName.NEUTRAL_VARIANT
    assert BTOP_KEY_SPECS["process_start"].family is PaletteName.PRIMARY
    assert BTOP_KEY_SPECS["process_mid"].family is PaletteName.SECONDARY
    assert BTOP_KEY_SPECS["process_end"].family is PaletteName.TERTIARY


def test_required_fixed_role_mappings_are_pinned() -> None:
    assert BTOP_KEY_ROLES["main_bg"] is MaterialRole.SURFACE
    assert BTOP_KEY_ROLES["main_fg"] is MaterialRole.ON_SURFACE
    assert BTOP_KEY_ROLES["title"] is MaterialRole.PRIMARY
    assert BTOP_KEY_ROLES["hi_fg"] is MaterialRole.PRIMARY
    assert BTOP_KEY_ROLES["selected_bg"] is MaterialRole.PRIMARY_CONTAINER
    assert BTOP_KEY_ROLES["inactive_fg"] is MaterialRole.OUTLINE
    assert BTOP_KEY_ROLES["meter_bg"] is MaterialRole.SURFACE_CONTAINER_HIGH


def test_rows_resolve_fixed_roles_and_family_tonal_variants() -> None:
    theme = load_theme()
    for mode in (theme.dark, theme.light):
        rows = build_btop_rows(mode)

        assert len(rows) == 48
        assert tuple(row.key for row in rows) == DOCUMENTED_BTOP_KEYS
        for row in rows:
            spec = BTOP_KEY_SPECS[row.key]
            assert row.component is spec.component
            assert row.intent is spec.intent
            assert row.family is spec.family
            if row.is_gradient:
                assert row.tone in TONES
                assert row.color == mode.palettes[row.family].tones[row.tone]
                assert row.background_key in BTOP_KEY_SPECS
                assert row.contrast == pytest.approx(
                    ratio(row.color, rows_by_key(mode)[row.background_key].color)
                )
            else:
                assert row.role is not None
                assert row.color == mode.roles[row.role]


@pytest.mark.parametrize("mode_name", [ModeName.DARK, ModeName.LIGHT])
def test_network_graphs_are_visible_against_meter_bg(mode_name: ModeName) -> None:
    """The regression: NET graphs must not disappear into the empty meter."""
    theme = load_theme()
    mode = theme.dark if mode_name is ModeName.DARK else theme.light
    rows = rows_by_key(mode)
    meter_bg = rows["meter_bg"].color

    assert rows["download_end"].color != meter_bg
    assert rows["upload_end"].color != meter_bg

    for key in (
        "download_start",
        "download_mid",
        "download_end",
        "upload_start",
        "upload_mid",
        "upload_end",
    ):
        row = rows[key]
        assert row.background_key == "meter_bg"
        assert ratio(row.color, meter_bg) >= MIN_GRAPH_CONTRAST, key


@pytest.mark.parametrize("mode_name", [ModeName.DARK, ModeName.LIGHT])
def test_every_gradient_stop_is_contrast_safe(mode_name: ModeName) -> None:
    theme = load_theme()
    mode = theme.dark if mode_name is ModeName.DARK else theme.light
    rows = rows_by_key(mode)

    for gradient in BTOP_GRADIENTS:
        background = rows[gradient.background_key].color
        for stop in gradient.stops:
            row = rows[stop.key]
            assert row.contrast is not None
            assert row.contrast >= MIN_GRAPH_CONTRAST, stop.key
            assert ratio(row.color, background) >= MIN_GRAPH_CONTRAST, stop.key


@pytest.mark.parametrize("mode_name", [ModeName.DARK, ModeName.LIGHT])
def test_gradient_guard_never_leaves_the_assigned_family(mode_name: ModeName) -> None:
    theme = load_theme()
    mode = theme.dark if mode_name is ModeName.DARK else theme.light
    rows = rows_by_key(mode)

    for gradient in BTOP_GRADIENTS:
        for stop in gradient.stops:
            row = rows[stop.key]
            family_colors = set(mode.palettes[stop.family].tones.values())
            assert row.color in family_colors, stop.key


def test_dark_and_light_keep_semantically_equivalent_mode_aware_gradients() -> None:
    theme = load_theme()
    dark_rows = rows_by_key(theme.dark)
    light_rows = rows_by_key(theme.light)

    for gradient in BTOP_GRADIENTS:
        assert len(gradient.stops) == 3
        for stop in gradient.stops:
            assert dark_rows[stop.key].family is stop.family
            assert light_rows[stop.key].family is stop.family
            assert dark_rows[stop.key].component is light_rows[stop.key].component
            assert dark_rows[stop.key].intent is light_rows[stop.key].intent

        if gradient.component is BtopComponent.PROCESS_STATE:
            # Material container anchors: dark tone 30, light tone 90. The guard
            # then adapts each mode to its actual main_bg.
            assert [stop.dark_tone for stop in gradient.stops] == [30, 30, 30]
            assert [stop.light_tone for stop in gradient.stops] == [90, 90, 90]
        else:
            dark_anchors = [stop.dark_tone for stop in gradient.stops]
            light_anchors = [stop.light_tone for stop in gradient.stops]
            assert dark_anchors == sorted(dark_anchors)
            assert light_anchors == sorted(light_anchors, reverse=True)

        # The end stop is the most prominent stop in its own mode, so the
        # semantic progression survives the different tonal trajectories.
        for rows in (dark_rows, light_rows):
            start = rows[gradient.stops[0].key].contrast
            end = rows[gradient.stops[-1].key].contrast
            assert start is not None and end is not None
            assert end >= start


def test_mutating_a_palette_tone_moves_the_gradient(tmp_path: Path) -> None:
    theme = load_theme()
    primary = theme.dark.palettes[PaletteName.PRIMARY]
    tones = dict(primary.tones)
    tones[100] = Color.from_hex("#ffffff")
    palettes = dict(theme.dark.palettes)
    palettes[PaletteName.PRIMARY] = TonalPalette(name=PaletteName.PRIMARY, tones=tones)
    mutated = replace(
        theme,
        dark=Mode(mode=ModeName.DARK, roles=theme.dark.roles, palettes=palettes),
    )

    before = rows_by_key(theme.dark)["download_end"]
    after = rows_by_key(mutated.dark)["download_end"]

    assert before.color.hex != "#ffffff"
    assert after.color == Color.from_hex("#ffffff")
    assert after.tone == 100


def test_guard_fails_closed_when_no_family_variant_passes() -> None:
    theme = load_theme()
    meter_bg = theme.dark.roles[MaterialRole.SURFACE_CONTAINER_HIGH]
    tones = {tone: meter_bg for tone in TONES}
    palettes = dict(theme.dark.palettes)
    palettes[PaletteName.PRIMARY] = TonalPalette(name=PaletteName.PRIMARY, tones=tones)
    mutated = replace(
        theme,
        dark=Mode(mode=ModeName.DARK, roles=theme.dark.roles, palettes=palettes),
    )

    with pytest.raises(RuntimeError, match="download_start: no primary tonal variant"):
        build_btop_rows(mutated.dark)


def test_render_emits_only_documented_keys(tmp_path: Path) -> None:
    output = ProjectionRegistry().render("btop", load_theme(), tmp_path)
    lines = [
        line
        for line in output.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]

    parsed = []
    for line in lines:
        match = BTOP_LINE.fullmatch(line)
        assert match is not None, f"unexpected btop line: {line!r}"
        parsed.append(match.group(1))

    assert tuple(parsed) == DOCUMENTED_BTOP_KEYS
    assert len(parsed) == 48
    assert set(parsed) == set(DOCUMENTED_BTOP_KEYS)
    assert len(set(parsed)) == len(parsed), "btop must not emit duplicate keys"


def test_light_render_matches_the_recorded_snapshot(tmp_path: Path) -> None:
    output = ProjectionRegistry().render("btop", load_theme(), tmp_path, mode=ModeName.LIGHT)

    assert LIGHT_GOLDEN.is_file(), f"missing light golden snapshot: {LIGHT_GOLDEN}"
    assert output.read_bytes() == LIGHT_GOLDEN.read_bytes()


def test_projection_source_has_no_hardcoded_hex_color() -> None:
    source = Path(btop_module.__file__).read_text(encoding="utf-8")

    assert re.search(r"#[0-9a-fA-F]{6}\b", source) is None
