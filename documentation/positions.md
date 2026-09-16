# Time-aligned positions (measures & beats)

HAMON is a **harmony-label** standard. It tells you *what* the harmony is and *where* it
starts — not the note durations or rhythm, which stay in the source score. A harmony's
*extent* is implicit: it runs until the next label. Each harmony's **onset position** is
encoded optionally, at the **group** level. Since v0.4, HAMON also declares the **meter**
(`@meter:`), which is what lets a beat position (`ts`) be interpreted and range-checked.

## Surface: the position items (written first)

Since v0.4 the position is written **first** in the group, comma-separated with the labels,
using short `key:value` items. There are five forms, and you can combine them freely:

| Surface | Meaning | JSON (`group.position`) |
|---|---|---|
| `m:1,ts:3` | **measure : beat** | `{ "measure": 1, "beat": 3.0 }` |
| `m:4` | measure only | `{ "measure": 4 }` |
| `t:5/4` | **absolute musical** position, as a fraction of **quarter** notes | `{ "time": { "numerator": 5, "denominator": 4 } }` |
| `s:12.34` | **absolute physical** position, in **seconds** (v0.5) | `{ "seconds": 12.34 }` |
| `ref:note-9` | reference to a **score object** id (MEI `@startid`) | `{ "ref": "note-9" }` |

