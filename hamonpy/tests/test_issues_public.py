"""Regression tests for issues reported on the public repo (OMR-PRAIG-UA-ES/hamon).

One test per case the reporter gave, with their inputs and expected values, so the reply
to the issue can point at it. Issues #1–#3 are pinned beside their code (`test_music21.py`,
`test_harte.py`); these are the grammar-level ones.
"""
from __future__ import annotations

import pytest

from hamonpy import normalize
from hamonpy.adapters.treebank import leadsheet_chord_to_hamon_surface
from hamonpy.ast import ChordSymbolSemantic, TextSemantic
from hamonpy.parse import parse_hamon, parse_hamon_sequence


def sem(surface: str):
    return parse_hamon(surface)[0].primary[0].semantic


def alterations(s: ChordSymbolSemantic):
    return [(a["accidental"], a["degree"]) for a in (s.alterations or [])]


# ---------------------------------------------------------------------------
# Issue #4 — a letter quality followed by `b` / `add` was lexed as one WORD
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("surface, quality", [
    ("Cmb9", "minor"),
    ("Cminb9", "minor"),
    ("Cdimb9", "diminished"),
])
def test_quality_then_flat_ninth(surface, quality):
    s = sem(surface)
    assert isinstance(s, ChordSymbolSemantic)
    assert s.quality == quality
    assert alterations(s) == [("flat", 9)]
    assert s.seventh is None            # it used to come out as a dominant seventh
    assert not s.extensions


def test_dim_then_flat_fifth():
    s = sem("Cdimb5")
    assert (s.quality, alterations(s)) == ("diminished", [("flat", 5)])


def test_dim_then_add_nine():
    s = sem("Cdimadd9")
    assert (s.quality, s.adds, s.seventh) == ("diminished", [9], None)


def test_the_quality_is_the_same_when_not_followed_by_a_letter():
    # The spellings the reporter says already worked must agree with the glued ones.
    assert alterations(sem("Cm7b9")) == [("flat", 9)]
    assert sem("C°b9").quality == "diminished"
    assert sem("Cm(b9)") .quality == "minor"


@pytest.mark.parametrize("surface, note, accidental", [
    ("Ebbmaj7", "E", "double-flat"),    # the reporter's `Ebbmaj7`
    ("Ebb", "E", "double-flat"),
    ("Bbbm", "B", "double-flat"),
    ("E𝄫maj7", "E", "double-flat"),     # the Unicode spelling still works
    ("C##7", "C", "double-sharp"),
    ("Cx7", "C", "double-sharp"),       # `x` is the other ASCII double sharp
    ("C𝄪7", "C", "double-sharp"),
])
def test_ascii_double_accidentals_on_the_root(surface, note, accidental):
    s = sem(surface)
    assert isinstance(s, ChordSymbolSemantic)
    assert (s.root.note, s.root.accidental) == (note, accidental)


def test_ebbmaj7_is_a_major_seventh_not_a_dominant_one():
    s = sem("Ebbmaj7")
    assert (s.quality, s.seventh) == ("major", "maj7")


def test_a_single_b_is_still_a_flat():
    s = sem("Bbm7")
    assert (s.root.note, s.root.accidental, s.quality) == ("B", "flat", "minor")


def test_double_flat_alteration_and_bass():
    assert alterations(sem("C7bb9")) == [("double-flat", 9)]
    assert sem("Cm7/Gbb").bass.accidental == "double-flat"


# ---------------------------------------------------------------------------
# Issue #5 — an unrecognised word in a chord tail made a different chord
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("surface", ["Ger6", "Ger65", "Fr43", "Cmajfoo", "C7zz", "Gfoo", "Ger", "It+6"])
def test_unrecognised_word_keeps_the_label_as_text(surface):
    s = sem(surface)
    assert isinstance(s, TextSemantic)
    assert s.text == surface


