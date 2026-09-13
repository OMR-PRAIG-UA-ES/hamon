"""Poster box 2 — the typed model, next to the glyphs it came from.

One bar of the lead sheet, m. 29 beat 4, where the chord symbol `A7` and the
Roman reading `V7/ii` describe the same sound. HAMON keeps both, each with its
own normalized meaning, and keeps the key they are heard in as a region of the
sequence rather than as a label.

`sequence_to_json(seq)` writes the whole thing; this prints the part that fits
on a poster.

Run:  python ICCCM26/poster/example2.py
"""
import json
import textwrap
from pathlib import Path

from hamonpy.cli import convert_file
from hamonpy.serialize import sequence_to_dict

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

d = sequence_to_dict(convert_file(EXAMPLES / "flagship_love_walked_in.hamon"))
group = d["groups"][5]

for lab in group["primary"]:
    line = f'{lab["layer"]:7}{lab["surface"]:8}{json.dumps(lab["semantic"])}'
    print(textwrap.fill(line, 58, subsequent_indent=" " * 15))
print(f'{"at":7}{"":8}{json.dumps(group["position"])}')
print(f'{"key":7}{"":8}{json.dumps(d["regions"][0]["key"])}')
