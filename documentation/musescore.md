# MuseScore — Harmony Encoding

## Overview

[MuseScore](https://musescore.org/) is an open-source music notation editor. Its native format, MSCZ, is a ZIP archive wrapping an XML file with a `.mscx` extension. MuseScore can also export standard MusicXML, and the two representations encode harmony differently.

HAMON reads MuseScore's native MSCX with a text-level extractor.

---

## MSCX harmony element

In MSCX, a chord symbol is a `<Harmony>` element (capital H), reached through a `<Measure>` → `<voice>` → `<Harmony>` path. The surface label lives in it as plain text:

```xml
<Harmony>
  <text>Cmaj7</text>
</Harmony>
```

Older MuseScore versions (v3 and below) may use `<name>` instead of `<text>`:

```xml
<Harmony>
  <name>Cmaj7</name>
</Harmony>
```

HAMON's extractor looks for both `<text>` and `<name>`, and when both are present it takes `<text>`.

### What `<text>` contains

MuseScore stores the chord symbol **exactly as typed**, Unicode glyphs and all. There is no separate semantic encoding: `CΔ7`, `CM7`, and `Cmaj7` are each kept verbatim and rendered as typed. That makes MSCX the most faithful of the supported formats for chord-symbol surface fidelity — HAMON just parses whatever sits in `<text>`.

### Extended example

```xml
<Measure>
  <voice>
    <Harmony>
      <text>Bø7</text>
    </Harmony>
    <Chord>
      <Note><pitch>71</pitch></Note>
    </Chord>
    <Harmony>
      <text>V7</text>
    </Harmony>
    <Chord>
      <Note><pitch>67</pitch></Note>
    </Chord>
  </voice>
</Measure>
```

### Roman numerals, Nashville, figured bass

MuseScore 4 added a dedicated Roman-numeral analysis input mode. The XML it produces still stores the label as plain text in `<Harmony><text>`, so HAMON parses `V7`, `ii`, `6-5`, and the rest exactly as it would from any other source.

---

## Mapping: JSON fields → MuseScore MSCX

Every mapping below is stated against the canonical JSON schema (`grammar/hamon-schema.json`). MSCX has no semantic structure for harmony: every label is a plain surface string in `<Harmony><text>`. There is no per-field encoding — HAMON writes the whole `HarmonyLabel.surface` and reads it straight back.

| JSON field | HAMON → MSCX | MSCX → HAMON | Loss / note |
|---|---|---|---|
| `surface` (any `kind`) | `<Harmony><text>CΔ7</text></Harmony>` | `<text>` content → `surface` | none — surface is stored verbatim |
| `semantic` (any `kind`) | not encoded | derived by parsing `surface` | no structured fields in MSCX |
| `rendering.*` | reflected in `surface` text | recovered by parsing `surface` | glyph variants preserved via `surface` |

All `kind` values map the same way:

| JSON `kind` | `<text>` content example |
|---|---|
| `chordSymbol` | `CΔ7`, `Am7`, `Bb`, `Bø7` |
| `roman` | `V7`, `ii`, `bVII` |
| `figuredBass` | `6-5`, `4-3` |
| `nashville` | `2m`, `b7` |
| `functional` | `T`, `D->T` |
| `noChord` | `N.C.` |
| `text` | anything else |

MSCX never declares the notation system, so HAMON's grammar infers it from the `surface` value.

---

## Losses and ambiguities

- **No semantic layer**: MSCX keeps no semantic encoding next to the display text. A non-standard abbreviation or a typo therefore comes through as `textLabel` instead of the type you meant.
- **Formatting markup**: MuseScore 4 encodes styled text (superscripts, bold, and so on) as embedded XML fragments inside `<text>`, a subset of HTML. HAMON strips those tags and reads only the plain text.
- **`<name>` vs `<text>`**: tools that write MSCX programmatically may emit `<name>` (the MuseScore 3 convention) or `<text>` (MuseScore 4). HAMON's extractor handles both.
- **Time anchoring**: `<Harmony>` elements are children of `<voice>`, siblings of the `<Chord>` elements. HAMON reads labels in document order but does not yet keep beat position.

---

## How HAMON reads MuseScore MSCX

The adapter (`hamonpy/hamonpy/adapters/formats.py`, `_extract_musescore`):

1. Scans for `<Harmony>` blocks with a regex matching the full element.
2. Inside each block, extracts the content of `<text>` first, then `<name>` as fallback.
3. Strips any embedded HTML/XML markup tags from the extracted string.
4. Returns deduplicated, non-empty strings.

---

## Comparison: MSCX vs MusicXML export

| Aspect | MSCX (`<Harmony><text>`) | MusicXML (`<harmony><kind>`) |
|---|---|---|
| Surface fidelity | Exact — `CΔ7`, `CM7`, `Cmaj7` preserved as typed | Partial — display in `text` attr; semantic in inner text |
| Semantic encoding | None | Yes (`major-seventh`, `minor`, …) |
| Roman numerals | Plain text | Not standard |
| Extension/alteration details | Plain text | `<degree>` children |

---

## Examples from the HAMON fixture corpus

| Fixture | `<text>` content | HAMON surface | HAMON `kind` |
|---|---|---|---|
| `C_major` | `C` | `C` | `chordSymbol` |
| `Bb_major` | `Bb` | `Bb` | `chordSymbol` |
| `C_delta7` | `CΔ7` | `CΔ7` | `chordSymbol` |
| `B_hdim7` | `Bø7` | `Bø7` | `chordSymbol` |
| `C_dim` | `C°` | `C°` | `chordSymbol` |
| `rn_V7` | `V7` | `V7` | `roman` |
| `rn_ii` | `ii` | `ii` | `roman` |
| `fb_6_5` | `6-5` | `6-5` | `figuredBass` |
| `ns_2m` | `2m` | `2m` | `nashville` |

Full fixture files: `fixtures/chords/`, `fixtures/roman/`, `fixtures/figuredbass/`, `fixtures/nashville/`.
