"""Short, self-contained Python snippets for the poster's code boxes.

Each entry is a *summarized* but runnable-looking excerpt of the real hamonpy
API used by this package. ``print_snippets()`` dumps them to stdout so they can
be pasted into the poster (or rendered with a syntax highlighter).
"""
from __future__ import annotations

SNIPPETS: dict[str, str] = {
    "1 · Parse any encoding into HAMON": '''\
from pathlib import Path
from hamonpy.cli import convert_text, convert_file

# one label per line; A7[of:ii] = a Berklee applied dominant (V7 of ii)
text = "@cs\\n@key:C\\nDm7\\nG7\\nCmaj7\\nA7[of:ii]"
seq = convert_text(text, "hamon")

for g in seq.groups:                      # surface in, one typed model out
    lab = g.primary[0]
    of = lab.attributes and lab.attributes.applied
    print(lab.surface, "\u2192", lab.semantic.root.note, lab.semantic.quality,
          lab.semantic.seventh, f"of {of.target}" if of else "")
# Dm7       \u2192 D minor min7
# G7        \u2192 G major dom7
# Cmaj7     \u2192 C major maj7
# A7[of:ii] \u2192 A major dom7 of ii      <- the function, recovered

# ...or read any encoding from disk (Harte, iReal, DCML, MEI, Humdrum, MusicXML)
harte = convert_file(Path("examples/changes.lab"), "harte")''',

    "2 · One typed AST → HAMON JSON": '''\
from hamonpy.serialize import sequence_to_json

print(sequence_to_json(seq))
# {"groups":[{"primary":[{"surface":"Dm7",
#   "semantic":{"kind":"chordSymbol","root":{"note":"D"},
#               "quality":"minor","seventh":"min7"}}]}, ...]}''',

    "3 · What each encoding cannot say (xencoding)": '''\
from hamonpy.capability import native_loss
from hamonpy.report import WRITERS
from hamonpy.serialize import sequence_to_dict

for fmt in WRITERS:                       # hamon, harte, mei, ireal, dcml, ...
    lost = native_loss(sequence_to_dict(seq), text, fmt)
    print(fmt, dict(lost))                # {} for hamon
    #  harte -> {'applied': 1, 'key': 1}  chord labels only: no function, no key
    #  text held as an opaque string does NOT count as carried''',

    "4 · Export, and see what the round-trip lost": '''\
from hamonpy.report import lossy_report, write_to

print(write_to(seq, "harte", mode="native"))   # only Harte's own vocabulary
rep = lossy_report(seq, "harte", mode="native")
for f in rep.semantic:
    print(f"[{f.kind}] {f.path}: {f.summary}")
# [dropped] groups[3].primary[0].attributes: applied→ii      (the function is gone)
# [dropped] regions[0]: {key=C major, kind=key, fromGroup=0}  (no key context)''',
}


def print_snippets() -> None:
    bar = "─" * 72
    for title, code in SNIPPETS.items():
        print(f"\n{bar}\n{title}\n{bar}\n{code}")
