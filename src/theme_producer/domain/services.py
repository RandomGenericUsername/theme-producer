"""Pure alias vocabulary for Theme consumers.

The stable eight names are the semantic vocabulary used by consumers that can
carry named tokens. The legacy ``color0``..``color15`` names are positional
compatibility aliases only: the order below is deterministic, but it does not
define ANSI color intent. REQ-009 owns the deliberate ANSI projection.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from theme_producer.domain.enums import MaterialRole
from theme_producer.domain.exceptions import ThemeValidationError
from theme_producer.domain.models import Color, Mode

__all__ = [
    "ALIASES",
    "LEGACY_ALIASES",
    "LEGACY_COLOR_ORDER",
    "STABLE_ALIASES",
    "AliasService",
]

#: Stable semantic vocabulary shared by every projection that supports names.
STABLE_ALIASES: Mapping[str, MaterialRole] = MappingProxyType(
    {
        "background": MaterialRole.BACKGROUND,
        "foreground": MaterialRole.ON_SURFACE,
        "accent": MaterialRole.PRIMARY,
        "accent-muted": MaterialRole.SECONDARY,
        "surface": MaterialRole.SURFACE,
        "on_surface": MaterialRole.ON_SURFACE,
        "error": MaterialRole.ERROR,
        "warning": MaterialRole.TERTIARY,
    }
)

#: Positional order for the legacy ``color0``..``color15`` aliases.
#:
#: Positions are a stable reference order, not ANSI hue intent. ``color0``,
#: ``color7`` and ``color8`` deliberately point at surface/on-surface/outline
#: so the later ANSI projection can preserve those anchors.
LEGACY_COLOR_ORDER: tuple[MaterialRole, ...] = (
    MaterialRole.SURFACE,
    MaterialRole.ERROR,
    MaterialRole.TERTIARY,
    MaterialRole.SECONDARY,
    MaterialRole.PRIMARY,
    MaterialRole.SURFACE_VARIANT,
    MaterialRole.OUTLINE_VARIANT,
    MaterialRole.ON_SURFACE,
    MaterialRole.OUTLINE,
    MaterialRole.ERROR_CONTAINER,
    MaterialRole.TERTIARY_CONTAINER,
    MaterialRole.SECONDARY_CONTAINER,
    MaterialRole.PRIMARY_CONTAINER,
    MaterialRole.SURFACE_CONTAINER,
    MaterialRole.SURFACE_CONTAINER_HIGH,
    MaterialRole.ON_SURFACE_VARIANT,
)

LEGACY_ALIASES: Mapping[str, MaterialRole] = MappingProxyType(
    {f"color{index}": role for index, role in enumerate(LEGACY_COLOR_ORDER)}
)

ALIASES: Mapping[str, MaterialRole] = MappingProxyType({**STABLE_ALIASES, **LEGACY_ALIASES})


class AliasService:
    """Resolve stable and legacy alias names to Material roles."""

    def __init__(self, aliases: Mapping[str, MaterialRole] | None = None) -> None:
        self._aliases = MappingProxyType(dict(ALIASES if aliases is None else aliases))

    @property
    def aliases(self) -> Mapping[str, MaterialRole]:
        """The immutable alias-to-role table."""
        return self._aliases

    def resolve(self, alias: str) -> MaterialRole:
        """Return the Material role for ``alias`` or raise a validation error."""
        try:
            return self._aliases[alias]
        except KeyError:
            known = ", ".join(sorted(self._aliases))
            raise ThemeValidationError(
                f"unknown theme alias {alias!r}; known aliases: {known}"
            ) from None

    def resolve_role(self, alias: str) -> MaterialRole:
        """Alias of :meth:`resolve` for call sites that prefer the explicit name."""
        return self.resolve(alias)

    def resolve_alias(self, alias: str) -> MaterialRole:
        """Alias of :meth:`resolve` using the vocabulary's own name."""
        return self.resolve(alias)

    def resolve_color(self, mode: Mode, alias: str) -> Color:
        """Resolve an alias directly to the color in ``mode``."""
        return mode.roles[self.resolve(alias)]

    def __contains__(self, alias: object) -> bool:
        return alias in self._aliases
