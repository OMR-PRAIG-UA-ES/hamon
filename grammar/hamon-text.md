# HAMON text format

Version: 0.1.0
File extension: `.hamon`
Formal grammar: `grammar/hamon.ebnf`

The HAMON text format is the compact, human-readable serialization of a `HamonSequence`, one of three alongside `hamon-schema.json` (JSON) and `hamon-xml.md` (XML). It writes only the `surface` string of each `HarmonyLabel`; the semantic fields are recovered later by parsing that surface with the ANTLR4 grammar.

---

## File structure

```
@version:0.1.0
@cs
CΔ7
Am7
G7(#11)/D
C
```

```
@version:0.1.0
@rn
I
IV
V7
I
```

```
@fb
6-5
4-3
```

### Version declaration (optional, first line)

```
@version:<semver>
```

Maps to `HamonSequence.version`. Declares which version of the HAMON standard this sequence targets. When both are present, it must come before the system hint. Example: `@version:0.1.0`. When it's absent, the version is unspecified, and consumers should treat the sequence as compatible with the current standard.

### System hint (optional)

```
@<systemId>
```

Maps to `HamonSequence.sequenceSystemHint`. Values: `auto`, `cs`, `rn`, `ns`, `fb`, `fun`, `text`. When it's absent, the system is detected label by label.

### Groups — one per line

Each non-empty line after the optional hint is one `HarmonyGroup`, corresponding to one time point. Line order is temporal order.

### Labels within a group — `,` separator

Several labels on the same line, comma-separated, form the group's `primary` list — simultaneous labels at the same time point:

```
CΔ7, Am7
```

→ `HarmonyGroup.primary = [HarmonyLabel("CΔ7"), HarmonyLabel("Am7")]`

### Alternative layers — `|` separator

`|` separates alternative `harmonyList` slices within one group. The first slice is `primary`; each slice after it is one element of `alternatives`:

```
I | CΔ7
```

→ `primary = [HarmonyLabel("I")]`, `alternatives = [[HarmonyLabel("CΔ7")]]`

This encodes the same time point in two different notation systems — for example, a Roman numeral analysis next to a chord symbol.

### Quoted labels

A label that contains commas or pipe characters must be quoted:

```
"C, the tonic"
```

→ `TextSemantic.text = "C, the tonic"`

---

## Mapping: JSON fields → HAMON text

Every mapping below is relative to the canonical JSON schema (`grammar/hamon-schema.json`). The text format carries all its semantic content implicitly, through the `surface` string; there are no separate per-field encodings.

### Sequence level

| JSON field | HAMON → text | text → HAMON |
|---|---|---|
| `version` | `@version:0.1.0` on first line | `@version:<semver>` → `version` |
| `sequenceSystemHint` | `@cs` on second line (after version if present) | line starting with `@` + system id → `sequenceSystemHint` |
| `groups` | one `harmonyGroup` per line | each non-empty line → one `HarmonyGroup` |

### Group level

| JSON field | HAMON → text | text → HAMON |
|---|---|---|
| `primary` | first comma-separated list on the line | tokens before first `\|` → `primary` |
| `alternatives[0]` | after first `\|` | tokens after `\|` → `alternatives[0]` |
| `alternatives[n]` | after nth `\|` | nth slice → `alternatives[n]` |

### Label level

| JSON field | HAMON → text | text → HAMON | Notes |
|---|---|---|---|
| `surface` | written verbatim | the token itself | always present; exact original glyphs |
| `semantic` | not encoded directly | derived by parsing `surface` | recovered by ANTLR4 parser + normalizer |
| `rendering` | reflected in `surface` | derived from parsed surface | glyph variants preserved because `surface` is exact |
| `detectedSystem` | not encoded | derived from parsed surface | set by grammar/normalizer |
| `system` | `@<systemId>` hint at sequence level | resolved from hint + `detectedSystem` | per-label overrides not yet supported |

### Per-kind surface conventions

The `surface` string written for each kind follows the conventions below. When serializing semantic fields back into a surface string, the writer uses the `rendering` hints to preserve the original glyphs; when no rendering is present, it falls back to the canonical forms.

#### `chordSymbol`

```
surface = root.note
        + rendering.accidentalGlyphs[root.accidental] (or canonical: # b x bb n)
        + rendering.qualityGlyph (or canonical quality if non-major)
        + rendering.seventhGlyph (or canonical seventh)
        + extensions joined
        + alterations joined
        + "/"+bass.note+accidental  (if bass present)
```

