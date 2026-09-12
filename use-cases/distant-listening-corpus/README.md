# Use case — Distant Listening Corpus (DCML harmonies → tonal regions)

**Dataset.** [Distant Listening Corpus](https://github.com/DCMLab/distant_listening_corpus)
(Hentschel, Moss, Neuwirth, Rohrmeier; DCMLab) — MuseScore scores with aligned
**DCML TSV** tables. The `harmonies` tables carry `numeral/form/figbass`,
`relativeroot`, `localkey`, and `globalkey`. License: CC-BY-NC-SA-4.0 (verify per
corpus). Registry id `distant-listening-corpus` (also `dcml-corpora`).

**Scenario.** Convert a DCML harmonies table into the canonical model, lifting the
key columns into the **analytical layer** (`TonalRegion`s + applied functions).

**Input.** [`harmonies.tsv`](harmonies.tsv), a *synthetic* DCML harmonies excerpt:

```
chord  numeral … relativeroot  localkey  globalkey
I      I                        I         C
V64    V                        I         C
…
V7/V   V         V             I         C        ← tonicizes the dominant
V      V                        V         C        ← modulation to G
```

## Run it

```python
from hamonpy.adapters.dcml import dcml_tsv_to_hamon, hamon_to_dcml_tsv

seq = dcml_tsv_to_hamon("harmonies.tsv")

for r in seq.regions:
    print(r.kind, r.from_group, r.to_group, r.key.tonic.note, r.key.mode, r.degree)
# key          0 2    C major None
# tonicization 3 3    G major V        (parent=0)
# modulation   4 None G major None

# Round-trips back to DCML (localkey/globalkey/relativeroot columns):
print(hamon_to_dcml_tsv(seq))
```

And on the **real** corpus:

```python
from pathlib import Path
from hamonpy import datasets
from hamonpy.adapters.dcml import dcml_tsv_to_hamon

root = datasets.resolve_local_path("distant-listening-corpus")
for path in root.rglob("*.harmonies.tsv"):
    seq = dcml_tsv_to_hamon(str(path))
    ...
```

## Get the data

`python download_music_datasets.py --datasets distant_listening_corpus` (add
`--recurse-submodules` for the full corpus). See [`datasets/`](../../datasets/README.md).
Cite Hentschel et al. (2025); Moss et al. (2019).
