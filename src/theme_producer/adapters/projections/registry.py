"""Registry of open Theme projections and their capability table.

Projections are pure: this module builds one context from the selected Theme
mode (dark by default) and hands it to the Jinja renderer. Templates never read
each other and never read the filesystem. The dev-only HTML preview additionally
receives both modes so a reviewer can compare them; ``theme.json`` always carries
both modes and runtime light/dark switching stays out of scope.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from theme_producer.adapters.jinja_renderer import JinjaThemeRenderer
from theme_producer.adapters.projections.ansi import (
    ANSI_PROJECTIONS,
    SEQUENCES_PROJECTION,
    AnsiProjection,
    sequences_postprocess,
)
from theme_producer.adapters.projections.btop import BtopRow, build_btop_rows
from theme_producer.adapters.template_catalog_loader import (
    TemplateCatalog,
    TemplateCatalogLoader,
)
from theme_producer.domain.enums import TONE_ORDER, MaterialRole, ModeName, PaletteName
from theme_producer.domain.generation import UnknownFormatError
from theme_producer.domain.models import Color, Mode, Theme
from theme_producer.domain.services import AliasService
from theme_producer.ports.projection import Capability, Projection, ProjectionPort

__all__ = [
    "ALL_PROJECTIONS",
    "CAPABILITY_TABLE",
    "DEV_PROJECTIONS",
    "FIXED_PROJECTIONS",
    "FORMAT_NAMES",
    "LEGACY_ALIAS_COUNT",
    "OPEN_PROJECTIONS",
    "PROJECTION_VOCABULARY",
    "RUNTIME_PROJECTIONS",
    "ModeProjectionContext",
    "ProjectionContext",
    "ProjectionRegistry",
    "TemplateProjection",
    "build_mode_context",
    "build_projection_context",
    "default_format_names",
    "known_format_names",
    "projections_for_formats",
]

#: The stable projection vocabulary. ``background`` deliberately resolves to
#: Material ``surface`` (REQ-008 mapping), while ``foreground`` tracks
#: ``on_surface`` and ``accent`` tracks ``primary``.
PROJECTION_VOCABULARY: Mapping[str, MaterialRole] = MappingProxyType(
    {
        "background": MaterialRole.SURFACE,
        "foreground": MaterialRole.ON_SURFACE,
        "accent": MaterialRole.PRIMARY,
        "accent-muted": MaterialRole.SECONDARY,
        "surface": MaterialRole.SURFACE,
        "on_surface": MaterialRole.ON_SURFACE,
        "error": MaterialRole.ERROR,
        "warning": MaterialRole.TERTIARY,
    }
)

LEGACY_ALIAS_COUNT = 16

OPEN_PROJECTIONS: tuple[Projection, ...] = (
    Projection(
        name="gtk",
        filename="colors.gtk.css",
        capability="open",
        template="colors.gtk.css.j2",
    ),
    Projection(
        name="adw",
        filename="colors.adw.css",
        capability="open",
        template="colors.adw.css.j2",
    ),
    Projection(
        name="yaml",
        filename="colors.yaml",
        capability="open",
        template="colors.yaml.j2",
    ),
    Projection(
        name="rasi",
        filename="colors.rasi",
        capability="open",
        template="colors.rasi.j2",
    ),
    Projection(
        name="conf",
        filename="colors.conf",
        capability="open",
        template="colors.conf.j2",
    ),
    Projection(
        name="btop",
        filename="colors.btop.theme",
        capability="open",
        template="colors.btop.theme.j2",
    ),
    Projection(
        name="html",
        filename="theme.html",
        capability="open",
        template="theme.html.j2",
        dev_only=True,
    ),
)

#: The fixed ANSI projections (kitty + OSC sequences). They are registered in
#: the same registry but kept separate so the open catalog's identity is stable.
FIXED_PROJECTIONS: tuple[Projection, ...] = ANSI_PROJECTIONS

#: Every shipped projection, open first, then the fixed ANSI pair.
ALL_PROJECTIONS: tuple[Projection, ...] = OPEN_PROJECTIONS + FIXED_PROJECTIONS

#: Capability contract data: the complete projection catalog carries both the
#: open/semantic projections and the deliberate fixed ANSI table (REQ-009).
CAPABILITY_TABLE: Mapping[str, Capability] = MappingProxyType(
    {projection.name: projection.capability for projection in ALL_PROJECTIONS}
)

RUNTIME_PROJECTIONS: tuple[Projection, ...] = tuple(
    projection for projection in ALL_PROJECTIONS if not projection.dev_only
)
DEV_PROJECTIONS: tuple[Projection, ...] = tuple(
    projection for projection in ALL_PROJECTIONS if projection.dev_only
)

for _projection in ALL_PROJECTIONS:  # pragma: no cover - import-time guard
    if _projection.template.removesuffix(".j2") != _projection.filename:
        raise RuntimeError(
            f"projection {_projection.name!r} template/filename drift: "
            f"{_projection.template!r} != {_projection.filename!r}"
        )

#: Consumer-facing ``--format`` names, in stable display order. ``json`` is
#: special: it selects only the canonical ``theme.json`` artifact and therefore
#: has no projection record. The rest map to the filenames consumers already
#: know (``gtk.css``, ``btop.theme``, ...), not to internal projection names.
FORMAT_NAMES: tuple[str, ...] = (
    "json",
    "yaml",
    "conf",
    "gtk.css",
    "adw.css",
    "sequences",
    "rasi",
    "kitty",
    "btop.theme",
    "html",
)

_PROJECTION_BY_FORMAT: Mapping[str, Projection] = MappingProxyType(
    {
        "yaml": next(p for p in ALL_PROJECTIONS if p.name == "yaml"),
        "conf": next(p for p in ALL_PROJECTIONS if p.name == "conf"),
        "gtk.css": next(p for p in ALL_PROJECTIONS if p.name == "gtk"),
        "adw.css": next(p for p in ALL_PROJECTIONS if p.name == "adw"),
        "sequences": next(p for p in ALL_PROJECTIONS if p.name == "sequences"),
        "rasi": next(p for p in ALL_PROJECTIONS if p.name == "rasi"),
        "kitty": next(p for p in ALL_PROJECTIONS if p.name == "kitty"),
        "btop.theme": next(p for p in ALL_PROJECTIONS if p.name == "btop"),
        "html": next(p for p in ALL_PROJECTIONS if p.name == "html"),
    }
)


_FORMAT_BY_PROJECTION_NAME: Mapping[str, str] = MappingProxyType(
    {projection.name: name for name, projection in _PROJECTION_BY_FORMAT.items()}
)


def known_format_names() -> tuple[str, ...]:
    """Return every accepted ``--format``/default-format value."""
    return FORMAT_NAMES


def default_format_names() -> tuple[str, ...]:
    """Return the formats used when settings define none.

    The default is every non-dev projection; ``theme.json`` is written
    unconditionally by the processor and is not repeated here.
    """
    return tuple(
        _FORMAT_BY_PROJECTION_NAME[projection.name]
        for projection in RUNTIME_PROJECTIONS
        if projection.name in _FORMAT_BY_PROJECTION_NAME
    )


def projections_for_formats(formats: Iterable[str]) -> tuple[Projection, ...]:
    """Resolve consumer format names to projection records.

    ``json`` contributes no projection (``theme.json`` is always written).
    Unknown names raise :class:`UnknownFormatError` naming the accepted values.
    Duplicate names are collapsed while preserving the caller's order.
    """
    selected: list[Projection] = []
    seen: set[str] = set()
    for raw in formats:
        name = str(raw).strip()
        if name == "json":
            continue
        try:
            projection = _PROJECTION_BY_FORMAT[name]
        except KeyError:
            known = ", ".join(FORMAT_NAMES)
            raise UnknownFormatError(
                f"unknown output format {name!r}; known formats: {known}"
            ) from None
        if projection.name in seen:
            continue
        seen.add(projection.name)
        selected.append(projection)
    return tuple(selected)


@dataclass(frozen=True, slots=True)
class ModeProjectionContext:
    """One mode's ordered projection rows.

    Instances are built for both modes so the dev-only HTML preview can render
    them side by side without templates reaching into the domain model.
    """

    mode: Mode
    mode_name: str
    vocabulary: tuple[tuple[str, Color], ...]
    roles: tuple[tuple[str, Color], ...]
    extra_roles: tuple[tuple[str, Color], ...]
    legacy: tuple[tuple[str, Color], ...]
    palettes: tuple[tuple[str, tuple[tuple[int, Color], ...]], ...]
    btop: tuple[BtopRow, ...]


@dataclass(frozen=True, slots=True)
class ProjectionContext:
    """Typed view of everything a projection template may consume.

    ``mode``/``roles``/``palettes``/... describe the selected projection mode;
    ``modes`` always carries both modes, dark first, for the HTML preview.
    """

    theme: Theme
    mode: Mode
    mode_name: str
    scheme: str
    contrast: float
    source: Mapping[str, Any]
    generator: Mapping[str, Any]
    vocabulary: tuple[tuple[str, Color], ...]
    roles: tuple[tuple[str, Color], ...]
    extra_roles: tuple[tuple[str, Color], ...]
    legacy: tuple[tuple[str, Color], ...]
    palettes: tuple[tuple[str, tuple[tuple[int, Color], ...]], ...]
    btop: tuple[BtopRow, ...]
    modes: tuple[ModeProjectionContext, ...]

    def as_jinja_context(self) -> dict[str, Any]:
        """Return the mapping passed to Jinja.

        ``role_names`` and ``vocabulary_names`` keep duplicate suppression in
        templates declarative when a vocabulary alias shares a role name.
        """
        vocabulary_names = frozenset(name for name, _color in self.vocabulary)
        return {
            "theme": self.theme,
            "mode": self.mode,
            "mode_name": self.mode_name,
            "scheme": self.scheme,
            "contrast": self.contrast,
            "source": self.source,
            "generator": self.generator,
            "vocabulary": dict(self.vocabulary),
            "vocabulary_names": vocabulary_names,
            "roles": dict(self.roles),
            "role_rows": self.roles,
            "extra_roles": self.extra_roles,
            "legacy": dict(self.legacy),
            "legacy_rows": self.legacy,
            "palettes": self.palettes,
            "btop": self.btop,
            "modes": self.modes,
        }


def build_mode_context(mode: Mode) -> ModeProjectionContext:
    """Build one mode's deterministic rows for the projection templates."""
    alias_service = AliasService()

    vocabulary = tuple((name, mode.roles[role]) for name, role in PROJECTION_VOCABULARY.items())
    roles = tuple((role.value, mode.roles[role]) for role in MaterialRole)
    extra_roles = tuple((name, color) for name, color in roles if name not in PROJECTION_VOCABULARY)
    legacy = tuple(
        (f"color{index}", mode.roles[alias_service.resolve(f"color{index}")])
        for index in range(LEGACY_ALIAS_COUNT)
    )
    palettes = tuple(
        (
            palette_name.value,
            tuple((tone, mode.palettes[palette_name].tones[tone]) for tone in TONE_ORDER),
        )
        for palette_name in PaletteName
    )

    return ModeProjectionContext(
        mode=mode,
        mode_name=mode.mode.value,
        vocabulary=vocabulary,
        roles=roles,
        extra_roles=extra_roles,
        legacy=legacy,
        palettes=palettes,
        btop=build_btop_rows(mode),
    )