| JSON fields | Canonical text surface |
|---|---|
| `root:{note:"C"}`, `quality:"major"` | `C` |
| `root:{note:"A"}`, `quality:"minor"` | `Am` |
| `root:{note:"C"}`, `quality:"major"`, `seventh:"maj7"` | `Cmaj7` (or `CΔ7`, `CM7` if rendering hints present) |
| `root:{note:"G"}`, `quality:"major"`, `seventh:"dom7"` | `G7` |
| `root:{note:"B"}`, `quality:"half-diminished"`, `seventh:"hdim7"` | `Bø7` |
| `root:{note:"C"}`, `quality:"major"`, `bass:{note:"E"}` | `C/E` |
| `root:{note:"C"}`, `quality:"major"`, `suspensions:[4]` | `Csus4` |

#### `roman`

```
surface = prefixAccidentals.join("")
        + degree
        + tail (if present)
        + "/"+secondary (if present)
```

| JSON fields | Text surface |
|---|---|
| `degree:"V"` | `V` |
| `degree:"V"`, `tail:"7"` | `V7` |
| `prefixAccidentals:["b"]`, `degree:"VII"` | `bVII` |
| `degree:"V"`, `secondary:"V"` | `V/V` |

#### `nashville`

```
surface = prefixAccidentals.join("")
        + number
        + tail (if present)
        + "/"+secondary (if present)
```

| JSON fields | Text surface |
|---|---|
| `number:4` | `4` |
| `number:2`, `tail:"m"` | `2m` |
| `prefixAccidentals:["b"]`, `number:7` | `b7` |

#### `figuredBass`

```
surface = prefixAccidentals.join("")
        + number
        + tail (if present)
```

| JSON fields | Text surface |
|---|---|
| `number:6`, `tail:"-5"` | `6-5` |
| `number:4`, `tail:"-3"` | `4-3` |

#### `functional`

```
surface = chain.join("->")
```

| JSON fields | Text surface |
|---|---|
| `chain:["T"]` | `T` |
| `chain:["D","T"]` | `D->T` |

#### `noChord`

Canonical surface: `N.C.`  
Accepted alternatives: `NC`, `n.c.`, `NoChord`

#### `text`

The `text` field, written verbatim. If it contains commas or pipes, it is quoted:

```
"Ger65"
```

---

## Complete example

```
@version:0.1.0
@cs
CΔ7
Am7
F
G7
CΔ7
```

Parsed as `HamonSequence`:

```json
{
  "version": "0.1.0",
  "sequenceSystemHint": "cs",
  "groups": [
    { "primary": [{ "surface": "CΔ7",  "system": "cs", "semantic": { "kind": "chordSymbol", "root": { "note": "C" }, "quality": "major", "seventh": "maj7" }, "rendering": { "seventhGlyph": "Δ" } }], "alternatives": [] },
    { "primary": [{ "surface": "Am7",  "system": "cs", "semantic": { "kind": "chordSymbol", "root": { "note": "A" }, "quality": "minor", "seventh": "min7" }, "rendering": { "qualityGlyph": "m", "seventhGlyph": "7" } }], "alternatives": [] },
    { "primary": [{ "surface": "F",    "system": "cs", "semantic": { "kind": "chordSymbol", "root": { "note": "F" }, "quality": "major" } }], "alternatives": [] },
    { "primary": [{ "surface": "G7",   "system": "cs", "semantic": { "kind": "chordSymbol", "root": { "note": "G" }, "quality": "major", "seventh": "dom7" }, "rendering": { "seventhGlyph": "7" } }], "alternatives": [] },
    { "primary": [{ "surface": "CΔ7",  "system": "cs", "semantic": { "kind": "chordSymbol", "root": { "note": "C" }, "quality": "major", "seventh": "maj7" }, "rendering": { "seventhGlyph": "Δ" } }], "alternatives": [] }
  ]
}
```

---

## Relationship to the other encodings

| Encoding | File | Hub role | Surface preserved |
|---|---|---|---|
| **JSON** | `hamon-schema.json` | canonical hub | via `surface` field |
| **XML** | `hamon-xml.md` | XML counterpart to JSON | via `surface` attribute on `<label>` |
| **Text** | `hamon.ebnf` / `.hamon` | compact surface form | is the surface |

The text format is the most compact, and the easiest to edit by hand. JSON is the authoritative semantic record. XML is there for pipelines that require XML. All three round-trip: text → JSON (parse), JSON → text (serialize from `surface`, or reconstruct from semantic + rendering), JSON → XML, and XML → JSON.
