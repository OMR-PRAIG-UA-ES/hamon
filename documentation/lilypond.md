# LilyPond — Harmony Encoding

## Overview

[LilyPond](https://lilypond.org/) engraves music from a plain-text input language, and its typographic quality has made it a favourite in academic and new-music circles. In a LilyPond source file, harmony labels show up in two places:

1. **`\chordmode` blocks** — LilyPond's native chord notation, meant for printing chord symbols above a staff.
2. **`% hamon-surface:` comments** — a hamon-specific annotation for the label types LilyPond can't write natively (Roman numerals, figured bass, Nashville, functional).

LilyPond has no structured harmony model to import from, so HAMON reads it with a text-level regex extractor that handles both forms.

---

## Export: real `\chordmode` since 2026-09-03

The exporter used to emit a placeholder `c1` with every harmony parked in
`% hamon-surface:` comments. It produced a valid file that contained **no LilyPond
harmony at all** — and because the reader preferred those comments, the round-trip
reported LilyPond as near-lossless. It was reading our comments back.

`hamon_to_lilypond` now writes chord tokens:

```lilypond
\version "2.24.0"
\chordmode {
  d1:m7 g:7 c:maj7 f bes:maj7 s ees:7
}
```

Two rules it follows, both about not asserting what HAMON does not know:

- **The duration sits on the first token only**, and the rest inherit it. Writing `1` on
  every chord would state a rhythm the label stream has no opinion about.
- **A chord it cannot spell exactly becomes a skip (`s`)**, not an approximation. The
  `s` above is an `F#m7b5`: LilyPond can say it (`fis:m7.5-`) but this writer's mapping
  does not yet, and emitting `fis:m7` would be a *different chord*. The loss is reported
  rather than hidden — see `documentation/processing.md` on the xencoding report.

Extending the mapping to LilyPond's step-alteration syntax (`a:7.9-`, `g:7.9-.13-`) would
remove most of those skips; it needs matching reader support and is on the roadmap.

The reader accepts durations on chord tokens (`d1:m7`), which it previously rejected — so
it can read LilyPond written by LilyPond, not only files this exporter produced.


## `\chordmode` syntax

`\chordmode` takes a run of pitch tokens, each one optionally followed by a `:modifier` suffix. Pitches use lowercase Dutch note names, and the modifier after `:` sets the chord quality.

### Pitch names

| HAMON root | LilyPond token |
|---|---|
| `C` | `c` |
| `D` | `d` |
| `E` | `e` |
| `F` | `f` |
| `G` | `g` |
| `A` | `a` |
| `B` | `b` |
| `C#` / `Db` | `cis` / `des` |
| `Bb` | `bes` (not `bes` = `B♭`, not `bb`) |
| `Eb` / `D#` | `ees` or `es` / `dis` |
| `F#` / `Gb` | `fis` / `ges` |
| `Ab` / `G#` | `aes` or `as` / `gis` |

### Quality modifiers (`:suffix`)

| LilyPond modifier | HAMON surface | Semantic |
|---|---|---|
| *(none)* | `C` | major triad |
| `:m` | `Cm` | minor triad |
| `:aug` | `C+` | augmented triad |
| `:dim` | `C°` | diminished triad |
| `:7` | `G7` | dominant seventh |
| `:7+` | `Cmaj7` | major seventh (display depends on `majorSevenSymbol`) |
| `:m7` | `Am7` | minor seventh |
| `:dim7` | `B°7` | diminished seventh |
| `:m7.5-` | `Bø7` | half-diminished seventh |
| `:sus2` | `Csus2` | suspended second |
| `:sus4` | `Csus4` | suspended fourth |
| `:maj7` | `Cmaj7` | major seventh (alternative spelling) |

### `majorSevenSymbol` — display override

Internally, LilyPond encodes every major-seventh chord as `:7+`, no matter which glyph it prints. What you actually see is controlled by `\set majorSevenSymbol`:

```lilypond
\chordmode {
  \set majorSevenSymbol = \markup { "Δ7" }
  c:7+   % renders as CΔ7
}
```

```lilypond
\chordmode {
  \set majorSevenSymbol = \markup { "M7" }
  c:7+   % renders as CM7
}
```

With no `majorSevenSymbol` override, LilyPond renders `:7+` as `maj7`. HAMON's LilyPond extractor reads the `majorSevenSymbol` markup string and applies it as the surface for every `:7+` token in that block.

### Slash bass

A bass note is appended with `/+`:

```lilypond
\chordmode { c/e }   % C/E (first inversion)
```

### Full example

```lilypond
\chordmode {
  c      % C
  a:m    % Am
  g:7    % G7
  \set majorSevenSymbol = \markup { "Δ7" }
  c:7+   % CΔ7
  bes    % Bb
  b:m7.5-  % Bø7
}
```

---

## `% hamon-surface:` comment annotation

LilyPond has no native syntax for Roman numerals, Nashville numbers, figured bass, or functional labels. So for fixture files — and any LilyPond score that carries these label types — HAMON puts a comment annotation on the line before the relevant note (or in place of it):

```lilypond
% hamon-surface: V7
% hamon-surface: ii
% hamon-surface: 6-5
% hamon-surface: 2m
```

HAMON's extractor scans for lines matching `% hamon-surface: <label>` and collects those label strings directly, skipping `\chordmode` altogether. When a file has both a `% hamon-surface:` annotation and a `\chordmode` block, the annotation wins.

---

## Mapping: JSON fields → LilyPond

Every mapping below is stated against the canonical JSON schema (`grammar/hamon-schema.json`). LilyPond has two encoding paths: `\chordmode` for chord symbols, and `% hamon-surface:` comments for everything else.

### Chord symbols (`kind: "chordSymbol"`) — `\chordmode`

| JSON field | HAMON → LilyPond | LilyPond → HAMON | Loss / note |
|---|---|---|---|
| `root.note` | lowercase Dutch name: `c`, `g`, `a` | Dutch name → uppercase note | none |
| `root.accidental: "sharp"` | `is` suffix: `cis`, `fis` | `is` → `sharp` | `rendering.accidentalGlyphs` stores original |
| `root.accidental: "flat"` | `es`/`ees` suffix: `bes`, `des` | `es`/`ees` → `flat` | `bes` not `bflat` |
| `quality: "major"` | no `:modifier` | no modifier → `major` | none |
| `quality: "minor"` | `:m` | `:m` → `minor` | none |
| `quality: "augmented"` | `:aug` | `:aug` → `augmented` | none |
| `quality: "diminished"` | `:dim` | `:dim` → `diminished` | none |
| `quality: "half-diminished"` | `:m7.5-` | `:m7.5-` → `half-diminished` + `seventh: "hdim7"` | LilyPond bundles quality+seventh |
| `seventh: "dom7"` | `:7` | `:7` → `dom7` | none |
| `seventh: "maj7"` | `:7+` + `\set majorSevenSymbol = \markup{"Δ7"}` | `:7+` → `maj7`; markup string → `rendering.seventhGlyph` | glyph depends on `majorSevenSymbol`; defaults to `maj7` if absent |
| `seventh: "min7"` | `:m7` | `:m7` → `min7` | none |
| `seventh: "dim7"` | `:dim7` | `:dim7` → `dim7` | none |
| `suspensions: [4]` | `:sus4` | `:sus4` → `suspensions:[4]` | none |
| `suspensions: [2]` | `:sus2` | `:sus2` → `suspensions:[2]` | none |
| `bass.note` | `/+<pitch>` suffix | after `/+` → `bass` | none |

### All other notation systems — `% hamon-surface:` comment

LilyPond has no native syntax for `kind: "roman"`, `"nashville"`, `"figuredBass"`, `"functional"`, `"noChord"`, or `"text"`. HAMON writes the `HarmonyLabel.surface` string verbatim into a comment annotation:

| JSON field | HAMON → LilyPond | LilyPond → HAMON |
|---|---|---|
| `surface` (any non-chordSymbol kind) | `% hamon-surface: V7` | comment text → `surface`; system detected by grammar |

---

## Losses and ambiguities

- **Major-seventh display**: LilyPond stores only `:7+`; the rendered symbol comes from a separate `\set` directive. HAMON reads that directive when it is there and falls back to `maj7` when it isn't. Going the other way (HAMON → LilyPond) means writing the correct `majorSevenSymbol` markup.
- **No native Roman/Nashville/figured-bass syntax**: LilyPond simply has no mechanism for these systems. The `% hamon-surface:` comment convention is HAMON's own, and LilyPond renderers ignore it.
- **Pitch spelling**: LilyPond's Dutch names spell B♭ as `bes` (not `bb`) and E♭ as `ees`/`es`. HAMON's extractor normalizes these back to ASCII accidentals (`b`, `#`).

---

## How HAMON reads LilyPond

The adapter (`hamonpy/hamonpy/adapters/formats.py`, `_extract_lilypond`):

1. Scans for `% hamon-surface: <label>` lines. If found, returns those labels directly.
2. Otherwise, finds all `\chordmode { … }` blocks.
3. For each token inside a block: strips `{` / `}`, skips LilyPond commands (`\…`), parses `<pitch>[:<modifier>]`, converts Dutch pitch name + accidental suffix to ASCII, maps the modifier to a HAMON surface suffix.
4. Reads `\set majorSevenSymbol = \markup { "…" }` and applies the display string to subsequent `:7+` tokens.

---

## Examples from the HAMON fixture corpus

| Fixture | LilyPond token | HAMON surface | HAMON `kind` |
|---|---|---|---|
| `C_major` | `c` | `C` | `chordSymbol` |
| `Bb_major` | `bes` | `Bb` | `chordSymbol` |
| `C_minor` | `c:m` | `Cm` | `chordSymbol` |
| `G_dom7` | `g:7` | `G7` | `chordSymbol` |
| `C_maj7` | `c:7+` (no symbol override) | `Cmaj7` | `chordSymbol` |
| `C_delta7` | `c:7+` + `"Δ7"` | `CΔ7` | `chordSymbol` |
| `C_M7` | `c:7+` + `"M7"` | `CM7` | `chordSymbol` |
| `B_hdim7` | `b:m7.5-` | `Bø7` | `chordSymbol` |
| `rn_V7` | `% hamon-surface: V7` | `V7` | `roman` |
| `fb_6_5` | `% hamon-surface: 6-5` | `6-5` | `figuredBass` |
| `ns_2m` | `% hamon-surface: 2m` | `2m` | `nashville` |

Full fixture files: `fixtures/chords/`, `fixtures/roman/`, `fixtures/figuredbass/`, `fixtures/nashville/`.
