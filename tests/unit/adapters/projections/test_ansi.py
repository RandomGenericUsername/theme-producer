from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from theme_producer.adapters.projections import ansi as ansi_projection
from theme_producer.adapters.projections.ansi import (
    ANSI_PROJECTIONS,
    KITTY_PROJECTION,
    SEQUENCES_PROJECTION,
)
from theme_producer.adapters.projections.registry import (
    CAPABILITY_TABLE,
    ProjectionRegistry,
)
from theme_producer.domain.ansi import ansi_palette
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme

TESTS_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = TESTS_ROOT / "fixtures" / "theme.json"
GOLDEN_DIR = TESTS_ROOT / "fixtures" / "projections"

KITTY_LINE = re.compile(r"^(?P<key>[a-z0-9_]+) (?P<hex>#[0-9a-f]{6})$")
SEQUENCE_COLOR_LINE = re.compile(rb"^\x1b\]4;(?P<index>\d+);(?P<hex>#[0-9a-f]{6})\x1b\\$")
SEQUENCE_SCALAR_LINE = re.compile(rb"^\x1b\](?P<code>10|11|12);(?P<hex>#[0-9a-f]{6})\x1b\\$")

KITTY_KEYS = (
    "background",
    "foreground",
    "cursor",
    *(f"color{index}" for index in range(16)),
    "selection_background",
    "selection_foreground",
)


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def render(
    theme: Theme, tmp_path: Path, mode: ModeName | str = ModeName.DARK
) -> tuple[Path, Path]:
    registry = ProjectionRegistry()
    kitty = registry.render(KITTY_PROJECTION, theme, tmp_path, mode=mode)
    sequences = registry.render(SEQUENCES_PROJECTION, theme, tmp_path, mode=mode)
    return kitty, sequences


