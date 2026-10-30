//! `tpr-native` — theme-producer's v2 color engine.
//!
//! Reads exactly one source (an image or a seed color), generates both Material
//! modes with the MIT/Apache-2.0 `material-colors` crate, and writes the
//! canonical `theme.json` shape to stdout. The Python adapter owns validation
//! and parses this output; this binary keeps the surface deliberately small.

use std::env;
use std::fs;
use std::panic;
use std::process::ExitCode;

use material_colors::color::{Argb, Lab};
use material_colors::dynamic_color::{DynamicScheme, Variant};
use material_colors::hct::Hct;
use material_colors::image::{AsPixels, FilterType, ImageReader};
use material_colors::palette::CorePalette;
use material_colors::quantize::{PointProvider, PointProviderLab, Quantizer, QuantizerCelebi};
use material_colors::scheme::Scheme;
use material_colors::score::Score;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};

const ENGINE_NAME: &str = "native";
const ENGINE_VERSION: &str = "0.1.0";
const SCHEMA_VERSION: &str = "1.1";
const DEFAULT_SCHEME: &str = "scheme-tonal-spot";
/// matugen 4.2.0 presents four ranked source-color candidates (`0..4`, i.e.
/// 0-3), so the native helper ranks the same number.
const CANDIDATE_COUNT: i32 = 4;
const TONES: [i32; 18] = [
    0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 95, 98, 99, 100,
];

const SCHEMES: [&str; 9] = [
    "scheme-tonal-spot",
    "scheme-content",
    "scheme-expressive",
    "scheme-fidelity",
    "scheme-fruit-salad",
    "scheme-monochrome",
    "scheme-neutral",
    "scheme-rainbow",
    "scheme-vibrant",
];

