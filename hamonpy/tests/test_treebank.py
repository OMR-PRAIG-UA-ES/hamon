"""Tests for the Jazz Harmony Treebank adapter (hamonpy/adapters/treebank.py)."""
from __future__ import annotations

from hamonpy.adapters.treebank import (
    leadsheet_chord_to_hamon_surface, treebank_json_to_hamon, treebank_tunes,
)
from hamonpy.ast import ChordSymbolSemantic

TREEBANK = (
    '[{"title":"A","key":"C","chords":["Dm7","G7","C^7"]},'
    ' {"title":"B","key":"F","chords":["F^7","Bb7","Eh7"]}]'
)


def test_leadsheet_quality_sigils():
    assert leadsheet_chord_to_hamon_surface("G^7") == "Gmaj7"
    assert leadsheet_chord_to_hamon_surface("Eh7") == "Eø7"
    assert leadsheet_chord_to_hamon_surface("Co7") == "C°7"
    assert leadsheet_chord_to_hamon_surface("F#m7") == "F#m7"


def test_first_tune_to_chord_symbols():
    seq = treebank_json_to_hamon(TREEBANK)
    assert [g.primary[0].surface for g in seq.groups] == ["Dm7", "G7", "Cmaj7"]
    sems = [g.primary[0].semantic for g in seq.groups]
    assert all(isinstance(s, ChordSymbolSemantic) for s in sems)
    assert sems[2].seventh == "maj7"


def test_select_tune_by_title():
    seq = treebank_json_to_hamon(TREEBANK, title="B")
    assert [g.primary[0].surface for g in seq.groups] == ["Fmaj7", "Bb7", "Eø7"]


def test_iterate_tunes():
    tunes = treebank_tunes(TREEBANK)
    assert [t["title"] for t in tunes] == ["A", "B"]
