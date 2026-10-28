"""Presentation boundary for every CLI verb.

Adapters translate these calls into cli-output renderer views. JSON is the
machine contract; rich/plain are human views over the same objects.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from theme_producer.domain.generation import GenerationResult
from theme_producer.domain.models import Theme

__all__ = ["OutputPort"]


@runtime_checkable
class OutputPort(Protocol):
    def process_result(self, result: GenerationResult) -> None: ...

    def error(self, exc: BaseException) -> None: ...

    def message(self, text: str) -> None: ...

    def theme_display(self, theme: Theme, *, engine: str) -> None: ...

    def config_info(self, payload: Mapping[str, Any]) -> None: ...

    def engines_catalog(
        self,
        engines: list[dict[str, Any]],
        *,
        runtime: str,
        container_engine: str | None,
    ) -> None: ...

    def install_result(self, results: list[dict[str, Any]]) -> None: ...

    def uninstall_result(self, results: list[dict[str, Any]]) -> None: ...

    def version_info(self, version: str) -> None: ...
