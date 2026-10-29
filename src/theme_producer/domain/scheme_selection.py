"""Scheme-type selection: the ``tpr`` pseudo-value and its precedence.

The engine catalog only knows the nine concrete Material variants. ``tpr``
adds one pseudo-value — :data:`SMART_SCHEME_TYPE` — which asks the host-side
policy to pick a concrete variant from image metrics before the engine is
called. Keeping the vocabulary and the precedence here makes both CLI verbs,
settings validation, and the container hand-off agree on one rule:

1. an explicit ``--param scheme_type=...`` value,
2. ``[generation] scheme_type``,
3. the engine catalog's ``scheme_type`` default,
4. ``scheme-tonal-spot`` as the last resort.

Selecting ``scheme_policy`` alone never enables smart: only
``scheme_type=scheme-smart`` does. This module performs no I/O; measuring and
catalog loading are application concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from theme_producer.domain.engines import EngineDefinition
from theme_producer.domain.exceptions import InvalidSchemeTypeError
from theme_producer.domain.scheme_policy import ImageMetrics, SchemeVariant

__all__ = [
    "SMART_SCHEME_TYPE",
    "SchemeResolution",
    "engine_scheme_default",
    "is_smart_scheme_type",
    "normalize_scheme_type",
    "resolve_requested_scheme_type",
]

#: The tpr-level pseudo-variant that triggers policy resolution.
SMART_SCHEME_TYPE = "scheme-smart"

_VARIANTS = tuple(variant.value for variant in SchemeVariant)


def is_smart_scheme_type(value: object) -> bool:
    """Return whether ``value`` is the smart pseudo-value (case-sensitive)."""
    return isinstance(value, str) and value.strip() == SMART_SCHEME_TYPE


def normalize_scheme_type(value: object) -> str:
    """Return a concrete variant value or :data:`SMART_SCHEME_TYPE`.

    Anything else raises :class:`~theme_producer.domain.exceptions.InvalidSchemeTypeError`
    with the accepted vocabulary in the message.
    """
    if not isinstance(value, str) or not value.strip():
        raise InvalidSchemeTypeError(f"scheme_type must be a non-empty string; got {value!r}")
    candidate = value.strip()
    if candidate == SMART_SCHEME_TYPE:
        return SMART_SCHEME_TYPE
    try:
        return SchemeVariant(candidate).value
    except ValueError as exc:
        accepted = ", ".join((*_VARIANTS, SMART_SCHEME_TYPE))
        raise InvalidSchemeTypeError(
            f"unknown scheme_type {candidate!r}; must be one of: {accepted}"
        ) from exc


def engine_scheme_default(definition: EngineDefinition) -> str:
    """Return the catalog's ``scheme_type`` default, or tonal-spot if absent."""
    for parameter in definition.parameters:
        if parameter.name == "scheme_type":
            value = parameter.default
            if isinstance(value, str) and value.strip():
                return value.strip()
    return SchemeVariant.TONAL_SPOT.value


def resolve_requested_scheme_type(
    parameter_value: str | None,
    settings_value: str | None,
    engine_default: str | None,
) -> str:
    """Apply the documented precedence and return a validated request value."""
    for candidate in (parameter_value, settings_value, engine_default):
        if candidate is not None:
            return normalize_scheme_type(candidate)
    return SchemeVariant.TONAL_SPOT.value


@dataclass(frozen=True, slots=True)
class SchemeResolution:
    """The requested scheme type and, for smart, the concrete resolution."""

    requested: str
    variant: SchemeVariant
    profile: str | None = None
    metrics: ImageMetrics | None = None
    catalog_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested", normalize_scheme_type(self.requested))
        if not isinstance(self.variant, SchemeVariant):
            object.__setattr__(self, "variant", SchemeVariant(self.variant))
        if self.profile is not None and (
            not isinstance(self.profile, str) or not self.profile.strip()
        ):
            raise InvalidSchemeTypeError(
                f"scheme profile must be a non-empty string; got {self.profile!r}"
            )

    @property
    def smart(self) -> bool:
        """Whether the request used the smart pseudo-value."""
        return self.requested == SMART_SCHEME_TYPE

    @property
    def variant_value(self) -> str:
        """The concrete variant forwarded to the engine."""
        return self.variant.value

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe description used by ``--dry-run`` and the CLI contract."""
        metrics = None
        if self.metrics is not None:
            metrics = {
                "saturation": self.metrics.saturation,
                "colorfulness": self.metrics.colorfulness,
                "lightness": self.metrics.lightness,
                "contrast": self.metrics.contrast,
                "hue_diversity": self.metrics.hue_diversity,
            }
        return {
            "requested": self.requested,
            "variant": self.variant.value,
            "smart": self.smart,
            "profile": self.profile,
            "metrics": metrics,
            "catalog_path": self.catalog_path,
        }
