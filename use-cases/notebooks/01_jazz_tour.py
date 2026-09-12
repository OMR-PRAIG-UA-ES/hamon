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
# # HAMON — a jazz tour
#
# A 5-minute tour of HAMON on jazz harmony. We stitch two use-cases together:
#
# - [`jazz-leadsheet/`](../jazz-leadsheet/) — chord-symbol changes with an applied
#   function (`A7[of:ii]`),
# - [`berklee-jazz/`](../berklee-jazz/) — a Berklee reading with tensions, a related
#   ii–V, and altered dominants.
#
# We **parse** the surface into a typed AST, **export** it to other formats, and ask
# HAMON exactly **what each export loses** — the lossy diff is the point of an
# exchange standard.

# %%
from pathlib import Path

from hamonpy.parse import parse_hamon_sequence
from hamonpy.export import hamon_to_ireal, hamon_to_romantext
from hamonpy.serialize import sequence_to_hamon_text
from hamonpy.report import lossy_report
from hamonpy.ast import ChordSymbolSemantic

# Resolve use-cases/ whether run as a script (__file__ set) or in a Jupyter
# kernel (cwd is the notebook dir, i.e. use-cases/notebooks/).
try:
    HERE = Path(__file__).resolve().parent
except NameError:
    HERE = Path.cwd()
USE_CASES = HERE.parent


def show(title):
    print("\n" + title + "\n" + "-" * len(title))


# %% [markdown]
# ## 1. A jazz leadsheet → typed chord symbols
#
# `Dm7 G7 Cmaj7 A7[of:ii] Dm7` — a ii–V–I, then a secondary dominant `A7` that
# resolves to the `Dm7` (ii). The `[of:ii]` is HAMON's **applied-function** marker:
# it records the functional reading *without* mutating the chord.

# %%
seq = parse_hamon_sequence((USE_CASES / "jazz-leadsheet" / "tune.hamon").read_text())

show("Changes → (root, quality, applied-target)")
for g in seq.groups:
    lbl = g.primary[0]
    s = lbl.semantic
    applied = lbl.attributes.applied.target if (lbl.attributes and lbl.attributes.applied) else None
    assert isinstance(s, ChordSymbolSemantic)
    print(f"  {lbl.surface:<12} {s.root.note}{('' if not s.root.accidental else s.root.accidental)}"
          f" {s.seventh:<6} of={applied}")

# The applied target is carried on the AST, not faked into the chord:
a7 = seq.groups[3].primary[0]
assert a7.semantic.root.note == "A" and a7.semantic.seventh == "dom7"
assert a7.attributes.applied.target == "ii"
print("\n  ✓ A7 stays a plain dom7 chord; the V/ii reading lives in attributes.applied")

# %% [markdown]
# ## 2. A Berklee reading → tensions + related ii–V
#
# Same idea, richer: `@key:C` opens a tonal region, `Eø7[of:ii]` / `A7b9[of:ii]`
# are the **related ii–V of ii**, and `G7b9b13` is an altered primary dominant whose
# tensions are lifted into `alterations`.

# %%
berklee = parse_hamon_sequence((USE_CASES / "berklee-jazz" / "changes.hamon").read_text())

show("Berklee changes → tensions / applied")
for g in berklee.groups:
    s = g.primary[0].semantic
    alt = [a["degree"] for a in s.alterations] if s.alterations else []
    applied = g.primary[0].attributes.applied.target if (g.primary[0].attributes and g.primary[0].attributes.applied) else None
    print(f"  {g.primary[0].surface:<12} alterations={alt!s:<10} of={applied}")

region = berklee.regions[0]
print(f"\n  home region: {region.kind} {region.key.tonic.note} {region.key.mode}")
assert [a["degree"] for a in berklee.groups[4].primary[0].semantic.alterations] == [9, 13]
print("  ✓ G7b9b13 → alterations [9, 13]; related ii–V both carry of=ii")

# %% [markdown]
# ## 3. Export to other formats
#
# The canonical model round-trips out to whatever the consumer speaks. iReal Pro
# wants bare chord symbols; RomanText wants degrees in a key.

# %%
show("→ iReal Pro")
print(hamon_to_ireal(berklee))

show("→ RomanText")
print(hamon_to_romantext(berklee))

show("→ HAMON (canonical round-trip)")
print(sequence_to_hamon_text(berklee))

# %% [markdown]
# ## 4. The lossy diff — what does each export drop?
#
# This is what makes HAMON a *hub* rather than yet-another-format: it tells you,
# per field, what a given target cannot represent. iReal Pro has no notion of an
# applied function or a tonal region, so those are dropped (flagged
# non-`notational`, i.e. *semantic* loss).

# %%
rep = lossy_report(berklee, "ireal")
show(f"berklee-jazz → iReal:  lossless={rep.lossless}  ({len(rep.findings)} findings)")
for f in rep.findings:
    tag = "notation" if f.notational else "SEMANTIC"
    print(f"  [{tag}] {f.kind:<8} {f.path}  ←  {f.summary}")

# The applied [of:ii] readings and the @key:C region are the meaningful losses:
dropped = {f.summary for f in rep.findings if not f.notational}
assert "applied→ii" in dropped
print("\n  ✓ HAMON surfaces the semantic loss instead of hiding it.")
