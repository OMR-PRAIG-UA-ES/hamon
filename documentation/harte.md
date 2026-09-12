# Harte Notation

Harte notation writes chord symbols as compact text, and it was built for automatic chord recognition (ACR) research. Christopher Harte and colleagues at Queen Mary, University of London proposed it, and it stuck: today it is the de-facto standard for MIREX chord evaluation and the Million Song Dataset derivatives.

## Reference

Harte, C., Sandler, M., Abdallah, S., & Gómez, E. (2005). Symbolic representation of musical chords: A proposed syntax for text annotations. *Proceedings of the 6th International Society for Music Information Retrieval (ISMIR) Conference*, 66–71.

## Syntax

```
chord = root ":" shorthand ["/" bass_interval]
      | "N"        (no chord)
      | "X"        (unknown / don't care)

root = note_name [accidental]
note_name = "A" | "B" | "C" | "D" | "E" | "F" | "G"
accidental = "b" | "#" | "bb" | "##"

shorthand = "maj" | "min" | "dim" | "aug"
           | "maj7" | "min7" | "7" | "dim7" | "hdim7" | "minmaj7"
           | "maj6" | "min6" | "9" | "maj9" | "min9"
           | "sus2" | "sus4"
           | "1"          (root only)
           | "5"          (power chord)
           | (*7)         (extended notation with degree list)

bass_interval = ["b" | "#" | "bb" | "##"] degree_number
```

### Examples

| Harte token | Meaning |
|------------|---------|
| `C:maj` | C major triad |
| `C:min` | C minor triad |
| `G:7` | G dominant seventh |
| `Ab:maj7` | A-flat major seventh |
| `D:min7` | D minor seventh |
| `B:hdim7` | B half-diminished seventh |
| `E:dim7` | E diminished seventh |
| `F:sus4` | F suspended fourth |
| `C:maj/3` | C major, first inversion (E bass) |
| `N` | No chord |

## Shorthand vocabulary

| Harte shorthand | Quality | Seventh | HAMON equivalent |
|-----------------|---------|---------|-----------------|
| `maj` | major | — | (no suffix) |
| `min` | minor | — | `m` |
| `dim` | diminished | — | `°` |
| `aug` | augmented | — | `+` |
| `maj7` | major | maj7 | `maj7` |
| `min7` | minor | min7 | `m7` |
| `7` | major | dom7 | `7` |
| `dim7` | diminished | dim7 | `°7` |
| `hdim7` | half-dim | hdim7 | `ø7` |
| `minmaj7` | minor | maj7 | `mMaj7` |
| `sus4` | major+sus4 | — | `sus4` |
| `sus2` | major+sus2 | — | `sus2` |
| `maj6` | major | — | `6` |
| `min6` | minor | — | `m6` |
| `9` | major | dom7+9 | `9` |
| `maj9` | major | maj7+9 | `maj9` |
| `min9` | minor | min7+9 | `m9` |
| `1` | root only | — | (omit) |
| `5` | power chord | — | `5` |

## Mapping to HAMON

Harte tokens map to HAMON `ChordSymbolSemantic`:

| Harte field | HAMON field | Notes |
|------------|-------------|-------|
| `root` note name | `root.note` | Uppercase |
| `root` accidental | `root.accidental` | `#` or `b` |
| `shorthand` | `quality` + `seventh` | See table above |
| `/bass_interval` | `bass` | Harte names the bass as an altered degree above the root (`/b7`), HAMON as a pitch class. The two convert both ways — the degree fixes the letter, the accidental fixes the pitch — so this is a mapping, not a guess. |

On import, HAMON drops the `:` separator and rewrites the shorthands: `min` becomes `m`, `dim` becomes `°`, and so on.

## Known limitations

- Extended degree lists like `(*3,b7)` have no first-class fields in HAMON; they land in `tail`.
- A **compound** bass degree returns as its simple equivalent (`/9` → `/2`): the two name the same pitch, and HAMON's `bass` is a pitch class, which does not record the octave that told them apart. A re-spelling, not a loss — `report.py` finds nothing, because the semantics are identical.
- `X` (unknown/don't care) has no HAMON equivalent, so HAMON skips it on import.
- `minmaj7` maps to a `mMaj7` tail in HAMON, and that round-trips losslessly. (Until 2026-09-01 it did not: the letter-led spellings `mmaj7`/`mM7` normalized to a **dominant** seventh, because the chord-tail tokenizer swallowed `mmaj` as one word and left a bare `7`. Every spelling is now pinned in `conformance/corpus.txt`.)

## File format

Harte tokens sit one per line in plain-text `.txt` or `.lab` files, usually with timestamps:

```
0.000	0.500	N
0.500	2.000	C:maj
2.000	4.000	G:7
4.000	6.000	F:maj
```

The adapter reads both layouts: bare tokens (one chord per line) and the tab-separated timestamp form.

Since v0.5 the timestamps are **not discarded**. Both columns are read, in the clock the file
states them in:

- the `start` seconds become the group's `Position.seconds`, written `s:0.5` in the surface;
- `end - start` becomes the label's extent, written `[dur:1.5s]` — the `s` suffix is what says
  it is seconds and not quarter notes.

So the example above imports as `s:0,N[dur:0.5s]` / `s:0.5,C[dur:1.5s]` / `s:2,G7[dur:2s]` /
`s:4,F[dur:2s]`. A bare token line states no time, so it gets no position and no extent —
nothing is inferred from line order, and the seconds are never converted into a metric
`m:`/`ts:` position or into quarters, which would need a tempo map the file does not carry.
See [positions.md](positions.md#the-two-clocks-s-physical-time-v05).

The **writer** emits the same two forms, and the choice is all-or-nothing for the file: it
writes `start end label` when **every** harmony states both an `s:` onset and a `[dur:…s]`
extent, and bare tokens otherwise. So a `.lab` imported into HAMON comes back out byte for
byte, which is what the physical clock was for — this round-trip used to lose 100% of the
file's positional content.

Two things it will not do:

- **Invent an end.** A harmony with an onset but no extent leaves a column this writer has
  no honest value for; deriving it from the next onset is precisely what the Dezrann writer
  was cured of, because the invented value comes back on re-import looking like source data.
- **Mix the two forms.** A `.lab` is a positional-column format, so a file with some timed
  lines and some bare ones is not one. A single untimed harmony drops the whole file to bare
  tokens, and the seconds the other groups had are lost — a real loss, which `report.py`
  reports as such rather than papering over.
