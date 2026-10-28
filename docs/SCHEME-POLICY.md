# Scheme policy design — `scheme-smart` in `tpr`

Status: proposed
Date: 2026-10-28
Scope: standalone `theme-producer`; no dotfiles/provisioning/runtime changes.

## Problem

`scheme-smart` is matugen's opaque “pick one of the nine Material variants from the image” heuristic.
It is matugen-only today. We want a clean, explicit, user-extensible policy that works for **both**
engines and does not read GPL source.

## Decision summary (ADRs)

- **AD-1 — Policy lives in `tpr`, not the engine.** The engine stays a pure variant calculator.
  `tpr` computes image metrics, resolves a concrete variant, and calls the engine with it. Both
  matugen and native benefit; native needs no Rust changes.
- **AD-2 — Metrics are normalized to `[0,1]` and deterministic.** Pillow decodes; the image is
  resized to 256×256 (Triangle) before metrics. The formula is documented and tested.
- **AD-3 — Policies are ordered rules, first match wins, with a default.** No arbitrary code, no
  plugin execution, no expression language; only a small metric/comparison grammar.
- **AD-4 — Policies are a YAML catalog resolved by `config-assembler-engine`.** Same five-strategy
  chain as `settings.toml` / `engines.yaml`, with a Pydantic schema.
- **AD-5 — Explicit `scheme_type` wins.** `scheme_type` with a real variant bypasses the policy.
  `scheme_type=scheme-smart` is a `tpr` pseudo-value that runs the policy. `[generation]
  scheme_policy` selects the named profile.
- **AD-6 — Container resolution happens on the host.** The inner `tpr` receives the concrete variant
  (`scheme-tonal-spot`, …), never `scheme-smart`.
- **AD-7 — Built-in profiles plus user overrides.** The packaged catalog ships `balanced`,
  `vivid`, `muted`, `source-faithful`; users can replace/augment via XDG/env/CLI.
- **AD-8 — No dotfiles changes.** The feature is standalone; release `v0.4.0` with images.

## Hexagonal shape

```
CLI / processors
   │
   ▼
application use case (resolve scheme)
   │  uses
   ├── ImageMetricsPort          ← PillowImageMetrics adapter
   ├── SchemePolicyCatalogPort   ← YamlSchemePolicyCatalogLoader adapter
   └── SchemePolicyResolver      (pure domain service)
   │
   ▼
ThemeEnginePort (unchanged)  ← matugen / native
```

Domain is pure: no Pillow, no YAML, no filesystem.

## Domain model

```python
class SchemeVariant(StrEnum):
    TONAL_SPOT = "scheme-tonal-spot"
    CONTENT = "scheme-content"
    EXPRESSIVE = "scheme-expressive"
    FIDELITY = "scheme-fidelity"
    FRUIT_SALAD = "scheme-fruit-salad"
    MONOCHROME = "scheme-monochrome"
    NEUTRAL = "scheme-neutral"
    RAINBOW = "scheme-rainbow"
    VIBRANT = "scheme-vibrant"

@dataclass(frozen=True)
class ImageMetrics:
    saturation: float       # 0..1
    colorfulness: float     # 0..1
    lightness: float        # 0..1
    contrast: float         # 0..1
    hue_diversity: float    # 0..1

class MetricName(StrEnum):
    SATURATION = "saturation"
    COLORFULNESS = "colorfulness"
    LIGHTNESS = "lightness"
    CONTRAST = "contrast"
    HUE_DIVERSITY = "hue_diversity"

class Operator(StrEnum):
    LT = "lt"; LTE = "lte"; GT = "gt"; GTE = "gte"; BETWEEN = "between"

@dataclass(frozen=True)
class Condition:
    metric: MetricName
    operator: Operator
    value: float
    upper: float | None = None   # only for BETWEEN

@dataclass(frozen=True)
class Rule:
    conditions: tuple[Condition, ...]   # ANDed
    variant: SchemeVariant

@dataclass(frozen=True)
class SchemePolicy:
    name: str
    rules: tuple[Rule, ...]             # ordered; first match wins
    default: SchemeVariant

@dataclass(frozen=True)
class SchemePolicyCatalog:
    version: int
    default_policy: str
    policies: Mapping[str, SchemePolicy]
```

`SchemePolicyResolver.resolve(policy, metrics) -> SchemeVariant` is pure: evaluates rules in
order, returns the first whose conditions all hold, else `policy.default`. It validates metric
ranges and raises `SchemePolicyError` on invalid rules.

## Metrics (packaged default)

Computed on the 256×256 Triangle resize, sRGB, alpha dropped:

