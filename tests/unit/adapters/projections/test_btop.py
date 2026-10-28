from __future__ import annotations

import json
import re
from pathlib import Path

from theme_producer.adapters.projections.btop import (
    BTOP_KEY_ROLES,
    BTOP_KEYS,
    build_btop_rows,
)
from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.domain.enums import MaterialRole
from theme_producer.domain.models import Theme

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "theme.json"

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

BTOP_LINE = re.compile(r'^theme\[([a-z0-9_]+)\]="(#[0-9a-f]{6})"$')


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_documented_key_set_is_exactly_48_unique_keys() -> None:
    assert len(DOCUMENTED_BTOP_KEYS) == 48
    assert len(set(DOCUMENTED_BTOP_KEYS)) == 48
    assert BTOP_KEYS == DOCUMENTED_BTOP_KEYS


def test_capability_table_covers_exactly_the_documented_keys() -> None:
    assert set(BTOP_KEY_ROLES) == set(DOCUMENTED_BTOP_KEYS)
    assert len(BTOP_KEY_ROLES) == 48


def test_required_key_mappings_are_pinned() -> None:
    assert BTOP_KEY_ROLES["main_bg"] is MaterialRole.SURFACE
    assert BTOP_KEY_ROLES["main_fg"] is MaterialRole.ON_SURFACE
    assert BTOP_KEY_ROLES["title"] is MaterialRole.PRIMARY
    assert BTOP_KEY_ROLES["hi_fg"] is MaterialRole.PRIMARY
    assert BTOP_KEY_ROLES["selected_bg"] is MaterialRole.PRIMARY_CONTAINER
    assert BTOP_KEY_ROLES["inactive_fg"] is MaterialRole.OUTLINE


def test_rows_resolve_every_key_to_the_mapped_role_color() -> None:
    theme = load_theme()
    rows = build_btop_rows(theme.dark)

    assert len(rows) == 48
    assert tuple(row.key for row in rows) == DOCUMENTED_BTOP_KEYS
    for row in rows:
        assert row.color == theme.dark.roles[row.role]
        assert row.color.hex.startswith("#")


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
