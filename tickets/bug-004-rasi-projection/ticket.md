---
id: BUG-004
title: "colors.rasi projection emits GTK @define-color; rofi cannot parse it"
kind: bug
status: done
lane: 2
links:
  openspec: none
  bmad: none
worktree: none
branch: none
severity: high
---

# colors.rasi projection is invalid rasi

## Evidence

- Generated `~/.local/state/dotfiles/current/colors.rasi` starts with
  `@define-color role #hex;` (GTK syntax).
- `rofi` (2.0.0-dirty) fails:
  `Error while parsing theme: ~/.config/rofi/launcher/config.rasi`
  `Parser error: syntax error ... File: ~/.config/rofi/colors.rasi`.
- Template `src/theme_producer/defaults/templates/colors.rasi.j2` emits
  `@define-color` (it has since f98add6; BUG-003 only changed index padding).

## Requirement

The rasi projection must emit a standard rofi theme block so the launcher's
`@import "../colors.rasi"` and `@colorNN` references resolve:

```
/* colors.rasi — generated from theme.json */
* {
    background: #…;
    foreground: #…;
    accent: #…;
    accent-muted: #…;
    surface: #…;
    on_surface: #…;
    … all roles / produced roles …
    color00: #…;
    … color15 …
}
```

Keep every role name (declared + produced + legacy aliases). Emit no
`@define-color`. Update the golden fixture and add a regression test asserting
the block shape and absence of GTK directives (and, if a non-interactive rofi
syntax check exists on the host, use it).

## Acceptance

- [ ] Generated rasi is `* { name: value; }` with all roles + `color00..15`.
- [ ] `rg '@define-color' <generated rasi>` → 0.
- [ ] Golden fixture updated; test added.
- [ ] `make gates` green; release v0.5.1 after review.
- [ ] Live rofi launcher opens without a parser error.

## Outcome

Fixed in `v0.5.1` and deployed via PIN-0129. Template emits one `* { … }` block
with all roles (hyphenated: `on_surface` → `on-surface`, since rasi identifiers
cannot contain `_`) plus `color00..15`; no `@define-color`. Live check:
`rofi -dump-theme -theme ~/.config/rofi/launcher/config.rasi` → rc 0, no
`Failed to parse theme`, and the launcher no longer reports a parse error.
