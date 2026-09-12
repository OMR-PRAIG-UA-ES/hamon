# Use case — Jazz lead-sheet with an applied dominant

**Scenario.** A ii–V–I in C with a secondary dominant of ii, written as chord
symbols — and you want it as typed chord data with the applied function made
explicit.

**Input.** [`tune.hamon`](tune.hamon):

```
@version:0.2.0
@cs
Dm7
G7
Cmaj7
A7[of:ii]
Dm7
```

## Run it

```python
from hamonpy.parse import parse_hamon_sequence

seq = parse_hamon_sequence(open("tune.hamon").read())

for g in seq.groups:
    lbl = g.primary[0]
    sem = lbl.semantic
    print(lbl.surface, sem.root.note, sem.quality, sem.seventh,
          getattr(lbl.attributes, "applied", None))
# Dm7      D minor min7 None
# G7       G major dom7 None
# Cmaj7    C major maj7 None
# A7[of:ii] A major dom7 AppliedFunction(target='ii', chain=None)
# Dm7      D minor min7 None
```

## What you get

- Each change becomes a `ChordSymbolSemantic` (root, quality, seventh).
- The bracketed `[of:ii]` attaches a `HarmonyAttributes.applied` reading to the
  A7, marking it as the secondary dominant (V/ii) that resolves to Dm7 — without
  touching the chord itself.

To convert real charts at scale, export iReal Pro playlists and read them with
`hamonpy.adapters.ireal` (see [`datasets/`](../../datasets/README.md)).
