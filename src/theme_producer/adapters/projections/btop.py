"""btop theme capability table.

The 48 keys below are the documented btop theme key set. The mapping is
contract data, not template logic: the Jinja template only iterates the rows
produced here, so an accidental unknown key cannot reach ``colors.btop.theme``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from theme_producer.domain.enums import MaterialRole
from theme_producer.domain.models import Color, Mode

__all__ = [
    "BTOP_KEY_ROLES",
    "BTOP_KEYS",
    "BtopRow",
    "build_btop_rows",
]

#: Documented btop theme keys, in emission order. Exactly 48 entries.
BTOP_KEYS: tuple[str, ...] = (
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

#: Explicit key -> Material role mapping for all 48 documented keys.
BTOP_KEY_ROLES: Mapping[str, MaterialRole] = MappingProxyType(
    {
        "main_bg": MaterialRole.SURFACE,
        "main_fg": MaterialRole.ON_SURFACE,
        "title": MaterialRole.PRIMARY,
        "hi_fg": MaterialRole.PRIMARY,
        "selected_bg": MaterialRole.PRIMARY_CONTAINER,
        "selected_fg": MaterialRole.ON_PRIMARY_CONTAINER,
        "inactive_fg": MaterialRole.OUTLINE,
        "graph_text": MaterialRole.ON_SURFACE_VARIANT,
        "meter_bg": MaterialRole.SURFACE_CONTAINER_HIGH,
        "proc_misc": MaterialRole.SECONDARY,
        "cpu_box": MaterialRole.OUTLINE_VARIANT,
        "mem_box": MaterialRole.OUTLINE_VARIANT,
        "net_box": MaterialRole.OUTLINE_VARIANT,
        "proc_box": MaterialRole.OUTLINE_VARIANT,
        "div_line": MaterialRole.OUTLINE_VARIANT,
        "proc_pause_bg": MaterialRole.SECONDARY_CONTAINER,
        "proc_follow_bg": MaterialRole.PRIMARY_CONTAINER,
        "proc_banner_bg": MaterialRole.TERTIARY_CONTAINER,
        "proc_banner_fg": MaterialRole.ON_TERTIARY_CONTAINER,
        "followed_bg": MaterialRole.PRIMARY_CONTAINER,
        "followed_fg": MaterialRole.ON_PRIMARY_CONTAINER,
        "temp_start": MaterialRole.TERTIARY,
        "temp_mid": MaterialRole.SECONDARY,
        "temp_end": MaterialRole.ERROR,
        "cpu_start": MaterialRole.PRIMARY,
        "cpu_mid": MaterialRole.SECONDARY,
        "cpu_end": MaterialRole.TERTIARY,
        "free_start": MaterialRole.SURFACE_CONTAINER_LOW,
        "free_mid": MaterialRole.SURFACE_CONTAINER,
        "free_end": MaterialRole.SURFACE_CONTAINER_HIGH,
        "cached_start": MaterialRole.TERTIARY,
        "cached_mid": MaterialRole.SECONDARY,
        "cached_end": MaterialRole.ERROR,
        "available_start": MaterialRole.SURFACE_CONTAINER_LOW,
        "available_mid": MaterialRole.SURFACE_CONTAINER,
        "available_end": MaterialRole.SURFACE_CONTAINER_HIGH,
        "used_start": MaterialRole.PRIMARY_CONTAINER,
        "used_mid": MaterialRole.SECONDARY_CONTAINER,
        "used_end": MaterialRole.TERTIARY_CONTAINER,
        "download_start": MaterialRole.SURFACE_CONTAINER_LOW,
        "download_mid": MaterialRole.SURFACE_CONTAINER,
        "download_end": MaterialRole.SURFACE_CONTAINER_HIGH,
        "upload_start": MaterialRole.SURFACE_CONTAINER_LOW,
        "upload_mid": MaterialRole.SURFACE_CONTAINER,
        "upload_end": MaterialRole.SURFACE_CONTAINER_HIGH,
        "process_start": MaterialRole.PRIMARY_CONTAINER,
        "process_mid": MaterialRole.SECONDARY_CONTAINER,
        "process_end": MaterialRole.TERTIARY_CONTAINER,
    }
)

if set(BTOP_KEY_ROLES) != set(BTOP_KEYS):  # pragma: no cover - import-time guard
    raise RuntimeError(
        "btop capability table drifted from the documented key set: "
        f"missing={sorted(set(BTOP_KEYS) - set(BTOP_KEY_ROLES))}, "
        f"unknown={sorted(set(BTOP_KEY_ROLES) - set(BTOP_KEYS))}"
    )


@dataclass(frozen=True, slots=True)
class BtopRow:
    """One emitted btop key and its resolved color."""

    key: str
    role: MaterialRole
    color: Color


def build_btop_rows(mode: Mode) -> tuple[BtopRow, ...]:
    """Resolve the capability table against one mode, in documented order."""
    return tuple(
        BtopRow(key=key, role=BTOP_KEY_ROLES[key], color=mode.roles[BTOP_KEY_ROLES[key]])
        for key in BTOP_KEYS
    )
