# Use case — Time-aligned harmony positions

**Scenario.** You imported a chord progression from a *positioned* score (MEI
`@tstamp`, MusicXML `<offset>`, a Humdrum barline, …), and you want each chord to
keep **where it sits in time** — measure and beat — not just its order. HAMON
carries this on `HarmonyGroup.position`, and the v0.4 `.hamon` text writes it
**position-first**, comma-separated with the label.

**Input.** [`progression.hamon`](progression.hamon):

```
@version:0.4.0
@cs
@meter:4/4
m:1,ts:1,C
m:1,ts:3,Am
m:2,ts:1,F
m:2,ts:3,G7
m:3,ts:1,C
```

Position items come in four forms: `m:1,ts:3` (measure 1, beat 3 — `ts` is the
MEI `data.BEAT`, 1-based), `m:4` (measure only), `t:5/4` (an absolute position as
a fraction of quarter notes), and `ref:note-9` (a reference to a score-object id).
`@meter:N/D` declares the time signature and bounds the valid `ts` range.

## Run it

```python
from hamonpy.parse import parse_hamon_sequence

seq = parse_hamon_sequence(open("progression.hamon").read())

for g in seq.groups:
    p = g.position
    print(f"m{p.measure} beat {p.beat:g}: {g.primary[0].surface}")
# m1 beat 1: C
# m1 beat 3: Am
# m2 beat 1: F
# m2 beat 3: G7
# m3 beat 1: C
```

### Where positions come from

You normally don't hand-write position items; a format adapter fills them in:

```python
from hamonpy.adapters.musicxml import musicxml_to_hamon   # <harmony> + time model
from hamonpy.adapters.mei import mei_to_hamon              # <harm> @tstamp / @startid
from hamonpy.serialize import sequence_to_hamon_text

seq = musicxml_to_hamon(open("score.musicxml").read())
print(sequence_to_hamon_text(seq))    # → the .hamon text above, m:/ts: positions and all
```

### Round-trips

Positions survive every hop:

```python
from hamonpy.serialize import sequence_to_hamon_text
assert parse_hamon_sequence(sequence_to_hamon_text(seq)) == seq      # text ⇄ model
```

With music21 installed, `hamon_to_music21_stream` places the chords into
`music21.stream.Measure` objects at the right beats, and
`music21_stream_to_hamon` reads them back into positions — so
MusicXML → HAMON → music21 → HAMON preserves both measure and beat.
