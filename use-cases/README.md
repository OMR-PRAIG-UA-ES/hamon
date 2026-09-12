# Use cases

Worked, runnable scenarios that show HAMON acting as a **hub of harmony**. Each
folder takes some real input, converts it into the canonical model, and does
something useful with it. They double as living documentation and as smoke tests —
every `*.hamon` here is parsed by `hamonpy/tests/test_use_cases.py`.

Each use-case folder holds:
- a `README.md` — the scenario and how to run it,
- input fixtures (a `.hamon` surface and/or a source-format snippet),
- the expected outcome, described in prose.

For longer walkthroughs that stitch several cases together, see
[`notebooks/`](notebooks/): jupytext `.py` tours (rendered as Jupyter notebooks on
demand) that the test suite also executes, so they can't go stale.

## Index

### Concept demos (`.hamon` surface)

| Use case | Shows |
|---|---|
| [`roman-numeral-analysis/`](roman-numeral-analysis/) | tonal regions + a tonicization (`@key:`), secondary dominants, parsed into `TonalRegion`s with computed local tonics |
| [`jazz-leadsheet/`](jazz-leadsheet/) | chord-symbol changes with an applied-function attribute (`A7[of:ii]`) |
| [`berklee-jazz/`](berklee-jazz/) | Berklee-style jazz analysis — tensions, a related ii–V (`Eø7[of:ii]`/`A7b9[of:ii]`), altered dominants; + a "what HAMON captures vs. needs" gap table |
| [`time-aligned-positions/`](time-aligned-positions/) | time-aligned harmony — `HarmonyGroup.position` and the v0.4 position-first `m:`/`ts:` items |

### Real corpora (synthetic fixture + recipe for the actual dataset)

Each folder identifies the dataset (authors, paper, license, homepage), ships a
tiny **synthetic** fixture in the dataset's native format (we never bundle corpus
data), and gives the HAMON recipe. The recipe also runs on the real corpus once you
fetch it via the [dataset hub](../datasets/README.md) (`hamonpy.datasets.resolve_local_path`).

| Use case | Dataset | Adapter | Shows |
|---|---|---|---|
| [`when-in-rome/`](when-in-rome/) | When in Rome (RomanText) | `romantext` | degrees + key-change → `TonalRegion`/modulation |
| [`distant-listening-corpus/`](distant-listening-corpus/) | DCML / DLC (TSV) | `dcml` | `localkey`/`relativeroot` → regions + tonicization (import↔export) |
| [`jazz-harmony-treebank/`](jazz-harmony-treebank/) | Jazz Harmony Treebank (JSON) | `treebank` | Leadsheet `chords` → typed chord symbols |
| [`key-modulation/`](key-modulation/) | DDMAL key/modulation (Humdrum) | `humdrum` | `**harm`/`**function` spines → analytical layers |
| [`interactive-melodic-analysis/`](interactive-melodic-analysis/) | Rizo/Illescas (HA-MEI) | `mei` | HT/NHT melodic analysis → `ToneSemantic` |
| [`jazzmus-berklee-dezrann/`](jazzmus-berklee-dezrann/) | JAZZMUS (Humdrum) | `humdrum` + `dezrann` | full pipeline: JAZZMUS → HAMON Berklee analysis (tritone sub) → Dezrann `.dez` |

## Datasets

These use-cases ship tiny, self-contained fixtures. To run experiments on full
corpora, fetch them from their original authors via the dataset hub
(`hamonpy.datasets`) — HAMON never bundles third-party data. See
[`datasets/README.md`](../datasets/README.md).
