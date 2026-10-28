"""Jinja adapter for the bundled projection template catalog.

The environment is intentionally identical to CSG's renderer: a file-system
loader rooted at the resolved templates directory, ``StrictUndefined`` so a
missing context key fails loudly, and whitespace trimming so rendered artifacts
are deterministic. There are no shared partials: every ``*.j2`` in the catalog
is a complete projection.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, TemplateNotFound

from theme_producer.adapters.template_dir_resolver import TemplateDirResolver

__all__ = [
    "JinjaThemeRenderer",
    "TemplateNotFoundError",
    "TemplateRenderError",
]


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a requested template is not in the resolved catalog."""

    def __init__(self, template: str, searched: Path) -> None:
        self.template = template
        self.searched = searched
        super().__init__(f"Template {template!r} not found in {searched}")


class TemplateRenderError(RuntimeError):
    """Raised when Jinja cannot compile or render a template."""

    def __init__(self, template: str, reason: str) -> None:
        self.template = template
        self.reason = reason
        super().__init__(f"Failed to render template {template!r}: {reason}")


class JinjaThemeRenderer:
    """Render one complete ``*.j2`` projection into an output directory."""

    def __init__(
        self,
        resolver: TemplateDirResolver | None = None,
        *,
        templates_dir: Path | None = None,
    ) -> None:
        self._resolver = resolver or TemplateDirResolver()
        self._explicit_dir = Path(templates_dir) if templates_dir is not None else None
        self._templates_dir: Path | None = None
        self._env: Environment | None = None

    @property
    def templates_dir(self) -> Path:
        """The resolved template directory (resolved on first use)."""
        self._ensure_environment()
        assert self._templates_dir is not None
        return self._templates_dir

    @property
    def environment(self) -> Environment:
        """The configured Jinja environment (resolved on first use)."""
        self._ensure_environment()
        assert self._env is not None
        return self._env

    def _ensure_environment(self) -> None:
        if self._env is not None:
            return
        templates_dir = self._resolver.resolve(explicit_dir=self._explicit_dir)
        self._templates_dir = templates_dir
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @staticmethod
    def _validate_template_name(template_name: str) -> None:
        if not isinstance(template_name, str) or not template_name:
            raise ValueError("template_name must be a non-empty string")
        if Path(template_name).name != template_name:
            raise ValueError(f"template_name must be a basename, not a path: {template_name!r}")
        if not template_name.endswith(".j2"):
            raise ValueError(f"template_name must end with .j2: {template_name!r}")

    def render(
        self,
        template_name: str,
        context: Mapping[str, Any],
        output_dir: Path,
    ) -> Path:
        """Render ``template_name`` with ``context`` into ``output_dir``.

        The output file is named after the template without its ``.j2`` suffix,
        e.g. ``colors.gtk.css.j2`` becomes ``colors.gtk.css``.
        """
        self._validate_template_name(template_name)
        if not isinstance(context, Mapping):
            raise TypeError(f"context must be a mapping; got {type(context).__name__}")
        output_dir = Path(output_dir)

        try:
            template = self.environment.get_template(template_name)
        except TemplateNotFound:
            raise TemplateNotFoundError(template_name, self.templates_dir) from None
        except TemplateError as exc:
            raise TemplateRenderError(template_name, f"template compilation failed: {exc}") from exc

        try:
            rendered = template.render(**context)
        except TemplateError as exc:
            raise TemplateRenderError(template_name, str(exc)) from exc

        output_path = output_dir / template_name.removesuffix(".j2")
        try:
            output_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
            output_path.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            raise TemplateRenderError(template_name, f"cannot write {output_path}: {exc}") from exc
        return output_path