const USAGE: &str = "\
usage: tpr-native (--image <path> | --color <#rrggbb>)
                  [--scheme <scheme>] [--contrast <float>]
                  [--lightness-dark <float>] [--lightness-light <float>]
                  [--source-color-index <int>]
                  [--prefer <darkness|lightness|saturation|less-saturation|value|closest-to-fallback>]
                  [--fallback-color <#rrggbb>] [--json] [--version]

Image sources rank four candidate colors. `--prefer` picks one of them:
  darkness            lowest perceptual lightness (HCT tone)
  lightness           highest perceptual lightness (HCT tone)
  saturation          most colorful candidate (largest HSV max-min span)
  less-saturation     least chromatic candidate (lowest HCT chroma)
  value               lowest HSV value (matches matugen 4.2.0's oracle behavior)
  closest-to-fallback nearest candidate to --fallback-color in CIE Lab (CIE76)

Precedence: when `--prefer` is given it selects the source color and
`--source-color-index` is ignored. Without `--prefer`, `--source-color-index`
selects from the ranked candidates exactly as before (index 0 is the default).
`--fallback-color` is used when extraction yields no candidate color and as the
target for `closest-to-fallback`; that preference fails without it.

`--lightness-dark` moves the dark scheme's lightness: lightness 1 stays at 1,
lightness 0 moves to the argument, then the result is clamped. `--lightness-light`
does the light-scheme counterpart: lightness 0 stays at 0, lightness 1 moves to
1 + argument, then the result is clamped. Both default to 0 (no change), accept
[-1, 1] (out-of-range values are clamped), and apply to every scheme role except
`source_color`; tonal palettes are untouched. The lightness matugen transforms
was identified by oracle probing as the mean of the gamma-encoded sRGB channels
(HSI intensity, see `native/README.md`).";

/// How image source colors are chosen from the ranked candidate list.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Prefer {
    Darkness,
    Lightness,
    Saturation,
    LessSaturation,
    Value,
    ClosestToFallback,
}

impl Prefer {
    const NAMES: [&'static str; 6] = [
        "darkness",
        "lightness",
        "saturation",
        "less-saturation",
        "value",
        "closest-to-fallback",
    ];

    fn parse(raw: &str) -> Result<Self, String> {
        match raw {
            "darkness" => Ok(Self::Darkness),
            "lightness" => Ok(Self::Lightness),
            "saturation" => Ok(Self::Saturation),
            "less-saturation" => Ok(Self::LessSaturation),
            "value" => Ok(Self::Value),
            "closest-to-fallback" => Ok(Self::ClosestToFallback),
            other => Err(format!(
                "unknown --prefer {other:?}; expected one of: {}",
                Self::NAMES.join(", ")
            )),
        }
    }
}

#[derive(Debug)]
struct Options {
    image: Option<String>,
    color: Option<String>,
    scheme: String,
    contrast: f64,
    lightness_dark: f64,
    lightness_light: f64,
    source_color_index: usize,
    prefer: Option<Prefer>,
    fallback_color: Option<Argb>,
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("tpr-native: error: {message}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Result<(), String> {
    let options = parse_args(env::args().skip(1))?;
    let (source, source_value) = resolve_source(&options)?;
    let variant = variant_for(&options.scheme)?;

    let palette = CorePalette::of(source);
    let dark = Scheme::from(DynamicScheme::by_variant(
        source,
        &variant,
        true,
        Some(options.contrast),
    ));
    let light = Scheme::from(DynamicScheme::by_variant(
        source,
        &variant,
        false,
        Some(options.contrast),
    ));

    let payload = json!({
        "schema_version": SCHEMA_VERSION,
        "generator": {
            "engine": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "schema_version": SCHEMA_VERSION,
        },
        "source": source_value,
        "scheme": options.scheme,
        "contrast": options.contrast,
        "modes": {
            "dark": {
                "roles": roles(dark, source, options.lightness_dark, true),
                "palettes": palettes(&palette),
            },
            "light": {
                "roles": roles(light, source, options.lightness_light, false),
                "palettes": palettes(&palette),
            },
        },
    });

    let text = serde_json::to_string_pretty(&payload)
        .map_err(|error| format!("could not serialize theme: {error}"))?;
    println!("{text}");
    Ok(())
}

fn parse_args<I>(args: I) -> Result<Options, String>
where
    I: Iterator<Item = String>,
{
    let mut image = None;
    let mut color = None;
    let mut scheme = String::from(DEFAULT_SCHEME);
    let mut contrast = 0.0_f64;
    let mut lightness_dark = 0.0_f64;
    let mut lightness_light = 0.0_f64;
    let mut source_color_index = 0_usize;
    let mut prefer = None;
    let mut fallback_color = None;

    let mut args = args.peekable();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--version" | "-V" => {
                println!("{ENGINE_VERSION}");
                std::process::exit(0);
            }
            "--json" => {}
            "--image" => {
                if image.is_some() {
                    return Err("--image was provided more than once".into());
                }
                image = Some(take_value(&mut args, "--image")?);
            }
            "--color" => {
                if color.is_some() {
                    return Err("--color was provided more than once".into());
                }
                color = Some(take_value(&mut args, "--color")?);
            }
            "--scheme" => scheme = take_value(&mut args, "--scheme")?,
            "--contrast" => {
                let raw = take_value(&mut args, "--contrast")?;
                contrast = raw
                    .parse::<f64>()
                    .map_err(|_| format!("--contrast expects a number; got {raw:?}"))?;
                if !contrast.is_finite() || !(-1.0..=1.0).contains(&contrast) {
                    return Err(format!("--contrast must be within [-1, 1]; got {contrast}"));
                }
            }
            "--lightness-dark" => {
                let raw = take_value(&mut args, "--lightness-dark")?;
                lightness_dark = parse_lightness(&raw, "--lightness-dark")?;
            }
            "--lightness-light" => {
                let raw = take_value(&mut args, "--lightness-light")?;
                lightness_light = parse_lightness(&raw, "--lightness-light")?;
            }
            "--source-color-index" => {
                let raw = take_value(&mut args, "--source-color-index")?;
                source_color_index = raw.parse::<usize>().map_err(|_| {
                    format!("--source-color-index expects a non-negative int; got {raw:?}")
                })?;
            }
            "--prefer" => {
                let raw = take_value(&mut args, "--prefer")?;
                if prefer.is_some() {
                    return Err("--prefer was provided more than once".into());
                }
                prefer = Some(Prefer::parse(&raw)?);
            }
            "--fallback-color" => {
                let raw = take_value(&mut args, "--fallback-color")?;
                if fallback_color.is_some() {
                    return Err("--fallback-color was provided more than once".into());
                }
                fallback_color = Some(
                    parse_hex(&raw)
                        .map_err(|_| format!("--fallback-color expects #rrggbb; got {raw:?}"))?,
                );
            }
            "--help" | "-h" => {
                println!("{USAGE}");
                std::process::exit(0);
            }
            other => {
                return Err(format!("unknown argument {other:?}\n{USAGE}"));
            }
        }
    }

    if image.is_some() == color.is_some() {
        return Err(format!(
            "exactly one of --image or --color is required\n{USAGE}"
        ));
    }

    if prefer == Some(Prefer::ClosestToFallback) && fallback_color.is_none() {
        return Err("--prefer closest-to-fallback requires --fallback-color <#rrggbb>".to_string());
    }

    Ok(Options {
        image,
        color,
        scheme,
        contrast,
        lightness_dark,
        lightness_light,
        source_color_index,
        prefer,
        fallback_color,
    })
}

