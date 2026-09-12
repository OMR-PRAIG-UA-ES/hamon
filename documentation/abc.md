# ABC Notation — Harmony Encoding

## Overview

[ABC notation](https://abcnotation.com/) is a plain-text notation widely used for folk, traditional, and session music. It embeds harmony labels as **quoted strings**, placed right before the note they apply to.

ABC keeps no separate semantic structure for harmony — the quoted string is always a plain surface label. HAMON parses whatever is inside the quotes with the same grammar it uses for every other format, pulling the quoted strings out with a text-level regex extractor.

---

## Chord symbol syntax

A chord symbol is a quoted string that sits directly before a note, with no space between them:

```
"Am7"A2 "G7"G4
```

The ABC standard recommends the format `<note><accidental><type>/<bass>`:

- `<note>` — `A`–`G`
- `<accidental>` — `b` (flat) or `#` (sharp)
- `<type>` — quality and extension suffix: `m`, `min`, `maj`, `dim`, `aug`, `+`, `sus`, `7`, `9`, etc.
- `/<bass>` — optional slash bass note

```
"C"C         % C major
"Am"A        % A minor
"G7"G        % G dominant seventh
"F#min7"F    % F# minor seventh
"C/E"E       % C over E bass
"Bb"B        % B-flat major
```

ABC implementations are liberal about chord spellings; the standard enforces no strict grammar beyond the recommended format. That looseness suits HAMON's surface-first approach.

### Alternate chords

ABC allows alternate chords for display (playback may ignore them):

```
"G(Em)"G     % G, with Em as an alternate voicing label
```

HAMON grabs the whole quoted string and parses it. If the content doesn't match the `chordSymbol` rule, it falls through to `textLabel`.

### Annotations vs. chord symbols

A quoted string that starts with `^`, `_`, `<`, `>`, or `@` is an **annotation** — a text-placement marker, not a chord symbol. HAMON's ABC extractor skips any string beginning with one of these characters.

---

## Non-chord-symbol labels

ABC has no native syntax for Roman numerals, figured bass, Nashville numbers, or functional labels. In practice people just write them as quoted strings, and HAMON's grammar works out the system from the content:

```
"V7"C        % Roman numeral — hamon detects kind: "roman"
"6-5"C       % Figured bass — hamon detects kind: "figuredBass"
"4m"C        % Nashville — hamon detects kind: "nashville"
"N.C."z      % No chord — hamon detects kind: "noChord"
```

---

## Mapping: JSON fields → ABC

Every mapping below is stated against the canonical JSON schema (`grammar/hamon-schema.json`). ABC stores all harmony as a plain quoted surface string — there is no per-field structure.

| JSON field | HAMON → ABC | ABC → HAMON | Loss / note |
|---|---|---|---|
| `surface` (any `kind`) | `"CΔ7"` (quoted surface string) | quoted string content → `surface` | none — surface stored verbatim |
| `semantic` (any `kind`) | not encoded separately | derived by parsing `surface` | no structured fields in ABC |
| `rendering.*` | reflected in `surface` | recovered by parsing `surface` | glyph variants preserved via `surface` |

All `kind` values map the same way:

| JSON `kind` | ABC quoted string example |
|---|---|
| `chordSymbol` | `"CΔ7"`, `"Am7"`, `"Bb"`, `"Bø7"` |
| `roman` | `"V7"`, `"ii"`, `"bVII"` |
| `figuredBass` | `"6-5"`, `"4-3"` |
| `nashville` | `"2m"`, `"b7"` |
| `functional` | `"T"`, `"D"` |
| `noChord` | `"N.C."` |
| `text` | `"Ger65"`, `"It6"` |

---

## Losses and ambiguities

- **No system declaration**: at the encoding level, ABC can't tell a Roman numeral from a chord symbol. HAMON's grammar infers the system from the content, and a `@<system>` hint in the `.hamon` output settles the edge cases.
- **Annotation prefix collision**: strings starting with `^`, `_`, `<`, `>`, `@` are ABC annotations, not chords, so HAMON skips them.
- **Alternate chord notation** (`"G(Em)"`): HAMON keeps the full string, but whether the parenthesized part is an alternative or an extension is ambiguous — it lands in `rendering.rawParts` or `textLabel`.
- **Time anchoring**: ABC ties chord symbols to notes by their position in the text stream. HAMON pulls out a flat label list and does not keep beat position.

---

## How HAMON reads ABC

The adapter (`hamonpy/hamonpy/adapters/formats.py`, `_extract_abc`):

1. Scans the source for all `"…"` quoted strings.
2. Skips strings starting with annotation characters (`^`, `_`, `<`, `>`, `@`).
3. Returns the content of each remaining quoted string as a surface label.

---

## Examples from the HAMON fixture corpus

| Fixture | ABC snippet | HAMON surface | HAMON `kind` |
|---|---|---|---|
| `C_major` | `"C"C` | `C` | `chordSymbol` |
| `Bb_major` | `"Bb"B` | `Bb` | `chordSymbol` |
| `C_delta7` | `"CΔ7"C` | `CΔ7` | `chordSymbol` |
| `B_hdim7` | `"Bø7"B` | `Bø7` | `chordSymbol` |
| `rn_V7` | `"V7"C` | `V7` | `roman` |
| `fb_6_5` | `"6-5"C` | `6-5` | `figuredBass` |
| `ns_2m` | `"2m"C` | `2m` | `nashville` |

Full fixture files: `fixtures/chords/`, `fixtures/roman/`, `fixtures/figuredbass/`, `fixtures/nashville/`.
