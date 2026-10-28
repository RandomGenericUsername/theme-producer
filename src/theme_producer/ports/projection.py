"""Projection boundary and projection metadata.

A projection is a pure function of a :class:`~theme_producer.domain.models.Theme`.
The port deliberately exposes only ``render``; where the bytes come from (a
Jinja template, a mapping table) is an adapter detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from theme_producer.domain.enums import ModeName
from theme_producer.domain.models import Theme

__all__ = ["CAPABILITIES", "Capability", "Projection", "ProjectionPort"]

#: A projection either carries the complete role set (``open``) or a deliberate
#: fixed mapping table (``fixed``). REQ-009 owns the fixed ANSI projections.
CAPABILITIES: frozenset[str] = frozenset({"open", "fixed"})

Capability = Literal["open", "fixed"]


@dataclass(frozen=True, slots=True)
class Projection:
    """Static identity of one consumer artifact.

    ``name`` is the stable logical name, ``filename`` is the exact artifact the
    dotfiles runtime consumes, ``capability`` records whether the format can
    carry the full semantic role set, and ``template`` is the catalog entry that
    renders it. ``dev_only`` marks previews that are rendered but not part of
    the runtime artifact contract.
    """

    name: str
    filename: str
    capability: Capability
    template: str
    dev_only: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"projection name must be a non-empty string; got {self.name!r}")
        if not isinstance(self.filename, str) or not self.filename.strip():
            raise ValueError(
                f"projection filename must be a non-empty string; got {self.filename!r}"
            )
        if "/" in self.filename or "\\" in self.filename:
            raise ValueError(f"projection filename must be a basename; got {self.filename!r}")
        if self.capability not in CAPABILITIES:
            raise ValueError(
                f"projection capability must be one of {sorted(CAPABILITIES)}; "
                f"got {self.capability!r}"
            )
        if not isinstance(self.template, str) or not self.template.endswith(".j2"):
            raise ValueError(f"projection template must be a .j2 file; got {self.template!r}")


@runtime_checkable
class ProjectionPort(Protocol):
    """Render one Theme artifact into an output directory."""

    def render(
        self,
        theme: Theme,
        output_dir: Path,
        mode: ModeName | str = ModeName.DARK,
    ) -> Path:
        """Write this projection into ``output_dir`` and return its path."""
        ...
