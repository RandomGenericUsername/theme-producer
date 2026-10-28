"""Templates directory resolution.

Templates are a path-only concern: they go through ``CompositePathResolver``
and never through the settings assembler (CSG does the same).
"""

from __future__ import annotations

from importlib.resources import files as resource_files
from pathlib import Path

from config_assembler_engine.adapters.path_resolver import CompositePathResolver
from config_assembler_engine.adapters.strategies.cli_path import CliDirStrategy
from config_assembler_engine.adapters.strategies.default_file import DefaultDirStrategy
from config_assembler_engine.adapters.strategies.directory import DirTraversalStrategy
from config_assembler_engine.adapters.strategies.env_path import EnvDirStrategy
from config_assembler_engine.adapters.strategies.xdg import XdgDirStrategy
from config_assembler_engine.domain.models import ResolutionPolicy
from config_assembler_engine.errors import ConfigAssemblerError

from theme_producer.adapters.settings.errors import ConfigResolutionError

_DEFAULT_TEMPLATES_DIR = Path(resource_files("theme_producer") / "defaults" / "templates")
_RESOLUTION_POLICY = ResolutionPolicy(env_prefix="THEME_TEMPLATES")


class TemplateDirResolver:
    def __init__(self) -> None:
        strategies = [
            CliDirStrategy(),
            EnvDirStrategy(var="TEMPLATES_DIR"),
            DirTraversalStrategy(dirname="templates", max_levels=3),
            XdgDirStrategy(xdg_subdir="theme-producer", dirname="templates"),
            DefaultDirStrategy(path=_DEFAULT_TEMPLATES_DIR),
        ]
        self._resolver = CompositePathResolver(strategies)

    def resolve(self, explicit_dir: Path | None = None) -> Path:
        try:
            result = self._resolver.resolve(
                _RESOLUTION_POLICY,
                explicit_path=str(explicit_dir) if explicit_dir else None,
            )
        except ConfigAssemblerError as exc:
            raise ConfigResolutionError(
                key="templates.directory",
                reason=f"Failed to resolve templates directory: {exc}",
                source=exc,
            ) from exc
        return result.path
