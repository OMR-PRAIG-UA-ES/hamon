# partitura Integration

[partitura](https://github.com/CPJKU/partitura) (CP-JKU) is a Python package for
symbolic music processing. Its score model has a `Harmony` base class with
`RomanNumeral` and `ChordSymbol` subclasses. Each is a `TimedObject`, and you can
recover its onset in quarters via `part.quarter_map(obj.start.t)`.

hamonpy bridges partitura's harmony objects to and from the typed AST, carrying
onsets through as time-aligned `HarmonyGroup.position` values.

## Installation

partitura is an optional dependency:

```bash
pip install hamonpy[partitura]    # or: pip install partitura
```

## API (`hamonpy.adapters.partitura_adapter`)

```python
import partitura as pt
from hamonpy.adapters.partitura_adapter import (
    partitura_part_to_hamon, hamon_to_partitura_part,
)

# partitura → hamon
score = pt.load_score("piece.musicxml")
part = score.parts[0]
seq = partitura_part_to_hamon(part, system="auto")   # "rn"/"cs" forces a system
for g in seq.groups:
    print(g.primary[0].surface, g.position.time)

# hamon → partitura
part = hamon_to_partitura_part(seq)
```

## Mapping

| partitura | HAMON |
|-----------|-------|
| `Harmony.text` (or `ChordSymbol` root/kind/bass) | parsed `HarmonyLabel` surface |
| `obj.start.t` → `part.quarter_map(...)` | `HarmonyGroup.position.time` (quarters) |
| `RomanNumeral` | `RomanSemantic` (system `rn`) |
| `ChordSymbol` | `ChordSymbolSemantic` (system `cs`) |
| unparseable text | `TextSemantic` fallback |

On export (`hamon_to_partitura_part`), Roman-numeral labels become
`RomanNumeral` objects and everything else becomes a plain `Harmony` — the surface text
round-trips either way. Onsets use `divs_per_quarter` (default 4).

## Limitations

- Only harmony objects are read and written. partitura's full note/score model is out
  of scope, since HAMON is a harmony-label layer.
- `ChordSymbol` export uses the base `Harmony(text=…)` instead of reconstructing
  partitura's `root`/`kind` fields. The surface survives; the structured fields do not.
