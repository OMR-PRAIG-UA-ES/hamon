# Use case — Interactive melodic analysis (HT/NHT tones)

**Work.** Interactive harmonic + melodic analysis (Rizo, Illescas & Iñesta) —
classifying each melodic note as a **harmonic tone (HT)** or a **non-harmonic tone
(NHT)**: passing, neighbor, suspension, appoggiatura, the Fuxian *nota cambiata*,
and so on. This is what HAMON's `ToneSemantic` targets. Registry id
`interactive-melodic-analysis`. **No public automated download is known** — contact
the authors; the registry records this for traceability.

**Scenario.** Carry a note-level melodic analysis — alongside the chord/degree
layer and a tonal region — into the canonical model via the HA-MEI `<harm>`
convention.

**Input.** [`analysis.mei`](analysis.mei), a *synthetic* HA-MEI fragment:

```xml
<harm type="hamon:key">C</harm>
<harm type="degree">I</harm>
<harm type="tone">E[HT]</harm>
<harm type="tone">F[NHT:passing]</harm>
<harm type="tone">G[HT]</harm>
<harm type="tone">A[NHT:neighbor]</harm>
```

## Run it

```python
from hamonpy.adapters.mei import mei_to_hamon

seq = mei_to_hamon(open("analysis.mei").read())

print(seq.regions[0].kind, seq.regions[0].key.tonic.note)   # key C
for g in seq.groups:
    s = g.primary[0].semantic
    if getattr(s, "kind", None) == "tone":
        print(s.pitch.note, s.category, s.type)
# E harmonic    chord-tone
# F nonharmonic passing
# G harmonic    chord-tone
# A nonharmonic neighbor
```

For the full non-harmonic-tone vocabulary see
[`documentation/analysis.md`](../../documentation/analysis.md), and for the HA-MEI
carrier see [`mei.md`](../../documentation/mei.md). Cite Rizo, Illescas & Iñesta (2015).
