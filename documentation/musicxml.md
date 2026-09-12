# MusicXML — Harmony Encoding

## Overview

[MusicXML](https://www.musicxml.com/) is the XML interchange format for Western common-practice notation, maintained by the W3C Music Notation Community Group. It's how notation editors — Finale, Sibelius, MuseScore, Dorico — hand scores to one another, and it's a staple of music information retrieval.

Harmony rides on the `<harmony>` element, which sits as a sibling of notes inside a `<measure>`. MusicXML takes a **semantic** approach: the chord quality is a controlled-vocabulary keyword (`major-seventh`, say), and the display text goes separately in a `text` attribute. HAMON reads both, but prefers `text` when it's there, because that's the exact surface the composer or editor meant.

---

## The `<harmony>` element

A `<harmony>` element holds child elements that together spell out one chord symbol:

```xml
<harmony print-frame="no">
  <root>
    <root-step>C</root-step>
    <root-alter>-1</root-alter>   <!-- optional: -1=flat, 1=sharp, 2=double-sharp -->
  </root>
  <kind text="m7">minor-seventh</kind>
  <bass>                           <!-- optional: slash bass -->
    <bass-step>E</bass-step>
    <bass-alter>-1</bass-alter>
  </bass>
</harmony>
```

### `<root-step>` and `<root-alter>`

The root's pitch class: `A`–`G`. Accidentals are numeric semitone alterations — `-1` = flat, `1` = sharp, `-2` = double-flat, `2` = double-sharp. Natural is `0` or simply omitted.

### `<kind>`

The chord quality. The inner content is the **semantic keyword**; the optional `text` attribute holds the **display string**.

| Inner text (semantic) | Common `text` attribute | HAMON surface |
|---|---|---|
| `major` | (empty or `""`) | `C` |
| `minor` | `m` | `Cm` |
| `augmented` | `+` or `aug` | `C+` |
| `diminished` | `°` or `dim` | `C°` |
| `dominant` | `7` | `G7` |
| `major-seventh` | `maj7`, `M7`, `Δ7` | `Cmaj7` / `CM7` / `CΔ7` |
| `minor-seventh` | `m7` | `Am7` |
| `diminished-seventh` | `°7` or `dim7` | `B°7` |
| `half-diminished-seventh` | `ø7` or `m7b5` | `Bø7` |
| `suspended-second` | `sus2` | `Csus2` |
| `suspended-fourth` | `sus4` | `Csus4` |

When `text` is absent, HAMON reconstructs a surface string from the semantic keyword using the normalization table above.

### `<bass>`

Optional. Encodes a slash bass note (`C/E`, for example). Its structure mirrors `<root>`: `<bass-step>` (A–G) plus an optional `<bass-alter>`.

### `<degree>`

Optional. Encodes alterations or additions beyond the base quality (`#11`, `b9`). Each `<degree>` carries `<degree-value>`, `<degree-alter>`, and `<degree-type>` (`add`, `alter`, `subtract`). HAMON captures these as `chordSymbol` extension/alteration tokens when they also show up in the `text` attribute; a structural `<degree>` with no matching `text` attribute isn't mapped yet.

---

## Mapping: JSON fields → MusicXML

All mappings are relative to the canonical JSON schema (`grammar/hamon-schema.json`).

### Chord symbols (`kind: "chordSymbol"`)

| JSON field | HAMON → MusicXML | MusicXML → HAMON | Loss / note |
|---|---|---|---|
| `root.note` | `<root-step>C</root-step>` | read `<root-step>` | none |
| `root.accidental: "sharp"` | `<root-alter>1</root-alter>` | `alter=1` → `sharp` | numeric; enharmonic preserved |
| `root.accidental: "flat"` | `<root-alter>-1</root-alter>` | `alter=-1` → `flat` | none |
| `root.accidental: "double-sharp"` | `<root-alter>2</root-alter>` | `alter=2` → `double-sharp` | none |
| `root.accidental: "double-flat"` | `<root-alter>-2</root-alter>` | `alter=-2` → `double-flat` | none |
| `quality: "major"` | `<kind>major</kind>` | inner text `major` | none |
| `quality: "minor"` | `<kind text="m">minor</kind>` | inner text `minor` | `text` attr preferred for surface |
| `quality: "augmented"` | `<kind>augmented</kind>` | inner text `augmented` | none |
| `quality: "diminished"` | `<kind>diminished</kind>` | inner text `diminished` | none |
| `quality: "half-diminished"` | `<kind>half-diminished-seventh</kind>` | inner text `half-diminished…` | none |
| `seventh: "dom7"` | `<kind text="7">dominant</kind>` | inner text `dominant` | none |
| `seventh: "maj7"` | `<kind text="maj7">major-seventh</kind>` | inner text `major-seventh` | display glyph (`Δ7`, `M7`, `maj7`) in `text` attr; preserved in `rendering.seventhGlyph` |
| `seventh: "min7"` | `<kind text="m7">minor-seventh</kind>` | inner text `minor-seventh` | none |
| `seventh: "dim7"` | `<kind>diminished-seventh</kind>` | inner text `diminished-seventh` | none |
| `seventh: "hdim7"` | `<kind>half-diminished-seventh</kind>` | inner text `half-diminished…` | none |
| `suspensions: [4]` | `<kind text="sus4">suspended-fourth</kind>` | inner text `suspended-fourth` | none |
| `suspensions: [2]` | `<kind text="sus2">suspended-second</kind>` | inner text `suspended-second` | none |
| `bass.note` | `<bass><bass-step>E</bass-step></bass>` | read `<bass-step>` | none |
| `bass.accidental` | `<bass-alter>-1</bass-alter>` | same as root alter | none |
| `extensions[]` / `alterations[]` | `<degree>` children | read `<degree>` children | only extracted when reflected in `kind text`; structured `<degree>` without `text` is currently ignored |
| `rendering.seventhGlyph` | `<kind text="Δ7">` attribute | `kind text` attr → `rendering.seventhGlyph` | none |
| `rendering.qualityGlyph` | absorbed into `kind text` | `kind text` → `rendering.qualityGlyph` | none |

### Other notation systems

MusicXML's `<harmony>` only does chord symbols. There's no dedicated MusicXML element for Roman numerals, figured bass, Nashville numbers, or functional labels.

| JSON `kind` | HAMON → MusicXML | MusicXML → HAMON |
|---|---|---|
| `roman` | `<kind text="V7"/>` (non-standard; surface in `text`) | `text` attr → parsed as surface |
| `figuredBass` | `<kind text="6-5"/>` (non-standard) | `text` attr → parsed as surface |
| `nashville` | `<kind text="4m"/>` (non-standard) | `text` attr → parsed as surface |
| `functional` | not representable | — |
| `noChord` | `<kind text="N.C.">none</kind>` | `text` or inner `none` → `noChord` |
| `text` | `<kind text="…"/>` | `text` attr → `TextSemantic.text` |

---

## Time-aligned positions (schema 0.2.1)

`hamonpy.adapters.musicxml.musicxml_to_hamon(text)` builds a positioned
`HamonSequence`: each `<harmony>` becomes a `HarmonyGroup` that carries its
`position` (`{ measure, beat }`). HAMON works the beat out from the MusicXML time
model:

- `<divisions>` sets divisions-per-quarter, and it persists across measures.
- Elapsed time builds up within a measure from `<note>` durations (a `<chord>`
  note doesn't advance time), `<forward>`, and `<backup>`.
- A `<harmony><offset>` (in divisions) shifts the chord off the current position.
- `beat = (elapsed + offset) / divisions + 1` (1-based).

The `hamon convert` CLI uses this positioned adapter for MusicXML; the flat
`formats._extract_musicxml` (surface strings only) is still there when you don't
need positions.

---

## Losses and ambiguities

- **`text` vs. semantic divergence**: When `text="Δ7"` but the inner content is `major-seventh`, HAMON goes with `text` and produces `CΔ7`. A tool that reads only the semantic keyword and ignores `text` will display something else.
- **`<degree>` elements**: Extension and alteration elements (`#11`, for instance) don't make it into HAMON's alteration tokens unless they also appear in the `text` attribute.
- **Display-only `text`**: Some exporters — older Finale versions among them — write arbitrary strings in `text` that don't parse cleanly. HAMON falls back to `textLabel` for those.
- **Time anchoring**: `<harmony>` elements have an `<offset>` child and are positioned relative to the enclosing `<measure>`. HAMON currently extracts a flat label list and keeps no beat position.

---

## How HAMON reads MusicXML

hamonpy reads MusicXML with a pure-Python, text-level extractor
(`hamonpy/hamonpy/adapters/formats.py`, `_extract_musicxml`):

1. Finds every `<harmony>…</harmony>` block by regex.
2. Reads `<root-step>` (required — a block with no root is skipped) and the optional numeric `<root-alter>`, converting the alteration to an ASCII accidental (`1`→`#`, `-1`→`b`, `2`→`x`, `-2`→`bb`).
3. Reads the chord quality from the `<kind>` `text` attribute first, then the inner `<kind>` text, and normalizes it through a keyword map (`major`→`""`, `minor`→`m`, `dominant-seventh`→`7`, `major-seventh`→`maj7`, `half-diminished-seventh`→`ø7`, and so on).
4. Reads the optional `<bass-step>`/`<bass-alter>` and appends it as a slash bass (`/E`).
5. Assembles `{root}{accidental}{quality}{bass}` into one surface string per block, then deduplicates.

For position-aware reading — each `<harmony>` becomes a `HarmonyGroup` carrying its `{ measure, beat }` — use the `hamonpy.adapters.musicxml.musicxml_to_hamon(text)` adapter described above; `_extract_musicxml` gives you the flat surface list.

---

## Examples from the HAMON fixture corpus

| Fixture | `<kind>` inner | `<kind text>` | HAMON surface | `kind` |
|---|---|---|---|---|
| `C_major` | `major` | — | `C` | `chordSymbol` |
| `Bb_major` | `major` | — | `Bb` | `chordSymbol` |
| `C_minor` | `minor` | `m` | `Cm` | `chordSymbol` |
| `C_delta7` | `major-seventh` | `Δ7` | `CΔ7` | `chordSymbol` |
| `C_M7` | `major-seventh` | `M7` | `CM7` | `chordSymbol` |
| `C_maj7` | `major-seventh` | `maj7` | `Cmaj7` | `chordSymbol` |
| `G_dom7` | `dominant` | `7` | `G7` | `chordSymbol` |
| `B_hdim7` | `half-diminished-seventh` | — | `Bø7` | `chordSymbol` |
| `C_sus4` | `suspended-fourth` | `sus4` | `Csus4` | `chordSymbol` |

Full fixture files: `fixtures/chords/`.
