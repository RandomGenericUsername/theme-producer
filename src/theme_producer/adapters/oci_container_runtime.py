"""``oci-runtime`` implementation of :class:`ContainerRuntimePort`."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from theme_producer.domain.generation import ContainerRuntimeError
from theme_producer.ports.container_runtime import ContainerMount, ContainerResult

if TYPE_CHECKING:
    from oci_runtime.ports.engine import ContainerEngine as OciContainerEngine

__all__ = ["OciContainerRuntimeAdapter"]


class OciContainerRuntimeAdapter:
    """Run/build/remove images through one oci-runtime engine."""

    def __init__(self, engine: OciContainerEngine) -> None:
        self._engine = engine

    def run(
        self,
        image: str,
        command: list[str],
        mounts: list[ContainerMount],
        timeout: int,
        environment: Mapping[str, str] | None = None,
        memory_limit: str | None = None,
    ) -> ContainerResult:
        if timeout <= 0:
            raise ContainerRuntimeError(f"invalid container timeout: {timeout}")

        from oci_runtime.domain.enums import NetworkMode, VolumeMountType
        from oci_runtime.domain.types import RunConfig, VolumeMount

        volumes = tuple(
            VolumeMount(
                source=str(mount.source),
                target=str(mount.target),
                type=VolumeMountType.BIND,
                read_only=mount.read_only,
            )
            for mount in mounts
        )
        config = RunConfig(
            image=image,
            command=(),
            volumes=volumes,
            timeout=float(timeout),
            detach=True,
            remove=False,
            environment=dict(environment or {}),
            user=f"{os.getuid()}:{os.getgid()}",
            network=NetworkMode.NONE,
            memory_limit=memory_limit,
        )

        container_id: str | None = None
        try:
            container_id = self._engine.containers.run(config)
            result = self._engine.containers.exec_container(
                container=container_id,
                command=list(command),
                timeout=float(timeout),
            )
        except Exception as exc:
            raise ContainerRuntimeError(
                f"container execution failed for image {image!r}: {exc}"
            ) from exc
        finally:
            if container_id is not None:
                try:
                    self._engine.containers.remove(container_id, force=True)
                except Exception:  # pragma: no cover - cleanup must not mask the result
                    pass

        return ContainerResult(
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def image_exists(self, image: str) -> bool:
        try:
            return bool(self._engine.images.exists(image))
        except Exception as exc:
            raise ContainerRuntimeError(f"could not check image {image!r}: {exc}") from exc

    def pull_image(self, image: str) -> None:
        try:
            self._engine.images.pull(image)
        except Exception as exc:
            raise ContainerRuntimeError(f"could not pull image {image!r}: {exc}") from exc

    def build_image(
        self,
        dockerfile: Path,
        context: Path,
        image_name: str,
        timeout: int | None = 600,
        build_args: Mapping[str, str] | None = None,
        labels: Mapping[str, str] | None = None,
    ) -> str:
        from oci_runtime.domain.types import BuildContext

        if timeout is not None and timeout <= 0:
            raise ContainerRuntimeError(f"invalid build timeout: {timeout}")
        build_context = BuildContext(
            build_file_path=Path(dockerfile),
            context_path=Path(context),
            build_args=dict(build_args or {}),
            labels=dict(labels or {}),
        )
        try:
            self._engine.images.build(
                build_context,
                image_name,
                float(timeout) if timeout is not None else None,
            )
        except Exception as exc:
            raise ContainerRuntimeError(f"could not build image {image_name!r}: {exc}") from exc
        return image_name

    def remove_image(self, image: str, force: bool = False) -> None:
        try:
            self._engine.images.remove(image, force=force)
        except Exception as exc:
            raise ContainerRuntimeError(f"could not remove image {image!r}: {exc}") from exc