/// Parse a `--lightness-*` argument: a finite float clamped to [-1, 1].
fn parse_lightness(raw: &str, flag: &str) -> Result<f64, String> {
    let value = raw
        .parse::<f64>()
        .map_err(|_| format!("{flag} expects a number; got {raw:?}"))?;
    if !value.is_finite() {
        return Err(format!("{flag} expects a finite number; got {raw:?}"));
    }
    Ok(value.clamp(-1.0, 1.0))
}

fn take_value<I>(args: &mut std::iter::Peekable<I>, flag: &str) -> Result<String, String>
where
    I: Iterator<Item = String>,
{
    args.next()
        .ok_or_else(|| format!("{flag} requires a value\n{USAGE}"))
}

fn resolve_source(options: &Options) -> Result<(Argb, Value), String> {
    if let Some(path) = &options.image {
        return image_source(
            path,
            options.source_color_index,
            options.prefer,
            options.fallback_color,
        );
    }

    let raw = options
        .color
        .as_ref()
        .ok_or_else(|| "no source provided".to_string())?;
    color_source(raw)
}

fn color_source(raw: &str) -> Result<(Argb, Value), String> {
    let source = parse_hex(raw)?;
    Ok((
        source,
        json!({
            "kind": "color",
            "path": Value::Null,
            "hash": sha256_hex(raw.as_bytes()),
        }),
    ))
}

fn image_source(
    path: &str,
    source_color_index: usize,
    prefer: Option<Prefer>,
    fallback_color: Option<Argb>,
) -> Result<(Argb, Value), String> {
    let bytes =
        fs::read(path).map_err(|error| format!("could not read image {path:?}: {error}"))?;
    let hash = sha256_hex(&bytes);
    let resolved = fs::canonicalize(path).unwrap_or_else(|_| path.into());

    // `ImageReader::read` expects to decode valid image bytes and panics on a
    // corrupt payload; turn that into a clear process error instead.
    let decoded = panic::catch_unwind(|| ImageReader::read(bytes))
        .map_err(|_| format!("could not decode image {path:?}: not a supported image"))?;
    let mut image = decoded.map_err(|error| format!("could not decode image {path:?}: {error}"))?;
    // matugen 4.2.0 downscales to 112x112 with a triangle filter before
    // quantizing (probed with `--show-source-colors`: the candidate list is
    // resize-filter-invariant exactly at 112x112 and matches the crate's
    // `quantize` + `score` on that grid). Using the same grid keeps source-color
    // selection as close to the oracle as the shared crate allows.
    image.resize(112, 112, FilterType::Triangle);

    let pixels = image.as_pixels();
    let quantized = QuantizerCelebi::quantize(&pixels, 128);
    let ranked = Score::score(
        &quantized.color_to_count,
        Some(CANDIDATE_COUNT),
        fallback_color,
        None,
    );

    let source = match prefer {
        Some(preference) => select_preferred(&ranked, preference, fallback_color)?,
        None => {
            if ranked.is_empty() {
                // `Score::score` returns the fallback (Google Blue by default)
                // instead of an empty list, so this only guards a future change.
                fallback_color.unwrap_or_else(default_fallback)
            } else {
                ranked[source_color_index.min(ranked.len() - 1)]
            }
        }
    };

    Ok((
        source,
        json!({
            "kind": "image",
            "path": resolved.to_string_lossy(),
            "hash": hash,
        }),
    ))
}

/// Google Blue, the `material-colors` `Score` fallback.
const fn default_fallback() -> Argb {
    Argb::new(255, 66, 133, 244)
}

