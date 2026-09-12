"""Poster box 3 — what each encoding cannot say.

The same lead sheet, offered to every format HAMON can write. For each one we
count the analytical aspects the format has **no vocabulary for** — not what
our writer happens to drop, and not what it can only park in a free-text field,
because holding our string in a text slot says nothing about the format and
nothing another tool could act on.

The answer is not a ranking of good and bad formats. It is a map of what each
one was built to say. Humdrum keeps the chords in one spine and the analysis in
another, so nothing is lost. MusicXML is a notation format: it carries the chord
symbols a player reads, and has nowhere to put the function or the key. DCML and
RomanText are the mirror image — the Roman analysis survives, the chord symbols
have no home at all.

Run:  python ICCCM26/poster/example3.py
"""
import textwrap
from pathlib import Path

from hamonpy.capability import ASPECT_LABEL, native_loss
from hamonpy.cli import convert_file
from hamonpy.serialize import sequence_to_dict

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
SOURCE = EXAMPLES / "flagship_love_walked_in.hamon"
SHOWN = ("hamon", "humdrum", "musicxml", "mei", "romantext", "dcml", "harte")

text = SOURCE.read_text(encoding="utf-8")
seq_dict = sequence_to_dict(convert_file(SOURCE))

for fmt in SHOWN:
    lost = native_loss(seq_dict, text, fmt)
    what = ", ".join(f"{ASPECT_LABEL.get(k, k)} x{n}" for k, n in lost.items())
    print(textwrap.fill(f"{fmt:10} {what or 'nothing — it can say all of it'}",
                        60, subsequent_indent=" " * 11))
