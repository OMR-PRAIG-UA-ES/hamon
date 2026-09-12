"""Tests for the music21 adapter (hamonpy/adapters/music21_adapter.py).

All tests skip gracefully when music21 is not installed (it is an optional
dependency: ``pip install hamonpy[music21]``).
"""
from __future__ import annotations

import pytest

m21 = pytest.importorskip("music21", reason="music21 not installed; skipping")

from hamonpy.adapters.music21_adapter import (
    music21_stream_to_hamon,
    hamon_to_music21_stream,
)
from hamonpy.ast import ChordSymbolSemantic, RomanSemantic, NoChordSemantic, Position
from hamonpy.parse import parse_hamon_sequence


# ---------------------------------------------------------------------------
# music21 → hamon
# ---------------------------------------------------------------------------

def _make_chord_symbol_stream(*chords):
    """Create a music21 Part with the given chord symbol strings."""
    import music21.stream
    import music21.harmony
    part = music21.stream.Part()
    for i, c in enumerate(chords):
        cs = music21.harmony.ChordSymbol(c)
        part.insert(float(i), cs)
    return part


def test_chord_symbol_stream_to_hamon_basic():
    stream = _make_chord_symbol_stream("C", "F", "G")
    seq = music21_stream_to_hamon(stream)
    assert len(seq.groups) == 3
    roots = [g.primary[0].semantic.root.note for g in seq.groups]
    assert roots == ["C", "F", "G"]


def test_chord_symbol_dominant7():
    stream = _make_chord_symbol_stream("G7")
    seq = music21_stream_to_hamon(stream)
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "G"
    assert sem.seventh == "dom7"


def test_chord_symbol_minor_seventh():
    stream = _make_chord_symbol_stream("Am7")
    seq = music21_stream_to_hamon(stream)
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.quality == "minor"
    assert sem.seventh == "min7"


def test_chord_symbol_major7():
    stream = _make_chord_symbol_stream("Cmaj7")
    seq = music21_stream_to_hamon(stream)
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.seventh == "maj7"


def test_no_chord_stream():
    import music21.stream
    import music21.harmony
    part = music21.stream.Part()
    part.insert(0.0, music21.harmony.NoChord())
    seq = music21_stream_to_hamon(part)
    assert len(seq.groups) == 1
    assert isinstance(seq.groups[0].primary[0].semantic, NoChordSemantic)


def test_stream_system_hint():
    stream = _make_chord_symbol_stream("C")
    seq = music21_stream_to_hamon(stream, sequence_system_hint="cs")
    assert seq.sequence_system_hint == "cs"


# ---------------------------------------------------------------------------
# hamon → music21
# ---------------------------------------------------------------------------

def test_hamon_to_stream_basic():
    seq = parse_hamon_sequence("@cs\nC\nF\nG7")
    part = hamon_to_music21_stream(seq)
    import music21.harmony
    elements = list(part.flatten().getElementsByClass(music21.harmony.ChordSymbol))
    assert len(elements) == 3


def test_hamon_to_stream_minor():
    seq = parse_hamon_sequence("@cs\nAm")
    part = hamon_to_music21_stream(seq)
    import music21.harmony
    elements = list(part.flatten().getElementsByClass(music21.harmony.ChordSymbol))
    assert len(elements) == 1


def test_hamon_to_stream_no_chord():
    seq = parse_hamon_sequence("@cs\nN.C.")
    part = hamon_to_music21_stream(seq)
    import music21.harmony
    no_chords = list(part.flatten().getElementsByClass(music21.harmony.NoChord))
    assert len(no_chords) == 1


def test_hamon_roman_to_stream():
    seq = parse_hamon_sequence("@rn\nI\nIV\nV")
    part = hamon_to_music21_stream(seq)
    import music21.roman
    elements = list(part.flatten().getElementsByClass(music21.roman.RomanNumeral))
    assert len(elements) == 3


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_roundtrip_chord_symbols():
    original = "@cs\nC\nF\nG7\nAm7\nDm\nE"
    seq = parse_hamon_sequence(original)
    part = hamon_to_music21_stream(seq)
    seq2 = music21_stream_to_hamon(part)
    assert len(seq2.groups) == len(seq.groups)
    for g1, g2 in zip(seq.groups, seq2.groups):
        s1: ChordSymbolSemantic = g1.primary[0].semantic  # type: ignore[assignment]
        s2: ChordSymbolSemantic = g2.primary[0].semantic  # type: ignore[assignment]
        assert s1.root.note == s2.root.note, f"{s1.root} != {s2.root}"


# ---------------------------------------------------------------------------
# Time-aligned positions (schema 0.2.1) ↔ music21 measure/offset
# ---------------------------------------------------------------------------

def _positioned_seq():
    seq = parse_hamon_sequence("@cs\nC\nG7\nAm")
    seq.groups[0].position = Position(measure=1, beat=1.0)
    seq.groups[1].position = Position(measure=1, beat=3.0)
    seq.groups[2].position = Position(measure=2, beat=1.0)
    return seq


def test_export_places_elements_in_measures():
    import music21.stream
    import music21.harmony
    part = hamon_to_music21_stream(_positioned_seq())
    measures = list(part.getElementsByClass(music21.stream.Measure))
    assert [m.number for m in measures] == [1, 2]
    chords = list(part.recurse().getElementsByClass(music21.harmony.ChordSymbol))
    # offset within measure = beat - 1
    assert [(c.measureNumber, float(c.offset)) for c in chords] == [
        (1, 0.0), (1, 2.0), (2, 0.0),
    ]


