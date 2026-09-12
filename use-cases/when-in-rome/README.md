# Use case — When in Rome (RomanText functional analysis)

**Dataset.** [When in Rome](https://github.com/MarkGotham/When-in-Rome) (Gotham,
Tymoczko, Cuthbert et al.) — a meta-corpus of Roman-numeral analyses in
**RomanText** (`.rntxt`/`analysis.txt`), aligned with scores. License: CC-BY-SA
(verify per item). Registry id `when-in-rome`.

**Scenario.** Turn a RomanText analysis into the canonical model, recovering both
the scale-degree labels **and** the tonal regions its inline key changes imply.

**Input.** [`analysis.txt`](analysis.txt), a *synthetic* RomanText excerpt (not
copied from the corpus):

```
m1 C: I b2 IV b3 V7
m2 vi b2 ii6 b3 V
m3 G: I b2 V/V b3 V
m4 I
```

## Run it

```python
from hamonpy.adapters.romantext import romantext_to_hamon

seq = romantext_to_hamon(open("analysis.txt").read())

print([g.primary[0].semantic.degree for g in seq.groups])
# ['I','IV','V','vi','ii','V','I','V','V','I']
for r in seq.regions:
    print(r.kind, r.from_group, r.to_group, r.key.tonic.note, r.key.mode)
# key        0 5    C major
# modulation 6 None G major
```

On the **real** corpus (after fetching it — see below):

```python
from pathlib import Path
from hamonpy import datasets
from hamonpy.adapters.romantext import romantext_file_to_hamon

root = datasets.resolve_local_path("when-in-rome")          # uses MUSIC_DATASETS_MANIFEST
for path in (root / "Corpus").rglob("analysis.txt"):
    seq = romantext_file_to_hamon(str(path))
    ...
```

## Get the data (we don't bundle it)

Run `python download_music_datasets.py --root /data/music-corpora --datasets when_in_rome`,
then `export MUSIC_DATASETS_MANIFEST=/data/music-corpora/music_datasets_manifest.json`.
See [`datasets/`](../../datasets/README.md). Cite Gotham & Jonas (2022); Tymoczko,
Gotham, Cuthbert & Ariza (2019).
