# Use case — Key/Modulation dataset (Humdrum → tonal regions)

**Dataset.** [key_modulation_dataset](https://github.com/DDMAL/key_modulation_dataset)
(Nápoles López, Feisthauer et al.; DDMAL) — modulation/tonicization snippets from
music-theory textbooks (Kostka-Payne, …). Each piece is **Humdrum `**kern`** with a
`**text` analysis spine: the home key is a `*KEY:` tandem, and modulations are marked
inline as `KEY=>:degree` (e.g. `C=>:I`, `d=>:i`, `B-=>:I`, where `-` = flat). License:
see the repository. Registry id `key-modulation`.

**Scenario.** Recover both the Roman-numeral progression **and** the modulations,
the latter as `TonalRegion`s.

**Input.** [`snippet.krn`](snippet.krn), a *synthetic* excerpt in that exact format:

```
**kern  **text
*C:     *
4c      C=>:I
4f      IV
4g      V
4d      G=>:I      ← modulation to G major
4c      IV
4d      V7
```

## Run it

```python
from hamonpy.adapters.humdrum import key_modulation_to_hamon

seq = key_modulation_to_hamon(open("snippet.krn").read())

print([g.primary[0].semantic.degree for g in seq.groups])
# ['I','IV','V','I','IV','V']
for r in seq.regions:
    print(r.kind, r.from_group, r.to_group, r.key.tonic.note, r.key.mode)
# key        0 2    C major
# modulation 3 None G major
```

Consecutive repeats of the same label are collapsed into one event (the `**text`
spine repeats it on every note onset). And on the **real** corpus:

```python
from hamonpy import datasets
from hamonpy.adapters.humdrum import key_modulation_file_to_hamon

root = datasets.resolve_local_path("key-modulation")
for path in root.rglob("*.krn"):
    seq = key_modulation_file_to_hamon(str(path))
    ...
```

> For Humdrum files that instead use the standard `**harm` / `**function` / `**fb`
> spines, reach for `humdrum_to_hamon`, which maps each spine to an analytical layer.

## Get the data

Run `python download_music_datasets.py --datasets key_modulation_dataset`. See
[`datasets/`](../../datasets/README.md). Cite Nápoles López et al. (2020).
