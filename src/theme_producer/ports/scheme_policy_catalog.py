"""Scheme-policy catalog port.

Protocol only: this module names the boundary; it does not read YAML or touch
the filesystem. The adapter (``YamlSchemePolicyCatalogLoader`` in a later
ticket) resolves the catalog through ``config-assembler-engine`` with the same
single-file precedence chain as ``settings.toml`` and ``engines.yaml``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from theme_producer.domain.scheme_policy import SchemePolicyCatalog

__all__ = ["SchemePolicyCatalogPort"]


@runtime_checkable
class SchemePolicyCatalogPort(Protocol):
    """Load a validated scheme-policy catalog from a single file."""

    def load(self, explicit_path: str | None = None) -> SchemePolicyCatalog:
        """Return the catalog, or raise ``SchemePolicyError`` when it is invalid.

        ``explicit_path`` wins over the environment variable and the XDG paths;
        like the other catalogs this is single-file selection, never merging.
        """
        ...
