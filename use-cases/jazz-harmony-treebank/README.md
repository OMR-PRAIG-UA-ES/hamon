# Use case — Jazz Harmony Treebank (lead-sheet chords)

**Dataset.** [Jazz Harmony Treebank](https://github.com/DCMLab/JazzHarmonyTreebank)
(Harasim, Finkensiep et al.; DCMLab) — hierarchical harmonic analyses over
iRealPro jazz tunes. `treebank.json` is a list of tunes, each with a Leadsheet-
syntax `chords` list (`D7`, `G^7`, `F#m7`, `Em7`, …). License: see the repository.
Registry id `jazz-harmony-treebank`.

**Scenario.** Read a tune's chord sequence into the canonical model as typed
chord symbols, translating the Leadsheet quality sigils along the way
(`^`→maj, `h`→ø, `o`→°).

**Input.** [`treebank.json`](treebank.json), a *synthetic* one-tune file:

```json
[{"title": "…", "key": "C", "chords": ["Dm7","G7","C^7","A7","Dm7","G7","Eh7","A7"]}]
```

## Run it

```python
from hamonpy.adapters.treebank import treebank_json_to_hamon, treebank_tunes

seq = treebank_json_to_hamon("treebank.json")     # first tune
print([g.primary[0].surface for g in seq.groups])
# ['Dm7','G7','Cmaj7','A7','Dm7','G7','Eø7','A7']

# iterate the whole corpus:
for tune in treebank_tunes(open("treebank.json").read()):
    s = treebank_json_to_hamon([tune])
    ...
```

And on the **real** corpus:

```python
from hamonpy import datasets
from hamonpy.adapters.treebank import treebank_tunes, treebank_json_to_hamon

path = datasets.resolve_local_path("jazz-harmony-treebank") / "treebank.json"
for tune in treebank_tunes(str(path)):
    seq = treebank_json_to_hamon([tune])
    ...
```

## Get the data

Run `python download_music_datasets.py --datasets jazz_harmony_treebank`. See
[`datasets/`](../../datasets/README.md). Cite Harasim et al. (2020).
