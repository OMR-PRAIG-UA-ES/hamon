# Datasets — original sources, not copies

HAMON positions itself as a **hub of harmony**: it converts real-world corpora
into the canonical model (`grammar/hamon-schema.json`) so they can be exchanged
and analysed uniformly. To do that you need the corpora — but **HAMON does not
redistribute them**.

Instead, this folder ships a **manifest** of the original sources and a small
helper to download them, so you fetch each dataset **from its authors**, under
**its own license**, and convert it with the matching adapter.

## What's here

- [`manifest.json`](manifest.json) — the registry: **23 datasets**, each with its
  authors, homepage, license, citation, on-disk `format`, the HAMON
  `hamon_adapter` that reads it, an optional `harmony_glob` (which files carry the
  harmony), and a `download` block.
- Nothing else. **No dataset payloads are committed** — `/datasets/_data/` and
  `/datasets/cache/` are git-ignored.

## Using it (Python)

```python
from hamonpy import datasets

datasets.list_datasets()
# ['when-in-rome', 'distant-listening-corpus', 'dcml-corpora', 'annotated-mozart-sonatas',
#  'jazz-harmony-treebank', 'key-modulation', 'dilemmadata', 'jazzmus-code', 'jazzmus', …]

info = datasets.get_dataset('distant-listening-corpus')
print(info['license'], info['citation'], info['homepage'])

# Fetch into datasets/_data/ — git and http, harmony-only by default:
path = datasets.fetch_dataset('corelli')                  # → datasets/_data/corelli
datasets.fetch_dataset('corelli', harmony_only=False)     # full corpus (scores, submodules)
datasets.download_all()                                   # every git/http dataset

# Then convert with the matching adapter (`harmony_glob` says where the harmony lives):
from hamonpy.adapters.dcml import dcml_tsv_to_hamon
seq = dcml_tsv_to_hamon(next(path.glob("harmonies/*.tsv")))
```

The same from the CLI: `hamon datasets list | info <name> | path <name> | download <name>
[--full] | download-all [--full]`.

**Harmony-only is the default.** DCML datasets are sparse-cloned to just their
`harmonies/*.tsv` tables — for the meta-repos (`dcml-corpora`,
`distant-listening-corpus`) that means each submodule's `harmonies/` — skipping the
large MuseScore scores. Re-running fast-forwards to upstream. `--full` pulls the
scores and submodules too.

`builtin` (music21), `manual` and gated datasets are **not** fetched: `fetch_dataset`
raises with a pointer to the homepage and its terms. The older
`datasets.download_dataset(name)` is the narrow helper for a single `http(s)://` or
`file://` archive; `fetch_dataset` is the one you want.

## Your responsibilities

- **Honour each dataset's license** (shown in `license`; verify on the homepage).
- **Cite the original authors** (the `citation` field).
- HAMON only provides the conversion layer; the data and its terms are the
  authors'.

See [`documentation/datasets.md`](../documentation/datasets.md) for the full
reference and [`use-cases/`](../use-cases/README.md) for worked recipes.
