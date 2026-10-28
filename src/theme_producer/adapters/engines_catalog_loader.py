"""Resolve ``engines.yaml`` through ``config-assembler-engine``.

Mirrors CSG's proven catalog loader: CLI path > env path > directory traversal
(3 levels) > XDG > packaged default, with a Pydantic schema and no override
rules (the catalog is a single file, never merged).
"""

from __future__ import annotations

import logging
from importlib.resources import files as resource_files
from pathlib import Path

from config_assembler_engine.adapters.config_validator import PydanticValidator
from config_assembler_engine.adapters.env_reader import OsEnvironmentReader
from config_assembler_engine.adapters.parsers.yaml_parser import YamlConfigParser
from config_assembler_engine.adapters.path_resolver import CompositePathResolver
from config_assembler_engine.adapters.strategies.cli_path import CliPathStrategy
from config_assembler_engine.adapters.strategies.default_file import DefaultFileStrategy
from config_assembler_engine.adapters.strategies.directory import DirectoryTraversalStrategy
from config_assembler_engine.adapters.strategies.env_path import EnvPathStrategy
from config_assembler_engine.adapters.strategies.xdg import XdgStrategy
from config_assembler_engine.adapters.type_coercer import PydanticTypeCoercer
from config_assembler_engine.application.use_cases import AssembleConfiguration
from config_assembler_engine.domain.models import ResolutionPolicy, ResourceKind
from config_assembler_engine.errors import ConfigAssemblerError

from theme_producer.adapters.schemas.engines_catalog_schema import EnginesCatalogSchema
from theme_producer.domain.engines import (
    KNOWN_ENGINE_NAMES,
    EngineDefinition,
    EngineParameterDefinition,
)
from theme_producer.domain.exceptions import EngineConfigError

__all__ = ["EngineCatalogLoader", "YamlEngineCatalogLoader", "YamlEnginesCatalogLoader"]

logger = logging.getLogger(__name__)

CATALOG_FILENAME = "engines.yaml"
ENV_PREFIX = "THEME_ENGINES"


def _schema_to_domain(schema: EnginesCatalogSchema) -> dict[str, EngineDefinition]:
    result: dict[str, EngineDefinition] = {}
    for name, definition in schema.root.items():
        if name not in KNOWN_ENGINE_NAMES:
            logger.warning("Unknown engine '%s' in catalog — skipping", name)
            continue
        parameters = tuple(
            EngineParameterDefinition(
                name=parameter.name,
                param_type=parameter.param_type,
                default=parameter.default,
                choices=tuple(parameter.choices) if parameter.choices else None,
                description=parameter.description,
                required=parameter.required,
            )
            for parameter in definition.parameters
        )
        result[name] = EngineDefinition(
            name=name,
            display_name=definition.display_name or name.title(),
            description=definition.description,
            parameters=parameters,
            min_version=definition.min_version,
        )
    return result


def _error_key(exc: ConfigAssemblerError) -> str:
    return getattr(exc, "field_path", None) or CATALOG_FILENAME


class YamlEngineCatalogLoader:
    """Load and validate the engine catalog."""

    def __init__(self, assembler: AssembleConfiguration | None = None) -> None:
        strategies = [
            CliPathStrategy(kind=ResourceKind.FILE),
            EnvPathStrategy(kind=ResourceKind.FILE),
            DirectoryTraversalStrategy(
                filename=CATALOG_FILENAME,
                max_levels=3,
                kind=ResourceKind.FILE,
            ),
            XdgStrategy(
                xdg_subdir="theme-producer",
                filename=CATALOG_FILENAME,
                kind=ResourceKind.FILE,
            ),
            DefaultFileStrategy(
                path=Path(resource_files("theme_producer") / "defaults" / CATALOG_FILENAME),
                kind=ResourceKind.FILE,
            ),
        ]
        self._assembler = assembler or AssembleConfiguration(
            path_resolver=CompositePathResolver(strategies),
            parser=YamlConfigParser(),
            env_reader=OsEnvironmentReader(),
            validator=PydanticValidator(),
            coercer=PydanticTypeCoercer(),
        )
        self._policy = ResolutionPolicy(env_prefix=ENV_PREFIX)

    def load(self, *, explicit_path: str | None = None) -> dict[str, EngineDefinition]:
        """Return the engine catalog keyed by engine name."""
        try:
            result = self._assembler.execute(
                policy=self._policy,
                rules=[],
                schema=EnginesCatalogSchema,
                explicit_path=explicit_path,
            )
        except ConfigAssemblerError as exc:
            raise EngineConfigError(
                _error_key(exc),
                str(exc),
            ) from exc
        return _schema_to_domain(result.config)


#: Stable aliases for call sites that prefer the shorter names.
EngineCatalogLoader = YamlEngineCatalogLoader
YamlEnginesCatalogLoader = YamlEngineCatalogLoader
