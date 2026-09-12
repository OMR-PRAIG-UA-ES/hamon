# ms3 Integration

[`ms3`](https://johentsch.github.io/ms3) (Johannes Hentschel, DCML/EPFL) is a
Python library that parses MuseScore 3/4 files (`.mscx` / `.mscz`) without a
lossy round-trip. It reads harmony labels written in the **DCML annotation
standard** and hands them back as *expanded* harmony tables — pandas DataFrames.

Those tables are already in the expanded DCML shape, so the HAMON ms3 adapter
just delegates to the [DCML expanded adapter](dcml.md#expanded-time-aligned-tables--the-hentschel-annotation-standard--ms3).
Time alignment (`quarterbeats`), tonal regions, and cadence/phrase extraction all
come along for free.

## Installation

ms3 is an optional dependency:

```bash
pip install hamonpy[ms3]      # or: pip install ms3
```

## API (`hamonpy.adapters.ms3_adapter`)

```python
from hamonpy.adapters.ms3_adapter import (
    ms3_score_to_hamon, ms3_expanded_to_hamon,
    extract_cadences, extract_phrase_ends,
)

# 1. Straight from a MuseScore file (requires ms3 + MuseScore)
seq = ms3_score_to_hamon("sonata.mscx")

# 2. From an already-extracted expanded table (DataFrame, .to_csv object,
#    or a list of row dicts — handy for testing without ms3 installed)
import ms3
expanded = ms3.Score("sonata.mscx").mscx.expanded
seq = ms3_expanded_to_hamon(expanded)

for g in seq.groups:
    print(g.primary[0].surface, g.position.time)   # time-aligned
```

`ms3_expanded_to_hamon` accepts:
- a **pandas DataFrame** (or anything exposing `to_csv(sep=…, index=…)`),
- a **list of row dicts** (column order = keys of the first row).

Under the hood it renders the table to DCML TSV text and feeds that to
`expanded_tsv_text_to_hamon`, so chords, regions, positions, cadences, and phrase
ends are all available.

## Mapping

The column → AST mapping is the same one used for the
[DCML expanded tables](dcml.md#expanded-time-aligned-tables--the-hentschel-annotation-standard--ms3):
`chord`/`numeral`/`form`/`figbass`/`changes`/`relativeroot` become a typed label,
`localkey`/`globalkey` become tonal regions, `quarterbeats` becomes `position.time`,
and `cadence`/`phraseend` go to a side channel via `extract_cadences` /
`extract_phrase_ends`.

## Limitations

- `ms3_score_to_hamon` needs ms3 (and MuseScore for `.mscz` conversion). Without
  ms3 it raises `ImportError` with install guidance. The DataFrame/dict path needs
  neither.
- Only the expanded **harmonies** table is consumed. Note and measure tables are
  out of scope, because HAMON is a harmony-label layer.