def test_the_rule_does_not_depend_on_a_trailing_number():
    # `Gfoo` and `Gfoo7` used to be text and a chord respectively.
    assert isinstance(sem("Gfoo"), TextSemantic)
    assert isinstance(sem("Gfoo7"), TextSemantic)


@pytest.mark.parametrize("surface", ["Cmaj7", "Cm7b5", "C7sus4", "Cdim7", "C7(b9)", "Cadd9", "C6", "Cno3"])
def test_ordinary_chords_are_untouched(surface):
    assert isinstance(sem(surface), ChordSymbolSemantic)


def test_unread_parts_are_reported_to_the_sink():
    normalize.UNREAD_SINK = []
    try:
        normalize.normalize_chord_symbol_from_surface("C7foo")
        assert normalize.UNREAD_SINK == ["foo"]
    finally:
        normalize.UNREAD_SINK = None


# ---------------------------------------------------------------------------
# Found by the chord-tail catalog (`tools/scripts/chord_tail_catalog.py`)
# ---------------------------------------------------------------------------

def test_treebank_percent_is_half_diminished():
    # The Jazz Harmony Treebank spells half-diminished `%` (its readme); the adapter only
    # knew iReal's `h`, so `D%7` read as a plain dominant seventh.
    assert leadsheet_chord_to_hamon_surface("D%7") == "Dø7"
    s = sem(leadsheet_chord_to_hamon_surface("D%7"))
    assert (s.quality, s.seventh) == ("half-diminished", "hdim7")


def test_plain_four_is_an_added_tone():
    # The Choro songbook writes `G7(4)`.
    s = sem("G7(4)")
    assert (s.seventh, s.adds) == ("dom7", [4])


# ---------------------------------------------------------------------------
# Found while fixing #4: a flat bass after a chord with a tail was a syntax error
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("surface,root,quality,bass", [
    ("F#m7/Bb", ("F", "sharp"), "minor", ("B", "flat")),
    ("Dm7b5/Ab", ("D", None), "minor", ("A", "flat")),
    ("G7(b9)/Bb", ("G", None), "major", ("B", "flat")),
    ("Cmaj7/Ebb", ("C", None), "major", ("E", "double-flat")),
])
def test_flat_bass_after_a_tail(surface, root, quality, bass):
    s = sem(surface)
    assert isinstance(s, ChordSymbolSemantic)
    assert (s.root.note, s.root.accidental) == root
    assert s.quality == quality
    assert (s.bass.note, s.bass.accidental) == bass


@pytest.mark.parametrize("surface", ["C/foo", "F#m7/Bbfoo"])
def test_letters_after_the_bass_keep_the_label_as_text(surface):
    assert isinstance(sem(surface), TextSemantic)


def test_slash_inside_a_paren_group_is_not_a_bass():
    assert isinstance(sem("C7(b9/#11)"), ChordSymbolSemantic)


def test_catalog_measures_the_datasets_it_finds():
    """The catalog script runs end to end over whichever datasets are downloaded."""
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[2] / "tools" / "scripts"
    if not (scripts / "chord_tail_catalog.py").exists():
        pytest.skip("tools/ is not part of this checkout")
    sys.path.insert(0, str(scripts))
    try:
        import chord_tail_catalog as catalog
    finally:
        sys.path.pop(0)
    totals, tokens = catalog.measure()
    assert isinstance(totals, dict) and isinstance(tokens, dict)
    # No word in a chord tail goes unread in the sources we hold: that is the catalog's claim.
    assert not [t for t in tokens if any(ch.isalpha() for ch in t)]
    assert "# Chord-tail catalog" in catalog.render(totals, tokens)


def test_root_and_bass_glyphs_are_both_kept():
    """`F#m7/Bb` keeps the `#` of the root as well as the `b` of the bass (the bass used to
    overwrite the root's glyph in the rendering hints)."""
    seq = parse_hamon_sequence("F#m7/Bb")
    glyphs = seq.groups[0].primary[0].rendering.accidentalGlyphs
    assert glyphs == {"sharp": "#", "flat": "b"}
