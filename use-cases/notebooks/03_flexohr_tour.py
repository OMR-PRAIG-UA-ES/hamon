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
# # HAMON ↔ FlexOHR
#
# [FlexOHR](https://pypi.org/project/flexohr/) — *Flexible and Extensible Object for
# Harmony Representation* (DCMLab / Johannes Hentschel et al.) — is a harmony **object
# model**. This tour hands HAMON labels to FlexOHR's `OHR` objects and reads them back,
# with **HAMON as the wire format** between the encodings and FlexOHR.
#
# Scope: **chord symbols** and **Roman numerals**. Requires the optional extra
# `pip install -e "./hamonpy[flexohr]"`.

# %%
from hamonpy.parse import parse_hamon_sequence
from hamonpy.adapters.flexohr import (
    hamon_semantic_to_ohr,
    ohr_to_hamon_semantic,
    hamon_to_flexohr,
    flexohr_to_hamon,
)
from flexohr.harmony.harmony_enums import ChordQuality, Inversion


def show(title):
    print("\n" + title + "\n" + "-" * len(title))


# %% [markdown]
# ## 1. Chord symbols → FlexOHR OHR objects
#
# Parse a ii–V–I plus a half-diminished chord and a slash chord, hand each to FlexOHR,
# and read the object model back out: the root pitch class, the chord quality, and the
# inversion (a slash bass resolves to one).

# %%
seq = parse_hamon_sequence("@cs\nDm7\nG7\nCmaj7\nBø7\nC/E")

show("chord → FlexOHR OHR")
for g in seq.groups:
    ohr = hamon_semantic_to_ohr(g.primary[0].semantic)
    root = ohr.component("r").value.name
    quality = ohr.get_property("chord_quality").name
    inversion = ohr.get_property("inversion").name
    print(f"  {g.primary[0].surface:<7} → root={root:<3} quality={quality:<22} inversion={inversion}")

# Cmaj7 is a major-seventh OHR; the slash chord C/E is a first inversion.
cmaj7 = hamon_semantic_to_ohr(parse_hamon_sequence("@cs\nCmaj7").groups[0].primary[0].semantic)
c_over_e = hamon_semantic_to_ohr(parse_hamon_sequence("@cs\nC/E").groups[0].primary[0].semantic)
assert cmaj7.get_property("chord_quality") == ChordQuality.major_seventh
assert c_over_e.get_property("inversion") == Inversion.first
print("\n  ✓ quality and inversion land as typed FlexOHR objects")

# %% [markdown]
# ## 2. …and back to HAMON — a round-trip
#
# `flexohr_to_hamon` reconstructs the HAMON semantic from the OHR. Root, quality,
# seventh, suspensions and the slash bass all survive the round-trip.

# %%
ohrs = hamon_to_flexohr(seq)
back = flexohr_to_hamon(ohrs)

show("HAMON → FlexOHR → HAMON")
for src, dst in zip(seq.groups, back.groups):
    a, b = src.primary[0].semantic, dst.primary[0].semantic
    bass = f"{b.bass.note}" if b.bass else None
    print(f"  {src.primary[0].surface:<7} root={b.root.note}{b.root.accidental or ''} "
          f"seventh={b.seventh!s:<6} bass={bass}")
    assert (a.root, a.quality, a.seventh, a.bass) == (b.root, b.quality, b.seventh, b.bass)
print("\n  ✓ round-trip preserves root, quality, seventh and slash bass")

# %% [markdown]
# ## 3. Roman numerals in a key context
#
# A Roman numeral needs a tonal context, so the adapter builds the OHR against a key
# scale (default C major, overridable with `key=`). The degree, its accidentals, and
# the figured-bass inversion come back on the round-trip.

# %%
show("Roman → FlexOHR → Roman  (key of C)")
for label in ["V7", "ii", "V65", "bVII"]:
    sem = parse_hamon_sequence(f"@rn\n{label}").groups[0].primary[0].semantic
    rn = ohr_to_hamon_semantic(hamon_semantic_to_ohr(sem, key="C"))
    prefix = "".join(rn.prefixAccidentals or [])
    print(f"  {label:<5} → degree={prefix}{rn.degree:<4} tail={rn.tail}")

bvii = ohr_to_hamon_semantic(
    hamon_semantic_to_ohr(parse_hamon_sequence("@rn\nbVII").groups[0].primary[0].semantic, key="C")
)
assert bvii.degree == "VII" and bvii.prefixAccidentals == ["b"]
print("\n  ✓ degree, accidentals and figured-bass inversion survive")

# %% [markdown]
# ## What's in / out (first cut)
#
# **In:** chord symbols (root, quality + seventh, suspensions, slash bass) and Roman
# numerals (degree + accidentals, triad/seventh quality, figured-bass inversion in a key).
#
# **Out for now:** chord extensions/alterations, applied/secondary chains, pedal points,
# and parenthesised changes — the same Roman-numeral gaps tracked in
# [`ongoingwork/`](../../ongoingwork/).
