"""Open/semantic projection adapters."""

from __future__ import annotations

from theme_producer.adapters.projections.btop import (
    BTOP_GRADIENTS,
    BTOP_KEY_ROLES,
    BTOP_KEY_SPECS,
    BTOP_KEYS,
    MIN_GRAPH_CONTRAST,
    BtopComponent,
    BtopGradient,
    BtopGradientStop,
    BtopIntent,
    BtopKeySpec,
    BtopRow,
    build_btop_rows,
)
from theme_producer.adapters.projections.registry import (
    CAPABILITY_TABLE,
    DEV_PROJECTIONS,
    OPEN_PROJECTIONS,
    PROJECTION_VOCABULARY,
    RUNTIME_PROJECTIONS,
    ModeProjectionContext,
    ProjectionContext,
    ProjectionRegistry,
    TemplateProjection,
    build_mode_context,
    build_projection_context,
)

__all__ = [
    "BTOP_GRADIENTS",
    "BTOP_KEY_ROLES",
    "BTOP_KEY_SPECS",
    "BTOP_KEYS",
    "CAPABILITY_TABLE",
    "DEV_PROJECTIONS",
    "MIN_GRAPH_CONTRAST",
    "OPEN_PROJECTIONS",
    "PROJECTION_VOCABULARY",
    "RUNTIME_PROJECTIONS",
    "BtopComponent",
    "BtopGradient",
    "BtopGradientStop",
    "BtopIntent",
    "BtopKeySpec",
    "BtopRow",
    "ModeProjectionContext",
    "ProjectionContext",
    "ProjectionRegistry",
    "TemplateProjection",
    "build_btop_rows",
    "build_mode_context",
    "build_projection_context",
]
