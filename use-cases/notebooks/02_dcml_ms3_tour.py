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
# # HAMON ⇄ DCML — driving `ms3` into the canonical model
#
# A tour of the [`distant-listening-corpus/`](../distant-listening-corpus/) use-case
# using a real **DCML analysis library**: [`ms3`](https://johentsch.github.io/ms3)
# (Johannes Hentschel), the parser behind the DCML corpora.
#
# DCML harmony annotations are terse strings like `.C.I`, `V64`, `V7/V`. `ms3`'s
# `expand_dcml.expand_labels` is the canonical **analysis step** that expands them
# into the structured `numeral/form/figbass/relativeroot/localkey/globalkey`
# columns. HAMON then lifts those into tonal regions, tonicizations and modulations.
#
# > Needs the optional `ms3` dependency: `pip install ms3`.

# %%
import pandas as pd

from ms3.expand_dcml import expand_labels
from hamonpy.adapters.ms3_adapter import ms3_expanded_to_hamon


def show(title):
    print("\n" + title + "\n" + "-" * len(title))


# %% [markdown]
# ## 1. Raw DCML labels
#
# A short progression in C major that tonicizes the dominant (`V7/V`). The leading
# `.C.` on the first label sets the global key; the `mc`/`mn`/`quarterbeats` columns
# are the measure/time anchors `ms3` (and HAMON) use for alignment.

# %%
raw = pd.DataFrame({
    "mc":           [1, 1, 2, 3, 4, 5],
    "mn":           [1, 1, 2, 3, 4, 5],
    "quarterbeats": [0, 2, 4, 8, 12, 16],
    "label":        [".C.I", "V64", "I6", "V7/V", "V", "I"],
})
show("Raw DCML labels")
print(raw[["mc", "quarterbeats", "label"]].to_string(index=False))

# %% [markdown]
# ## 2. `ms3` expands them (the DCML analysis step)
#
# `expand_labels` parses each terse label into its components and **propagates** the
# key context downward — note how `localkey`/`globalkey` get filled in, and `V7/V`
# gets `relativeroot = V`.

# %%
expanded = expand_labels(raw, column="label")
cols = [c for c in ["chord", "numeral", "form", "figbass", "relativeroot", "localkey", "globalkey"]
        if c in expanded.columns]
show("ms3 expanded harmony table")
print(expanded[cols].fillna("").to_string(index=False))

# %% [markdown]
# ## 3. HAMON lifts the expanded table into the canonical model
#
# `ms3_expanded_to_hamon` delegates to HAMON's DCML-expanded adapter: the key
# columns become **tonal regions**, `relativeroot` becomes a **tonicization**, and
# the `quarterbeats` become time-aligned positions.

# %%
seq = ms3_expanded_to_hamon(expanded)

show("Groups (surface @ time)")
for g in seq.groups:
    t = g.position.time if g.position else None
    print(f"  {g.primary[0].surface:<6} @ q={t}")

show("Tonal regions")
for r in seq.regions:
    print(f"  {r.kind:<13} groups[{r.from_group}:{r.to_group}]  "
          f"{r.key.tonic.note} {r.key.mode}  degree={r.degree}")

# The V7/V is recognised as a tonicization of the dominant (G major):
ton = next(r for r in seq.regions if r.kind == "tonicization")
assert ton.key.tonic.note == "G" and ton.degree == "V"
print("\n  ✓ ms3 → HAMON: V7/V recognised as a tonicization of V (G major).")
