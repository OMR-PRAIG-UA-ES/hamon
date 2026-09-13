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
# # From a score with no analysis to every encoding
#
# The other tours start from harmony somebody already wrote down. This one starts
# from a score that carries **none**: a Bach chorale straight out of music21's
# corpus, four voices and not one harmonic label in the file.
#
# The chain is: analyse the score, put the result in HAMON, and let HAMON write it
# out to every format that will take it — measuring, per format, what could not be
# said. The analysis is music21's; HAMON's job starts the moment there is something
# to carry.
#
# Requires the optional extras `pip install "hamonpy[music21,flexohr]"`.

# %%
from music21 import corpus, roman

from hamonpy.adapters.flexohr import hamon_semantic_to_ohr
from hamonpy.capability import ASPECT_LABEL, native_loss
from hamonpy.cli import convert_text
from hamonpy.report import WRITERS, write_to
from hamonpy.serialize import sequence_to_dict


def show(title):
    print("\n" + title + "\n" + "-" * len(title))


# %% [markdown]
# ## 1. A score with nothing in it
#
# `bwv66.6` is four staves of notes. It has a key signature, and that is the whole
# of its harmonic information — no figures, no numerals, no chord symbols.

# %%
score = corpus.parse("bach/bwv66.6")
assert not score.recurse().getElementsByClass("Harmony"), "the file carries no harmony"
print(f"  {len(score.parts)} voices, {len(score.recurse().notes)} notes, 0 harmony labels")

# %% [markdown]
# ## 2. Analyse it
#
# Collapse the voices to a chord per onset, find the key, and read each chord as a
# Roman numeral in that key. This is music21 doing musicology; nothing here is HAMON.

# %%
key = score.analyze("key")
chords = list(score.chordify().recurse().getElementsByClass("Chord"))[:12]
figures = [roman.romanNumeralFromChord(c, key).figure for c in chords]

show(f"music21 says: {key}")
print("  " + " ".join(figures))

# %% [markdown]
# ## 3. Into HAMON
#
# A Roman-numeral sequence under the key it was heard in. From here on it is the
# same typed model every other tour uses, and the key is a **region** over the
# groups rather than a property of each label.

# %%
hamon_text = f"@rn\n@key:{key.tonic.name}:{key.mode}\n" + "\n".join(figures)
seq = convert_text(hamon_text, "hamon")

region = seq.regions[0]
assert len(seq.groups) == len(figures)
acc = {"sharp": "#", "flat": "b", None: ""}[region.key.tonic.accidental]
show("HAMON")
print(f"  {len(seq.groups)} labels over one region: "
      f"{region.key.tonic.note}{acc} {region.key.mode}")

# %% [markdown]
# ## 4. Out to everything, and what each one loses
#
# `native_loss` counts the aspects a format has **no vocabulary for** — not what our
# writer happens to drop, and not what it could only park in a free-text field.
#
# For a pure Roman analysis the split is clean. The formats built for functional
# analysis carry all of it. The formats built for chord symbols keep no numerals at
# all, so for them the analysis is the loss.

# %%
seq_dict = sequence_to_dict(seq)

show("what each encoding cannot say")
for fmt in WRITERS:
    lost = native_loss(seq_dict, hamon_text, fmt)
    what = ", ".join(f"{ASPECT_LABEL.get(a, a)} x{n}" for a, n in lost.items())
    print(f"  {fmt:10} {what or 'nothing'}")

lossless = [f for f in WRITERS if not native_loss(seq_dict, hamon_text, f)]
assert {"dcml", "romantext", "humdrum"} <= set(lossless)

# %% [markdown]
# The three that lose nothing are the three whose vocabulary was designed for this
# kind of statement. Here is the same analysis as RomanText, written by HAMON:

# %%
show("RomanText")
print("\n".join("  " + line for line in write_to(seq, "romantext", "native").splitlines()[:6]))

# %% [markdown]
# ## 5. And on to the object model
#
# [FlexOHR](https://pypi.org/project/flexohr/) (DCMLab) is not a file format: it is a
# harmony **object model**, a chord as intervals over a reference pitch, for analysis
# rather than for storage. HAMON hands it each label, so a score that had no analysis
# an hour ago arrives as objects DCMLab's tooling already understands.

# %%
show("HAMON → FlexOHR")
for fig, group in list(zip(figures, seq.groups))[:4]:
    ohr = hamon_semantic_to_ohr(group.primary[0].semantic, key=key.tonic.name)
    quality = ohr.get_property("chord_quality").name
    inversion = ohr.get_property("inversion").name
    print(f"  {fig:<7} → quality={quality:<22} inversion={inversion}")

# %% [markdown]
# ## What this tour is arguing
#
# Nothing here required a bespoke converter. The analyser is music21's, the object
# model is DCMLab's, and the encodings are everybody's. HAMON is the layer in the
# middle that lets them be swapped without the harmony quietly degrading on the way
# — and when a target genuinely cannot hold something, it says which aspect and how
# many times, instead of dropping it in silence.
