"""Tests for the Rock Corpus adapter (hamonpy.adapters.rock_corpus)."""
from __future__ import annotations

from hamonpy.adapters.rock_corpus import rock_corpus_to_hamon, _rock_to_hamon_roman


def test_quality_letter_normalisation():
    assert _rock_to_hamon_roman("Id7") == "I7"
    assert _rock_to_hamon_roman("Id42") == "I42"
    assert _rock_to_hamon_roman("iih43") == "iiø43"
    assert _rock_to_hamon_roman("viix7") == "vii°7"
    assert _rock_to_hamon_roman("iio6") == "ii°6"


def test_macro_expansion_and_measures():
    har = "\n".join([
        "% A song",
        "Vr: I | IV | V | I |",
        "S: [C] $Vr $Vr",
    ])
    seq = rock_corpus_to_hamon(har)
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["I", "IV", "V", "I", "I", "IV", "V", "I"]   # $Vr twice
    assert seq.regions[0].key.tonic.note == "C"
    # measures advance 1..8
    assert [g.position.measure for g in seq.groups] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_measure_repeat_and_rest_and_inline_comment():
    har = "\n".join([
        "S: [a] i |*3 R | iv | % could be different",
    ])
    seq = rock_corpus_to_hamon(har)
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["i", "i", "i", "iv"]      # i repeated to 3 measures, R is a rest
    assert seq.regions[0].key.tonic.note == "A"


def test_ref_repeat_star():
    har = "\n".join([
        "A: I | V |",
        "S: [G] $A*2",
    ])
    seq = rock_corpus_to_hamon(har)
    assert [g.primary[0].surface for g in seq.groups] == ["I", "V", "I", "V"]


def test_unparseable_chord_kept_as_text():
    seq = rock_corpus_to_hamon("S: [C] I | Vs4 |")
    labels = [g.primary[0] for g in seq.groups]
    assert labels[0].semantic.kind == "roman"
    assert labels[1].semantic.kind == "text" and labels[1].surface == "Vs4"


def test_no_song_rule_is_empty():
    assert rock_corpus_to_hamon("% just a comment\n").groups == []
