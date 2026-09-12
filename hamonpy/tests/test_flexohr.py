"""Tests for the FlexOHR adapter (hamonpy.adapters.flexohr).

Skipped entirely when the optional ``flexohr`` dependency is absent.
"""
import warnings

import pytest

flexohr = pytest.importorskip("flexohr")

from hamonpy.ast import ChordSymbolSemantic, HamonSequence, RomanSemantic
from hamonpy.adapters.flexohr import (
    flexohr_to_hamon,
    hamon_semantic_to_ohr,
    hamon_to_flexohr,
    ohr_to_hamon_semantic,
)
from hamonpy.parse import parse_hamon_sequence


def _cs(label: str) -> ChordSymbolSemantic:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return parse_hamon_sequence(f"@cs\n{label}").groups[0].primary[0].semantic


def _rn(label: str) -> RomanSemantic:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return parse_hamon_sequence(f"@rn\n{label}").groups[0].primary[0].semantic


# --- chord symbols: full HAMON -> OHR -> HAMON round-trip -------------------

CHORD_CASES = ["C", "Cmaj7", "Am7", "G7", "Bdim7", "Bø7", "Csus4", "C/E", "F#m7", "Ebmaj7"]


@pytest.mark.parametrize("label", CHORD_CASES)
def test_chord_symbol_roundtrip(label):
    src = _cs(label)
    back = ohr_to_hamon_semantic(hamon_semantic_to_ohr(src))
    assert isinstance(back, ChordSymbolSemantic)
    assert back.root == src.root
    assert back.quality == src.quality
    assert back.seventh == src.seventh
    assert back.suspensions == src.suspensions
    assert back.bass == src.bass


def test_chord_symbol_ohr_components():
    # The OHR carries the right FlexOHR objects (not just a lossless dict).
    from flexohr.harmony.harmony_enums import ChordQuality

    ohr = hamon_semantic_to_ohr(_cs("Cmaj7"))
    assert ohr.component("r").value.name == "C"
    assert ohr.get_property("chord_quality") == ChordQuality.major_seventh


def test_slash_bass_becomes_inversion():
    from flexohr.harmony.harmony_enums import Inversion

    ohr = hamon_semantic_to_ohr(_cs("C/E"))
    assert ohr.get_property("inversion") == Inversion.first
    back = ohr_to_hamon_semantic(ohr)
    assert back.bass and back.bass.note == "E"


# --- Roman numerals: build in a key, read the components back --------------

@pytest.mark.parametrize(
    "label,degree,prefix,tail",
    [
        ("V", "V", None, None),
        ("V7", "V", None, "7"),
        ("ii", "ii", None, None),
        ("ii7", "ii", None, "7"),
        ("V65", "V", None, "65"),
        ("IV", "IV", None, None),
        ("bVII", "VII", ["b"], None),
    ],
)
def test_roman_build_and_read(label, degree, prefix, tail):
    back = ohr_to_hamon_semantic(hamon_semantic_to_ohr(_rn(label), key="C"))
    assert isinstance(back, RomanSemantic)
    assert back.degree == degree
    assert back.prefixAccidentals == prefix
    assert back.tail == tail


def test_roman_quality_maps_to_chord_quality():
    from flexohr.harmony.harmony_enums import ChordQuality

    ohr = hamon_semantic_to_ohr(_rn("V7"), key="C")
    chord = ohr.ohr("b")
    assert chord.get_property("chord_quality") == ChordQuality.dominant_seventh


# --- sequence-level helpers ------------------------------------------------

def test_sequence_roundtrip():
    seq = parse_hamon_sequence("@cs\nCmaj7\nAm7\nDm7\nG7")
    ohrs = hamon_to_flexohr(seq)
    assert len(ohrs) == 4
    back = flexohr_to_hamon(ohrs)
    assert isinstance(back, HamonSequence)
    assert [g.primary[0].semantic.root.note for g in back.groups] == ["C", "A", "D", "G"]
    assert [g.primary[0].semantic.seventh for g in back.groups] == ["maj7", "min7", "min7", "dom7"]


def test_unsupported_semantic_raises():
    nc = parse_hamon_sequence("N.C.").groups[0].primary[0].semantic
    with pytest.raises(ValueError):
        hamon_semantic_to_ohr(nc)
