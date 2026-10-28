"""Pure, immutable Theme domain objects and their canonical JSON shape.

The domain has no I/O: every object validates at construction time and the
only serialization entry points are :meth:`Theme.to_dict` and
:meth:`Theme.from_dict`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar

from theme_producer.domain.enums import (
    TONE_ORDER,
    TONES,
    MaterialRole,
    ModeName,
    PaletteName,
    SourceKind,
)
from theme_producer.domain.exceptions import ThemeValidationError

__all__ = [
    "SCHEMA_VERSION",
    "Color",
    "GeneratorMetadata",
    "Mode",
    "Source",
    "Theme",
    "TonalPalette",
]

SCHEMA_VERSION = "1"

_HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ThemeValidationError(f"{field_name} must be a non-empty string; got {value!r}")
    return value


def _require_mapping(value: object, field_name: str) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping):
        raise ThemeValidationError(f"{field_name} must be a mapping; got {type(value).__name__}")
    return value


def _normalize_rgb(rgb: object) -> tuple[int, int, int]:
    if not isinstance(rgb, tuple | list) or len(rgb) != 3:
        raise ThemeValidationError(f"Color rgb must be a 3-tuple of numbers; got {rgb!r}")
    channels: list[int] = []
    for component in rgb:
        if isinstance(component, bool) or not isinstance(component, int | float):
            raise ThemeValidationError(f"Color rgb components must be numbers; got {component!r}")
        number = float(component)
        if not math.isfinite(number):
            raise ThemeValidationError(f"Color rgb components must be finite; got {component!r}")
        channels.append(max(0, min(255, round(number))))
    return (channels[0], channels[1], channels[2])


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))


def _normalize_contrast(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ThemeValidationError(f"contrast must be a number; got {value!r}")
    contrast = float(value)
    if not math.isfinite(contrast):
        raise ThemeValidationError(f"contrast must be finite; got {value!r}")
    if not -1.0 <= contrast <= 1.0:
        raise ThemeValidationError(f"contrast must be within [-1, 1]; got {contrast!r}")
    return contrast


@dataclass(frozen=True, slots=True)
class Color:
    """An sRGB color stored as a canonical lowercase ``#rrggbb`` string.

    ``rgb`` is optional on construction: when omitted it is derived from
    ``hex``. When supplied it is rounded, clamped to 0..255, and the ``hex``
    field is resynchronized from the normalized channels.
    """

    hex: str
    rgb: tuple[int, int, int] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.hex, str) or not _HEX_PATTERN.fullmatch(self.hex):
            raise ThemeValidationError(
                f"Color hex must match ^#[0-9a-fA-F]{{6}}$; got {self.hex!r}"
            )
        rgb = _hex_to_rgb(self.hex) if self.rgb is None else _normalize_rgb(self.rgb)
        object.__setattr__(self, "rgb", rgb)
        object.__setattr__(self, "hex", _rgb_to_hex(rgb))

    @classmethod
    def from_hex(cls, value: str) -> Color:
        """Build a Color from a ``#rrggbb`` string."""
        return cls(hex=value)

    @classmethod
    def from_rgb(cls, r: int | float, g: int | float, b: int | float) -> Color:
        """Build a Color from three channels, rounding/clamping as needed."""
        rgb = _normalize_rgb((r, g, b))
        return cls(hex=_rgb_to_hex(rgb), rgb=rgb)

    def to_dict(self) -> str:
        """Return the canonical lowercase hex string."""
        return self.hex


@dataclass(frozen=True, slots=True)
class Source:
    """Where a Theme's seed came from."""

    kind: SourceKind | str
    path: str | None = None
    hash: str | None = None

    def __post_init__(self) -> None:
        try:
            kind = SourceKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ThemeValidationError(
                f"source kind must be one of {[item.value for item in SourceKind]}; "
                f"got {self.kind!r}"
            ) from exc
        object.__setattr__(self, "kind", kind)
        if self.path is not None:
            _require_non_empty_string(self.path, "source path")
        if self.hash is not None:
            _require_non_empty_string(self.hash, "source hash")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Source:
        data = _require_mapping(payload, "source")
        return cls(kind=data.get("kind"), path=data.get("path"), hash=data.get("hash"))

    def to_dict(self) -> dict[str, str | None]:
        return {"kind": self.kind.value, "path": self.path, "hash": self.hash}


