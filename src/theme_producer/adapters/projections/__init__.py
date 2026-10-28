"""Open/semantic projection adapters."""

from __future__ import annotations

from theme_producer.adapters.projections.btop import (
    BTOP_KEY_ROLES,
    BTOP_KEYS,
    BtopRow,
    build_btop_rows,
)
from theme_producer.adapters.projections.registry import (
    CAPABILITY_TABLE,
    DEV_PROJECTIONS,
    OPEN_PROJECTIONS,
    PROJECTION_VOCABULARY,
    RUNTIME_PROJECTIONS,
    ProjectionContext,
    ProjectionRegistry,
    TemplateProjection,
    build_projection_context,
)

__all__ = [
    "BTOP_KEY_ROLES",
    "BTOP_KEYS",
    "CAPABILITY_TABLE",
    "DEV_PROJECTIONS",
    "OPEN_PROJECTIONS",
    "PROJECTION_VOCABULARY",
    "RUNTIME_PROJECTIONS",
    "BtopRow",
    "ProjectionContext",
    "ProjectionRegistry",
    "TemplateProjection",
    "build_btop_rows",
    "build_projection_context",
]
