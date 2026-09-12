# Tutorial: encoding harmony with HAMON

HAMON gives you **two serializations of one model**:

- **HAMON surface** — a compact, human-writable text line (`Cmaj7`, `m:1,ts:1,cs:Dm7,rn:ii7`).
  This is the format you *type*.
- **HAMON JSON** — the canonical, typed structure (`grammar/hamon-schema.json`). This is the
  **hub** every other format maps to and from.

Parsing turns surface into JSON; serializing turns JSON back into surface. The two round-trip
cleanly: `parse(serialize(x)) == x`. This tutorial starts with a single chord and works up to a
positioned, analysed progression, showing both forms side by side.

> A note on the engraved staves throughout: they are **illustrative only**. HAMON encodes harmony
> *labels*, not notes. The label is the source of truth; the score is just there to help you read it.

---

## 1. Your first label — a single chord

The smallest HAMON document is a single label. Here it is as surface:

```
@cs
Cmaj7
```

`@cs` is an optional **system hint** — it says "this sequence is chord symbols" (see
[systems.md](systems.md)). The label `Cmaj7` is a C major seventh chord.

![A single Cmaj7 chord symbol on a staff](tutorial-assets/cmaj7.svg)

Now the same label as **HAMON JSON**. The exact glyphs are kept in `surface`, and the parsed
meaning goes in `semantic`:

```json
{
  "sequenceSystemHint": "cs",
  "groups": [
    { "primary": [ {
      "surface": "Cmaj7",
      "semantic": { "kind": "chordSymbol", "root": { "note": "C" }, "quality": "major", "seventh": "maj7" },
      "detectedSystem": "cs", "system": "cs"
    } ] }
  ]
}
```

Two ideas show up right away:

- **`surface` vs `semantic`.** `surface` is lossless (`"Cmaj7"`); `semantic` is the normalized
  reading. `CM7`, `CΔ7`, and `Cmaj7` all share one semantic but each keeps its own surface.
- **Groups.** A sequence is a list of **groups**, one per time point. Each group holds one or more
  `primary` labels — more than one when several analytical readings coexist (see §4).

---

## 2. The surface at a glance

A few common chord-symbol glyphs (all optional spellings normalize to the same semantic):

| Surface | Meaning |
|---|---|
| `C` | C major triad |
| `Cm` / `Cmin` / `C-` | C minor |
| `C7` | C dominant seventh |
| `Cmaj7` / `CM7` / `CΔ7` | C major seventh |
| `Cm7b5` / `Cø7` | C half-diminished seventh |
| `Cdim7` / `C°7` | C diminished seventh |
| `C/E` | C major with E in the bass |
| `NC` / `N.C.` | no chord |

Other systems use their own spellings: Roman numerals (`V7`, `ii°6`), Nashville (`1`, `5-4`),
figured bass (`6`, `6-5`), functional (`T`, `D`, `S`). See [systems.md](systems.md).

---

## 3. A progression, in time — measures, beats, meter

Real music sits at a point in time. Since v0.4 a group can start with **position items** (written
first, comma-separated), and the sequence can declare its **meter**:

```
@cs
@meter:4/4
m:1,ts:1,Dm7
m:2,ts:1,G7
m:3,ts:1,Cmaj7
```

- **`@meter:4/4`** — the time signature. Its numerator is the beat count, so it bounds the valid
  `ts` range to `[1, 5)` (see [positions.md](positions.md)).
- **`m:1,ts:1`** — measure 1, beat 1. `ts:` follows MEI
  [`data.BEAT`](https://music-encoding.org/guidelines/v5/data-types/data.BEAT.html) (1-based,
  decimals allowed).

![A ii–V–I chord chart: Dm7, G7, CMaj7 in 4/4](tutorial-assets/ii-v-i.svg)

In JSON, each group gets its own position and the meter lives in a top-level array:

```json
{
  "sequenceSystemHint": "cs",
  "meters": [ { "numerator": 4, "denominator": 4, "fromGroup": 0 } ],
  "groups": [
    { "primary": [ { "surface": "Dm7", "semantic": { "kind": "chordSymbol", "root": { "note": "D" }, "quality": "minor", "seventh": "min7" }, "detectedSystem": "cs" } ],
      "position": { "measure": 1, "beat": 1.0 } },
    { "primary": [ { "surface": "G7",  "semantic": { "kind": "chordSymbol", "root": { "note": "G" }, "quality": "major", "seventh": "dom7" }, "detectedSystem": "cs" } ],
      "position": { "measure": 2, "beat": 1.0 } },
    { "primary": [ { "surface": "Cmaj7", "semantic": { "kind": "chordSymbol", "root": { "note": "C" }, "quality": "major", "seventh": "maj7" }, "detectedSystem": "cs" } ],
      "position": { "measure": 3, "beat": 1.0 } }
  ]
}
```

