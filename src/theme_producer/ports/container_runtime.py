"""Container runtime boundary used by the container/dry-run processors.

The port is intentionally narrower than ``oci-runtime``'s engine: this package
only runs one image, checks for images, builds them, and removes them. Fakes in
tests implement exactly this surface.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["ContainerMount", "ContainerResult", "ContainerRuntimePort"]


@dataclass(frozen=True, slots=True)
class ContainerMount:
    """A bind mount for one container run."""

    source: Path
    target: str
    read_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", Path(self.source))


@dataclass(frozen=True, slots=True)
class ContainerResult:
    """The outcome of one container execution."""

    return_code: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0


@runtime_checkable
class ContainerRuntimePort(Protocol):
    def run(
        self,
        image: str,
        command: list[str],
        mounts: list[ContainerMount],
        timeout: int,
        environment: Mapping[str, str] | None = None,
        memory_limit: str | None = None,
    ) -> ContainerResult: ...

    def image_exists(self, image: str) -> bool: ...

    def pull_image(self, image: str) -> None: ...

    def build_image(
        self,
        dockerfile: Path,
        context: Path,
        image_name: str,
        timeout: int | None = 600,
        build_args: Mapping[str, str] | None = None,
        labels: Mapping[str, str] | None = None,
    ) -> str: ...

    def remove_image(self, image: str, force: bool = False) -> None: ...
