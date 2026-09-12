# JAMS

**JAMS** (JSON Annotated Music Specification) is a JSON container for time-aligned MIR
annotations — chords, keys, beats, segments, melody, tags. Each annotation carries rich
metadata: who annotated it, which corpus and data source it came from, whether it was
validated, and a confidence score. It is a common way to distribute audio-derived
annotations, chord-recognition corpora in particular.

## Reference

Humphrey, E. J., Salamon, J., Nieto, O., Forsyth, J., Bittner, R. M., & Bello, J. P. (2014).
JAMS: A JSON Annotated Music Specification for reproducible MIR research. *Proceedings of the
15th ISMIR Conference*, 591–596. Docs: <https://jams.readthedocs.io/en/stable/jams_structure.html>

## Structure

```
JAMS
├─ file_metadata     { title, artist, release, duration (s), identifiers, jams_version }
├─ annotations[]
│  ├─ namespace              e.g. "chord", "chord_harte", "key_mode", "beat", "segment_open"
│  ├─ data[]                 { time (s), duration (s), value, confidence }
│  ├─ annotation_metadata    { annotator, corpus, data_source, curator, validation, … }
│  └─ sandbox                arbitrary payload
└─ sandbox
```

For **harmony**, the relevant namespaces are:

- **`chord`** / **`chord_harte`** — the `value` is a **[Harte](harte.md)** chord label
  (`"C:maj7"`, `"D:min7/b3"`, `"N"`).
- **`key_mode`** — the `value` is `"TONIC:mode"` (`"C:major"`, `"Bb:minor"`).

Observation `time`/`duration` are in **audio seconds** — HAMON's `s:` clock since v0.5.

## Mapping to/from HAMON (`hamonpy/hamonpy/adapters/jams.py`)

| JAMS | HAMON |
|---|---|
| `chord` / `chord_harte` observation `value` | a chord-symbol `HarmonyLabel` (parsed via the Harte adapter) |
| observation order (by `time`) | group order |
| `key_mode` value | a tonal region (`@key:`) |
| observation `time` (audio seconds) | `Position.seconds` — the `s:` clock (v0.5); written back on export |
| observation `duration` (audio seconds) | `attributes.durationSeconds`, surface `[dur:1.5s]` — the extent in the same clock ([positions.md](positions.md#the-extent-inherits-the-clock)); written back too |
| `annotation_metadata`, `confidence` | not modelled yet — see the planned provenance layer |

- **`jams_to_hamon(text_or_dict)`** — reads the first `chord`/`chord_harte` annotation into
  ordered groups and the first `key_mode` into a region.
- **`hamon_to_jams(seq)`** — emits a `chord` annotation (Harte values) and, when the sequence
  has regions, a `key_mode` annotation; one observation per group. A group's stated `s:`
  seconds become its `time` and a stated `[dur:…s]` its `duration`. **What the source did
  not state is written as `null`, never as a number.** This writer used to fall back to the
  group's index for `time` and to `1` for `duration` — which a JAMS consumer reads as real
  audio timestamps, so a sequence positioned in bars came out claiming its harmonies land
  one second apart. That is the invention the Dezrann writer was cured of, and `report.py`
  was duly flagging every one of them as `added`.

  The cost, taken deliberately: a HAMON sequence with **no** audio clock now yields a
  document that is *not* schema-valid, since JAMS requires a numeric `time`. The format has
  no way to say "unknown", and saying nothing beats saying something false.

The adapter is **dependency-free**. It reads and writes the JAMS JSON directly, so you do not
need the `jams` Python package.

## What JAMS carries natively (the loss picture)

Standard JAMS harmony is just chord symbols plus key. So, like Harte, it natively **loses**
Roman numerals, figured bass, functional (T–S–D), Nashville, chord-scales, applied-chain detail,
and **metric positions** — its times are audio seconds. Those seconds are no longer a loss in
the other direction: since v0.5 they are HAMON's `s:` clock, and JAMS is one of the two targets
that carry it natively. What sets it apart from Harte is the
first-class **`sandbox`**: the full HAMON reading can ride along there **out-of-band**, with no
loss. That is exactly the distinction the ICCCM'26 loss viewer draws for the `JAMS` target
(native vs. native + HAMON).

## Provenance

JAMS's `annotation_metadata` (annotator, corpus, data source, validation) and per-observation
`confidence` line up closely with HAMON's planned **provenance / traceability layer**. Once that
layer lands, JAMS becomes a natural carrier for import/export provenance in both directions.

See also: [Harte](harte.md) (the chord syntax JAMS uses), [positions](positions.md)
(metric vs audio time), [Dezrann](dezrann.md) (another time-aligned label JSON).
