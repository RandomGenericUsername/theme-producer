"""btop theme capability table with a semantic component contract.

The 48 keys below are the documented btop theme key set. The mapping is
contract data, not template logic: the Jinja template only iterates the rows
produced here, so an accidental unknown key cannot reach ``colors.btop.theme``.

Every key belongs to one btop component and one semantic intent. Fixed chrome
and ink keys emit a Material role; gradient components resolve their three
stops from the Theme's existing tonal palettes. A contrast guard keeps every
visible graph stop at least :data:`MIN_GRAPH_CONTRAST` against its real btop
background (``meter_bg`` for graphs/meters, ``main_bg`` for process text).
Tonal variants are internal contrast anchors, never a public authoring model.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from theme_producer.domain.color_metrics import contrast_ratio, relative_luminance
from theme_producer.domain.enums import TONE_ORDER, TONES, MaterialRole, ModeName, PaletteName
from theme_producer.domain.models import Color, Mode

__all__ = [
    "BTOP_GRADIENTS",
    "BTOP_KEY_ROLES",
    "BTOP_KEY_SPECS",
    "BTOP_KEYS",
    "BtopComponent",
    "BtopGradient",
    "BtopGradientStop",
    "BtopIntent",
    "BtopKeySpec",
    "BtopRow",
    "MIN_GRAPH_CONTRAST",
    "build_btop_rows",
]

#: Minimum WCAG contrast for a visible graph/meter stop.
MIN_GRAPH_CONTRAST = 3.0

#: Documented btop theme keys, in emission order. Exactly 48 entries.
BTOP_KEYS: tuple[str, ...] = (
    "main_bg",
    "main_fg",
    "title",
    "hi_fg",
    "selected_bg",
    "selected_fg",
    "inactive_fg",
    "graph_text",
    "meter_bg",
    "proc_misc",
    "cpu_box",
    "mem_box",
    "net_box",
    "proc_box",
    "div_line",
    "proc_pause_bg",
    "proc_follow_bg",
    "proc_banner_bg",
    "proc_banner_fg",
    "followed_bg",
    "followed_fg",
    "temp_start",
    "temp_mid",
    "temp_end",
    "cpu_start",
    "cpu_mid",
    "cpu_end",
    "free_start",
    "free_mid",
    "free_end",
    "cached_start",
    "cached_mid",
    "cached_end",
    "available_start",
    "available_mid",
    "available_end",
    "used_start",
    "used_mid",
    "used_end",
    "download_start",
    "download_mid",
    "download_end",
    "upload_start",
    "upload_mid",
    "upload_end",
    "process_start",
    "process_mid",
    "process_end",
)


class BtopComponent(StrEnum):
    """A btop surface or chart, independent of the raw theme keys."""

    GLOBAL_CHROME = "global.chrome"
    CPU_LOAD = "cpu.load"
    CPU_THERMAL_PRESSURE = "cpu.thermal_pressure"
    CPU_CHROME = "cpu.chrome"
    MEMORY_USED = "memory.used"
    MEMORY_CAPACITY = "memory.capacity"
    MEMORY_CACHED = "memory.cached"
    MEMORY_CHROME = "memory.chrome"
    NETWORK_DOWNLOAD = "network.download"
    NETWORK_UPLOAD = "network.upload"
    NETWORK_CHROME = "network.chrome"
    PROCESS_STATE = "process.state"
    PROCESS_CHROME = "process.chrome"


class BtopIntent(StrEnum):
    """What a btop component communicates to the user."""

    CHROME = "chrome"
    INK = "ink"
    EMPTY_METER = "empty_meter"
    DATA_INBOUND = "data_inbound"
    DATA_OUTBOUND = "data_outbound"
    COMPUTE_LOAD = "compute_load"
    THERMAL_PRESSURE = "thermal_pressure"
    USED_CAPACITY = "used_capacity"
    FREE_CAPACITY = "free_capacity"
    CACHED_CAPACITY = "cached_capacity"
    INTERACTION_STATE = "interaction_state"


@dataclass(frozen=True, slots=True)
class BtopKeySpec:
    """One documented key's component, intent, and resolution mode."""

    key: str
    component: BtopComponent
    intent: BtopIntent
    family: PaletteName
    role: MaterialRole | None = None

    @property
    def is_gradient(self) -> bool:
        """Whether this key resolves from tonal variants instead of a role."""
        return self.role is None