| Metric | Definition |
|---|---|
| `saturation` | mean HSV saturation over pixels |
| `colorfulness` | Hasler–Süsstrunk: `sqrt(σ_rg²+σ_yb²) + 0.3·sqrt(μ_rg²+μ_yb²)`, normalized |
| `lightness` | mean relative luminance (sRGB-linearized) |
| `contrast` | standard deviation of relative luminance, normalized |
| `hue_diversity` | saturation-weighted circular variance of hue, normalized |

For a color source, the metrics are derived from that single color (`contrast=0`,
`hue_diversity=0`, `colorfulness=0`).

## Policy catalog schema

```yaml
version: 1
default: balanced

policies:
  balanced:
    default: scheme-tonal-spot
    rules:
      - when:
          colorfulness: { lt: 0.08 }
        variant: scheme-monochrome
      - when:
          saturation: { lt: 0.15 }
        variant: scheme-neutral
      - when:
          colorfulness: { gte: 0.35 }
          saturation: { gte: 0.55 }
        variant: scheme-vibrant
      - when:
          hue_diversity: { gte: 0.60 }
        variant: scheme-expressive

  vivid:
    default: scheme-vibrant
    rules:
      - when: { colorfulness: { lt: 0.10 } }
        variant: scheme-neutral
      - when: { contrast: { gte: 0.55 } }
        variant: scheme-vibrant

  muted:
    default: scheme-neutral
    rules:
      - when: { colorfulness: { gte: 0.35 } }
        variant: scheme-tonal-spot
      - when: { hue_diversity: { gte: 0.65 } }
        variant: scheme-expressive

  source-faithful:
    default: scheme-content
    rules:
      - when: { contrast: { gte: 0.50 } }
        variant: scheme-fidelity
```

Rules are ANDed; first match wins. `default` is required per policy and at catalog level.
Unknown metric/operator/variant, out-of-range values, or empty rules fail at load time.

## Resolution and precedence

1. `scheme_type` explicit (one of the nine) → use it, skip the policy.
2. `scheme_type=scheme-smart` or `scheme_policy` set → load catalog, compute metrics, resolve
   variant.
3. No policy and no explicit scheme → engine default (`scheme-tonal-spot`).

`scheme_policy` selects the profile name; `--policies-file` / `THEME_SCHEME_POLICIES_CONFIG_FILE_PATH`
selects the catalog file.

## Ports and adapters

| Port | Adapter | Notes |
|---|---|---|
| `ImageMetricsPort` | `PillowImageMetrics` | Pillow, 256×256, pure formula |
| `SchemePolicyCatalogPort` | `YamlSchemePolicyCatalogLoader` | config-assembler-engine, YAML schema |
| `SchemePolicyResolver` | domain service | pure, first-match |

`ThemeEnginePort` is unchanged.

## Settings / CLI / env

```toml
[generation]
scheme_type = "scheme-smart"   # or a real variant
scheme_policy = "balanced"
```

```bash
tpr generate wall.png --scheme-policy balanced
tpr generate wall.png --policies-file ./my-policies.yaml
tpr generate wall.png --param scheme_type=scheme-smart
```

```
THEME__GENERATION__SCHEME_TYPE=scheme-smart
THEME__GENERATION__SCHEME_POLICY=balanced
THEME_SCHEME_POLICIES_CONFIG_FILE_PATH=/path/to/scheme-policies.yaml
```

`dump-config` includes the policy fields; `info` includes the resolved catalog path and profile.
`generate --dry-run` prints metrics and the resolved variant.

## Container behavior

Resolve metrics and policy on the host; pass the concrete variant to the container inner command.
`theme.json` records the chosen variant in `scheme` (as today).

## Tests

- Domain: condition/operator evaluation, AND semantics, first match, defaults, invalid rules.
- Adapter: metrics on white/black/colorful/muted synthetic images; catalog resolution chain;
  schema errors; user catalog override.
- CLI: `scheme_type=scheme-smart`, `--scheme-policy`, `--policies-file`, precedence, dry-run,
  container concrete variant, `info`/`dump-config`.
- Corpus: seven real wallpapers; record metrics → variant table; no surprises.
- Hermetic: synthetic images only; no host wallpapers in the gates.

## Non-goals

- No arbitrary code/plugin policies.
- No OR expressions; AND-only conditions in v1.
- No mode selection in the policy (dark/light remains `--mode smart`).
- No matugen heuristic reuse or GPL source reading.
- No dotfiles changes.

## Release

`v0.4.0` after all three tickets; rebuild images; no dotfiles pin.