/// Pick one color from `ranked` according to `prefer`.
///
/// The metrics mirror matugen 4.2.0's observable behavior on the real-wallpaper
/// corpus (see `tests/contract/test_native_source_parity.py`):
///
/// * `darkness` — lowest HCT tone (perceptual lightness).
/// * `lightness` — highest HCT tone.
/// * `saturation` — largest HSV span (`max - min`); matugen's pick matches this
///   rather than normalized HSV saturation or HCT chroma on the corpus.
/// * `less-saturation` — smallest HCT chroma./// * `value` — lowest HSV value. matugen's `value` preference selects the
///   darkest candidate, not the brightest; we mirror the oracle.
/// * `closest-to-fallback` — nearest candidate in CIE Lab (CIE76). Probing every
///   observed pick over the corpus narrowed the metric to CIE76.
fn select_preferred(
    ranked: &[Argb],
    prefer: Prefer,
    fallback_color: Option<Argb>,
) -> Result<Argb, String> {
    if ranked.is_empty() {
        return fallback_color.ok_or_else(|| {
            "image produced no candidate colors and no --fallback-color was given".to_string()
        });
    }

    let first = ranked[0];
    let picked = match prefer {
        Prefer::Darkness => ranked.iter().copied().reduce(|best, color| {
            if hct_tone(color) < hct_tone(best) {
                color
            } else {
                best
            }
        }),
        Prefer::Lightness => ranked.iter().copied().reduce(|best, color| {
            if hct_tone(color) > hct_tone(best) {
                color
            } else {
                best
            }
        }),
        Prefer::Saturation => ranked.iter().copied().reduce(|best, color| {
            if hsv_span(color) > hsv_span(best) {
                color
            } else {
                best
            }
        }),
        Prefer::LessSaturation => ranked.iter().copied().reduce(|best, color| {
            if hct_chroma(color) < hct_chroma(best) {
                color
            } else {
                best
            }
        }),
        Prefer::Value => ranked.iter().copied().reduce(|best, color| {
            if hsv(color).2 < hsv(best).2 {
                color
            } else {
                best
            }
        }),
        Prefer::ClosestToFallback => {
            let target = fallback_color.ok_or_else(|| {
                "--prefer closest-to-fallback requires --fallback-color <#rrggbb>".to_string()
            })?;
            let target_lab: Lab = target.into();
            let mut best = first;
            let mut best_distance = lab_distance(best, &target_lab);
            for color in ranked.iter().copied().skip(1) {
                let distance = lab_distance(color, &target_lab);
                if distance < best_distance {
                    best = color;
                    best_distance = distance;
                }
            }
            Some(best)
        }
    };

    picked.ok_or_else(|| "image produced no candidate colors".to_string())
}

fn hct_tone(color: Argb) -> f64 {
    let hct: Hct = color.into();
    hct.get_tone()
}

/// HSV `max - min` span in 0..=255; the "colorfulness" matugen's saturation
/// preference ranks by.
fn hsv_span(color: Argb) -> u8 {
    let max = color.red.max(color.green).max(color.blue);
    let min = color.red.min(color.green).min(color.blue);
    max - min
}

fn hct_chroma(color: Argb) -> f64 {
    let hct: Hct = color.into();
    hct.get_chroma()
}

/// HSV as `(hue degrees, saturation, value)`.
fn hsv(color: Argb) -> (f64, f64, f64) {
    let (red, green, blue) = (
        f64::from(color.red) / 255.0,
        f64::from(color.green) / 255.0,
        f64::from(color.blue) / 255.0,
    );
    let max = red.max(green).max(blue);
    let min = red.min(green).min(blue);
    let delta = max - min;
    let hue = if delta == 0.0 {
        0.0
    } else if max == red {
        60.0 * (((green - blue) / delta) % 6.0)
    } else if max == green {
        60.0 * ((blue - red) / delta + 2.0)
    } else {
        60.0 * ((red - green) / delta + 4.0)
    };
    (hue, if max == 0.0 { 0.0 } else { delta / max }, max)
}

/// Squared CIE76 distance; `PointProviderLab` omits the square root because
/// only the ordering matters.
fn lab_distance(color: Argb, other: &Lab) -> f64 {
    let lab: Lab = color.into();
    PointProviderLab::distance(&lab, other)
}

