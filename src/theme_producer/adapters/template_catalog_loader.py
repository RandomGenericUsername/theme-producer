"""Load and validate the projection template catalog.

The catalog is a flat directory of complete Jinja templates. Every ``*.j2`` file
must map 1:1 to a projection: a missing projection template and a stray template
are both hard errors, so a partial can never silently become its own artifact.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from theme_producer.adapters.template_dir_resolver import TemplateDirResolver

__all__ = [
    "MissingTemplateError",
    "TemplateCatalog",
    "TemplateCatalogError",
    "TemplateCatalogLoader",
    "UnknownTemplateError",
]


class TemplateCatalogError(RuntimeError):
    """Base class for template catalog failures."""


class MissingTemplateError(TemplateCatalogError):
    """Raised when a projection template is absent from the catalog."""

    def __init__(self, templates: Iterable[str], directory: Path) -> None:
        self.templates = tuple(sorted(templates))
        self.directory = directory
        super().__init__(f"Missing template(s) in {directory}: {', '.join(self.templates)}")


class UnknownTemplateError(TemplateCatalogError):
    """Raised when the catalog contains a template no projection owns."""

    def __init__(self, templates: Iterable[str], directory: Path) -> None:
        self.templates = tuple(sorted(templates))
        self.directory = directory
        super().__init__(f"Unknown template(s) in {directory}: {', '.join(self.templates)}")


@dataclass(frozen=True, slots=True)
class TemplateCatalog:
    """A validated, flat set of projection templates."""

    directory: Path
    templates: tuple[str, ...]

    def path_for(self, template: str) -> Path:
        """Return the path for a catalog entry, rejecting non-catalog names."""
        if template not in self.templates:
            raise KeyError(f"template {template!r} is not in the catalog")
        return self.directory / template

    def __contains__(self, template: object) -> bool:
        return template in self.templates


class TemplateCatalogLoader:
    """Resolve the templates directory and validate its contents."""

    def __init__(self, resolver: TemplateDirResolver | None = None) -> None:
        self._resolver = resolver or TemplateDirResolver()

    def load(
        self,
        expected_templates: Iterable[str],
        *,
        explicit_dir: Path | None = None,
    ) -> TemplateCatalog:
        """Return the catalog, or raise when a template is missing/unknown."""
        expected = tuple(sorted(set(expected_templates)))
        directory = self._resolver.resolve(explicit_dir=explicit_dir)
        if not directory.is_dir():
            raise TemplateCatalogError(f"Templates directory does not exist: {directory}")

        found = tuple(
            sorted(
                path.name for path in directory.iterdir() if path.is_file() and path.suffix == ".j2"
            )
        )
        expected_set = set(expected)
        found_set = set(found)
        missing = expected_set - found_set
        if missing:
            raise MissingTemplateError(missing, directory)
        unknown = found_set - expected_set
        if unknown:
            raise UnknownTemplateError(unknown, directory)
        return TemplateCatalog(directory=directory, templates=expected)
