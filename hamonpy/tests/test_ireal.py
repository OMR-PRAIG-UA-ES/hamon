"""Tests for the iReal Pro adapter (hamonpy/adapters/ireal.py)."""
from __future__ import annotations

import pytest

from hamonpy.adapters.ireal import ireal_chart_text_to_hamon, _quality_suffix_to_hamon
from hamonpy.ast import ChordSymbolSemantic, NoChordSemantic


# ---------------------------------------------------------------------------
# Quality suffix mapping
# ---------------------------------------------------------------------------

def test_suffix_major_empty():
    assert _quality_suffix_to_hamon("") == ""


def test_suffix_minor():
    assert _quality_suffix_to_hamon("-") == "m"
    assert _quality_suffix_to_hamon("m") == "m"


def test_suffix_major7():
    assert _quality_suffix_to_hamon("^7") == "maj7"


def test_suffix_dominant7():
    assert _quality_suffix_to_hamon("7") == "7"


def test_suffix_minor7():
    assert _quality_suffix_to_hamon("-7") == "m7"
    assert _quality_suffix_to_hamon("m7") == "m7"


def test_suffix_hdim7():
    assert _quality_suffix_to_hamon("h7") == "ø7"
    assert _quality_suffix_to_hamon("ø7") == "ø7"


def test_suffix_dim7():
    assert _quality_suffix_to_hamon("dim7") == "°7"
    assert _quality_suffix_to_hamon("o7") == "°7"


def test_suffix_sus4():
    assert _quality_suffix_to_hamon("sus") == "sus4"
    assert _quality_suffix_to_hamon("sus4") == "sus4"


# ---------------------------------------------------------------------------
# Plain-text chord parsing
# ---------------------------------------------------------------------------

def test_plain_C_major():
    seq = ireal_chart_text_to_hamon("C\n")
    assert len(seq.groups) == 1
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "C"
    assert sem.quality == "major"


def test_plain_G_dom7():
    seq = ireal_chart_text_to_hamon("G7\n")
    assert len(seq.groups) == 1
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "G"
    assert sem.seventh == "dom7"


def test_plain_Bb_maj7():
    seq = ireal_chart_text_to_hamon("Bbmaj7\n")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "B"
    assert sem.root.accidental == "flat"
    assert sem.seventh == "maj7"


def test_plain_multiple_chords():
    text = "C\nF\nG7\nAm\n"
    seq = ireal_chart_text_to_hamon(text)
    assert len(seq.groups) == 4
    roots = [g.primary[0].semantic.root.note for g in seq.groups]
    assert roots == ["C", "F", "G", "A"]


def test_plain_no_chord():
    seq = ireal_chart_text_to_hamon("N\n")
    assert len(seq.groups) == 1
    assert isinstance(seq.groups[0].primary[0].semantic, NoChordSemantic)


def test_plain_skips_comments():
    seq = ireal_chart_text_to_hamon("# header\nC\nF\n")
    assert len(seq.groups) == 2


def test_system_hint_is_cs():
    seq = ireal_chart_text_to_hamon("C\n")
    assert seq.sequence_system_hint == "cs"


# ---------------------------------------------------------------------------
# Chart-string parsing
# ---------------------------------------------------------------------------

def test_chart_string_extracts_chords():
    # Minimal iReal-style chart with bar lines
    chart = "|C |F |G7 |Am |"
    seq = ireal_chart_text_to_hamon(chart)
    assert len(seq.groups) >= 4
    roots = [g.primary[0].semantic.root.note for g in seq.groups[:4]]
    assert roots == ["C", "F", "G", "A"]


def test_chart_skips_structural_markers():
    # XyQ, bar lines, and section markers should be ignored
    chart = "|[C ][F |G7 ]Am |"
    seq = ireal_chart_text_to_hamon(chart)
    assert len(seq.groups) >= 4


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

def test_decode_rotation():
    from hamonpy.adapters.ireal import _rotate_block
    # A 50-char block should be rotated correctly
    block = "A" * 24 + "X" + "B" * 24 + "Z"  # 50 chars
    rotated = _rotate_block(block)
    # Centre char (pos 24) should be at pos 24 in output
    assert rotated[24] == "X"
    assert rotated[:24] == "B" * 24
    assert rotated[25:49] == "A" * 24