@dataclass(frozen=True, slots=True)
class GeneratorMetadata:
    """Identity of the engine that produced a Theme."""

    engine: str
    engine_version: str
    schema_version: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.engine, "generator engine")
        _require_non_empty_string(self.engine_version, "generator engine_version")
        _require_non_empty_string(self.schema_version, "generator schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GeneratorMetadata:
        data = _require_mapping(payload, "generator")
        return cls(
            engine=_require_non_empty_string(data.get("engine"), "generator engine"),
            engine_version=_require_non_empty_string(
                data.get("engine_version"), "generator engine_version"
            ),
            schema_version=_require_non_empty_string(
                data.get("schema_version"), "generator schema_version"
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "engine": self.engine,
            "engine_version": self.engine_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class TonalPalette:
    """One Material tonal palette with exactly the 18 canonical tones."""

    name: PaletteName | str
    tones: Mapping[int, Color]

    def __post_init__(self) -> None:
        try:
            name = PaletteName(self.name)
        except (TypeError, ValueError) as exc:
            raise ThemeValidationError(
                f"palette name must be one of {[item.value for item in PaletteName]}; "
                f"got {self.name!r}"
            ) from exc
        object.__setattr__(self, "name", name)

        tones = _require_mapping(self.tones, "palette tones")
        normalized: dict[int, Color] = {}
        for tone, color in tones.items():
            if isinstance(tone, bool) or not isinstance(tone, int):
                raise ThemeValidationError(
                    f"{name.value} palette tone keys must be ints; got {tone!r}"
                )
            if not isinstance(color, Color):
                raise ThemeValidationError(
                    f"{name.value} palette tone {tone} must be a Color; got {color!r}"
                )
            normalized[tone] = color

        missing = sorted(TONES - normalized.keys())
        extra = sorted(normalized.keys() - TONES)
        if missing or extra:
            raise ThemeValidationError(
                f"{name.value} palette tones must be exactly the 18 canonical tones "
                f"{list(TONE_ORDER)}; missing={missing}, extra={extra}"
            )
        object.__setattr__(self, "tones", MappingProxyType(normalized))

    @classmethod
    def from_dict(cls, name: PaletteName | str, payload: Mapping[str, Any]) -> TonalPalette:
        data = _require_mapping(payload, f"{name} palette tones")
        tones: dict[int, Color] = {}
        for raw_tone, raw_color in data.items():
            try:
                tone = int(raw_tone)
            except (TypeError, ValueError) as exc:
                raise ThemeValidationError(
                    f"{name} palette tone key must be an integer; got {raw_tone!r}"
                ) from exc
            if tone in tones:
                raise ThemeValidationError(f"{name} palette contains duplicate tone {tone}")
            if not isinstance(raw_color, str):
                raise ThemeValidationError(
                    f"{name} palette tone {tone} must be a hex string; got {raw_color!r}"
                )
            tones[tone] = Color.from_hex(raw_color)
        return cls(name=name, tones=tones)

    def to_dict(self) -> dict[str, str]:
        return {str(tone): self.tones[tone].hex for tone in TONE_ORDER}


@dataclass(frozen=True, slots=True)
class Mode:
    """One of the two modes: all 50 roles plus all six tonal palettes."""

    mode: ModeName | str
    roles: Mapping[MaterialRole, Color]
    palettes: Mapping[PaletteName, TonalPalette]

    def __post_init__(self) -> None:
        try:
            mode = ModeName(self.mode)
        except (TypeError, ValueError) as exc:
            raise ThemeValidationError(
                f"mode must be 'dark' or 'light'; got {self.mode!r}"
            ) from exc
        object.__setattr__(self, "mode", mode)

        roles = _require_mapping(self.roles, f"{mode.value} roles")
        normalized_roles: dict[MaterialRole, Color] = {}
        for raw_role, color in roles.items():
            try:
                role = MaterialRole(raw_role)
            except (TypeError, ValueError) as exc:
                raise ThemeValidationError(
                    f"{mode.value} mode has unknown Material role {raw_role!r}"
                ) from exc
            if not isinstance(color, Color):
                raise ThemeValidationError(
                    f"{mode.value} role {role.value} must be a Color; got {color!r}"
                )
            normalized_roles[role] = color

        missing_roles = [role.value for role in MaterialRole if role not in normalized_roles]
        if missing_roles:
            raise ThemeValidationError(
                f"{mode.value} mode is missing Material roles: {missing_roles}"
            )
        if len(normalized_roles) != len(MaterialRole):
            raise ThemeValidationError(
                f"{mode.value} mode must contain exactly {len(MaterialRole)} roles; "
                f"got {len(normalized_roles)}"
            )

        palettes = _require_mapping(self.palettes, f"{mode.value} palettes")
        normalized_palettes: dict[PaletteName, TonalPalette] = {}
        for raw_palette, palette in palettes.items():
            try:
                palette_name = PaletteName(raw_palette)
            except (TypeError, ValueError) as exc:
                raise ThemeValidationError(
                    f"{mode.value} mode has unknown palette {raw_palette!r}"
                ) from exc
            if not isinstance(palette, TonalPalette):
                raise ThemeValidationError(
                    f"{mode.value} palette {palette_name.value} must be a TonalPalette; "
                    f"got {palette!r}"
                )
            if palette.name != palette_name:
                raise ThemeValidationError(
                    f"{mode.value} palette {palette_name.value} carries mismatched "
                    f"TonalPalette name {palette.name.value!r}"
                )
            normalized_palettes[palette_name] = palette

        missing_palettes = [
            palette.value for palette in PaletteName if palette not in normalized_palettes
        ]
        if missing_palettes or len(normalized_palettes) != len(PaletteName):
            raise ThemeValidationError(
                f"{mode.value} mode must contain exactly {len(PaletteName)} palettes "
                f"{[item.value for item in PaletteName]}; missing={missing_palettes}, "
                f"got={len(normalized_palettes)}"
            )

        object.__setattr__(self, "roles", MappingProxyType(normalized_roles))
        object.__setattr__(self, "palettes", MappingProxyType(normalized_palettes))

    @classmethod
    def from_dict(cls, mode: ModeName | str, payload: Mapping[str, Any]) -> Mode:
        data = _require_mapping(payload, f"{mode} mode")
        roles_payload = _require_mapping(data.get("roles"), f"{mode} mode roles")
        palettes_payload = _require_mapping(data.get("palettes"), f"{mode} mode palettes")

        roles: dict[MaterialRole, Color] = {}
        for raw_role, raw_color in roles_payload.items():
            try:
                role = MaterialRole(raw_role)
            except (TypeError, ValueError) as exc:
                raise ThemeValidationError(
                    f"{mode} mode has unknown Material role {raw_role!r}"
                ) from exc
            if not isinstance(raw_color, str):
                raise ThemeValidationError(
                    f"{mode} role {role.value} must be a hex string; got {raw_color!r}"
                )
            roles[role] = Color.from_hex(raw_color)

        palettes: dict[PaletteName, TonalPalette] = {}
        for raw_palette, raw_tones in palettes_payload.items():
            try:
                palette_name = PaletteName(raw_palette)
            except (TypeError, ValueError) as exc:
                raise ThemeValidationError(
                    f"{mode} mode has unknown palette {raw_palette!r}"
                ) from exc
            palettes[palette_name] = TonalPalette.from_dict(palette_name, raw_tones)

        return cls(mode=mode, roles=roles, palettes=palettes)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            "roles": {role.value: self.roles[role].hex for role in MaterialRole},
            "palettes": {name.value: self.palettes[name].to_dict() for name in PaletteName},
        }


@dataclass(frozen=True, slots=True)
class Theme:
    """Root domain object: source identity plus dark and light modes."""

    source: Source
    scheme: str
    contrast: float
    dark: Mode
    light: Mode
    generator: GeneratorMetadata

    SCHEMA_VERSION: ClassVar[str] = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.source, Source):
            raise ThemeValidationError(f"theme source must be a Source; got {self.source!r}")
        if not isinstance(self.generator, GeneratorMetadata):
            raise ThemeValidationError(
                f"theme generator must be GeneratorMetadata; got {self.generator!r}"
            )
        _require_non_empty_string(self.scheme, "scheme")
        object.__setattr__(self, "contrast", _normalize_contrast(self.contrast))

        if not isinstance(self.dark, Mode) or self.dark.mode != ModeName.DARK:
            raise ThemeValidationError("theme dark must be a Mode with mode='dark'")
        if not isinstance(self.light, Mode) or self.light.mode != ModeName.LIGHT:
            raise ThemeValidationError("theme light must be a Mode with mode='light'")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Theme:
        """Validate the canonical ``theme.json`` shape into a Theme."""
        data = _require_mapping(payload, "theme")
        schema_version = data.get("schema_version")
        if schema_version != SCHEMA_VERSION:
            raise ThemeValidationError(
                f"unsupported theme schema_version {schema_version!r}; expected {SCHEMA_VERSION!r}"
            )

        modes = _require_mapping(data.get("modes"), "theme modes")
        return cls(
            source=Source.from_dict(_require_mapping(data.get("source"), "theme source")),
            scheme=_require_non_empty_string(data.get("scheme"), "scheme"),
            contrast=_normalize_contrast(data.get("contrast")),
            dark=Mode.from_dict(ModeName.DARK, _require_mapping(modes.get("dark"), "dark mode")),
            light=Mode.from_dict(
                ModeName.LIGHT, _require_mapping(modes.get("light"), "light mode")
            ),
            generator=GeneratorMetadata.from_dict(
                _require_mapping(data.get("generator"), "theme generator")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical, JSON-serializable ``theme.json`` shape."""
        return {
            "schema_version": SCHEMA_VERSION,
            "generator": self.generator.to_dict(),
            "source": self.source.to_dict(),
            "scheme": self.scheme,
            "contrast": self.contrast,
            "modes": {
                "dark": self.dark.to_dict(),
                "light": self.light.to_dict(),
            },
        }