fn parse_hex(raw: &str) -> Result<Argb, String> {
    let value = raw.strip_prefix('#').unwrap_or(raw);
    if value.len() != 6 || !value.chars().all(|character| character.is_ascii_hexdigit()) {
        return Err(format!("expected #rrggbb; got {raw:?}"));
    }
    let number =
        u32::from_str_radix(value, 16).map_err(|_| format!("expected #rrggbb; got {raw:?}"))?;
    Ok(Argb::from_u32(0xff00_0000 | number))
}

fn variant_for(scheme: &str) -> Result<Variant, String> {
    match scheme {
        "scheme-tonal-spot" => Ok(Variant::TonalSpot),
        "scheme-content" => Ok(Variant::Content),
        "scheme-expressive" => Ok(Variant::Expressive),
        "scheme-fidelity" => Ok(Variant::Fidelity),
        "scheme-fruit-salad" => Ok(Variant::FruitSalad),
        "scheme-monochrome" => Ok(Variant::Monochrome),
        "scheme-neutral" => Ok(Variant::Neutral),
        "scheme-rainbow" => Ok(Variant::Rainbow),
        "scheme-vibrant" => Ok(Variant::Vibrant),
        other => Err(format!(
            "unsupported scheme {other:?}; supported schemes: {}",
            SCHEMES.join(", ")
        )),
    }
}

fn roles(scheme: Scheme, source: Argb, lightness: f64, dark: bool) -> Value {
    let mut roles = Map::new();
    for (name, color) in scheme {
        let color = affine_lightness(color, lightness, dark);
        roles.insert(name, Value::String(hex(color)));
    }
    roles.insert("source_color".to_string(), Value::String(hex(source)));
    Value::Object(roles)
}

/// Apply matugen 4.2.0's per-mode lightness transform to one scheme role.
///
/// The lightness it transforms was identified by oracle probing (all 50 roles,
/// five seeds, both modes, `-1..1`): it is the arithmetic mean of the
/// gamma-encoded sRGB channels, i.e. HSI intensity in `0..=1`. The transform is
/// affine on that scalar and the color is rebuilt by scaling every sRGB channel
/// by `target / intensity`, then clamping. matugen truncates the scaled channel
/// to `u8` (a rounding implementation is one unit high), which this mirrors.
///
/// * dark: `target = argument + (1 - argument) * intensity` (1 stays at 1,
///   0 moves to `argument`).
/// * light: `target = (1 + argument) * intensity` (0 stays at 0, 1 moves to
///   `1 + argument`).
///
/// A zero argument is an exact identity, and an all-black color (intensity 0)
/// is left untouched; `source_color` is inserted after this runs.
fn affine_lightness(color: Argb, argument: f64, dark: bool) -> Argb {
    if argument == 0.0 {
        return color;
    }
    let intensity =
        (f64::from(color.red) + f64::from(color.green) + f64::from(color.blue)) / (3.0 * 255.0);
    if intensity <= 0.0 {
        return color;
    }
    let target = if dark {
        argument + (1.0 - argument) * intensity
    } else {
        (1.0 + argument) * intensity
    };
    let scale = target / intensity;
    Argb::new(
        255,
        scaled_channel(color.red, scale),
        scaled_channel(color.green, scale),
        scaled_channel(color.blue, scale),
    )
}

fn scaled_channel(value: u8, scale: f64) -> u8 {
    (f64::from(value) * scale).clamp(0.0, 255.0) as u8
}

fn palettes(palette: &CorePalette) -> Value {
    let mut palettes = Map::new();
    for (name, tones) in [
        ("primary", &palette.primary),
        ("secondary", &palette.secondary),
        ("tertiary", &palette.tertiary),
        ("neutral", &palette.neutral),
        ("neutral_variant", &palette.neutral_variant),
        ("error", &palette.error),
    ] {
        let mut entry = Map::new();
        for tone in TONES {
            entry.insert(tone.to_string(), Value::String(hex(tones.tone(tone))));
        }
        palettes.insert(name.to_string(), Value::Object(entry));
    }
    Value::Object(palettes)
}

