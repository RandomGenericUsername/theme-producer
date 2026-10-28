# Router fixtures + expected lanes

Dry-run inputs for the triage rubric. Each fixture maps to one lane and cites the covering spec
scenario. This file lives under `tickets/_fixtures/`, which is excluded from item counting — the
INDEX completeness check only counts item files (`tickets/*/ticket.md`).

## Fixture A — XS fix → Lane 1 (XS direct)

**Request**: "Fix the typo in the README header (`Producr` → `Producer`)."

- `kind:` ops-task (single trivial edit, no parent, no uncertainty)
- `lane:` 1 — XS direct
- Why: trivial, fully understood, one small edit; cheapest safe path is a ticket worked directly
  with no OpenSpec change.

## Fixture B — single feature → Lane 2 (openspec-single)

**Request**: "Add a `--dry-run` flag to `tpr generate` that prints the resolved engine command and
projection list without executing anything."

- `kind:` requirement (one bounded behavior addition)
- `lane:` 2 — openspec-single (one item + one OpenSpec change)
- Why: single bounded feature, understood, fits one proposal/spec/design/tasks slice.

## Fixture C — multi-part understood → Lane 3 (ticket-multi, no BMAD)

**Request**: "Add the five projection formats for btop, rofi, kitty, hyprland and sequences, each
with a golden test and a capability table."

- `kind:` requirement (multi-part, all parts specified, no unknowns)
- `lane:` 3 — ticket-multi, no BMAD (one item + N OpenSpec changes)
- Why: multi-part but fully understood with no architectural unknowns; BMAD would be overkill.

## Fixture D — architectural → Lane 4 (bmad-advisory)

**Request**: "Define the Theme contract and engine boundary: Material roles, tonal palettes,
light/dark, matugen vs own engine, projection capability rules, and how the dotfiles runtime would
adopt it."

- `kind:` epic (broad, multi-ticket scope with architectural unknowns)
- `lane:` 4 — bmad-advisory (BMAD specialist advice → spec → changes)
- Why: broad/uncertain/architectural; needs advisory exploration before planning. Triage
  recommends BMAD vs plain split with reasons and the user selects; BMAD advice never
  auto-executes. A small-looking epic would still decompose, never build.