`ts:` is a **timestamp/beat** following MEI [`data.BEAT`](https://music-encoding.org/guidelines/v5/data-types/data.BEAT.html):
a **1-based decimal**, with fractions allowed (`ts:2.5`).

`t:` and `s:` are both absolute and are **not the same clock**: `t:` counts quarter notes
(musical time), `s:` counts seconds (physical time — audio, or one performance). Neither is
ever computed from the other; see [Hold, don't convert](#the-two-clocks-hold-dont-convert).

```
@version:0.5.0
@meter:4/4
@key:C
m:25,ts:1,cs:C,rn:I
m:27,ts:1,cs:F,rn:iv
m:28,ts:3,cs:Fm7,rn:ii
```

The position items come **before** the label(s), so an analysed chord and its position live
together in one comma-separated group (`m:3,ts:3,cs:A7[of:ii][scale:altered]`).

## Meter (time signature) — `@meter:N/D`

A `ts` beat only means something relative to a **time signature**. Since v0.4 a
`@meter:N/D` directive declares the meter in effect. Write it **at the start and at every
metric change** (just like `@key:`). The **numerator `N` is the beat count**, and that fixes
the valid range of `ts`: following MEI `data.BEAT`, the downbeat is `ts:1` and the next
barline is `ts:(N+1)`, so **`ts` spans `[1, N+1)`**.

| `@meter` | beats | valid `ts` |
|---|---|---|
| `4/4` | 4 | `1` … `< 5` (e.g. `4.5` ✓, `5` ✗) |
| `2/2` | 2 | `1` … `< 3` |
| `3/4` | 3 | `1` … `< 4` |
| `6/8` | 6 | `1` … `< 7` |

```
@meter:4/4
m:1,ts:1,cs:C
m:2,ts:4,cs:G7      # ts:4 ✓ (last beat of 4/4)
@meter:2/2          # metric change — from here ts spans [1,3)
m:3,ts:1,cs:C
```

- **Additive and optional.** A sequence with no `@meter` is still valid. Without one, the
  beat range is simply unknown, so `ts` goes unchecked.
- **Non-blocking validation.** A `ts` outside the current meter's range (say `ts:5` in
  `4/4`) is a **warning**, never a parse error — HAMON has to round-trip imperfect sources.
  (`hamonpy` emits a `HamonWarning`; the pure check is `hamonpy.validate.validate_positions`.)
- **JSON.** Meters serialize to an optional top-level `meters` array. Each entry is
  `{ "numerator", "denominator", "fromGroup" }`, where `fromGroup` is the index of the first
  group it governs.
- HAMON declares the meter **only to interpret `ts`**. It still does not model note
  durations or rhythm.

## JSON

Positions serialize to an optional `position` object on each `HarmonyGroup`
(`grammar/hamon-schema.json` → `HarmonyGroup.position`). It holds five fields, all optional
and freely combinable:

```json
{ "groups": [
  { "primary": [ { "surface": "C", "layer": "chord", "semantic": { "kind": "chordSymbol", … } } ],
    "position": { "measure": 25, "beat": 1.0 } }
] }
```

- `measure` (int) + `beat` (float, 1-based) — mirror an MEI `@tstamp`.
- `time` (fraction) — an **absolute** offset in **quarter notes**, independent of barlines.
  This one holds up when there is no bar structure to lean on. Quarters because that is what
  every source uses: DCML `quarterbeats`, Dezrann `start`, the DiLeMMa pitch arrays, music21
  offsets. `t:4` is the fifth quarter — in 4/4, the downbeat of bar 2.
- `seconds` (float, v0.5) — an **absolute** offset in **physical** time. This is what an
  audio annotation states, and until v0.5 it was the one thing HAMON could not hold.
- `ref` (string) — a score-object id (MEI `@startid`), for exact anchoring.

## Design rationale (scope)

- **Meter only bounds `ts`; no durations.** `@meter:` declares the time signature so a
  beat can be interpreted and range-checked. It stops there — HAMON does not duplicate the
  score's rhythmic model. It anchors *when a harmony begins*, and the span runs until the next label.
- **Optional and sparse.** Most exchange scenarios (lead sheets, label lists) need no
  positions at all. You add them only when time-alignment matters.
- **Four anchoring strategies coexist:** metric (`m:`/`ts:`), absolute musical (`t:`),
  absolute physical (`s:`), and structural (`ref:`). A converter stores whichever the
  source provides — all of them, if it provides all of them.

## Position loss (the ICCCM'26 matrix)

The ICCCM'26 loss matrix counts, inside each cell, the onsets the target can't carry
natively (`position` in the cell's itemised `lost_aspects`) — and since v0.5 that question
is asked **per clock**, because a target that holds one clock still loses the other. Most
score and annotation formats carry `measure:beat` (`POSITION_NATIVE` in
`hamonpy/capability.py`); the audio-time pair, Harte and JAMS, carry seconds instead
(`SECONDS_NATIVE`). So a metric onset is lost by **Harte** and **JAMS** only; a `s:` onset
is lost by everything except those two. DCML used to be counted with them because its
writer emitted the plain `chord/localkey/globalkey` table; it now writes the expanded
table's `mn`/`mn_onset`/`quarterbeats` columns for every placed group, so the format is
credited with what it has always held. A position counts as dropped only when the target can carry **none**
of the clocks it states.

## Mapping to/from formats

| Format | Carries position as |
|---|---|
| **MEI** | `<harm @tstamp>` (measure:beat) or `@startid` (→ `ref`) |
| **DCML** (the expanded table, ms3) | `mc`/`mn` → measure, `mn_onset` → beat, `quarterbeats` → `time` — read and written; a table with any of those columns is read as expanded |
| **DiLeMMa pitch arrays** | one row per **note**; the harmony's onset is the first note carrying it (`quarterbeats_playthrough` / `j_offset` → `time`) — see [dcml.md](dcml.md#pitch-arrays--the-dilemma-training-tables) |
| **Humdrum** | spine row alignment (implicit measure:beat) |
| **Harte `.lab`** | `start end label`; the `start` seconds → `s:` (v0.5) — a different clock, not a metric position |
| **JAMS** | observation `time` in seconds → `s:` (v0.5) |
| **RomanText**, **iReal**, bare **Harte labels** | measure numbers only, or none |

## Extent — how long a harmony lasts (v0.4.1, seconds since v0.5)

A position is an **onset**. The extent is `[dur:…]` and `[endref:…]`, and it lives on the
**label**, not the group — full reference in
[analysis.md](analysis.md#10-bis-extent-v041--how-long-a-reading-lasts). Absent means
*unknown*: the rule that a harmony runs to the next group is a computation, never stored.

That rule is right most of the time and wrong in four cases, which is why the field
exists — the last harmony of a piece (there is no next group), a harmony that ends before
the next one starts (a rest, an `N.C.`, a fermata close), an anacrusis or repeat where the
next label is not the next in time, and two `alternatives` that segment the same passage
differently.

Where the extent comes from, and where it still does not:

| Format | States extent as | HAMON |
|---|---|---|
| Dezrann `.dez` | `start` + `duration` (quarters) | ✅ read and written; the writer no longer fills the gap |
| DCML expanded | `quarterbeats` + `duration_qb` | ✅ read and written |
| DiLeMMa (AugmentedNet) | `a_duration` | ✅ read |
| MEI `<harm>` | `@tstamp2`, `@endid` | ✅ `@endid` → `endRef`; `@tstamp2` needs the meter, not read yet |
| Harte `.lab` | start + end, in **seconds** | ✅ read as `s:` + `[dur:…s]` (v0.5) — the [physical clock](#the-two-clocks-s-physical-time-v05) |
| JAMS | `time` + `duration`, in **seconds** | ✅ same, and written back |

Before this existed, a Dezrann round-trip was not lossless but *looked* lossless: the
writer recomputed `duration` from the gap, the re-parsed copy matched, and `report.py` —
which diffs the canonical dicts — could not object, because an aspect the AST does not
model can never be reported as `dropped`. It now is one.

## The two clocks: `s:` physical time (v0.5)

Until v0.5 HAMON had metric (`m:`/`ts:`), musical absolute (`t:`) and structural (`ref:`)
and **nothing in seconds**. So Harte and JAMS, whose *only* positional data is audio
seconds, came in with no position whatsoever — an interlingua that drops what a source
stated is not converting, it is discarding. `s:12.34` closes that: physical time is a
**fourth clock**, alongside the others rather than instead of them.

```
@version:0.5.0
@cs
s:0,C
s:2.5,F
s:4.25,G7
```

For a multimodal source — audio plus a transcription of it — both clocks are stated and
both are kept, in one position:

```
m:25,ts:1,s:48.5,G7
```

That line is the whole point. In the recording the **seconds are the certain datum** and
the bar is an estimate; in the score it is the other way round. Only holding both says
which is which.

### Hold, don't convert

> **Hold, don't convert.** Every clock a source states is stored as stated; a clock it did
> not state stays absent; conversions are computed on demand where a map exists. Never
> overwrite a stated clock with a derived one — that launders an estimate into a fact.

This is why there is no tempo field and no `s:` ⇄ `t:` conversion in the AST. Going from
one clock to the other needs a tempo map that the label stream does not have; a converter
that owns one can compute the crossing itself, and what it computes is its own, not the
source's. `hamonpy` therefore never fills `seconds` from `time` or the reverse — Harte's
importer sets only `seconds`, MEI's sets only `measure`/`beat`.

### The extent inherits the clock

An onset in seconds implies an extent in seconds, so `[dur:…]` takes an optional `s`
suffix: **`[dur:3/4]` is quarter notes, `[dur:1.85s]` is seconds**. One key, two clocks,
and the suffix is the whole difference — a bare value is never read as seconds. They are
separate fields (`attributes.duration` and `attributes.durationSeconds`) for the same
reason `t:` and `s:` are: a target that speaks quarters must see a seconds extent as
*absent*, not as a number it can use.

So the audio-time formats now keep both ends of their annotation:

| Format | States | HAMON |
|---|---|---|
| Harte `.lab` | `start end label`, in **seconds** | ✅ `start` → `s:`, `end - start` → `[dur:…s]` |
| JAMS | observation `time` + `duration`, in **seconds** | ✅ both, and both written back |

A bare Harte label list, with no columns, still gets no position and no extent: absent
means unknown. Harte's **writer** puts the columns back when every harmony states both, so
a `.lab` round-trips byte for byte; one untimed harmony and the whole file falls back to
bare tokens, because a half-timed `.lab` is not a `.lab` (see
[harte.md](harte.md#file-format)).

> **Measureless music.** Unmetered and **mensural** repertoire has no barlines and no
> time signature, so `@meter:` and `m:`/`ts:` don't apply — they assume a measure, exactly as
> `data.BEAT` does. There, the absolute `t:` and `ref:` items are your anchors. See the
> "measureless harmony" open item.

See also: [analysis.md](analysis.md) (the analytical layer), [dcml.md](dcml.md)
(expanded time-aligned tables), [systems.md](systems.md) (system hint vs analytical layer).
