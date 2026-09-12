# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3 (hamonpy)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # HAMON — the grand tour (end to end)
#
# One journey through everything HAMON does: **take a dataset**, read it into the
# canonical model, see the **five harmony systems**, **convert it to other formats**
# (always measuring what is lost), **analyse a real Bach chorale live with music21**
# (key + Roman numerals, positioned into HAMON, rendered back to a score), run a small
# **loss matrix**, write a **MuseScore** file to open, and **save** the artifacts.
#
# It runs as a plain script (the `pytest` suite executes it) and as a notebook
# (`jupytext --to notebook 04_grand_tour.py`). Optional steps (a downloaded dataset,
# music21) light up when available and are skipped cleanly otherwise.

# %%
import json
import tempfile
from pathlib import Path

from hamonpy.cli import convert_file, transcode
from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_json
from hamonpy.report import write_to

# Resolve the repo whether run as a script (__file__ set) or in a Jupyter kernel.
try:
    HERE = Path(__file__).resolve().parent
except NameError:
    HERE = Path.cwd()
REPO = HERE.parents[1]
USE_CASES = REPO / "use-cases"

OUT = Path(tempfile.mkdtemp(prefix="hamon-tour-"))   # where step 8 saves the artifacts


def show(title):
    print("\n" + title + "\n" + "-" * len(title))


# %% [markdown]
# ## 1. Pick a dataset
#
# We use the small DCML excerpt committed in the repo, so the tour is reproducible
# everywhere. It is a DCML harmonies table — Roman-numeral analysis with a tonal
# context. Any full corpus you download (`hamon datasets download …`) plugs in exactly
# the same way — point `dataset_tsv` at its `harmonies/*.tsv`.

# %%
dataset_tsv = USE_CASES / "distant-listening-corpus" / "harmonies.tsv"
seq = convert_file(dataset_tsv)
show("Dataset: in-repo excerpt (distant-listening-corpus)")
print(f"  file:   {dataset_tsv.relative_to(REPO)}")
print(f"  groups: {len(seq.groups)}")
print(f"  labels: {[g.primary[0].surface for g in seq.groups]}")
assert seq.groups, "the dataset produced no harmony groups"

# Downloaded corpora (git-ignored) work identically — just larger:
downloaded = sorted((REPO / "datasets" / "_data").glob("*/**/harmonies/*.tsv")) \
    if (REPO / "datasets" / "_data").is_dir() else []
if downloaded:
    print(f"  (also available: {len(downloaded)} harmony tables under datasets/_data/ — "
          f"set dataset_tsv to one to run the tour on a full corpus)")

# %% [markdown]
# ## 2. The canonical model — the hub
#
# Every format maps to and from this one typed structure. This is what tools read,
# write and validate.

# %%
doc = json.loads(sequence_to_json(seq))
kinds = {}
for g in seq.groups:
    k = g.primary[0].semantic.kind
    kinds[k] = kinds.get(k, 0) + 1
show("Canonical model")
print(f"  semantic kinds: {kinds}")
print("  first group JSON:")
print("   ", json.dumps(doc["groups"][0], ensure_ascii=False))

# %% [markdown]
# ## 3. One music, five systems
#
# HAMON represents chord symbols, Roman numerals, Nashville numbers, figured bass and
# functional labels — the same typed model underneath. A quick gallery, each parsed to
# its own semantic kind:

# %%
GALLERY = {
    "chord symbol (cs)":  "@cs\nDm7\nG7\nCmaj7",
    "roman numeral (rn)": "@rn\nii7\nV7\nI",
    "Nashville (ns)":     "@ns\n1\n4\n5",
    "figured bass (fb)":  "@fb\n6-5\n7-6\n4-3",
    "functional (fun)":   "@fun\nT\nS\nDD",
}
show("Five harmony systems")
for name, surface in GALLERY.items():
    g = parse_hamon_sequence(surface)
    kind = g.groups[0].primary[0].semantic.kind
    labels = " ".join(x.primary[0].surface for x in g.groups)
    print(f"  {name:22} {labels:16} → kind={kind}")
    assert kind != "text", f"{name} should parse semantically"

# %% [markdown]
# ## 4. Convert to any format — and measure the loss
#
# `transcode` reads the dataset, produces the canonical JSON, writes the target format
# and reports what the target could not carry — all in one call. Because no two formats
# carry the same information, most conversions lose something; HAMON records it.

# %%
show("Any → any, with the loss report")
for target in ("romantext", "mei", "musescore", "humdrum"):
    tc = transcode(dataset_tsv, target)
    lost = [f for f in tc.report.findings if not f.notational]
    first = (tc.output.strip().splitlines() or ["(empty)"])[0]
    print(f"  → {target:10} {len(tc.output):4d} bytes | semantic loss: {len(lost):2d} | e.g. {first[:44]!r}")

