"""Settings resolution through ``config-assembler-engine``.

Mirrors CSG's proven chain and override rules with theme-producer's names:
CLI path > env path > directory traversal (3 levels) > XDG > packaged default.
"""

from __future__ import annotations

from importlib.resources import files as resource_files
from pathlib import Path

from config_assembler_engine.adapters.config_validator import PydanticValidator
from config_assembler_engine.adapters.env_reader import OsEnvironmentReader
from config_assembler_engine.adapters.parsers.toml_parser import TomlConfigParser
from config_assembler_engine.adapters.path_resolver import CompositePathResolver
from config_assembler_engine.adapters.strategies.cli_path import CliPathStrategy
from config_assembler_engine.adapters.strategies.default_file import DefaultFileStrategy
from config_assembler_engine.adapters.strategies.directory import DirectoryTraversalStrategy
from config_assembler_engine.adapters.strategies.env_path import EnvPathStrategy
from config_assembler_engine.adapters.strategies.xdg import XdgStrategy
from config_assembler_engine.adapters.type_coercer import PydanticTypeCoercer
from config_assembler_engine.application.use_cases import AssembleConfiguration
from config_assembler_engine.domain.models import (
    OverrideRule,
    OverrideSource,
    ResolutionPolicy,
    ResourceKind,
)
from config_assembler_engine.errors import (
    ConfigAssemblerError,
    ConfigValidationError,
    OverrideCoercionError,
)

from theme_producer.adapters.settings.errors import ConfigResolutionError
from theme_producer.adapters.settings.schema import CoreSettingsSchema
from theme_producer.adapters.version_provider import get_version
from theme_producer.domain.settings import (
    AppliedOverride,
    AppSettings,
    ConfigResolverResult,
    ContainerEngine,
    ContainerSettings,
    GenerationSettings,
    OutputSettings,
    RuntimeMode,
    RuntimeSettings,
    TemplatesSettings,
    Verbosity,
)


def _resolve_image_tag(image_tag: str) -> str:
    """Pin an empty tag to ``v<package version>``; keep explicit tags verbatim."""
    return image_tag or f"v{get_version()}"


def _convert_to_app_settings(validated: CoreSettingsSchema) -> AppSettings:
    return AppSettings(
        output=OutputSettings(
            directory=validated.output.directory,
            default_formats=tuple(validated.output.default_formats),
            overwrite=validated.output.overwrite,
            verbosity=Verbosity(validated.output.verbosity),
            apply_to_terminal=validated.output.apply_to_terminal,
            default_mode=validated.output.default_mode,
            smart_threshold=validated.output.smart_threshold,
        ),
        generation=GenerationSettings(
            engine=validated.generation.engine,
            default_params=dict(validated.generation.default_params),
            scheme_type=validated.generation.scheme_type,
            scheme_policy=validated.generation.scheme_policy,
        ),
        templates=TemplatesSettings(directory=validated.templates.directory),
        runtime=RuntimeSettings(mode=RuntimeMode(validated.runtime.mode)),
        container=ContainerSettings(
            engine=ContainerEngine(validated.container.engine),
            image_prefix=validated.container.image_prefix,
            image_tag=_resolve_image_tag(validated.container.image_tag),
            timeout_seconds=validated.container.timeout_seconds,
            memory_limit=validated.container.memory_limit,
        ),
    )


def _error_key(exc: ConfigAssemblerError) -> str:
    """Best field path available for a typed resolution error."""
    if isinstance(exc, OverrideCoercionError):
        return exc.field_path
    if isinstance(exc, ConfigValidationError):
        errors = exc.errors or []
        if errors:
            loc = errors[0].get("loc", ())
            if loc:
                return ".".join(str(part) for part in loc)
    return "settings.toml"


class AssembledConfigResolver:
    def __init__(self, assembler: AssembleConfiguration | None = None) -> None:
        strategies = [
            CliPathStrategy(kind=ResourceKind.FILE),
            EnvPathStrategy(kind=ResourceKind.FILE),
            DirectoryTraversalStrategy(
                filename="settings.toml", max_levels=3, kind=ResourceKind.FILE
            ),
            XdgStrategy(
                xdg_subdir="theme-producer",
                filename="settings.toml",
                kind=ResourceKind.FILE,
            ),
            DefaultFileStrategy(
                path=Path(resource_files("theme_producer") / "defaults" / "settings.toml"),
                kind=ResourceKind.FILE,
            ),
        ]
        self._assembler = assembler or AssembleConfiguration(
            path_resolver=CompositePathResolver(strategies),
            parser=TomlConfigParser(),
            env_reader=OsEnvironmentReader(),
            validator=PydanticValidator(),
            coercer=PydanticTypeCoercer(),
        )
        self._policy = ResolutionPolicy(env_prefix="THEME")
        self._rules = [
            OverrideRule("output.directory", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("output.default_formats", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("output.overwrite", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("output.verbosity", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("output.apply_to_terminal", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("output.default_mode", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("output.smart_threshold", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("generation.engine", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("generation.default_params", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("generation.scheme_type", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("generation.scheme_policy", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("templates.directory", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("runtime.mode", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("container.engine", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("container.image_prefix", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("container.image_tag", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("container.timeout_seconds", {OverrideSource.CLI, OverrideSource.ENV}),
            OverrideRule("container.memory_limit", {OverrideSource.CLI, OverrideSource.ENV}),
        ]
        self.last_result: ConfigResolverResult | None = None

    def resolve(
        self,
        cli_overrides: dict[str, str] | None = None,
        explicit_path: str | None = None,
    ) -> AppSettings:
        try:
            result = self._assembler.execute(
                policy=self._policy,
                rules=self._rules,
                schema=CoreSettingsSchema,
                cli_overrides=cli_overrides,
                explicit_path=explicit_path,
            )
        except ConfigAssemblerError as exc:
            raise ConfigResolutionError(
                key=_error_key(exc),
                reason=str(exc),
                source=exc,
            ) from exc
        self.last_result = ConfigResolverResult(
            resolved_path=result.resolved_path.path,
            applied_overrides=tuple(
                AppliedOverride(
                    field_path=override.field_path,
                    raw_value=override.raw_value,
                    coerced_value=override.coerced_value,
                    source=override.source.value,
                )
                for override in result.applied_overrides
            ),
        )
        return _convert_to_app_settings(result.config)
