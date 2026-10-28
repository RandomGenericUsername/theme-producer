"""Pure domain objects for the ``scheme-smart`` policy.

The policy selects one of the nine concrete Material variants from normalized
image metrics. It is a small, declarative rule grammar — ordered rules with
ANDed conditions, first match wins, and a per-policy default — never code,
plugins, or an expression language.

Nothing here performs I/O: metrics are measured by an ``ImageMetricsPort``
adapter and catalogs are loaded by a ``SchemePolicyCatalogPort`` adapter. This
module only holds immutable, self-validating objects plus the vocabulary the
resolver needs. ``scheme-smart`` itself is not a variant: it is the ``tpr``
pseudo-value that triggers policy resolution.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from theme_producer.domain.exceptions import (
    InvalidImageMetricsError,
    InvalidSchemePolicyCatalogError,
    InvalidSchemeRuleError,
    SchemePolicyError,
    UnknownSchemePolicyError,
)

__all__ = [
    "CATALOG_VERSION",
    "Condition",
    "ImageMetrics",
    "MetricName",
    "Operator",
    "Rule",
    "SchemePolicy",
    "SchemePolicyCatalog",
    "SchemeVariant",
]

#: The only supported scheme-policy catalog schema version.
CATALOG_VERSION = 1


class SchemeVariant(StrEnum):
    """The nine concrete Material 3 scheme variants an engine accepts."""

    TONAL_SPOT = "scheme-tonal-spot"
    CONTENT = "scheme-content"
    EXPRESSIVE = "scheme-expressive"
    FIDELITY = "scheme-fidelity"
    FRUIT_SALAD = "scheme-fruit-salad"
    MONOCHROME = "scheme-monochrome"
    NEUTRAL = "scheme-neutral"
    RAINBOW = "scheme-rainbow"
    VIBRANT = "scheme-vibrant"


class MetricName(StrEnum):
    """The normalized image metrics a policy may test."""

    SATURATION = "saturation"
    COLORFULNESS = "colorfulness"
    LIGHTNESS = "lightness"
    CONTRAST = "contrast"
    HUE_DIVERSITY = "hue_diversity"


class Operator(StrEnum):
    """The comparison operators allowed in a condition."""

    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    BETWEEN = "between"


def _unit_float(value: object, field_name: str, error: type[SchemePolicyError]) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise error(f"{field_name} must be a number in [0, 1]; got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise error(f"{field_name} must be finite; got {value!r}")
    if not 0.0 <= number <= 1.0:
        raise error(f"{field_name} must be within [0, 1]; got {number!r}")
    return number


def _require_variant(value: object, field_name: str) -> SchemeVariant:
    try:
        return SchemeVariant(value)
    except (TypeError, ValueError) as exc:
        known = [variant.value for variant in SchemeVariant]
        raise InvalidSchemeRuleError(f"{field_name} must be one of {known}; got {value!r}") from exc


@dataclass(frozen=True, slots=True)
class ImageMetrics:
    """Five normalized metrics, each a finite float in ``[0, 1]``."""

    saturation: float
    colorfulness: float
    lightness: float
    contrast: float
    hue_diversity: float

    def __post_init__(self) -> None:
        for field_name in (
            "saturation",
            "colorfulness",
            "lightness",
            "contrast",
            "hue_diversity",
        ):
            object.__setattr__(
                self,
                field_name,
                _unit_float(
                    getattr(self, field_name),
                    f"image metric {field_name}",
                    InvalidImageMetricsError,
                ),
            )

    def value_for(self, metric: MetricName | str) -> float:
        """Return the value of ``metric``; field names mirror metric names."""
        try:
            name = MetricName(metric)
        except (TypeError, ValueError) as exc:
            known = [item.value for item in MetricName]
            raise InvalidImageMetricsError(
                f"unknown image metric {metric!r}; known metrics: {known}"
            ) from exc
        return float(getattr(self, name.value))


@dataclass(frozen=True, slots=True)
class Condition:
    """One metric comparison.

    ``between`` is inclusive and needs ``upper >= value``; every other operator
    must leave ``upper`` as ``None``.
    """

    metric: MetricName | str
    operator: Operator | str
    value: float
    upper: float | None = None

    def __post_init__(self) -> None:
        try:
            metric = MetricName(self.metric)
        except (TypeError, ValueError) as exc:
            known = [item.value for item in MetricName]
            raise InvalidSchemeRuleError(
                f"condition metric must be one of {known}; got {self.metric!r}"
            ) from exc
        object.__setattr__(self, "metric", metric)

        try:
            operator = Operator(self.operator)
        except (TypeError, ValueError) as exc:
            known = [item.value for item in Operator]
            raise InvalidSchemeRuleError(
                f"condition operator must be one of {known}; got {self.operator!r}"
            ) from exc
        object.__setattr__(self, "operator", operator)

        value = _unit_float(self.value, "condition value", InvalidSchemeRuleError)
        object.__setattr__(self, "value", value)

        if operator is not Operator.BETWEEN:
            if self.upper is not None:
                raise InvalidSchemeRuleError(
                    f"condition upper is only valid for the 'between' operator; "
                    f"got upper={self.upper!r} with operator={operator.value!r}"
                )
            return

        if self.upper is None:
            raise InvalidSchemeRuleError("condition operator 'between' requires an upper bound")
        upper = _unit_float(self.upper, "condition upper", InvalidSchemeRuleError)
        if upper < value:
            raise InvalidSchemeRuleError(
                f"condition upper must be >= value for 'between'; got "
                f"value={value!r}, upper={upper!r}"
            )
        object.__setattr__(self, "upper", upper)


@dataclass(frozen=True, slots=True)
class Rule:
    """A set of ANDed conditions and the variant they select."""

    conditions: tuple[Condition, ...]
    variant: SchemeVariant | str

    def __post_init__(self) -> None:
        if not isinstance(self.conditions, tuple | list):
            raise InvalidSchemeRuleError(
                f"rule conditions must be a tuple of Condition; got {self.conditions!r}"
            )
        conditions = tuple(self.conditions)
        if not conditions:
            raise InvalidSchemeRuleError("rule must contain at least one condition")
        if not all(isinstance(condition, Condition) for condition in conditions):
            raise InvalidSchemeRuleError(
                f"rule conditions must all be Condition instances; got {conditions!r}"
            )
        object.__setattr__(self, "conditions", conditions)
        object.__setattr__(self, "variant", _require_variant(self.variant, "rule variant"))


@dataclass(frozen=True, slots=True)
class SchemePolicy:
    """An ordered rule list plus the variant used when no rule matches."""

    name: str
    rules: tuple[Rule, ...]
    default: SchemeVariant | str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidSchemeRuleError(
                f"scheme policy name must be a non-empty string; got {self.name!r}"
            )
        if not isinstance(self.rules, tuple | list):
            raise InvalidSchemeRuleError(
                f"scheme policy {self.name!r} rules must be a tuple of Rule; got {self.rules!r}"
            )
        rules = tuple(self.rules)
        if not rules:
            raise InvalidSchemeRuleError(
                f"scheme policy {self.name!r} must contain at least one rule"
            )
        if not all(isinstance(rule, Rule) for rule in rules):
            raise InvalidSchemeRuleError(
                f"scheme policy {self.name!r} rules must all be Rule instances; got {rules!r}"
            )
        object.__setattr__(self, "rules", rules)
        object.__setattr__(
            self, "default", _require_variant(self.default, f"scheme policy {self.name!r} default")
        )


@dataclass(frozen=True, slots=True)
class SchemePolicyCatalog:
    """A versioned set of named policies with one default profile."""

    version: int
    default_policy: str
    policies: Mapping[str, SchemePolicy]

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise InvalidSchemePolicyCatalogError(
                f"scheme policy catalog version must be an int; got {self.version!r}"
            )
        if self.version != CATALOG_VERSION:
            raise InvalidSchemePolicyCatalogError(
                f"unsupported scheme policy catalog version {self.version!r}; "
                f"expected {CATALOG_VERSION!r}"
            )

        if not isinstance(self.policies, Mapping):
            raise InvalidSchemePolicyCatalogError(
                f"scheme policy catalog policies must be a mapping; "
                f"got {type(self.policies).__name__}"
            )
        if not self.policies:
            raise InvalidSchemePolicyCatalogError(
                "scheme policy catalog must contain at least one policy"
            )

        normalized: dict[str, SchemePolicy] = {}
        for raw_name, policy in self.policies.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                raise InvalidSchemePolicyCatalogError(
                    f"scheme policy names must be non-empty strings; got {raw_name!r}"
                )
            if not isinstance(policy, SchemePolicy):
                raise InvalidSchemePolicyCatalogError(
                    f"scheme policy {raw_name!r} must be a SchemePolicy; got {policy!r}"
                )
            if policy.name != raw_name:
                raise InvalidSchemePolicyCatalogError(
                    f"scheme policy catalog key {raw_name!r} does not match "
                    f"the policy name {policy.name!r}"
                )
            normalized[raw_name] = policy

        if not isinstance(self.default_policy, str) or not self.default_policy.strip():
            raise InvalidSchemePolicyCatalogError(
                f"scheme policy catalog default_policy must be a non-empty string; "
                f"got {self.default_policy!r}"
            )
        if self.default_policy not in normalized:
            known = ", ".join(sorted(normalized))
            raise UnknownSchemePolicyError(
                f"default scheme policy {self.default_policy!r} is not in the catalog; "
                f"known policies: {known}"
            )

        object.__setattr__(self, "policies", MappingProxyType(normalized))

    def select(self, name: str | None = None) -> SchemePolicy:
        """Return the named policy, or the catalog default when ``name`` is ``None``."""
        key = self.default_policy if name is None else name
        if not isinstance(key, str):
            raise UnknownSchemePolicyError(f"scheme policy name must be a string; got {key!r}")
        policy = self.policies.get(key)
        if policy is None:
            known = ", ".join(sorted(self.policies))
            raise UnknownSchemePolicyError(
                f"unknown scheme policy {key!r}; known policies: {known}"
            )
        return policy