fn hex(color: Argb) -> String {
    format!("#{:02x}{:02x}{:02x}", color.red, color.green, color.blue)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn argb(hex: &str) -> Argb {
        let value = u32::from_str_radix(hex.trim_start_matches('#'), 16).unwrap();
        Argb::from_u32(0xff00_0000 | value)
    }

    /// Synthetic ranked list whose metrics are far apart in every dimension:
    /// yellow is lightest, dark blue is darkest, red is most saturated, gray is
    /// least chromatic.
    fn ranked() -> Vec<Argb> {
        vec![
            argb("#f9c711"),
            argb("#ff0000"),
            argb("#808080"),
            argb("#123456"),
        ]
    }

    #[test]
    fn darkness_picks_the_lowest_tone() {
        assert_eq!(
            select_preferred(&ranked(), Prefer::Darkness, None).unwrap(),
            argb("#123456")
        );
    }

    #[test]
    fn lightness_picks_the_highest_tone() {
        assert_eq!(
            select_preferred(&ranked(), Prefer::Lightness, None).unwrap(),
            argb("#f9c711")
        );
    }

    #[test]
    fn saturation_picks_the_highest_hsv_saturation() {
        assert_eq!(
            select_preferred(&ranked(), Prefer::Saturation, None).unwrap(),
            argb("#ff0000")
        );
    }

    #[test]
    fn less_saturation_picks_the_lowest_chroma() {
        assert_eq!(
            select_preferred(&ranked(), Prefer::LessSaturation, None).unwrap(),
            argb("#808080")
        );
    }

    #[test]
    fn value_picks_the_lowest_hsv_value() {
        assert_eq!(
            select_preferred(&ranked(), Prefer::Value, None).unwrap(),
            argb("#123456")
        );
    }

    #[test]
    fn closest_to_fallback_uses_cie76_distance() {
        let ranked = ranked();
        assert_eq!(
            select_preferred(&ranked, Prefer::ClosestToFallback, Some(argb("#ff0000"))).unwrap(),
            argb("#ff0000")
        );
        assert_eq!(
            select_preferred(&ranked, Prefer::ClosestToFallback, Some(argb("#0a0a0a"))).unwrap(),
            argb("#123456")
        );
    }

    #[test]
    fn closest_to_fallback_requires_a_fallback() {
        let error = select_preferred(&ranked(), Prefer::ClosestToFallback, None).unwrap_err();
        assert!(
            error.contains("closest-to-fallback"),
            "unexpected error: {error}"
        );
        assert!(
            error.contains("--fallback-color"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn empty_ranked_list_uses_the_fallback() {
        assert_eq!(
            select_preferred(&[], Prefer::Darkness, Some(argb("#123456"))).unwrap(),
            argb("#123456")
        );
    }

    #[test]
    fn empty_ranked_list_without_fallback_fails() {
        let error = select_preferred(&[], Prefer::Lightness, None).unwrap_err();
        assert!(
            error.contains("no candidate colors"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn unknown_preference_is_rejected_with_the_choices() {
        let error = Prefer::parse("brightest").unwrap_err();
        for name in Prefer::NAMES {
            assert!(error.contains(name), "missing {name} in {error}");
        }
    }

    #[test]
    fn prefer_overrides_the_source_color_index() {
        let options = parse_args(
            [
                "--image",
                "wall.ppm",
                "--source-color-index",
                "3",
                "--prefer",
                "lightness",
            ]
            .into_iter()
            .map(String::from),
        )
        .unwrap();
        assert_eq!(options.source_color_index, 3);
        assert_eq!(options.prefer, Some(Prefer::Lightness));

        let error = parse_args(
            ["--image", "wall.ppm", "--prefer", "closest-to-fallback"]
                .into_iter()
                .map(String::from),
        )
        .unwrap_err();
        assert!(
            error.contains("--fallback-color"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn invalid_fallback_hex_is_rejected() {
        let error = parse_args(
            ["--image", "wall.ppm", "--fallback-color", "#12345g"]
                .into_iter()
                .map(String::from),
        )
        .unwrap_err();
        assert!(error.contains("#rrggbb"), "unexpected error: {error}");
    }

    #[test]
    fn zero_lightness_is_an_exact_identity() {
        for hex in ["#ff0000", "#808080", "#1a1110", "#ffffff", "#000000"] {
            let color = argb(hex);
            assert_eq!(affine_lightness(color, 0.0, true), color);
            assert_eq!(affine_lightness(color, 0.0, false), color);
        }
    }

    #[test]
    fn dark_lightness_keeps_white_and_black_bounds() {
        // 1 stays at 1.
        assert_eq!(
            affine_lightness(argb("#ffffff"), 0.5, true),
            argb("#ffffff")
        );
        assert_eq!(
            affine_lightness(argb("#ffffff"), -0.5, true),
            argb("#ffffff")
        );
        // Clamping: maximum lightness saturates to white.
        assert_eq!(
            affine_lightness(argb("#808080"), 1.0, true),
            argb("#ffffff")
        );
        // Zero-intensity colors cannot be scaled.
        assert_eq!(
            affine_lightness(argb("#000000"), 0.5, true),
            argb("#000000")
        );
        // The affine may go below zero; channels clamp to black.
        assert_eq!(
            affine_lightness(argb("#808080"), -1.0, true),
            argb("#000000")
        );
    }

    #[test]
    fn dark_lightness_uses_the_srgb_channel_mean() {
        // intensity = 128/255; target = 0.5 + 0.5 * 128/255; scale = 1.5.
        assert_eq!(
            affine_lightness(argb("#808080"), 0.5, true),
            argb("#bfbfbf")
        );
        // A chromatic color keeps its channel ratios: (26,17,16) * ~6.94.
        assert_eq!(
            affine_lightness(argb("#1a1110"), 0.5, true),
            argb("#b5766f")
        );
    }

    #[test]
    fn light_lightness_scales_from_zero_and_clamps() {
        // 0 stays at 0, so every channel is multiplied by 1 + argument.
        assert_eq!(
            affine_lightness(argb("#643219"), 0.5, false),
            argb("#964b25")
        );
        assert_eq!(
            affine_lightness(argb("#643219"), 1.0, false),
            argb("#c86432")
        );
        assert_eq!(
            affine_lightness(argb("#ffffff"), 1.0, false),
            argb("#ffffff")
        );
        // -1 collapses everything to black.
        assert_eq!(
            affine_lightness(argb("#ffffff"), -1.0, false),
            argb("#000000")
        );
    }

    #[test]
    fn source_color_is_never_transformed() {
        let options = parse_args(
            ["--color", "#ff0000", "--lightness-dark", "0.5"]
                .into_iter()
                .map(String::from),
        )
        .unwrap();
        let source = parse_hex("#ff0000").unwrap();
        let scheme = Scheme::from(DynamicScheme::by_variant(
            source,
            &Variant::TonalSpot,
            true,
            Some(options.contrast),
        ));
        let roles = roles(scheme, source, options.lightness_dark, true);
        assert_eq!(
            roles.get("source_color").and_then(Value::as_str),
            Some("#ff0000")
        );
        assert_ne!(
            roles.get("primary").and_then(Value::as_str),
            Some("#ffb4a8")
        );
    }

    #[test]
    fn lightness_flags_default_to_zero() {
        let options = parse_args(["--color", "#ff0000"].into_iter().map(String::from)).unwrap();
        assert_eq!(options.lightness_dark, 0.0);
        assert_eq!(options.lightness_light, 0.0);
    }

    #[test]
    fn lightness_flags_are_parsed_and_clamped() {
        let options = parse_args(
            [
                "--color",
                "#ff0000",
                "--lightness-dark",
                "2.5",
                "--lightness-light",
                "-9",
            ]
            .into_iter()
            .map(String::from),
        )
        .unwrap();
        assert_eq!(options.lightness_dark, 1.0);
        assert_eq!(options.lightness_light, -1.0);
    }

    #[test]
    fn invalid_lightness_values_are_rejected() {
        for (flag, value) in [
            ("--lightness-dark", "abc"),
            ("--lightness-light", "etc"),
            ("--lightness-dark", "nan"),
            ("--lightness-light", "inf"),
        ] {
            let error = parse_args(
                ["--color", "#ff0000", flag, value]
                    .into_iter()
                    .map(String::from),
            )
            .unwrap_err();
            assert!(error.contains(flag), "missing {flag} in {error}");
        }
    }

    #[test]
    fn lightness_flags_require_a_value() {
        let error = parse_args(
            ["--color", "#ff0000", "--lightness-dark"]
                .into_iter()
                .map(String::from),
        )
        .unwrap_err();
        assert!(
            error.contains("requires a value"),
            "unexpected error: {error}"
        );
    }
}
