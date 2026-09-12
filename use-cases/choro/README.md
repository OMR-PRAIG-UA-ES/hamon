# How to audit a corpus with HAMON — worked example: the DCML Choro Songbook

This use case is written as a **recipe you can reuse**. It starts from a situation you
often meet with symbolic-music corpora and shows, step by step, how HAMON turns an
awkward validation job into a few lines. The DCML
[*Choro Songbook Corpus*](https://github.com/DCMLab/choro) is the worked example.

## The situation

> *Suppose you are handed a corpus that stores the same music **more than once** — say a
> per-piece source in one notation, and a big merged table in another — and each chord is
> written in **several encodings** (an absolute chord symbol, a Roman numeral, a Harte
> label). You want to trust it: are the two representations **consistent**, and are the
> encodings of each chord **mutually correct**?*

Doing that by hand means writing bespoke parsers for each format and a pile of
string-wrangling to line them up. The encodings don't compare directly — `A7` vs `V7` vs
`A:7` are the "same" chord only once you know the key and the notation rules.

For Choro concretely, the two representations are:

- **`choro.tsv`** — every piece merged into one table, **one row per chord onset**, with
  `chord` (absolute, e.g. `A7`), `rn_chord` (Roman, e.g. `V7`), `harte` (e.g. `A:7`),
  `local_key`, `bar_no`, the form columns `phrase`/`part`, and `filename`.
- **`transcriptions/<piece>.txt`** — a compact **form grammar**:

  | line | meaning |
  |---|---|
  | `P1: A7 \| Dm \| C7 . \|` | a **phrase**: bars split by `\|`; an empty bar or `.` holds the previous chord; a bar may list several chords |
  | `PartA[key]: $P1 $P2` | a **part**: a sequence of `$`-references |
  | `S[Dm, 2/4]: $Intro $PartA …` | the **song**: parts/phrases in order; `$ref*N` repeats a reference `N` times |

## Why HAMON helps

HAMON parses **every** encoding into one typed model (`HamonSequence` of chord symbols /
Roman numerals / Harte), so once each source is in that model, comparing them is ordinary
Python — no per-format special-casing. That is the whole point of an interlingua.

## The recipe

### Step 1 — Get each source into a `HamonSequence`

You need each encoding parsed into HAMON's model. There are **two ways**, depending on
whether you're just doing your own analysis or contributing the format to HAMON:

**Path A — just use HAMON (a snippet in your own script).** You don't have to touch HAMON
at all. Pull the chord strings out of your file however you like, and hand them to the
public API:

```python
from hamonpy.parse import parse_hamon_sequence

chords = my_reader("choro.tsv")                      # your own throwaway parsing
seq = parse_hamon_sequence("@cs\n" + "\n".join(chords))
# now use the model: compare roots, degree_to_pitch, transcode, lossy_report, …
```

That's enough for a one-off audit — no adapter, no registration, nothing added to HAMON.

**Path B — contribute an adapter (what this use case did).** If you want the format to be
*first-class* — reusable, `hamon convert … --format choro`, auto-detected, a downloadable
dataset, covered by tests — package the parsing as an adapter,
[`hamonpy/adapters/choro.py`](../../hamonpy/hamonpy/adapters/choro.py):

- `read_tsv(text)` groups the merged table by `filename`.
- `tsv_piece_to_hamon(rows, column=…)` turns one piece into a `HamonSequence` from the
  chosen encoding column, keeping `bar_no` as the position.
- `expand_transcription(text)` implements the form grammar — it resolves `$ref*N` repeats
  and holds the previous chord on empty bars / `.` — and `transcription_to_hamon(text)`
  parses the result.
- `normalize_chord` handles the one corpus-specific glyph (Brazilian `7M` = `maj7`).

Registering the format (auto-detection + a [dataset entry](../../datasets/manifest.json) so
`hamon datasets download choro` works and it shows up in the demo) is a few extra lines in
`hamonpy/cli.py`.

Steps 2–3 below are identical either way — they only need the parsed `HamonSequence`. We
show them with the adapter (Path B), but Path A's `seq` slots in unchanged.

### Step 2 — Consistency check: does one representation reproduce the other?

Expand each `.txt` song to its flat chord-onset sequence and compare it, chord for chord,
to the piece's rows in the TSV:

```python
from hamonpy.adapters import choro
pieces = choro.read_tsv(open("choro.tsv").read())
onsets = choro.expand_transcription(open("transcriptions/1_assanhado_WF.txt").read())
assert onsets == [r["chord"] for r in pieces["1_assanhado_WF.txt"]]
```

Over the full corpus **292/295 pieces match exactly**; the few that diverge are surfaced
for review (this extract includes one, `1_forro_de_gala`, whose files disagree).

### Step 3 — Correctness checks: do the encodings agree?

Parse each encoding into HAMON and compare in the model:

- **Absolute ↔ absolute** — `chord` and `harte` must name the same root. Parse both, read
  `semantic.root`, compare pitch-classes. (100% across the corpus.)
- **Absolute ↔ functional** — the hard one by hand: realise each `rn_chord` in its
  `local_key` with HAMON's mode-aware
  [`degree_to_pitch`](../../hamonpy/hamonpy/normalize.py) (so `VII` in a minor key is the
  natural ♭7) and check it points at the same root as the absolute chord. (100%.)

### Step 4 — Run it, pin it, scale it

The three steps live in the runnable tour
[`../notebooks/05_choro_tour.py`](../notebooks/05_choro_tour.py), and
`hamonpy/tests/test_choro.py` pins them against the extract so they can't bit-rot. To run
over the whole corpus, `hamon datasets download choro` (or clone
`github.com/DCMLab/choro`) and point the tour's `CHORO` path at its `data/`.

## What you get

Two of the three audits pass cleanly over the corpus (the encodings are internally
faithful); the consistency audit flags the handful of pieces whose two representations
disagree — the kind of cross-file, cross-encoding finding that is easy to miss by hand and
one line to catch with a shared model. **Apply the same steps to your own corpus:** get
each source into a `HamonSequence` — a snippet in your script (Path A) or a full adapter
(Path B) — then compare in the HAMON model.

## This extract

`choro-extract.tsv` + `transcriptions/*.txt` hold three pieces (`1_assanhado`,
`3_davilicenca`, `1_forro_de_gala`) — enough to exercise every grammar feature and both a
clean match and a flagged divergence — plus `LICENSE-choro`.

## Attribution

The corpus is **© DCMLab** and released under **CC BY 4.0** (Attribution) — reuse, including
commercial reuse, is allowed as long as you attribute the authors. Its bundled `LICENSE` file
is copied here as `LICENSE-choro`. Cite:

> Moss, F. C., Souza, W. F., & Rohrmeier, M. *Choro Songbook Corpus.* DCMLab.
> https://github.com/DCMLab/choro · https://doi.org/10.5281/zenodo.21219604

HAMON only adds an exchange/validation layer; the data and its terms belong to DCMLab. The
extract here is redistributed under that same `LICENSE-choro`.