@dataclass(frozen=True, slots=True)
class BtopGradientStop:
    """One stop of a semantic gradient and its mode-aware tonal anchors."""

    key: str
    family: PaletteName
    dark_tone: int
    light_tone: int


@dataclass(frozen=True, slots=True)
class BtopGradient:
    """A three-stop semantic gradient and the background it must be visible on."""

    component: BtopComponent
    intent: BtopIntent
    background_key: str
    stops: tuple[BtopGradientStop, ...]


def _stop(key: str, family: PaletteName, dark_tone: int, light_tone: int) -> BtopGradientStop:
    return BtopGradientStop(
        key=key,
        family=family,
        dark_tone=dark_tone,
        light_tone=light_tone,
    )


#: Semantic gradients. The anchor order is mode-aware: dark mode ascends
#: (60 -> 80 -> 100) while light mode descends (40 -> 25 -> 10), so the end
#: stop is always the most prominent stop for its own background.
BTOP_GRADIENTS: tuple[BtopGradient, ...] = (
    BtopGradient(
        component=BtopComponent.NETWORK_DOWNLOAD,
        intent=BtopIntent.DATA_INBOUND,
        background_key="meter_bg",
        stops=(
            _stop("download_start", PaletteName.PRIMARY, 60, 40),
            _stop("download_mid", PaletteName.PRIMARY, 80, 25),
            _stop("download_end", PaletteName.PRIMARY, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.NETWORK_UPLOAD,
        intent=BtopIntent.DATA_OUTBOUND,
        background_key="meter_bg",
        stops=(
            _stop("upload_start", PaletteName.TERTIARY, 60, 40),
            _stop("upload_mid", PaletteName.TERTIARY, 80, 25),
            _stop("upload_end", PaletteName.TERTIARY, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.CPU_LOAD,
        intent=BtopIntent.COMPUTE_LOAD,
        background_key="meter_bg",
        stops=(
            _stop("cpu_start", PaletteName.PRIMARY, 60, 40),
            _stop("cpu_mid", PaletteName.PRIMARY, 80, 25),
            _stop("cpu_end", PaletteName.PRIMARY, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.CPU_THERMAL_PRESSURE,
        intent=BtopIntent.THERMAL_PRESSURE,
        background_key="meter_bg",
        stops=(
            _stop("temp_start", PaletteName.TERTIARY, 60, 40),
            _stop("temp_mid", PaletteName.TERTIARY, 80, 25),
            _stop("temp_end", PaletteName.ERROR, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.MEMORY_USED,
        intent=BtopIntent.USED_CAPACITY,
        background_key="meter_bg",
        stops=(
            _stop("used_start", PaletteName.SECONDARY, 60, 40),
            _stop("used_mid", PaletteName.TERTIARY, 80, 25),
            _stop("used_end", PaletteName.TERTIARY, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.MEMORY_CACHED,
        intent=BtopIntent.CACHED_CAPACITY,
        background_key="meter_bg",
        stops=(
            _stop("cached_start", PaletteName.SECONDARY, 60, 40),
            _stop("cached_mid", PaletteName.SECONDARY, 80, 25),
            _stop("cached_end", PaletteName.TERTIARY, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.MEMORY_CAPACITY,
        intent=BtopIntent.FREE_CAPACITY,
        background_key="meter_bg",
        stops=(
            _stop("free_start", PaletteName.NEUTRAL_VARIANT, 60, 40),
            _stop("free_mid", PaletteName.NEUTRAL_VARIANT, 80, 25),
            _stop("free_end", PaletteName.NEUTRAL_VARIANT, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.MEMORY_CAPACITY,
        intent=BtopIntent.FREE_CAPACITY,
        background_key="meter_bg",
        stops=(
            _stop("available_start", PaletteName.NEUTRAL_VARIANT, 60, 40),
            _stop("available_mid", PaletteName.NEUTRAL_VARIANT, 80, 25),
            _stop("available_end", PaletteName.NEUTRAL_VARIANT, 100, 10),
        ),
    ),
    BtopGradient(
        component=BtopComponent.PROCESS_STATE,
        intent=BtopIntent.INTERACTION_STATE,
        background_key="main_bg",
        stops=(
            _stop("process_start", PaletteName.PRIMARY, 30, 90),
            _stop("process_mid", PaletteName.SECONDARY, 30, 90),
            _stop("process_end", PaletteName.TERTIARY, 30, 90),
        ),
    ),
)


def _fixed(
    key: str,
    component: BtopComponent,
    intent: BtopIntent,
    family: PaletteName,
    role: MaterialRole,
) -> BtopKeySpec:
    return BtopKeySpec(
        key=key,
        component=component,
        intent=intent,
        family=family,
        role=role,
    )


_FIXED_KEY_SPECS: tuple[BtopKeySpec, ...] = (
    # Global chrome: surfaces, ink, selection and dividers.
    _fixed(
        "main_bg",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.CHROME,
        PaletteName.NEUTRAL,
        MaterialRole.SURFACE,
    ),
    _fixed(
        "main_fg",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.INK,
        PaletteName.NEUTRAL,
        MaterialRole.ON_SURFACE,
    ),
    _fixed(
        "title",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.CHROME,
        PaletteName.PRIMARY,
        MaterialRole.PRIMARY,
    ),
    _fixed(
        "hi_fg",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.INK,
        PaletteName.PRIMARY,
        MaterialRole.PRIMARY,
    ),
    _fixed(
        "selected_bg",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.INTERACTION_STATE,
        PaletteName.PRIMARY,
        MaterialRole.PRIMARY_CONTAINER,
    ),
    _fixed(
        "selected_fg",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.INK,
        PaletteName.PRIMARY,
        MaterialRole.ON_PRIMARY_CONTAINER,
    ),
    _fixed(
        "inactive_fg",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.INK,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.OUTLINE,
    ),
    _fixed(
        "graph_text",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.INK,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.ON_SURFACE_VARIANT,
    ),
    _fixed(
        "div_line",
        BtopComponent.GLOBAL_CHROME,
        BtopIntent.CHROME,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.OUTLINE_VARIANT,
    ),
    # Network chrome owns the shared empty-meter surface used by every graph.
    _fixed(
        "net_box",
        BtopComponent.NETWORK_CHROME,
        BtopIntent.CHROME,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.OUTLINE_VARIANT,
    ),
    _fixed(
        "meter_bg",
        BtopComponent.NETWORK_CHROME,
        BtopIntent.EMPTY_METER,
        PaletteName.NEUTRAL,
        MaterialRole.SURFACE_CONTAINER_HIGH,
    ),
    # Box borders.
    _fixed(
        "cpu_box",
        BtopComponent.CPU_CHROME,
        BtopIntent.CHROME,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.OUTLINE_VARIANT,
    ),
    _fixed(
        "mem_box",
        BtopComponent.MEMORY_CHROME,
        BtopIntent.CHROME,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.OUTLINE_VARIANT,
    ),
    _fixed(
        "proc_box",
        BtopComponent.PROCESS_CHROME,
        BtopIntent.CHROME,
        PaletteName.NEUTRAL_VARIANT,
        MaterialRole.OUTLINE_VARIANT,
    ),
    # Process interaction states. Containers are the documented intent; the
    # gradient stops above are guarded separately because btop paints them as
    # text over main_bg.
    _fixed(
        "proc_misc",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INK,
        PaletteName.SECONDARY,
        MaterialRole.SECONDARY,
    ),
    _fixed(
        "proc_pause_bg",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INTERACTION_STATE,
        PaletteName.SECONDARY,
        MaterialRole.SECONDARY_CONTAINER,
    ),
    _fixed(
        "proc_follow_bg",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INTERACTION_STATE,
        PaletteName.PRIMARY,
        MaterialRole.PRIMARY_CONTAINER,
    ),
    _fixed(
        "proc_banner_bg",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INTERACTION_STATE,
        PaletteName.TERTIARY,
        MaterialRole.TERTIARY_CONTAINER,
    ),
    _fixed(
        "proc_banner_fg",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INK,
        PaletteName.TERTIARY,
        MaterialRole.ON_TERTIARY_CONTAINER,
    ),
    _fixed(
        "followed_bg",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INTERACTION_STATE,
        PaletteName.PRIMARY,
        MaterialRole.PRIMARY_CONTAINER,
    ),
    _fixed(
        "followed_fg",
        BtopComponent.PROCESS_STATE,
        BtopIntent.INK,
        PaletteName.PRIMARY,
        MaterialRole.ON_PRIMARY_CONTAINER,
    ),
)


def _gradient_key_specs() -> tuple[BtopKeySpec, ...]:
    return tuple(
        BtopKeySpec(
            key=stop.key,
            component=gradient.component,
            intent=gradient.intent,
            family=stop.family,
        )
        for gradient in BTOP_GRADIENTS
        for stop in gradient.stops
    )


BTOP_KEY_SPECS: Mapping[str, BtopKeySpec] = MappingProxyType(
    {spec.key: spec for spec in (*_FIXED_KEY_SPECS, *_gradient_key_specs())}
)

#: Nominal Material role for every key, retained as a compatibility view.
#: Fixed keys emit this exact role; gradient keys emit a tonal variant from
#: the family and use the nominal role only for classification.
_FAMILY_NOMINAL_ROLE: Mapping[PaletteName, MaterialRole] = MappingProxyType(
    {
        PaletteName.PRIMARY: MaterialRole.PRIMARY,
        PaletteName.SECONDARY: MaterialRole.SECONDARY,
        PaletteName.TERTIARY: MaterialRole.TERTIARY,
        PaletteName.NEUTRAL: MaterialRole.SURFACE_CONTAINER,
        PaletteName.NEUTRAL_VARIANT: MaterialRole.OUTLINE_VARIANT,
        PaletteName.ERROR: MaterialRole.ERROR,
    }
)

BTOP_KEY_ROLES: Mapping[str, MaterialRole] = MappingProxyType(
    {
        key: spec.role if spec.role is not None else _FAMILY_NOMINAL_ROLE[spec.family]
        for key, spec in BTOP_KEY_SPECS.items()
    }
)


def _validate_contract() -> None:
    all_specs = (*_FIXED_KEY_SPECS, *_gradient_key_specs())
    if len(all_specs) != len({spec.key for spec in all_specs}):
        raise RuntimeError("btop semantic contract declares a key more than once")
    if set(BTOP_KEY_SPECS) != set(BTOP_KEYS):
        raise RuntimeError(
            "btop semantic contract drifted from the documented key set: "
            f"missing={sorted(set(BTOP_KEYS) - set(BTOP_KEY_SPECS))}, "
            f"unknown={sorted(set(BTOP_KEY_SPECS) - set(BTOP_KEYS))}"
        )
    for gradient in BTOP_GRADIENTS:
        if len(gradient.stops) != 3:
            raise RuntimeError(
                f"{gradient.component.value} must have exactly three stops, "
                f"got {len(gradient.stops)}"
            )
        if gradient.background_key not in BTOP_KEY_SPECS:
            raise RuntimeError(
                f"{gradient.component.value} background {gradient.background_key!r} is not a key"
            )
        background_spec = BTOP_KEY_SPECS[gradient.background_key]
        if background_spec.is_gradient:
            raise RuntimeError(
                f"{gradient.component.value} background {gradient.background_key!r} "
                "must be a fixed role, not a gradient"
            )
        for stop in gradient.stops:
            spec = BTOP_KEY_SPECS.get(stop.key)
            if spec is None:
                raise RuntimeError(f"gradient stop {stop.key!r} is not a documented key")
            if not spec.is_gradient:
                raise RuntimeError(f"gradient stop {stop.key!r} is declared as a fixed role")
            if spec.component is not gradient.component or spec.intent is not gradient.intent:
                raise RuntimeError(f"gradient stop {stop.key!r} has mismatched component/intent")
            if stop.dark_tone not in TONES or stop.light_tone not in TONES:
                raise RuntimeError(f"gradient stop {stop.key!r} uses a non-canonical tone")
    for key, spec in BTOP_KEY_SPECS.items():
        if spec.is_gradient:
            continue
        assert spec.role is not None
        if key not in BTOP_KEYS:  # pragma: no cover - covered by the set guard
            raise RuntimeError(f"fixed key {key!r} is not documented")


_validate_contract()


@dataclass(frozen=True, slots=True)
class BtopRow:
    """One emitted btop key and its resolved color plus semantic metadata."""

    key: str
    component: BtopComponent
    intent: BtopIntent
    family: PaletteName
    color: Color
    role: MaterialRole | None = None
    tone: int | None = None
    background_key: str | None = None
    contrast: float | None = None

    @property
    def is_gradient(self) -> bool:
        """Whether this row was resolved through a tonal gradient."""
        return self.tone is not None


def _resolve_gradient_stop(
    mode: Mode,
    stop: BtopGradientStop,
    background: Color,
    used_tones: set[int],
) -> tuple[Color, int, float]:
    """Pick a contrast-safe tone from the stop's own role family.

    The mode's anchor is the preferred tonal variant. When it fails the
    contrast guard, the nearest passing variant *in the same family* is used;
    the guard never crosses into another family. The returned contrast is
    measured against the stop's real btop background.
    """
    palette = mode.palettes[stop.family]
    background_luminance = relative_luminance(background)
    anchor = stop.dark_tone if mode.mode is ModeName.DARK else stop.light_tone

    scored: list[tuple[int, Color, float]] = []
    for tone in TONE_ORDER:
        color = palette.tones[tone]
        ratio = contrast_ratio(relative_luminance(color), background_luminance)
        scored.append((tone, color, ratio))

    passing = [entry for entry in scored if entry[2] >= MIN_GRAPH_CONTRAST]
    if not passing:
        # No variant in this family can reach the guard against this background.
        # Stay inside the family and use its most visible variant; the row keeps
        # the measured ratio so the caller can diagnose it.
        passing = [max(scored, key=lambda entry: (entry[2], -entry[0]))]

    available = [entry for entry in passing if entry[0] not in used_tones] or passing
    tone, color, ratio = min(available, key=lambda entry: (abs(entry[0] - anchor), entry[0]))
    return color, tone, ratio


def build_btop_rows(mode: Mode) -> tuple[BtopRow, ...]:
    """Resolve the semantic contract against one mode, in documented order."""
    rows: dict[str, BtopRow] = {}

    for spec in _FIXED_KEY_SPECS:
        assert spec.role is not None
        rows[spec.key] = BtopRow(
            key=spec.key,
            component=spec.component,
            intent=spec.intent,
            family=spec.family,
            color=mode.roles[spec.role],
            role=spec.role,
        )

    for gradient in BTOP_GRADIENTS:
        background = rows[gradient.background_key].color
        used_tones: set[int] = set()
        for stop in gradient.stops:
            color, tone, ratio = _resolve_gradient_stop(mode, stop, background, used_tones)
            used_tones.add(tone)
            rows[stop.key] = BtopRow(
                key=stop.key,
                component=gradient.component,
                intent=gradient.intent,
                family=stop.family,
                color=color,
                tone=tone,
                background_key=gradient.background_key,
                contrast=ratio,
            )

    return tuple(rows[key] for key in BTOP_KEYS)
