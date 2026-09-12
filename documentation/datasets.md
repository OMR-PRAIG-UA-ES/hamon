# Datasets & the harmony hub

HAMON is a **hub of harmony**: it converts real corpora into one canonical model
(`grammar/hamon-schema.json`) so they can interoperate. What it deliberately
**does not** do is redistribute anyone else's dataset. Instead it ships a
*registry* of the original sources plus a small downloader. You fetch each corpus
from its authors, under its own license, and convert it with a format adapter.

- Registry: [`datasets/manifest.json`](../datasets/manifest.json)
- Policy + quickstart: [`datasets/README.md`](../datasets/README.md)
- Worked recipes: [`use-cases/`](../use-cases/README.md)
- API: `hamonpy.datasets`

## The registry (`datasets/manifest.json`)

Each entry records the `name`, `title`, `description`, `authors`, `homepage`,
`license`, and `citation`, along with the on-disk `format`, the `hamon_adapter`
that reads it, and a `download` block (`method` = `http` | `git` | `builtin` |
`manual`, plus a `url` when there is a single archive to grab).

| Dataset | Format | Adapter | Download |
|---|---|---|---|
| `when-in-rome` | RomanText | `hamonpy.adapters.romantext` | `git` (MarkGotham) |
| `distant-listening-corpus` | DCML TSV | `hamonpy.adapters.dcml` | `git` (DCMLab) |
| `dcml-corpora` | DCML TSV | `hamonpy.adapters.dcml` | `git` (DCMLab) |
| `jazz-harmony-treebank` | `treebank.json` | `hamonpy.adapters.treebank` | `git` (DCMLab) |
| `key-modulation` | Humdrum `**kern` | `hamonpy.adapters.humdrum` | `git` (DDMAL) |
| `dilemmadata` | pitch-array TSV (note-level) | `hamonpy.adapters.dilemma` | `git` (Zenodo) |
| `jazzmus` / `jazzmus-code` | MusicXML + `**kern` / code | `hamonpy.adapters.humdrum` | `huggingface` (gated) / `git` |
| `interactive-melodic-analysis` | HT/NHT (HA-MEI) | `hamonpy.adapters.mei` | `manual` (contact authors) |
| `isophonics` | Harte `.lab` | `hamonpy.adapters.harte` | `manual` (isophonics.net) |
| `music21-corpus` | music21 stream | `hamonpy.adapters.music21_adapter` | `builtin` (`music21.corpus`) |
| `irealpro` | `irealb://` URI | `hamonpy.adapters.ireal` | `manual` (export your own) |

The first nine are the datasets from the HAMON use-cases paper; there is a worked
recipe for each under [`use-cases/`](../use-cases/README.md).

### Using the companion downloader

You can fetch those datasets unattended with the paper's `download_music_datasets.py`,
which writes its own manifest. HAMON understands that manifest's integration contract,
so you can point it at data you have already downloaded:

```python
import os
from hamonpy import datasets
from hamonpy.adapters.romantext import romantext_file_to_hamon

os.environ["MUSIC_DATASETS_MANIFEST"] = "/data/music-corpora/music_datasets_manifest.json"
root = datasets.resolve_local_path("when-in-rome")     # maps name → downloader id → local path
seq = romantext_file_to_hamon(str(next((root / "Corpus").rglob("analysis.txt"))))
```

`resolve_local_path(name, manifest_path=None)` respects the contract's
`status_ok_values` (`cloned`/`updated`/`exists`/`downloaded`), and it raises for
gated datasets (`jazzmus`) or unavailable ones (`interactive-melodic-analysis`).

## API

```python
from hamonpy import datasets

datasets.list_datasets()            # names
datasets.get_dataset("dcml-corpora")  # the manifest entry (license, citation, …)
datasets.default_cache_dir()        # ~/.cache/hamon/datasets  (override: HAMON_CACHE_DIR)
datasets.download_dataset(name, dest_dir=None, url=None)
```

`download_dataset` pulls only `http(s)://` and `file://` sources into the cache;
it never bundles, scrapes, or mirrors anything. For `git` / `builtin` / `manual`
datasets it raises and points you at the homepage and license — you obtain those
yourself. Pass `url=` to use a mirror or a local copy.

To override where the manifest lives, set `HAMON_DATASETS_MANIFEST`.

## Responsibilities

HAMON provides only the conversion layer. **The data and its terms belong to the
original authors** — so honour each dataset's `license` and cite its `citation`
in anything you publish. Downloaded payloads stay in the git-ignored cache and
are never committed.

## Converting a corpus

```python
from hamonpy import datasets
from hamonpy.adapters.dcml import dcml_tsv_to_hamon

info = datasets.get_dataset("dcml-corpora")
print("Cite:", info["citation"], "| License:", info["license"])
# obtain the corpus per info["homepage"], then:
seq = dcml_tsv_to_hamon("path/to/annotations.tsv")
```

The source adapters map key/region columns — DCML `localkey`/`relativeroot`, the
Humdrum `**harm`/`**function` layering — into the analytical layer (`TonalRegion`,
`HarmonyLabel.layer`). See [`../STATUS.md`](../STATUS.md).
