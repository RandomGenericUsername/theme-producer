"""Fixed ANSI projections: kitty and OSC sequences.

Both projections are rendered from the same :func:`theme_producer.domain.ansi.ansi_palette`
table. The sequences artifact additionally applies CSG's documented binary
post-processing (``]`` -> ESC ``]`` and ``\\`` -> ESC ``\\``), so the final
artifact is a stream of OSC 4/10/11/12 sequences. Only this adapter transforms
bytes; every other projection keeps the renderer's text output unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from theme_producer.adapters.jinja_renderer import JinjaThemeRenderer
from theme_producer.domain.ansi import ansi_palette
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Theme
from theme_producer.ports.projection import Projection

__all__ = [
    "ANSI_PROJECTIONS",
    "KITTY_PROJECTION",
    "SEQUENCES_PROJECTION",
    "AnsiProjection",
    "build_ansi_context",
    "sequences_postprocess",
]

#: Terminal chrome is semantic, not positional. ``background``,
#: ``foreground``, ``cursor``, and selection are resolved directly from the
#: selected mode's Material roles. Never derive these keys from an ANSI slot
#: index: slot roles can change independently (REQ-024 moved slot 15 to
#: ``on_surface_variant``, which regressed foreground/cursor in REQ-025).

KITTY_PROJECTION = Projection(
    name="kitty",
    filename="colors.kitty",
    capability="fixed",
    template="colors.kitty.j2",
)

SEQUENCES_PROJECTION = Projection(
    name="sequences",
    filename="colors.sequences",
    capability="fixed",
    template="colors.sequences.j2",
)

#: The fixed ANSI projections. Keeping them separate from the open catalog
#: preserves the open projections' contract while both sets share one registry.
ANSI_PROJECTIONS: tuple[Projection, ...] = (KITTY_PROJECTION, SEQUENCES_PROJECTION)


def build_ansi_context(
    theme: Theme,
    mode: ModeName | str = ModeName.DARK,
) -> Mapping[str, Any]:
    """Build the template context from the selected mode's ANSI table and roles."""
    mode_name = ModeName(mode)
    selected = theme.dark if mode_name is ModeName.DARK else theme.light
    colors = ansi_palette(theme, mode_name)
    return {
        "colors": colors,
        "background": selected.roles[MaterialRole.SURFACE],
        "foreground": selected.roles[MaterialRole.ON_SURFACE],
        "cursor": selected.roles[MaterialRole.ON_SURFACE],
        "selection_background": selected.roles[MaterialRole.SURFACE],
        "selection_foreground": selected.roles[MaterialRole.ON_SURFACE],
    }


def sequences_postprocess(rendered: str) -> bytes:
    """Turn the OSC template into CSG-compatible terminal bytes.

    The template writes ``]4;N;<hex>\\`` lines; this transformation prepends ESC
    to every OSC introducer and replaces the template's literal ``\\`` terminator
    with ST (ESC ``\\``). Newlines are preserved.
    """
    return rendered.replace("]", "\x1b]").replace("\\", "\x1b\\").encode("utf-8")


class AnsiProjection:
    """A fixed ANSI projection bound to the shared Jinja renderer."""

    def __init__(
        self,
        projection: Projection,
        renderer: JinjaThemeRenderer,
        *,
        postprocess: Callable[[str], bytes] | None = None,
    ) -> None:
        self._projection = projection
        self._renderer = renderer
        self._postprocess = postprocess

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
        """Render this ANSI projection into ``output_dir`` and return its path."""
        output = self._renderer.render(
            self._projection.template,
            build_ansi_context(theme, mode),
            Path(output_dir),
        )
        if self._postprocess is not None:
            output.write_bytes(self._postprocess(output.read_text(encoding="utf-8")))
        return output