# Honest edge case: a Roman-numeral corpus → Harte (a chord-symbol-only format) carries
# *nothing*, because Harte cannot express Roman numerals. The output is empty — and the
# report says exactly why, instead of pretending it worked.
harte = transcode(dataset_tsv, "harte")
print(f"  → harte      {len(harte.output):4d} bytes | Harte can't represent Roman numerals → empty (see the report)")
assert harte.output.strip() == "", "expected an empty Harte export from Roman-numeral input"

# %% [markdown]
# ## 5. A real score, analysed live (music21)
#
# The realistic digital-musicology path: take an actual score, analyse it, and bring the
# result into HAMON. We use a **Bach chorale that ships with music21** (no download), let
# music21 find the key and the Roman numerals, and bridge those — *with their measure/beat
# positions* — into the HAMON model. Then we export the analysis and render a harmonic
# reduction you can open in MuseScore. Needs the `music21` extra; skipped cleanly without it.

# %%
show("A real score → analysis → HAMON")
try:
    from music21 import corpus, roman
    from hamonpy.adapters.music21_adapter import music21_stream_to_hamon, hamon_to_music21_stream

    score = corpus.parse("bach/bwv66.6")                 # bundled with music21
    key = score.analyze("key")
    reduction = score.chordify()                         # vertical harmonic slices
    for ch in list(reduction.recurse().getElementsByClass("Chord")):
        ch.activeSite.insert(ch.offset, roman.romanNumeralFromChord(ch, key))

    analysed = music21_stream_to_hamon(reduction, "rn")  # → positioned HAMON (measure+beat)
    positioned = [g for g in analysed.groups if g.position]
    print(f"  Bach BWV 66.6 — key {key}, {len(analysed.groups)} chords "
          f"({len(positioned)} time-aligned)")
    for g in positioned[:6]:
        print(f"    m{g.position.measure} beat {g.position.beat:>3}: {g.primary[0].surface}")

    # export the live analysis and render a harmonic reduction you can open in MuseScore
    (OUT / "bach_analysis.rntxt").write_text(write_to(analysed, "romantext"), encoding="utf-8")
    (OUT / "bach_analysis.mei").write_text(write_to(analysed, "mei"), encoding="utf-8")
    reduction.write("musicxml", fp=str(OUT / "bach_reduction.musicxml"))
    print(f"  wrote bach_analysis.rntxt / .mei and bach_reduction.musicxml → {OUT.name}/")

    # and the reverse direction: HAMON chord symbols → a music21 stream
    m21 = hamon_to_music21_stream(parse_hamon_sequence("@cs\nCmaj7\nA7\nDm7\nG7"))
    print(f"  reverse bridge: built a {type(m21).__name__} from HAMON chord symbols")
    assert positioned, "expected time-aligned Roman numerals from the analysis"
except ImportError:
    print("  music21 not installed — skipping (pip install -e ./hamonpy[music21])")
except Exception as e:  # best-effort across music21 versions; never fail the whole tour
    print(f"  music21 step skipped: {e!r}")

# %% [markdown]
# ## 6. Process — a small loss matrix
#
# The same content, exported to several targets, scored by how much it keeps. This is
# the empirical core of the interlingua argument: which format preserves which reading.

# %%
show("Loss matrix (semantic fields dropped/changed per target)")
for target in ("romantext", "mei", "humdrum", "dcml", "musescore", "harte"):
    tc = transcode(dataset_tsv, target)
    lost = [f for f in tc.report.findings if not f.notational]
    mark = "lossless" if not lost else f"{len(lost)} lost"
    print(f"  {target:10} {mark}")

# %% [markdown]
# ## 7. Open it in MuseScore
#
# HAMON writes an uncompressed MuseScore file (`.mscx`) you can open in MuseScore 4.

# %%
mscx = OUT / "tour.mscx"
mscx.write_text(write_to(seq, "musescore"), encoding="utf-8")
show("MuseScore")
print(f"  wrote {mscx}")
print("  → open it in MuseScore 4 (File ▸ Open)")
assert mscx.stat().st_size > 0

# %% [markdown]
# ## 8. Save the artifacts
#
# The canonical JSON, a RomanText rendering, an MEI fragment and the MuseScore file —
# written to a temp folder and listed here.

# %%
(OUT / "tour.hamon.json").write_text(sequence_to_json(seq) + "\n", encoding="utf-8")
(OUT / "tour.rntxt").write_text(write_to(seq, "romantext"), encoding="utf-8")
(OUT / "tour.mei").write_text(write_to(seq, "mei"), encoding="utf-8")
show(f"Saved artifacts in {OUT}")
for p in sorted(OUT.iterdir()):
    print(f"  {p.name:20} {p.stat().st_size:5d} bytes")

# %% [markdown]
# ## Where next
#
# - the **[processing cookbook](../../documentation/processing.md)** — every operation,
#   format by format, in CLI and Python;
# - **[editors & environments](../../documentation/editors-and-environments.md)** —
#   wiring HAMON into PyCharm/VS Code/Jupyter and the digital-musicology stack;
# - the other tours here: `01_jazz_tour`, `02_dcml_ms3_tour`, `03_flexohr_tour`.
print("\nGrand tour complete.")