def build_projection_context(
    theme: Theme,
    mode: ModeName | str = ModeName.DARK,
) -> ProjectionContext:
    """Build the deterministic context for the selected projection ``mode``."""
    mode_name = ModeName(mode)
    selected = theme.dark if mode_name is ModeName.DARK else theme.light
    view = build_mode_context(selected)
    modes = tuple(build_mode_context(candidate) for candidate in (theme.dark, theme.light))

    return ProjectionContext(
        theme=theme,
        mode=selected,
        mode_name=selected.mode.value,
        scheme=theme.scheme,
        contrast=theme.contrast,
        source=theme.source.to_dict(),
        generator=theme.generator.to_dict(),
        vocabulary=view.vocabulary,
        roles=view.roles,
        extra_roles=view.extra_roles,
        legacy=view.legacy,
        palettes=view.palettes,
        btop=view.btop,
        modes=modes,
    )


class TemplateProjection:
    """A registered projection bound to the Jinja renderer.

    This is the concrete :class:`~theme_producer.ports.ProjectionPort`
    implementation: one metadata record plus a pure ``Theme -> file`` render.
    """

    def __init__(self, projection: Projection, renderer: JinjaThemeRenderer) -> None:
        self._projection = projection
        self._renderer = renderer

    @property
    def metadata(self) -> Projection:
        """The static projection record."""
        return self._projection

    def render(
        self,
        theme: Theme,
        output_dir: Path,
        mode: ModeName | str = ModeName.DARK,
    ) -> Path:
        """Render this projection into ``output_dir`` and return its path."""
        context = build_projection_context(theme, mode=mode)
        return self._renderer.render(
            self._projection.template,
            context.as_jinja_context(),
            Path(output_dir),
        )


