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
# # The corpora, read where they live
#
# The other tours argue about one piece. This one argues about the field.
#
# Each corpus below publishes harmony in its own table dialect, and each dialect
# arrived with its own paper and its own parser. None of them can be written back —
# they are read-only. HAMON reads all of them into the one typed model, with no
# per-corpus code on the caller's side: `convert_file` recognizes the dialect and
# hands back the same object every time.
#
# Requires the optional extra `pip install "hamonpy[flexohr]"` for the last section.

# %%
from pathlib import Path

from hamonpy.adapters.flexohr import flexohr_to_hamon, hamon_to_flexohr
from hamonpy.cli import FORMATS, convert_file, convert_text, detect_file_format
from hamonpy.report import WRITERS

try:                                  # the tours also run as notebooks, where
    HERE = Path(__file__).resolve().parent   # __file__ does not exist
except NameError:
    HERE = Path.cwd()
USE_CASES = HERE.parent

CORPORA = [
    ("Distant Listening Corpus", "distant-listening-corpus/harmonies.tsv"),
    ("Jazz Harmony Treebank", "jazz-harmony-treebank/treebank.json"),
    ("Choro Songbook", "choro/choro-extract.tsv"),
    ("Key / Modulation (DDMAL)", "key-modulation/snippet.krn"),
]

# %% [markdown]
# ## 1. Four corpora, four dialects, one call
#
# Each line is a different table layout, detected from the file itself. What comes
# back is the same `HamonSequence` in every case.

# %%
for title, rel in CORPORA:
    path = USE_CASES / rel
    if not path.exists():
        # The Choro extract is CC BY-NC-SA and does not ship with HAMON; the rest of
        # the tour stands on its own, so name the gap and carry on.
        print(f"{title:26}{'(not bundled)':16}"
              "`hamon datasets download choro` to run this line")
        continue
    seq = convert_file(path)
    heads = " ".join(lab.primary[0].surface for lab in seq.groups[:5])
    print(f"{title:26}{detect_file_format(path):16}{heads}")

# %% [markdown]
# ## 2. DiLeMMa, where the grid has to be collapsed
#
# [DiLeMMa](https://github.com/johentsch/dilemmadata) (Hentschel et al.) is the
# training data behind AnalysisGNN, so it ships **one row per note**, with the
# harmony repeated on every note it covers. Reading it means collapsing that grid
# back to one label per harmony.

# %%
DILEMMA = (
    "pitch\tunfolded_harmony_index\tmn\tbeat_float\tchord\tnumeral\tfigbass"
    "\trelativeroot\tlocalkey\tglobalkey\n"
    "60\t0\t1\t1.0\tI\tI\t\t\tI\tC\n"
    "64\t0\t1\t1.0\tI\tI\t\t\tI\tC\n"
    "62\t1\t1\t3.0\tV7/V\tV\t7\tV\tI\tC\n"
    "67\t2\t2\t1.0\tV\tV\t\t\tI\tC\n"
)
seq = convert_text(DILEMMA, "dilemma")
labels = [lab.primary[0].surface for lab in seq.groups]
assert labels == ["I", "V7/V", "V"], labels
print(f"{'DiLeMMa pitch array':26}{'dilemma':16}"
      + " ".join(labels) + "   (4 notes -> 3 harmonies)")

print(f"\n{len(FORMATS)} formats in, {len(WRITERS)} out. The other "
      f"{len(set(FORMATS) - set(WRITERS))} are read-only dialects nothing writes back.")

# %% [markdown]
# ## 3. And the object model the analysis is done in
#
# [FlexOHR](https://pypi.org/project/flexohr/) (DCMLab) is not a file format at all:
# it is a harmony **object model**, a chord as intervals over a reference pitch, for
# analysis rather than for storage. HAMON converts both ways, so a corpus read above
# can be handed straight to it.

# %%
lead = convert_text("@cs\n@key:C\nDm7\nG7\nCmaj7\nA7[of:ii]", "hamon")
ohr = hamon_to_flexohr(lead, key="C")[3]
intervals = " ".join(str(c).split("(")[1].split(",")[0] for c in ohr.body)
sem = flexohr_to_hamon([ohr]).groups[0].primary[0].semantic

print(f"\n{'FlexOHR (DCMLab)':26}A7[of:ii] -> {ohr.reference} "
      + " ".join(p.value for p in ohr.properties))
print(f"{'':26}             {intervals}")
print(f"{'':26}back -> {sem.root.note} {sem.quality} {sem.seventh}"
      "   (the glyphs and [of:ii] stay behind)")

# %% [markdown]
# That last line is the honest part. FlexOHR keeps the whole harmonic content — root,
# quality, seventh — and does not keep the exact glyphs or the applied function,
# because neither is its job. It represents the chord, not how it was written nor
# what it does in the key.
