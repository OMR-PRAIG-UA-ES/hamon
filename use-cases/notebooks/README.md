# Notebook tours

Narrative, executable **tours** that stitch several [`use-cases/`](../) together into
one story. They complement the per-case `README.md`s; they don't replace them.

## The format: jupytext `.py:percent` (not committed `.ipynb`)

The **source of truth is the `.py` file**, in [`jupytext`](https://jupytext.readthedocs.io)
*percent* format (`# %%` cell markers, `# %% [markdown]` for prose). We deliberately
do **not** commit `.ipynb`, for three reasons:

- **Diff-able.** A `.py` reviews line-by-line in a PR. An `.ipynb` is JSON with
  embedded outputs and execution counts — which means unreadable diffs and churn.
- **No stale outputs.** Since outputs are never stored, they can't drift out of sync
  with the code. They're regenerated when you open or run the notebook.
- **It's a real test.** Each tour is valid Python, so `hamonpy/tests/test_notebooks.py`
  *executes* it on every CI run — the same anti-bit-rot guarantee as `test_use_cases.py`.

## Open it as a notebook

```bash
# one-off: generate the .ipynb next to the .py (gitignored)
jupytext --to notebook 01_jazz_tour.py        # → 01_jazz_tour.ipynb
jupyter lab 01_jazz_tour.ipynb

# or pair them so Jupyter keeps the .py in sync as you edit the .ipynb
jupytext --set-formats py:percent,ipynb 01_jazz_tour.py
```

Edit the `.py` (or the paired `.ipynb`), but commit only the `.py`.

## Run them (CI / locally)

```bash
# as plain scripts — fastest, zero notebook deps (what pytest does):
python 01_jazz_tour.py

# the whole suite, incl. notebook execution:
pytest hamonpy/tests/test_notebooks.py -q

# fully execute as a notebook (kernel) and fail on any cell error:
jupytext --to notebook --execute 01_jazz_tour.py -o /dev/null
```

## The tours

| Tour | Stitches | Shows |
|---|---|---|
| [`01_jazz_tour.py`](01_jazz_tour.py) | [`jazz-leadsheet`](../jazz-leadsheet/) + [`berklee-jazz`](../berklee-jazz/) | parse jazz changes → typed AST (applied `[of:ii]`, tensions) → export to iReal/RomanText → **lossy diff** of what each target drops |
| [`02_dcml_ms3_tour.py`](02_dcml_ms3_tour.py) | [`distant-listening-corpus`](../distant-listening-corpus/) | drive DCML's **`ms3`** analysis library (`expand_dcml.expand_labels`) on raw harmony labels → expanded table → HAMON regions/tonicization |
| [`03_flexohr_tour.py`](03_flexohr_tour.py) | the [`flexohr`](../../documentation/flexohr.md) adapter | hand HAMON chord symbols + Roman numerals to **FlexOHR**'s `OHR` object model (root, quality, inversion, degree) and round-trip them back |
| [`04_grand_tour.py`](04_grand_tour.py) | [`distant-listening-corpus`](../distant-listening-corpus/) + a live **music21** score + every layer | the end-to-end journey: **take a dataset** → canonical model → the **five harmony systems** → **convert any→any** with the loss report → **analyse a real Bach chorale** (music21 key + Roman numerals, positioned into HAMON, rendered back to a score) → a small **loss matrix** → write a **MuseScore** file → **save** the artifacts |
| [`05_choro_tour.py`](05_choro_tour.py) | [`choro`](../choro/) (DCML Choro Songbook) | **corpus curation**: use HAMON to audit a real corpus — check the form-grammar transcriptions are **consistent** with the merged TSV, and that the three chord encodings (**absolute vs. Roman vs. Harte**) agree, via one typed model |

> `02_dcml_ms3_tour.py` and `03_flexohr_tour.py` need the optional `ms3` / `flexohr`
> dependencies (`pip install -e "./hamonpy[ms3]"` / `[flexohr]`); the test skips a tour
> when its dependency isn't installed. `04_grand_tour.py` runs everywhere: its live-score
> section uses `music21` when present (`[music21]`) and skips just that section otherwise.