class ProjectionRegistry:
    """Render the shipped projection catalog from one Theme."""

    def __init__(
        self,
        *,
        templates_dir: Path | None = None,
        renderer: JinjaThemeRenderer | None = None,
        catalog_loader: TemplateCatalogLoader | None = None,
    ) -> None:
        self._templates_dir = Path(templates_dir) if templates_dir is not None else None
        self._renderer = renderer or JinjaThemeRenderer(templates_dir=self._templates_dir)
        self._catalog_loader = catalog_loader or TemplateCatalogLoader()
        self._catalog: TemplateCatalog | None = None
        self._projection_renderers: dict[str, ProjectionPort] = {
            projection.name: TemplateProjection(projection, self._renderer)
            for projection in OPEN_PROJECTIONS
        }
        for projection in FIXED_PROJECTIONS:
            postprocess = sequences_postprocess if projection == SEQUENCES_PROJECTION else None
            self._projection_renderers[projection.name] = AnsiProjection(
                projection,
                self._renderer,
                postprocess=postprocess,
            )

    @property
    def projections(self) -> tuple[Projection, ...]:
        """All shipped projections, including dev-only previews."""
        return ALL_PROJECTIONS

    @property
    def runtime_projections(self) -> tuple[Projection, ...]:
        """Shipped projections that are part of the runtime artifact contract."""
        return RUNTIME_PROJECTIONS

    def catalog(self) -> TemplateCatalog:
        """Validate and return the 1:1 template catalog for every projection."""
        if self._catalog is None:
            self._catalog = self._catalog_loader.load(
                (projection.template for projection in ALL_PROJECTIONS),
                explicit_dir=self._templates_dir,
            )
        return self._catalog

    def _resolve(self, projection: Projection | str) -> Projection:
        if isinstance(projection, Projection):
            if projection not in ALL_PROJECTIONS:
                raise KeyError(f"projection {projection.name!r} is not registered")
            return projection
        for candidate in ALL_PROJECTIONS:
            if candidate.name == projection:
                return candidate
        known = ", ".join(item.name for item in ALL_PROJECTIONS)
        raise KeyError(f"unknown projection {projection!r}; known projections: {known}")

    def renderer_for(self, projection: Projection | str) -> ProjectionPort:
        """Return the ``ProjectionPort`` implementation for one projection."""
        resolved = self._resolve(projection)
        return self._projection_renderers[resolved.name]

    def render(
        self,
        projection: Projection | str,
        theme: Theme,
        output_dir: Path,
        mode: ModeName | str = ModeName.DARK,
    ) -> Path:
        """Render one projection into ``output_dir`` using ``mode``."""
        self.catalog()
        return self.renderer_for(projection).render(theme, Path(output_dir), mode=mode)

    def _render_many(
        self,
        projections: Iterable[Projection],
        theme: Theme,
        output_dir: Path,
        mode: ModeName | str = ModeName.DARK,
    ) -> dict[str, Path]:
        self.catalog()
        rendered: dict[str, Path] = {}
        for projection in projections:
            rendered[projection.filename] = self._projection_renderers[projection.name].render(
                theme, Path(output_dir), mode=mode
            )
        return rendered

    def render_all(
        self,
        theme: Theme,
        output_dir: Path,
        mode: ModeName | str = ModeName.DARK,
    ) -> dict[str, Path]:
        """Render every shipped projection, including dev-only previews."""
        return self._render_many(ALL_PROJECTIONS, theme, output_dir, mode=mode)

    def render_runtime(
        self,
        theme: Theme,
        output_dir: Path,
        mode: ModeName | str = ModeName.DARK,
    ) -> dict[str, Path]:
        """Render the runtime projections only (no dev preview)."""
        return self._render_many(RUNTIME_PROJECTIONS, theme, output_dir, mode=mode)
