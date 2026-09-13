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
# # HAMON for corpus curation — the Choro Songbook
#
# The DCML [*Choro Songbook Corpus*](https://github.com/DCMLab/choro) encodes the same
# music **twice**: a merged table (`choro.tsv`, one row per chord onset, with the chord
# in three encodings) and per-piece **form-grammar** transcriptions
# (`transcriptions/*.txt`: phrases `P1: A7 | Dm |…`, parts `PartA: $P1 $P2`, a song
# `S[Dm, 2/4]: $PartA …`).
#
# Keeping those in agreement — and checking the three chord encodings against each other
# — is fiddly by hand. HAMON parses every encoding into **one typed model**, so each
# audit becomes a short comparison. We run three:
#
# 1. **Consistency** — does the expanded transcription reproduce the TSV chord column?
# 2. **Correctness (absolute)** — do the `chord` and `harte` columns name the same root?
# 3. **Correctness (functional)** — does each Roman numeral, read in its `local_key`,
#    point at the same root as the absolute chord?
#
# A small **extract** of the corpus lives in [`use-cases/choro/`](../choro/); point the
# paths at a full checkout to run it over all 295 pieces.

# %%
import csv
import re
from pathlib import Path

from hamonpy.adapters import choro
from hamonpy.ast import ChordSymbolSemantic, Key, PitchClass
from hamonpy.normalize import degree_to_pitch
from hamonpy.parse import parse_hamon_sequence

try:
    HERE = Path(__file__).resolve().parent
except NameError:
    HERE = Path.cwd()
CHORO = HERE.parent / "choro"

_EXTRACT = CHORO / "choro-extract.tsv"
if not _EXTRACT.exists():
    print("the DCML Choro Songbook extract is CC BY-NC-SA 4.0 and is not redistributed with HAMON; fetch it with `hamon datasets download choro`.")
    raise SystemExit(0)

pieces = choro.read_tsv(_EXTRACT.read_text(encoding="utf-8"))


def show(title):
    print("\n" + title + "\n" + "-" * len(title))


_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ACC = {"sharp": 1, "flat": -1, "double-sharp": 2, "double-flat": -2, "natural": 0, None: 0}


def pitch_pc(pitch):
    """Absolute pitch-class (0–11) of a PitchClass."""
    return (_PC[pitch.note] + _ACC[pitch.accidental]) % 12


def root_pc(semantic):
    """Absolute pitch-class of a parsed chord-symbol root, or None."""
    if not isinstance(semantic, ChordSymbolSemantic):
        return None
    return pitch_pc(semantic.root)


def parse_key(text):
    m = re.match(r"^([A-G])([#b]?)(m?)$", text.strip())
    acc = {"#": "sharp", "b": "flat", "": None}[m.group(2)]
    return Key(tonic=PitchClass(note=m.group(1), accidental=acc),
               mode="minor" if m.group(3) == "m" else "major")


# %% [markdown]
# ## 1. Consistency: transcription ↔ TSV
#
# Expand each `.txt` song grammar to its flat chord-onset sequence (empty bars and `.`
# hold the previous chord; `$ref*N` repeats) and compare, chord for chord, with the
# piece's rows in the TSV. They should be identical.

# %%
show("Transcription vs TSV (chord sequence)")
flagged = []
for fn, rows in pieces.items():
    txt = (CHORO / "transcriptions" / fn).read_text(encoding="utf-8")
    onsets = choro.expand_transcription(txt)
    tsv_chords = [r["chord"] for r in rows]
    ok = onsets == tsv_chords
    print(f"  {fn:26} txt={len(onsets):3d}  tsv={len(tsv_chords):3d}  {'consistent' if ok else 'DIVERGES'}")
    if not ok:
        i = next((k for k, (a, b) in enumerate(zip(onsets, tsv_chords)) if a != b), min(len(onsets), len(tsv_chords)))
        print(f"      first divergence at onset {i}: txt={onsets[i:i+3]} vs tsv={tsv_chords[i:i+3]}")
        flagged.append(fn)

# The extract deliberately includes one piece whose two encodings disagree — the whole
# point is that HAMON *finds* it instead of it slipping through.
assert "1_forro_de_gala_WF.txt" in flagged, "expected the known inconsistency to be flagged"

# %% [markdown]
# ## 2. Correctness (absolute): chord ↔ Harte
#
# The `chord` and `harte` columns are two absolute encodings of the same chord. Parse
# both with HAMON and check they agree on the root pitch-class.

# %%
show("chord vs harte (root)")
agree = total = 0
for fn, rows in pieces.items():
    for r in rows:
        ch, ha = choro.normalize_chord(r["chord"]), (r.get("harte") or "").strip()
        if not ch or not ha or ha == "N" or r["chord"] == "NC":
            continue
        a = root_pc(parse_hamon_sequence("@cs\n" + ch).groups[0].primary[0].semantic)
        hseq = choro.harte_text_to_hamon(ha)
        b = root_pc(hseq.groups[0].primary[0].semantic) if hseq.groups else None
        if a is None or b is None:
            continue
        total += 1
        agree += (a == b)
print(f"  {agree}/{total} chords agree on root  ({100*agree/total:.1f}%)")
assert agree == total, "chord and harte should name the same root"

# %% [markdown]
# ## 3. Correctness (functional): chord ↔ Roman numeral in its key
#
# The hard one by hand: is each Roman numeral consistent with the absolute chord, given
# the `local_key`? HAMON's `degree_to_pitch` realises the numeral in the key (mode-aware,
# so `VII` in a minor key is the natural ♭7) — then we compare roots.

# %%
show("chord vs Roman-in-key (root)")
agree = total = 0
mismatches = []
for fn, rows in pieces.items():
    for r in rows:
        ch, rn, lk = choro.normalize_chord(r["chord"]), r["rn_chord"].strip(), r["local_key"].strip()
        if not ch or not rn or not lk or r["chord"] == "NC":
            continue
        m = re.match(r"^([b#]*)([iIvV]+)", rn)
        if not m:
            continue
        a = root_pc(parse_hamon_sequence("@cs\n" + ch).groups[0].primary[0].semantic)
        rn_pc = pitch_pc(degree_to_pitch(parse_key(lk), list(m.group(1)), m.group(2)))
        if a is None or rn_pc is None:
            continue
        total += 1
        if a == rn_pc:
            agree += 1
        else:
            mismatches.append((fn, r["chord"], rn, lk))
print(f"  {agree}/{total} chords agree with their Roman numeral  ({100*agree/total:.1f}%)")
for mm in mismatches[:8]:
    print("    mismatch:", mm)
assert agree == total, "each chord should match its Roman numeral read in local_key"

# %% [markdown]
# ## What this shows
#
# Two of the three checks pass cleanly over the extract (the encodings are internally
# faithful); the first flags a piece whose transcription and table disagree. Over the
# full corpus the same three functions audit all 295 pieces — the kind of cross-file,
# cross-encoding check that HAMON's one typed model turns from a scripting chore into a
# few lines. The `choro` adapter is in `hamonpy/adapters/choro.py`.
print("\nChoro corpus audit complete.")
