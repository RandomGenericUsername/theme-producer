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

use material_colors::color::Argb;
use material_colors::dynamic_color::{DynamicScheme, Variant};
use material_colors::image::{AsPixels, FilterType, ImageReader};
use material_colors::palette::CorePalette;
use material_colors::quantize::{Quantizer, QuantizerCelebi};
use material_colors::scheme::Scheme;
use material_colors::score::Score;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};

const ENGINE_NAME: &str = "native";
const ENGINE_VERSION: &str = "0.1.0";
const SCHEMA_VERSION: &str = "1";
const DEFAULT_SCHEME: &str = "scheme-tonal-spot";
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
                  [--source-color-index <int>] [--json]
                  [--version]";

struct Options {
    image: Option<String>,
    color: Option<String>,
    scheme: String,
    contrast: f64,
    source_color_index: usize,
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
                "roles": roles(dark, source),
                "palettes": palettes(&palette),
            },
            "light": {
                "roles": roles(light, source),
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
    let mut source_color_index = 0_usize;

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
            "--source-color-index" => {
                let raw = take_value(&mut args, "--source-color-index")?;
                source_color_index = raw.parse::<usize>().map_err(|_| {
                    format!("--source-color-index expects a non-negative int; got {raw:?}")
                })?;
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

    Ok(Options {
        image,
        color,
        scheme,
        contrast,
        source_color_index,
    })
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
        return image_source(path, options.source_color_index);
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

fn image_source(path: &str, source_color_index: usize) -> Result<(Argb, Value), String> {
    let bytes =
        fs::read(path).map_err(|error| format!("could not read image {path:?}: {error}"))?;
    let hash = sha256_hex(&bytes);
    let resolved = fs::canonicalize(path).unwrap_or_else(|_| path.into());

    // `ImageReader::read` expects to decode valid image bytes and panics on a
    // corrupt payload; turn that into a clear process error instead.
    let decoded = panic::catch_unwind(|| ImageReader::read(bytes))
        .map_err(|_| format!("could not decode image {path:?}: not a supported image"))?;
    let mut image = decoded.map_err(|error| format!("could not decode image {path:?}: {error}"))?;
    image.resize(128, 128, FilterType::Lanczos3);

    let pixels = image.as_pixels();
    let quantized = QuantizerCelebi::quantize(&pixels, 128);
    let ranked = Score::score(&quantized.color_to_count, None, None, None);
    let fallback = Argb::new(255, 66, 133, 244);
    let source = if ranked.is_empty() {
        fallback
    } else {
        ranked[source_color_index.min(ranked.len() - 1)]
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

fn roles(scheme: Scheme, source: Argb) -> Value {
    let mut roles = Map::new();
    for (name, color) in scheme {
        roles.insert(name, Value::String(hex(color)));
    }
    roles.insert("source_color".to_string(), Value::String(hex(source)));
    Value::Object(roles)
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
