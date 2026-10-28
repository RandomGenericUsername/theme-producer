"""One processor boundary for local, container, and dry-run execution."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from theme_producer.domain.generation import GenerationRequest, GenerationResult
from theme_producer.domain.settings import AppSettings

__all__ = ["ProcessorPort"]


@runtime_checkable
class ProcessorPort(Protocol):
    """Execute a generation request without knowing the runtime backend."""

    def process_generate(
        self, request: GenerationRequest, settings: AppSettings
    ) -> GenerationResult:
        """Generate a Theme plus the selected projections."""
        ...

    def process_show(self, request: GenerationRequest, settings: AppSettings) -> GenerationResult:
        """Generate a Theme for display without writing files."""
        ...
