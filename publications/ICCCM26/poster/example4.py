"""Poster box 4 — export, and see exactly what the round-trip lost.

Box 3 asked what a format *can* say. This one writes the file, reads it back,
and diffs it against the original, so the loss is measured rather than asserted.

Humdrum is the interesting case. Both readings survive, in two spines side by
side, and so does the key — but this writer places a label on the barline and
not on the beat within the bar, and the diff says so instead of quietly
rounding. MusicXML drops the second label of every group, which is the Roman
reading. DCML drops whole groups, because the chord symbols have no home in it.

That is the point: a conversion that loses something should be able to name it.

Run:  python ICCCM26/poster/example4.py
"""
from pathlib import Path

from hamonpy.cli import convert_file
from hamonpy.report import lossy_report, write_to

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

seq = convert_file(EXAMPLES / "flagship_love_walked_in.hamon")

humdrum = write_to(seq, "humdrum", mode="native").splitlines()
print("\n".join(humdrum[:2] + humdrum[9:12]))     # the header, then m. 29
print("        ^ chords and analysis, two spines, neither one lost")
print()

# Every diff also reports bookkeeping the target has no slot for (which layer a
# label belonged to, the HAMON version, the meter). Skip those to show the
# finding that is actually about the music.
BOOKKEEPING = {"layer", "version", "meters"}


def leaf(finding):
    return finding.path.rsplit(".", 1)[-1].split("[")[0]


for fmt in ("humdrum", "musicxml", "dcml"):
    findings = lossy_report(seq, fmt, mode="native").semantic
    musical = [f for f in findings if leaf(f) not in BOOKKEEPING]
    f = (musical or findings)[0]
    print(f"{fmt:9} {len(findings):2} findings, e.g. [{f.kind}] {f.path}: {f.summary}")