def parse_kitty(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = KITTY_LINE.fullmatch(line)
        assert match is not None, f"invalid kitty line: {line!r}"
        key = match.group("key")
        assert key not in parsed, f"duplicate kitty key: {key}"
        parsed[key] = match.group("hex")
    return parsed


def parse_sequences(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    content = path.read_bytes()
    lines = content.splitlines()
    assert len(lines) == 19

    for index, line in enumerate(lines[:-3]):
        match = SEQUENCE_COLOR_LINE.fullmatch(line)
        assert match is not None, f"invalid sequence line: {line!r}"
        assert match.group("index").decode() == str(index)
        parsed[f"color{index}"] = match.group("hex").decode()

    for line, code in zip(lines[-3:], ("10", "11", "12"), strict=True):
        match = SEQUENCE_SCALAR_LINE.fullmatch(line)
        assert match is not None, f"invalid sequence line: {line!r}"
        assert match.group("code").decode() == code
        parsed[{"10": "foreground", "11": "background", "12": "cursor"}[code]] = match.group(
            "hex"
        ).decode()
    return parsed


def mutate_role(theme: Theme, role: MaterialRole, hex_value: str) -> Theme:
    roles = dict(theme.dark.roles)
    roles[role] = Color.from_hex(hex_value)
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def test_ansi_projections_are_registered_as_fixed() -> None:
    assert tuple((p.name, p.filename, p.capability) for p in ANSI_PROJECTIONS) == (
        ("kitty", "colors.kitty", "fixed"),
        ("sequences", "colors.sequences", "fixed"),
    )
    assert CAPABILITY_TABLE["kitty"] == "fixed"
    assert CAPABILITY_TABLE["sequences"] == "fixed"


def test_kitty_emits_only_valid_keys(tmp_path: Path) -> None:
    kitty, _sequences = render(load_theme(), tmp_path)
    parsed = parse_kitty(kitty)

    assert tuple(parsed) == KITTY_KEYS
    assert len(parsed) == 21


def test_kitty_and_sequences_share_one_table(tmp_path: Path) -> None:
    theme = load_theme()
    kitty, sequences = render(theme, tmp_path)

    kitty_colors = parse_kitty(kitty)
    sequence_colors = parse_sequences(sequences)
    expected = [color.hex for color in ansi_palette(theme)]

    for index in range(16):
        key = f"color{index}"
        assert kitty_colors[key] == expected[index]
        assert sequence_colors[key] == expected[index]

    assert kitty_colors["background"] == expected[0] == sequence_colors["background"]


@pytest.mark.parametrize("mode_name", [ModeName.DARK, ModeName.LIGHT])
def test_terminal_chrome_uses_semantic_roles(
    tmp_path: Path, mode_name: ModeName
) -> None:
    theme = load_theme()
    mode = theme.dark if mode_name is ModeName.DARK else theme.light
    kitty, sequences = render(theme, tmp_path, mode_name)

    kitty_colors = parse_kitty(kitty)
    sequence_colors = parse_sequences(sequences)
    roles = mode.roles

    chrome = {
        "background": MaterialRole.SURFACE,
        "foreground": MaterialRole.ON_SURFACE,
        "cursor": MaterialRole.ON_SURFACE,
        "selection_background": MaterialRole.SURFACE,
        "selection_foreground": MaterialRole.ON_SURFACE,
    }
    for key, role in chrome.items():
        assert kitty_colors[key] == roles[role].hex, key

    assert sequence_colors["background"] == roles[MaterialRole.SURFACE].hex
    assert sequence_colors["foreground"] == roles[MaterialRole.ON_SURFACE].hex
    assert sequence_colors["cursor"] == roles[MaterialRole.ON_SURFACE].hex


def test_chrome_ignores_slot_15_when_it_differs_from_on_surface(
    tmp_path: Path,
) -> None:
    theme = load_theme()
    roles = dict(theme.dark.roles)
    roles[MaterialRole.ON_SURFACE] = Color.from_hex("#f0dede")
    roles[MaterialRole.ON_SURFACE_VARIANT] = Color.from_hex("#d7c1c1")
    mutated = replace(
        theme,
        dark=Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes),
    )

    kitty, sequences = render(mutated, tmp_path)
    kitty_colors = parse_kitty(kitty)
    sequence_colors = parse_sequences(sequences)
    palette = ansi_palette(mutated)

    # Slot 15 is on_surface_variant and must not leak into chrome.
    assert kitty_colors["color15"] == sequence_colors["color15"] == palette[15].hex
    assert palette[15].hex == "#d7c1c1"

    assert kitty_colors["foreground"] == "#f0dede"
    assert kitty_colors["cursor"] == "#f0dede"
    assert kitty_colors["selection_foreground"] == "#f0dede"
    assert sequence_colors["foreground"] == "#f0dede"
    assert sequence_colors["cursor"] == "#f0dede"
    for key in ("foreground", "cursor", "selection_foreground"):
        assert kitty_colors[key] != palette[15].hex

    assert kitty_colors["background"] == kitty_colors["selection_background"]
    assert kitty_colors["background"] == palette[0].hex
    assert sequence_colors["background"] == palette[0].hex


def test_slot_index_chrome_constants_are_gone() -> None:
    for symbol in (
        "ANSI_BACKGROUND_INDEX",
        "ANSI_FOREGROUND_INDEX",
        "ANSI_CURSOR_INDEX",
        "ANSI_SELECTION_BACKGROUND_INDEX",
        "ANSI_SELECTION_FOREGROUND_INDEX",
    ):
        assert not hasattr(ansi_projection, symbol), symbol


def test_sequences_are_osc_bytes_with_esc_prefix_and_st_terminator(tmp_path: Path) -> None:
    _kitty, sequences = render(load_theme(), tmp_path)
    content = sequences.read_bytes()

    assert content.startswith(b"\x1b]4;0;")
    assert b"\x1b]4;15;" in content
    assert content.endswith(b"\x1b\\")
    assert content.count(b"\x1b]") == 19
    assert content.count(b"\x1b\\") == 19


def test_sequences_use_csg_binary_postprocess(tmp_path: Path) -> None:
    _kitty, sequences = render(load_theme(), tmp_path)
    content = sequences.read_bytes()

    # No template literal survives: every introducer/terminator is ESC/ST.
    assert content.count(b"]") == content.count(b"\x1b]")
    assert b"\\" not in content.replace(b"\x1b\\", b"")


@pytest.mark.parametrize(
    ("projection", "filename"),
    [(KITTY_PROJECTION, "colors.kitty"), (SEQUENCES_PROJECTION, "colors.sequences")],
    ids=["kitty", "sequences"],
)
def test_projection_matches_golden(tmp_path: Path, projection, filename: str) -> None:
    output = ProjectionRegistry().render(projection, load_theme(), tmp_path)
    golden = GOLDEN_DIR / filename

    assert golden.is_file(), f"missing golden snapshot: {golden}"
    assert output.read_bytes() == golden.read_bytes()


def test_registry_renders_ansi_projections_deterministically(tmp_path: Path) -> None:
    theme = load_theme()
    registry = ProjectionRegistry()

    first = registry.render("kitty", theme, tmp_path / "one")
    second = registry.render("kitty", theme, tmp_path / "two")
    first_sequences = registry.render("sequences", theme, tmp_path / "one")
    second_sequences = registry.render("sequences", theme, tmp_path / "two")

    assert first.read_bytes() == second.read_bytes()
    assert first_sequences.read_bytes() == second_sequences.read_bytes()


def test_unrelated_role_mutation_does_not_change_ansi_bytes(tmp_path: Path) -> None:
    theme = load_theme()
    roles = dict(theme.dark.roles)
    roles[MaterialRole.INVERSE_PRIMARY] = Color.from_hex("#123456")
    mutated = replace(
        theme,
        dark=Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes),
    )

    before_kitty, before_sequences = render(theme, tmp_path / "before")
    after_kitty, after_sequences = render(mutated, tmp_path / "after")

    assert after_kitty.read_bytes() == before_kitty.read_bytes()
    assert after_sequences.read_bytes() == before_sequences.read_bytes()


@pytest.mark.parametrize(
    "role",
    [
        MaterialRole.ERROR,
        MaterialRole.TERTIARY,
        MaterialRole.SECONDARY,
        MaterialRole.PRIMARY,
        MaterialRole.ERROR_CONTAINER,
        MaterialRole.PRIMARY_CONTAINER,
        MaterialRole.ON_SURFACE_VARIANT,
    ],
)
def test_role_mutation_changes_ansi_bytes(tmp_path: Path, role: MaterialRole) -> None:
    theme = load_theme()
    mutated = mutate_role(theme, role, "#010203")

    before_kitty, before_sequences = render(theme, tmp_path / "before")
    after_kitty, after_sequences = render(mutated, tmp_path / "after")

    assert after_kitty.read_bytes() != before_kitty.read_bytes()
    assert after_sequences.read_bytes() != before_sequences.read_bytes()