A `ts` that falls outside its meter (say `ts:5` in `4/4`) is a **non-blocking warning**, never an
error. HAMON has to round-trip imperfect sources, so it never rejects them.

A position can also say **when in seconds** (`s:`, since v0.5), which is what an audio
annotation states, and it can say both at once:

```
m:1,ts:1,s:0,Dm7
m:2,ts:1,s:2.4,G7
```

The clocks sit side by side and neither is computed from the other — see
[positions.md](positions.md#the-two-clocks-s-physical-time-v05).

---

## 4. Layered analysis — a chord *and* its Roman numeral

One sonority can carry several **analytical layers** in a single group, joined by commas with
short tags (`cs:` chord symbol, `rn:` Roman, `fb:` figured bass, `fn:` functional). A `@key:`
directive opens a tonal region, which is what gives the Roman numerals something to mean:

```
@meter:4/4
@key:C
m:1,ts:1,cs:Dm7,rn:ii7
m:2,ts:1,cs:G7,rn:V7
m:3,ts:1,cs:Cmaj7,rn:I
```

Each group's `primary` now carries **two** labels — the chord symbol and the Roman numeral — and
each one records its own `layer`:

```json
{ "primary": [
    { "surface": "Dm7", "layer": "chord",  "semantic": { "kind": "chordSymbol", "root": { "note": "D" }, "quality": "minor", "seventh": "min7" } },
    { "surface": "ii7", "layer": "degree", "semantic": { "kind": "roman", "degree": "ii", "tail": "7" } }
  ],
  "position": { "measure": 1, "beat": 1.0 } }
```

The `@key:C` region is recorded just once, at the top level, in `regions` (see
[analysis.md](analysis.md) for tonicizations, modulations, chord-scales, and non-harmonic tones).

---

## 5. Figured bass

Figured bass is another system. `@fb` hints it at the sequence level; `fb:` tags it inside a
layered group. Figures use `-` to stack intervals — `6-5` means a 6 moving to a 5:

```
@fb
@meter:4/4
m:1,ts:1,fb:6-5
m:1,ts:3,fb:6
```

```json
{ "primary": [ { "surface": "6-5", "semantic": { "kind": "figuredBass", "number": 6, "tail": "-5" }, "detectedSystem": "fb" } ],
  "position": { "measure": 1, "beat": 1.0 } }
```

(A real figured-bass example — Mozart, K. 282/i — ships in `ICCCM26/examples/sat_mozart_fb.hamon`.)

---

## 6. The JSON structure, in one view

```
HamonSequence
├─ version?              "0.4.0"
├─ sequenceSystemHint?   "cs" | "rn" | "ns" | "fb" | "fun" | "auto"
├─ meters?               [ { numerator, denominator, fromGroup } ]      ← time signatures (§3)
├─ regions?              [ { key, kind, fromGroup, toGroup?, scales? } ] ← @key: analysis (§4)
└─ groups                [ HarmonyGroup ]
   └─ HarmonyGroup
      ├─ primary         [ HarmonyLabel ]        ← one per layer (§4)
      ├─ alternatives?   [ [ HarmonyLabel ] ]    ← competing whole readings
      └─ position?       { measure?, beat?, time?, seconds?, ref? }   ← where it starts (§3)
         HarmonyLabel
         ├─ surface      "Dm7"        ← exact glyphs (lossless)
         ├─ layer?       "chord" | "degree" | "bass" | "function" | …
         ├─ semantic     { kind: "chordSymbol" | "roman" | "nashville" | "figuredBass" | "functional" | "noChord" | "text", … }
         └─ system       detected notation system
```

`grammar/hamon-schema.json` is the normative JSON Schema (2020-12). Everything above is optional
except `groups` and each group's `primary`.

---

## 7. Round-tripping in code

**Python (`hamonpy`):**

```python
from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_json, sequence_to_hamon_text

seq = parse_hamon_sequence("@cs\n@meter:4/4\nm:1,ts:1,Dm7\nm:2,ts:1,G7\nm:3,ts:1,Cmaj7")
print(sequence_to_json(seq))         # → canonical JSON
print(sequence_to_hamon_text(seq))   # → back to surface (round-trips)
```

---

## Where next

- **[positions.md](positions.md)** — measures, beats, `@meter`, and absolute/reference anchors.
- **[analysis.md](analysis.md)** — the full analytical layer (regions, tonicizations, chord-scales,
  non-harmonic tones, alternative readings).
- **[systems.md](systems.md)** — the `@` system hint vs the per-label detected system vs the layer tag.
- **[index.md](index.md)** — every source/annotation format HAMON maps to and from.
