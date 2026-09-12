"""Import resilience: a single un-parseable surface label must not crash the import.

Regression for the demo bug where DCML cadence/phrase markers embedded in MuseScore
<Harmony> text (e.g. 'I|PAC', 'V(64)', 'C.I[I{') raised a parser SyntaxError and the
whole file imported nothing.
"""
from __future__ import annotations

from hamonpy.cli import _labels_to_seq, convert_text


def test_bad_label_falls_back_to_text_not_crash():
    labels = ["I", "C.I[I{", "V(64)", "I|PAC}{", "ii7"]
    seq = _labels_to_seq(labels)
    # Every label is preserved as a group; nothing is dropped, nothing raised.
    assert len(seq.groups) >= len(labels) - 0
    surfaces = [l.surface for g in seq.groups for l in g.primary]
    assert "C.I[I{" in surfaces  # the offending label survives as text
    bad = next(l for g in seq.groups for l in g.primary if l.surface == "C.I[I{")
    assert bad.semantic.kind == "text"


def test_valid_labels_still_parse_normally():
    seq = _labels_to_seq(["Cmaj7", "Dm7", "G7"])
    kinds = [l.semantic.kind for g in seq.groups for l in g.primary]
    assert kinds == ["chordSymbol", "chordSymbol", "chordSymbol"]


def test_musescore_with_dcml_markers_imports_without_error():
    mscx = (
        '<?xml version="1.0"?><museScore><Score><Staff id="1">'
        "<Harmony><text>I</text></Harmony>"
        "<Harmony><text>I|PAC}{</text></Harmony>"
        "<Harmony><text>V(64)</text></Harmony>"
        "</Staff></Score></museScore>"
    )
    seq = convert_text(mscx, "musescore")
    assert len(seq.groups) == 3
