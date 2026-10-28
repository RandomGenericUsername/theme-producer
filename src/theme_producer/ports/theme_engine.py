"""Engine generation port.

The Theme is produced by an engine behind this boundary; projections and the
rest of the domain never know which process or library generated the colors.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.models import Theme

__all__ = ["ThemeEnginePort"]


@runtime_checkable
class ThemeEnginePort(Protocol):
    """A replaceable color-generation engine."""

    def is_available(self) -> bool:
        """Return whether the engine can be executed on this host."""
        ...

    def generate(self, request: ThemeRequest, config: EngineConfig) -> Theme:
        """Generate a complete Theme from exactly one source."""
        ...
