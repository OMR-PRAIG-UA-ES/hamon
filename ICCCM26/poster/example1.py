"""Poster box 1 — any encoding in, one typed model out.

Two files that look nothing alike. A lead-sheet analysis written in HAMON,
which carries the chord symbols a player reads *and* the Roman reading of the
same bars, coordinated. And a Harte annotation, the format audio chord
estimation publishes in, which has chord labels and nothing else.

Both land in the same typed model, and every label keeps the exact glyphs it
came in as (`surface`) next to the normalized meaning (`semantic`).

Run:  python ICCCM26/poster/example1.py
"""
from pathlib import Path

from hamonpy.cli import convert_file

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

seq = convert_file(EXAMPLES / "flagship_love_walked_in.hamon")

print("Love Walked In (Gershwin), mm. 29-30 — two readings, one model")
for g in seq.groups[4:7]:
    both = " ".join(f"{lab.layer}={lab.surface:<7}" for lab in g.primary)
    print(f"  m{g.position.measure} beat {g.position.beat:g}   {both}".rstrip())

key = seq.regions[0].key
print(f"  key           {key.tonic.note} {key.mode}   (a region, not a label)")

harte = convert_file(EXAMPLES / "changes.lab", "harte")
print("changes.lab (Harte) — same model, from a completely different notation")
print("  " + "  ".join(lab.primary[0].surface for lab in harte.groups))
