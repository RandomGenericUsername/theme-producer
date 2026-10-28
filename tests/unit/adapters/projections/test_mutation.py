from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "theme.json"

MUTATED_HEX = "#123456"


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def render_bytes(theme: Theme, output_dir: Path) -> dict[str, bytes]:
    paths = ProjectionRegistry().render_all(theme, output_dir)
    return {filename: path.read_bytes() for filename, path in paths.items()}


def mutate_dark_role(theme: Theme, role_name: str, hex_value: str) -> Theme:
    role = MaterialRole(role_name)
    roles = dict(theme.dark.roles)
    roles[role] = Color.from_hex(hex_value)
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def test_inverse_primary_mutation_only_changes_dependent_projections(tmp_path: Path) -> None:
    theme = load_theme()
    mutated = mutate_dark_role(theme, "inverse_primary", MUTATED_HEX)

    before = render_bytes(theme, tmp_path / "before")
    after = render_bytes(mutated, tmp_path / "after")

    changed = {name for name in before if before[name] != after[name]}
    unchanged = {name for name in before if before[name] == after[name]}

    # btop's 48-key table does not reference inverse_primary.
    assert unchanged == {"colors.btop.theme"}
    assert changed == set(before) - {"colors.btop.theme"}

    # Every dependent open projection carries the new role value.
    for filename in changed:
        needle = MUTATED_HEX[1:] if filename == "colors.conf" else MUTATED_HEX
        assert needle.encode() in after[filename], filename

    # The mutation really is the role we intended, and btop stayed identical.
    assert mutated.dark.roles[MaterialRole.INVERSE_PRIMARY].hex == MUTATED_HEX
    assert after["colors.btop.theme"] == before["colors.btop.theme"]


def test_mutating_a_btop_role_changes_btop_too(tmp_path: Path) -> None:
    theme = load_theme()
    mutated = mutate_dark_role(theme, "primary_container", MUTATED_HEX)

    before = render_bytes(theme, tmp_path / "before")
    after = render_bytes(mutated, tmp_path / "after")

    assert after["colors.btop.theme"] != before["colors.btop.theme"]
    assert MUTATED_HEX.encode() in after["colors.btop.theme"]
