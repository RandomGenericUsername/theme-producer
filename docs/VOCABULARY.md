# Vocabulary — engine roles and the produced `on_backdrop`

`theme.json` carries two vocabularies:

- **Engine roles** — exactly the 50 Material 3 roles matugen 4.2.0 and the
  native helper emit. `MaterialRole` and the canonical `theme.json` schema pin
  this set; it never grows because a consumer wants another name.
- **Produced roles** — roles `tpr` derives from the source image *after* the
  engine returns. There is exactly one today: `on_backdrop`.

Produced roles live beside `roles` and `palettes` on each mode
(`modes.dark.on_backdrop`, `modes.light.on_backdrop`), not inside `roles`, so
the engine-role count stays 50. The additive schema version is `1.1`.

## Engine roles (50)

```text
background                    on_secondary                  primary_container             surface_container_high
error                         on_secondary_container        primary_fixed                 surface_container_highest
error_container               on_secondary_fixed            primary_fixed_dim             surface_container_low
inverse_on_surface            on_secondary_fixed_variant    scrim                         surface_container_lowest
inverse_primary               on_surface                    secondary                     surface_dim
inverse_surface               on_surface_variant            secondary_container           surface_tint
on_background                 on_tertiary                   secondary_fixed               surface_variant
on_error                      on_tertiary_container         secondary_fixed_dim           tertiary
on_error_container            on_tertiary_fixed             shadow                        tertiary_container
on_primary                    on_tertiary_fixed_variant     source_color                  tertiary_fixed
on_primary_container          outline                       surface                       tertiary_fixed_dim
on_primary_fixed              outline_variant               surface_bright
on_primary_fixed_variant      primary                       surface_container
```

## Produced role: `on_backdrop`

`on_backdrop` answers one question: **what existing theme color reads over the
wallpaper's top bar band?** It replaces the runtime icon-contrast guard, which
used to answer the same question at the consumer layer.

### Band measurement

- Band = the top `min(48, image height)` rows of the source image. `48` is the
  documented bar-band constant (`icon_contrast_sampler.band_px` in the dotfiles
  runtime).
- The band is resized to at most `64` pixels wide (and at most 64 tall) with
  Pillow's default resize filter, then averaged per pixel.
- The average is the mean WCAG 2.1 relative luminance: sRGB linearization
  (`c / 12.92` below `0.04045`, otherwise `((c + 0.055) / 1.055) ** 2.4`) and
  Rec.709 weights `0.2126, 0.7152, 0.0722`. The formula is shared with
  `adapters/image_metrics.py` and `domain/color_metrics.py`.

### Selection

Candidates are the mode's neutral-pole roles only, never a random hue:

```text
on_surface, on_surface_variant, on_background, inverse_on_surface,
inverse_surface, outline, outline_variant, surface, surface_dim,
surface_container_lowest
```

The candidate with the highest WCAG contrast ratio
`(L1 + 0.05) / (L2 + 0.05)` against the band luminance wins. Candidates are
tested in the order above, so an exact tie keeps the earlier candidate;
`on_surface` therefore wins every tie. The result is **best effort**: when
every candidate is below the WCAG 4.5 body-text threshold, the maximum-contrast
candidate is still returned. A theme color cannot beat a pathological band
without inventing a color, which is out of scope.

### Properties

- **Per mode.** `dark` and `light` are selected independently from their own
  role sets.
- **May leave the ink family.** `on_backdrop` can intentionally sit on the
  opposite luminance pole from `on_surface` when the wallpaper band disagrees
  with the scheme (dark scheme over a bright band, light scheme over a dark
  band). That is the role's purpose, not a bug.
- **Engine-independent.** The producer measures and selects on the host after
  the engine output, so `matugen` and `native` produce the same
  `on_backdrop` for the same image.
- **No image source.** A seed-color or imported-JSON theme has no band to
  measure: `on_backdrop = on_surface`. An image that cannot be decoded also
  keeps this fallback.
- **Projections.** Every named-token projection emits it: `theme.json` (both
  modes), `colors.yaml`, `colors.gtk.css`, `colors.adw.css`, `colors.rasi`, and
  `colors.conf`. ANSI/kitty/sequences/btop have no slot for it and are
  byte-identical.

Evidence: `src/theme_producer/domain/on_backdrop.py`,
`src/theme_producer/adapters/image_metrics.py`,
`src/theme_producer/adapters/on_backdrop.py`,
`dotfiles-runtime/src/runtime/adapters/icon_contrast_sampler.py:20-52`.

Verify: `uv run tpr generate <image> --format json`, then inspect
`theme.json.modes.dark.on_backdrop` and `theme.json.modes.light.on_backdrop`.
