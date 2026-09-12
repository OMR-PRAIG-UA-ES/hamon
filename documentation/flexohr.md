# FlexOHR

[FlexOHR](https://pypi.org/project/flexohr/) — *Flexible and Extensible Object for
Harmony Representation* — is DCMLab's harmony object model (`pip install flexohr`). It
represents, stores, and queries harmony as an immutable recursive object (`OHR`) with a
pitch-space paradigm and a DCML codec. HAMON bridges to it so a HAMON label can be handed
to FlexOHR's model — and back — with **HAMON as the wire format** between the encodings and
whatever analysis runs on the FlexOHR side.

> HAMON is not an analysis library; FlexOHR is the representation model the analysis side
> uses. The adapter keeps the two interoperating without either adopting the other's model.

## Install

```bash
pip install -e "./hamonpy[flexohr]"
```

## Usage

```python
from hamonpy.parse import parse_hamon_sequence
from hamonpy.adapters.flexohr import (
    hamon_to_flexohr,        # HamonSequence -> list[flexohr.OHR]
    flexohr_to_hamon,        # list[flexohr.OHR] -> HamonSequence
    hamon_semantic_to_ohr,   # one chordSymbol/roman semantic -> OHR
    ohr_to_hamon_semantic,   # one OHR -> semantic
)

seq  = parse_hamon_sequence("@cs\nCmaj7\nAm7\nDm7\nG7")
ohrs = hamon_to_flexohr(seq)          # -> [OHR, OHR, OHR, OHR]
back = flexohr_to_hamon(ohrs)         # -> HamonSequence

# Roman numerals need a tonal context (default C major, overridable):
from hamonpy.parse import parse_hamon_sequence
v7 = parse_hamon_sequence("@rn\nV7").groups[0].primary[0].semantic
ohr = hamon_semantic_to_ohr(v7, key="C")   # OHR rooted on the C-major scale
```

## Mapping

| HAMON | FlexOHR |
|---|---|
| `ChordSymbolSemantic.root` (`PitchClass`) | `SPC` (specific pitch class, fifths-based) |
| `quality` + `seventh` | `ChordQuality` (e.g. `major`+`maj7` → `major_seventh`, `half-diminished`+`hdim7` → `half_diminished_seventh`) |
| `suspensions` `[4]` / `[2]` | `ChordQuality.suspended_fourth` / `suspended_second` |
| `bass` (slash bass) | resolved to `Inversion` via `OHR.with_(bass=…)` |
| `RomanSemantic.degree` (+ `prefixAccidentals`) | `SD` (scale degree) in a key `Scale`, via the DCML codec |
| roman `tail` (figbass + quality symbol) | `ChordQuality` + `Inversion` |
| key context | `Scale.from_collection_type(major/natural_minor, tonic)` |

Chord symbols round-trip **root, quality + seventh, suspensions, and slash bass**
losslessly. Roman numerals map **degree (+ accidentals), triad/seventh quality, and the
figured-bass inversion** in a key context.

## Limitations (first cut)

- Chord-symbol **extensions / alterations / adds / omits** are not yet carried into
  FlexOHR (root + quality + seventh + suspensions + bass are).
- Roman **applied/secondary chains** (`V/V`), **pedal**, and parenthesised **changes**
  (`V(4)`) are out of scope for now — see the
  our DCML audit, which tracks the same gaps in the
  Roman-numeral AST.
- Only chord symbols and Roman numerals are supported; Nashville, figured bass, and
  functional labels are not mapped (FlexOHR has no dedicated vocabulary for them).
- FlexOHR emits DCML strings via `ohr.to_format("dcml")`; when building an OHR for a
  round-trippable string, pass `inversion=` explicitly (the adapter always does).
