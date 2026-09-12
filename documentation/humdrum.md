# Humdrum **kern — Harmony Encoding

## Overview

[Humdrum](https://www.humdrum.org/) is David Huron's toolkit for music analysis. Everything in it is built around **spines**: parallel streams of tokens separated by tabs, each named by an **exclusive interpretation** header on the first line (`**kern`, `**harm`, and so on). One file can carry several spines at once, each describing a different aspect of the same music.

Harmony goes in its own spines. The spine type fixes two things: the notation system (chord symbols, Roman numerals, figured bass, or functional) and, for chord symbols, which vocabulary standard applies. HAMON maps every Humdrum harmony spine into its unified `HamonSequence` AST.

---

## File structure

A minimal Humdrum file comes in three parts:

```
**harm          ← exclusive interpretation (spine header)
I               ← data record (one per "event")
V7              ← data record
*-              ← spine terminator
```

Multi-spine files tab-separate their tokens. Comments start with `!` (local) or `!!` (global). Barlines start with `=`. Tandem interpretations — tempo, key, meter, and the like — start with `*` but aren't `*-`.

```
**kern	**harm
=1	=1
4c 4e 4g	I
4g 4b 4d	V
=2	=2
1c 1e 1g	I
*-	*-
```

HAMON reads harmony only from the spines that carry it; it ignores the `**kern` pitch data when extracting harmony.

---

## Layered import (analytical layer, v0.2.0)

A Humdrum score often carries **several harmony spines at once** — say `**harm`
(Roman-numeral analysis), `**function` (Riemannian function), and `**fb` (figured
bass) all running alongside `**kern`. The layered adapter
`hamonpy.adapters.humdrum.humdrum_to_hamon(text)` keeps that alignment intact:

| Spine | Analytical layer |
|-------|------------------|
| `**harm` | `degree` |
| `**function` | `function` |
| `**fb` | `bass` (read as figured bass) |
| `**mxhm` / `**jazz` / `**irb` / `**harte` | `chord` |

Every data line with at least one non-null harmony token turns into one
`HarmonyGroup`, and the co-temporal spine tokens become its `primary` labels,
each tagged with its `HarmonyLabel.layer`. The `**function` spine un-shadows `D`
so it reads as the dominant rather than a D-major chord, and `**fb` numbers read
as figured bass. When a file has a **single** harmony spine, HAMON drops the
layer tag — you get a plain single-system reading — and sets the sequence hint to
match (`**harm`→`rn`, `**function`→`fun`, `**fb`→`fb`, chord spines→`cs`).

```
**kern  **harm  **function  **fb
4c      I       T           .
4g      V7      D           6-5
*-      *-      *-          *-
```

becomes two groups: `[rn:I, fn:T]` and `[rn:V7, fn:D, fb:6-5]`.

If you just need a flat, deduplicated list of surfaces with no layers, the
`formats.read_harmony_labels("kern_*", text)` extractor is still there — the
fixture round-trip tests use it.

### Time-aligned positions (schema 0.2.1)

`humdrum_to_hamon` follows the numbered barlines (`=N`) and sets each group's
`position = { measure }`. It leaves out the beat within the measure: pinning that
down would mean parsing the `**kern` spine's rhythm — the note durations — which
the harmony adapter doesn't read. Measure-level alignment is as fine as the
barlines alone can reliably get you. Bare `=` barlines (no number) produce no
position.

## Harmony spine types

### `**harm` — generic harmony

This is the catch-all spine for any written harmony label. In practice it holds whatever notation suits the piece: Roman numerals in analytical scores, Nashville numbers in pop and country, figured bass in Baroque works. You have to read a token's meaning from context — the key signature, the labels before it, or a HAMON `@<system>` hint.

```
**harm
I
IV
V7
I
*-
```

```
**harm
6-5
4-3
*-
```

```
**harm
1
4
5
2m
*-
```

HAMON routes `**harm` tokens by pattern:
- A Roman numeral pattern (`I`, `bVII`, `ii65`, …) → `roman`
- A figured bass pattern (`6-5`, `4-3`, `7-6`, …) → `figuredBass`
- A Nashville pattern (`1`, `4m`, `b7`, …) → `nashville`
- Anything else → chord symbol or `textLabel`

### `**mxhm` — MusicXML chord symbols

Chord symbols in the MusicXML convention: a root note (capital letter), an optional ASCII accidental (`#` or `b`), then a quality suffix. This spine type says outright that its vocabulary is "the same as MusicXML `<harmony>`".

```
**mxhm
C
Am
G7
Cmaj7
Bø7
*-
```

Accidentals look like `Bb`, `F#`, `Eb`. Quality suffixes follow the MusicXML kind-text conventions: `m`, `maj7`, `m7`, `7`, `dim`, `°`, `aug`, `+`, `ø7`, `sus4`, `sus2`, and so on.

### `**jazz` — jazz chord symbols

Chord symbols in jazz notation convention. The surface forms overlap heavily with `**mxhm`; the distinction mainly records provenance — a jazz lead sheet versus a MusicXML export — and can influence how enharmonic spellings get chosen. At the grammar level, HAMON treats `**jazz` exactly like `**mxhm`.

```
**jazz
CΔ7
Am7
G7
Bø7
Bb
*-
```

Unicode quality glyphs (`Δ`, `°`, `ø`) turn up often in jazz notation, and HAMON's `chordSymbol` rule accepts them.

### `**irb` — IRB chord symbols

Chord symbols in the International Reference Basis vocabulary — a chord-symbol standardization used in some academic and digital-library settings. The surface forms match jazz and MusicXML chord symbols, and at parse time HAMON treats `**irb` exactly like `**mxhm` and `**jazz`.

### `**fb` — figured bass

Figured bass notation: a bass pitch lives in `**kern`, and the `**fb` spine gives the interval structure above it. An `**fb` token holds the figures only — never the bass note.

```
**fb
6-5
4-3
7-6
*-
```

Figures are integers. When several sound at once, they stack vertically inside one token, separated by `-`. HAMON parses these as `figuredBass` labels through the `numberHarmony` rule — the hyphen-digit signal is what tells figured bass apart from Nashville numbers.

### `**function` — functional harmony

Functional harmony labels in Riemannian notation — T, S, D and their variants. This spine type comes out of Humdrum extensions used in German-language analytical traditions.

```
**function
T
S
D
T
*-
```

HAMON maps `**function` tokens to the `functionalHarmony` rule. It supports `T`, `S`, `D`, `PD`, `SD`, and `DD`. Secondary functions and variants (`Tp`, `Sp`, `DP`, and the like) fall through to `textLabel` until the grammar's `functionalHarmony` rule grows to cover them.

---

## Token conventions shared across spines

| Convention | Example | Notes |
|---|---|---|
| Null token | `.` | Spine continues with no new harmony; HAMON skips it |
| Rest token | `r` | No harmony; HAMON skips it |
| Barline | `=1`, `=||` | Not a harmony token; HAMON skips it |
| Tandem interpretation | `*M4/4`, `*k[b-]` | Not a harmony token; HAMON skips it |
| Comment | `! label` | Not a harmony token; HAMON skips it |

---

## Mapping: JSON fields → Humdrum

All mappings are relative to the canonical JSON schema (`grammar/hamon-schema.json`). Humdrum encodes every harmony as a plain-text token, and the spine type (`**mxhm`, `**harm`, `**fb`, `**function`) picks the notation system.

### Chord symbols (`kind: "chordSymbol"`) — spines `**mxhm`, `**jazz`, `**irb`

| JSON field | HAMON → Humdrum token | Humdrum token → HAMON | Loss / note |
|---|---|---|---|
| `root.note` | first char(s): `C`, `G`, `A` | first letter → `root.note` | none |
| `root.accidental: "sharp"` | `#` suffix on root: `C#` | `#` → `sharp` | ASCII only; `rendering.accidentalGlyphs` may hold original glyph |
| `root.accidental: "flat"` | `b` suffix: `Bb` | `b` → `flat` | none |
| `quality: "major"` | no suffix: `C` | no suffix → `major` | none |
| `quality: "minor"` | `m`: `Cm` | `m` → `minor` | none |
| `quality: "augmented"` | `+` or `aug`: `C+` | → `augmented` | none |
| `quality: "diminished"` | `°` or `dim`: `C°` | → `diminished` | none |
| `quality: "half-diminished"` | `ø`: `Cø` | → `half-diminished` | none |
| `seventh: "dom7"` | `7`: `G7` | `7` after root → `dom7` | none |
| `seventh: "maj7"` | `maj7`, `Δ7`, `M7`: `Cmaj7` | → `maj7`; glyph → `rendering.seventhGlyph` | multiple surface variants |
| `seventh: "min7"` | `m7`: `Am7` | → `min7` | none |
| `seventh: "dim7"` | `°7`: `B°7` | → `dim7` | none |
| `seventh: "hdim7"` | `ø7`: `Bø7` | → `hdim7` | none |
| `suspensions: [4]` | `sus4`: `Csus4` | → `suspensions:[4]` | none |
| `suspensions: [2]` | `sus2`: `Csus2` | → `suspensions:[2]` | none |
| `bass.note` | `/E`: `C/E` | after `/` → `bass.note` | none |
| `extensions[]` / `alterations[]` | appended to token: `C7(#11)` | captured in `rendering.rawParts` | structured extraction not yet implemented |

### Roman numerals (`kind: "roman"`) — spine `**harm`

| JSON field | HAMON → `**harm` | `**harm` → HAMON | Loss / note |
|---|---|---|---|
| `prefixAccidentals[]` | `b` / `#` prefix: `bVII` | prefix chars → `prefixAccidentals` | none |
| `degree` | Roman token: `V`, `ii` | token → `degree` | case preserved |
| `tail` | appended: `V65` | remaining chars → `tail` | not further parsed |
| `secondary` | `/V` suffix | after `/` → `secondary` | none |

### Figured bass (`kind: "figuredBass"`) — spines `**fb` or `**harm`

| JSON field | HAMON → token | token → HAMON | Loss / note |
|---|---|---|---|
| `number` | leading integer: `6` | first digit → `number` | none |
| `tail` | `-5` suffix: `6-5` | `-\d` signal → `figuredBass` kind; remainder → `tail` | none |

### Nashville (`kind: "nashville"`) — spine `**harm`

| JSON field | HAMON → token | token → HAMON | Loss / note |
|---|---|---|---|
| `prefixAccidentals[]` | `b` / `#` prefix: `b7` | prefix → `prefixAccidentals` | none |
| `number` | integer: `4` | digit → `number` | disambiguated from figuredBass by absence of `-\d` |
| `tail` | quality suffix: `4m` | suffix → `tail` | none |

### Functional (`kind: "functional"`) — spine `**function`

| JSON field | HAMON → token | token → HAMON |
|---|---|---|
| `chain[0]` | `T`, `S`, `D`, `PD`, `SD`, `DD` | token → `chain[0]` |
| `chain[1..n]` | not representable in a single token | — |

### Other

| JSON `kind` | HAMON → Humdrum | Humdrum → HAMON |
|---|---|---|
| `noChord` | `.` (null token) | `.` → skipped (no label) |
| `text` | token as-is | unmatched token → `TextSemantic` |

### Losses and ambiguities

- **`**harm` ambiguity**: The spine type on its own can't tell Roman numeral from Nashville. HAMON settles it by grammar detection — Roman tokens have letter-based degrees, Nashville tokens are pure integers with an optional quality suffix — and a `@<system>` hint in the output clears up anything left over.
- **Enharmonics**: Humdrum uses ASCII accidentals (`#`, `b`), and HAMON keeps the exact source spelling (surface-first).
- **Extensions beyond the grammar**: Complex chord symbols like `C7(#11b9)` that outrun the current HAMON grammar rules are kept losslessly as `textLabel`.
- **Time anchoring**: Humdrum encodes a harmony's time position through where its token sits within the spine. HAMON currently pulls out a flat label list and keeps no beat or onset information.
- **Multiple harmony spines**: If a file has both `**harm` and `**mxhm`, HAMON reads the leftmost matching column. Combining layers isn't supported yet.

---

## How HAMON reads Humdrum

hamonpy reads Humdrum with a pure-Python, text-level extractor
(`hamonpy/hamonpy/adapters/formats.py`, `_extract_kern`):

1. Scans for the first spine-header line — one carrying an exclusive interpretation like `**kern`, `**harm`, `**mxhm`, `**jazz`, `**irb`, `**harte`, `**fb`, or `**function`.
2. From that header, records which columns are harmony spines (`**harm`, `**mxhm`, `**jazz`, `**irb`, `**harte`, `**fb`, `**function`).
3. Reads down the data lines, skipping the spine terminator (`*-`), comments (`!`), tandem interpretations (`*…`), and barlines (`=`). For each harmony column it collects every non-null token (anything that isn't `.`).
4. Normalizes a few tokens on the way out — e.g. Humdrum Harte notation `C:maj7` becomes `Cmaj7`.
5. If no spine header is found, it falls back to grabbing any chord-like token (one that starts with a note letter `A`–`G`) from the non-comment lines.

Results are deduplicated, order-preserving. For layered, position-aware reading — several harmony spines kept aligned into `HarmonyGroup`s — use `hamonpy.adapters.humdrum.humdrum_to_hamon(text)` described above; `_extract_kern` gives you the flat surface list.

The format keys hamonpy recognizes for Humdrum harmony are `kern_harm`, `kern_mxhm`, `kern_jazz`, `kern_irb`, `kern_harte`, `kern_fb`, and `kern_function` (any key containing `kern` or `humdrum` routes here).

---

## How HAMON writes Humdrum

`hamonpy.export.hamon_to_humdrum(seq)` (the `humdrum` target of `hamon export` /
`hamon report`) is the mirror of the layered reader:

- **one spine per analytical layer** — a layered sequence such as
  `m:25,ts:1,cs:C,rn:I` becomes parallel `**mxhm` and `**harm` spines, one data line
  per group, with `.` where a layer is silent; an unlayered sequence is a single spine
  chosen by its system (`**mxhm`, `**harm`, `**fb`, `**function`);
- **the key as a tandem interpretation** — a tonal region opens with `*C:` / `*b-:`
  on every spine (upper case major, lower case minor), which the reader turns back
  into the region; a tonicization (`@key:V`) has no Humdrum spelling and is not written;
- **measures as barlines** — `=25` before the first group of each measure, from the
  groups' `m:` positions. The beat is not written: a harmony-only file has no
  `**recip` to place it on, so `ts:` is the one thing this round-trip loses.

Layers Humdrum has no spine for (`melodic`, `key`, `tone`) are omitted and reported as
loss by `hamon report`.

```
**mxhm	**harm
*C:	*C:
=25	=25
C	I
=28	=28
Fm7	iv7
Bb7	bVII7
*-	*-
```

---

## Examples from the HAMON fixture corpus

| Fixture | Spine | Token | HAMON `kind` | Notes |
|---|---|---|---|---|
| `C_major` | `**mxhm` | `C` | `chordSymbol` | major triad, no suffix |
| `Bb_major` | `**mxhm` | `Bb` | `chordSymbol` | flat accidental |
| `C_delta7` | `**jazz` | `CΔ7` | `chordSymbol` | Unicode delta glyph |
| `C_M7` | `**irb` | `CM7` | `chordSymbol` | capital-M major seventh |
| `B_hdim7` | `**mxhm` | `Bø7` | `chordSymbol` | half-diminished glyph |
| `C_sus4` | `**mxhm` | `Csus4` | `chordSymbol` | suspended fourth |
| `rn_V7` | `**harm` | `V7` | `roman` | dominant seventh Roman |
| `rn_ii` | `**harm` | `ii` | `roman` | lowercase = minor |
| `fb_6_5` | `**fb` | `6-5` | `figuredBass` | suspension figure |
| `fb_6_5` | `**harm` | `6-5` | `figuredBass` | same figure, different spine |
| `ns_2m` | `**harm` | `2m` | `nashville` | minor 2 |

Full fixture files: `fixtures/chords/`, `fixtures/roman/`, `fixtures/figuredbass/`, `fixtures/nashville/`.
