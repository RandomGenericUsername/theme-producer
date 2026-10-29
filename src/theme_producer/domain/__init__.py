"""Public surface of the pure Theme domain."""

from __future__ import annotations

from theme_producer.domain.enums import (
    TONE_ORDER,
    TONES,
    MaterialRole,
    ModeName,
    PaletteName,
    SourceKind,
)
from theme_producer.domain.exceptions import (
    InvalidImageMetricsError,
    InvalidSchemePolicyCatalogError,
    InvalidSchemeRuleError,
    InvalidSchemeTypeError,
    SchemePolicyError,
    ThemeValidationError,
    UnknownSchemePolicyError,
)
from theme_producer.domain.models import (
    SCHEMA_VERSION,
    Color,
    GeneratorMetadata,
    Mode,
    Source,
    Theme,
    TonalPalette,
)
from theme_producer.domain.scheme_policy import (
    CATALOG_VERSION,
    Condition,
    ImageMetrics,
    MetricName,
    Operator,
    Rule,
    SchemePolicy,
    SchemePolicyCatalog,
    SchemeVariant,
)
from theme_producer.domain.scheme_policy_resolver import SchemePolicyResolver
from theme_producer.domain.scheme_selection import (
    SMART_SCHEME_TYPE,
    SchemeResolution,
    normalize_scheme_type,
)
from theme_producer.domain.services import (
    ALIASES,
    LEGACY_ALIASES,
    LEGACY_COLOR_ORDER,
    STABLE_ALIASES,
    AliasService,
)

__all__ = [
    "ALIASES",
    "CATALOG_VERSION",
    "LEGACY_ALIASES",
    "LEGACY_COLOR_ORDER",
    "SCHEMA_VERSION",
    "SMART_SCHEME_TYPE",
    "STABLE_ALIASES",
    "TONE_ORDER",
    "TONES",
    "AliasService",
    "Color",
    "Condition",
    "GeneratorMetadata",
    "ImageMetrics",
    "InvalidImageMetricsError",
    "InvalidSchemePolicyCatalogError",
    "InvalidSchemeRuleError",
    "InvalidSchemeTypeError",
    "MaterialRole",
    "MetricName",
    "Mode",
    "ModeName",
    "Operator",
    "PaletteName",
    "Rule",
    "SchemePolicy",
    "SchemePolicyCatalog",
    "SchemePolicyError",
    "SchemePolicyResolver",
    "SchemeResolution",
    "SchemeVariant",
    "Source",
    "SourceKind",
    "Theme",
    "ThemeValidationError",
    "TonalPalette",
    "UnknownSchemePolicyError",
    "normalize_scheme_type",
]