def test_position_roundtrip_through_music21():
    seq = _positioned_seq()
    seq2 = music21_stream_to_hamon(hamon_to_music21_stream(seq))
    assert [g.primary[0].surface for g in seq2.groups] == ["C", "G7", "Am"]
    assert [g.position for g in seq2.groups] == [
        Position(measure=1, beat=1.0),
        Position(measure=1, beat=3.0),
        Position(measure=2, beat=1.0),
    ]


def test_absolute_time_is_quarters_not_whole_notes():
    """`Position.time` is in quarter notes — music21's own offset unit — so it goes in
    unscaled. This used to multiply by 4, which put every DCML- or Dezrann-sourced
    harmony four times too late: the bar-per-chord chart below landed on bars 1, 5, 9."""
    import music21.harmony
    from hamonpy.ast import Fraction

    seq = parse_hamon_sequence("@cs\nCmaj7\nA7\nDm7")
    for group, quarters in zip(seq.groups, (0, 4, 8)):      # one chord per 4/4 bar
        group.position = Position(time=Fraction(numerator=quarters, denominator=1))

    part = hamon_to_music21_stream(seq)
    chords = list(part.recurse().getElementsByClass(music21.harmony.ChordSymbol))
    assert [float(c.offset) for c in chords] == [0.0, 4.0, 8.0]


def test_positionless_sequence_stays_flat_and_unpositioned():
    seq = parse_hamon_sequence("@cs\nC\nF\nG7")
    seq2 = music21_stream_to_hamon(hamon_to_music21_stream(seq))
    assert all(g.position is None for g in seq2.groups)


# ---------------------------------------------------------------------------
# Faithful native-object mapping (slash bass, suspensions, alterations, key)
# ---------------------------------------------------------------------------

def _first_cs(part):
    import music21.harmony
    return list(part.flatten().getElementsByClass(music21.harmony.ChordSymbol))[0]


def _first_rn(part):
    import music21.roman
    return list(part.flatten().getElementsByClass(music21.roman.RomanNumeral))[0]


def test_chord_symbol_slash_bass_export():
    cs = _first_cs(hamon_to_music21_stream(parse_hamon_sequence("@cs\nG7/B")))
    assert cs.bass().name == "B"
    assert {p.name for p in cs.pitches} == {"G", "B", "D", "F"}


def test_chord_symbol_suspension_export():
    cs = _first_cs(hamon_to_music21_stream(parse_hamon_sequence("@cs\nCsus4")))
    assert {p.name for p in cs.pitches} == {"C", "F", "G"}


def test_chord_symbol_alteration_export():
    # Dm7b5 (half-diminished) must lower the fifth to A-flat.
    cs = _first_cs(hamon_to_music21_stream(parse_hamon_sequence("@cs\nDm7b5")))
    assert {p.name for p in cs.pitches} == {"D", "F", "A-", "C"}


def test_chord_symbol_added_tone_export():
    cs = _first_cs(hamon_to_music21_stream(parse_hamon_sequence("@cs\nCadd9")))
    assert {p.name for p in cs.pitches} == {"C", "E", "G", "D"}


def test_roman_resolves_against_region_key():
    # @key:G ⇒ V in G major is a D-major triad.
    part = hamon_to_music21_stream(parse_hamon_sequence("@rn\n@key:G\nV"))
    rn = _first_rn(part)
    assert rn.key.tonic.name == "G"
    assert {p.name for p in rn.pitches} == {"D", "F#", "A"}


def test_roman_secondary_dominant_export():
    # V7/V in G major = A dominant seventh (A C# E G).
    part = hamon_to_music21_stream(parse_hamon_sequence("@rn\n@key:G\nV7/V"))
    rn = _first_rn(part)
    assert {p.name for p in rn.pitches} == {"A", "C#", "E", "G"}


def test_roman_borrowed_degree_export():
    # bVI in C major = A-flat major (Ab C Eb).
    part = hamon_to_music21_stream(parse_hamon_sequence("@rn\n@key:C\nbVI"))
    rn = _first_rn(part)
    assert {p.name for p in rn.pitches} == {"A-", "C", "E-"}


# ---------------------------------------------------------------------------
# music21 SubConverter — .hamon as a native I/O format
# ---------------------------------------------------------------------------

def test_subconverter_parse_by_format():
    from hamonpy.adapters.music21_converter import register_hamon_format
    register_hamon_format()
    from music21 import converter
    import music21.harmony
    s = converter.parse("@cs\nC\nF\nG7", format="hamon")
    figs = [e.figure for e in s.flatten().getElementsByClass(music21.harmony.ChordSymbol)]
    assert figs == ["C", "F", "G7"]


def test_subconverter_write_and_parse_by_extension(tmp_path):
    from hamonpy.adapters.music21_converter import register_hamon_format
    register_hamon_format()
    from music21 import converter
    import music21.harmony

    s = converter.parse("@cs\nC\nAm\nF\nG7", format="hamon")
    fp = tmp_path / "out.hamon"
    s.write("hamon", fp=str(fp))

    written = fp.read_text()
    assert written.startswith("@cs\n")
    assert "G7" in written

    # round-trip: load the file back by extension (no explicit format)
    s2 = converter.parse(str(fp))
    figs = [e.figure for e in s2.flatten().getElementsByClass(music21.harmony.ChordSymbol)]
    assert figs == ["C", "Am", "F", "G7"]
