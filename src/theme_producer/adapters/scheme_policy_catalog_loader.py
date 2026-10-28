"""Resolve ``scheme-policies.yaml`` through ``config-assembler-engine``.

The catalog is a single file, never merged, and uses the same five-strategy
chain as ``settings.toml`` / ``engines.yaml``:

1. explicit CLI path,
2. ``THEME_SCHEME_POLICIES_CONFIG_FILE_PATH``,
3. directory traversal (3 levels up),
4. ``$XDG_CONFIG_HOME/theme-producer/scheme-policies.yaml``,
5. the packaged ``defaults/scheme-policies.yaml``.

A Pydantic schema owns the document shape; the pure domain objects own the
metric/operator/variant vocabulary and range/rule/default invariants. Every
domain error is re-raised with the resolved source path so an unknown name
points at the file that contains it.
"""

from __future__ import annotations

from collections.abc import Mapping
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any

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

from theme_producer.adapters.schemas.scheme_policies_catalog_schema import (
    SchemePolicyCatalogSchema,
    SchemePolicySchema,
)
from theme_producer.domain.exceptions import (
    InvalidSchemePolicyCatalogError,
    InvalidSchemeRuleError,
    SchemePolicyError,
)
from theme_producer.domain.scheme_policy import (
    Condition,
    Rule,
    SchemePolicy,
    SchemePolicyCatalog,
)

__all__ = ["SchemePolicyCatalogLoader", "YamlSchemePolicyCatalogLoader"]

CATALOG_FILENAME = "scheme-policies.yaml"
ENV_PREFIX = "THEME_SCHEME_POLICIES"


def _conditions_from(when: Mapping[str, Mapping[str, Any]], source: Path) -> tuple[Condition, ...]:
    """Flatten the compact ``metric: {operator: operand}`` map into conditions."""
    conditions: list[Condition] = []
    for metric, operators in when.items():
        if not isinstance(operators, Mapping) or not operators:
            raise InvalidSchemeRuleError(
                f"{source}: metric {metric!r} must map to at least one operator"
            )
        for operator, operand in operators.items():
            if operator == "between":
                if isinstance(operand, list | tuple) and len(operand) == 2:
                    value, upper = operand
                elif isinstance(operand, Mapping) and set(operand) == {"min", "max"}:
                    value, upper = operand["min"], operand["max"]
                else:
                    raise InvalidSchemeRuleError(
                        f"{source}: metric {metric!r} 'between' needs [lower, upper] "
                        f"or {{min: ..., max: ...}}; got {operand!r}"
                    )
                conditions.append(Condition(metric, operator, value, upper))
            else:
                conditions.append(Condition(metric, operator, operand))
    return tuple(conditions)


def _schema_to_domain(schema: SchemePolicyCatalogSchema, source: Path) -> SchemePolicyCatalog:
    policies: dict[str, SchemePolicy] = {}
    for name, policy_schema in schema.policies.items():
        policies[name] = _policy_to_domain(name, policy_schema, source)
    return SchemePolicyCatalog(
        version=schema.version,
        default_policy=schema.default,
        policies=policies,
    )


def _policy_to_domain(name: str, schema: SchemePolicySchema, source: Path) -> SchemePolicy:
    rules = tuple(Rule(_conditions_from(rule.when, source), rule.variant) for rule in schema.rules)
    return SchemePolicy(name=name, rules=rules, default=schema.default)


class YamlSchemePolicyCatalogLoader:
    """Load and validate the scheme-policy catalog."""

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
        self._resolver = CompositePathResolver(strategies)
        self._assembler = assembler or AssembleConfiguration(
            path_resolver=self._resolver,
            parser=YamlConfigParser(),
            env_reader=OsEnvironmentReader(),
            validator=PydanticValidator(),
            coercer=PydanticTypeCoercer(),
        )
        self._policy = ResolutionPolicy(env_prefix=ENV_PREFIX)
        #: Path of the last catalog resolution, even when validation failed.
        self.last_source_path: Path | None = None

    def load(self, explicit_path: str | None = None) -> SchemePolicyCatalog:
        """Return the validated catalog, or raise a typed ``SchemePolicyError``."""
        try:
            resolved = self._resolver.resolve(self._policy, explicit_path)
        except ConfigAssemblerError as exc:
            self.last_source_path = None
            raise InvalidSchemePolicyCatalogError(
                f"no scheme policy catalog found ({CATALOG_FILENAME}): {exc}"
            ) from exc

        self.last_source_path = resolved.path
        try:
            result = self._assembler.execute(
                policy=self._policy,
                rules=[],
                schema=SchemePolicyCatalogSchema,
                explicit_path=explicit_path,
            )
        except ConfigAssemblerError as exc:
            raise InvalidSchemePolicyCatalogError(f"{resolved.path}: {exc}") from exc

        source = result.resolved_path.path
        self.last_source_path = source
        try:
            return _schema_to_domain(result.config, source)
        except SchemePolicyError as exc:
            # Preserve the domain error type (unknown policy, bad rule, ...) but
            # make the offending file part of the message.
            raise type(exc)(f"{source}: {exc}") from exc


#: Stable alias for call sites that prefer the shorter name.
SchemePolicyCatalogLoader = YamlSchemePolicyCatalogLoader
