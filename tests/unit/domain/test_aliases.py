from __future__ import annotations

import json
from pathlib import Path

import pytest

from theme_producer.domain import (
    LEGACY_COLOR_ORDER,
    AliasService,
    MaterialRole,
    Theme,
    ThemeValidationError,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"

STABLE = {
    "background": MaterialRole.BACKGROUND,
    "foreground": MaterialRole.ON_SURFACE,
    "accent": MaterialRole.PRIMARY,
    "accent-muted": MaterialRole.SECONDARY,
    "surface": MaterialRole.SURFACE,
    "on_surface": MaterialRole.ON_SURFACE,
    "error": MaterialRole.ERROR,
    "warning": MaterialRole.TERTIARY,
}


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text()))


def test_stable_eight_aliases_resolve() -> None:
    service = AliasService()

    for alias, role in STABLE.items():
        assert service.resolve(alias) is role
        assert service.resolve_role(alias) is role
        assert service.resolve_alias(alias) is role
        assert alias in service
        assert service.aliases[alias] is role


@pytest.mark.parametrize("index", range(16))
def test_legacy_color_aliases_resolve_in_documented_order(index: int) -> None:
    service = AliasService()
    alias = f"color{index}"

    assert service.resolve(alias) is LEGACY_COLOR_ORDER[index]
    assert service.aliases[alias] is LEGACY_COLOR_ORDER[index]


def test_legacy_order_is_sixteen_unique_roles_with_ansi_anchors() -> None:
    assert len(LEGACY_COLOR_ORDER) == 16
    assert len(set(LEGACY_COLOR_ORDER)) == 16
    assert LEGACY_COLOR_ORDER[0] is MaterialRole.SURFACE
    assert LEGACY_COLOR_ORDER[7] is MaterialRole.ON_SURFACE
    assert LEGACY_COLOR_ORDER[8] is MaterialRole.OUTLINE


def test_alias_table_is_exactly_stable_eight_plus_legacy_sixteen() -> None:
    aliases = AliasService().aliases

    assert len(aliases) == 24
    assert set(aliases) == set(STABLE) | {f"color{index}" for index in range(16)}


def test_resolve_color_returns_the_mode_color() -> None:
    theme = load_theme()
    service = AliasService()

    assert service.resolve_color(theme.dark, "accent") == theme.dark.roles[MaterialRole.PRIMARY]
    assert (
        service.resolve_color(theme.light, "foreground")
        == theme.light.roles[MaterialRole.ON_SURFACE]
    )
    assert service.resolve_color(theme.dark, "color0") == theme.dark.roles[MaterialRole.SURFACE]


def test_unknown_alias_raises_validation_error() -> None:
    with pytest.raises(ThemeValidationError, match="unknown theme alias 'nope'"):
        AliasService().resolve("nope")
