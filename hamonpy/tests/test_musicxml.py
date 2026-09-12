"""Tests for the positioned MusicXML adapter (hamonpy/adapters/musicxml.py).

Positions (HarmonyGroup.position, schema 0.2.1) come from the MusicXML time model:
<divisions> + accumulated <note>/<forward>/<backup> durations + <harmony><offset>.
"""
from __future__ import annotations

from hamonpy.adapters.musicxml import musicxml_to_hamon
from hamonpy.ast import ChordSymbolSemantic, Position
from hamonpy.serialize import sequence_to_dict

_SCORE = """<score-partwise><part id="P1">
<measure number="1">
  <attributes><divisions>4</divisions></attributes>
  <harmony><root><root-step>C</root-step></root><kind>major</kind></harmony>
  <note><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration></note>
  <harmony><root><root-step>G</root-step></root><kind text="7">dominant</kind></harmony>
  <note><pitch><step>G</step><octave>3</octave></pitch><duration>8</duration></note>
</measure>
<measure number="2">
  <harmony><root><root-step>A</root-step></root><kind>minor</kind></harmony>
  <note><pitch><step>A</step><octave>3</octave></pitch><duration>16</duration></note>
</measure>
</part></score-partwise>"""


def test_surfaces_and_semantics():
    seq = musicxml_to_hamon(_SCORE)
    assert [g.primary[0].surface for g in seq.groups] == ["C", "G7", "Am"]
    assert isinstance(seq.groups[1].primary[0].semantic, ChordSymbolSemantic)
    assert seq.groups[1].primary[0].semantic.seventh == "dom7"


def test_positions_from_time_model():
    seq = musicxml_to_hamon(_SCORE)
    # divisions=4 (per quarter). C at start → beat 1; G after a half note (8 div =
    # 2 quarters) → beat 3; Am at the start of measure 2 → beat 1.
    assert [g.position for g in seq.groups] == [
        Position(measure=1, beat=1.0),
        Position(measure=1, beat=3.0),
        Position(measure=2, beat=1.0),
    ]


def test_offset_shifts_beat():
    xml = (
        '<score-partwise><part id="P1"><measure number="1">'
        "<attributes><divisions>2</divisions></attributes>"
        "<harmony><root><root-step>F</root-step></root><kind>major</kind>"
        "<offset>2</offset></harmony>"  # +2 divisions = +1 quarter
        "<note><pitch><step>F</step></pitch><duration>8</duration></note>"
        "</measure></part></score-partwise>"
    )
    seq = musicxml_to_hamon(xml)
    assert seq.groups[0].position == Position(measure=1, beat=2.0)


def test_backup_rewinds_elapsed_time():
    xml = (
        '<score-partwise><part id="P1"><measure number="1">'
        "<attributes><divisions>4</divisions></attributes>"
        "<note><duration>8</duration></note>"      # advance 2 quarters
        "<backup><duration>8</duration></backup>"   # rewind to start
        "<harmony><root><root-step>D</root-step></root><kind>minor</kind></harmony>"
        "<note><duration>4</duration></note>"
        "</measure></part></score-partwise>"
    )
    seq = musicxml_to_hamon(xml)
    assert seq.groups[0].position == Position(measure=1, beat=1.0)


def test_chord_notes_do_not_advance_time():
    xml = (
        '<score-partwise><part id="P1"><measure number="1">'
        "<attributes><divisions>4</divisions></attributes>"
        "<note><duration>4</duration></note>"
        "<note><chord/><duration>4</duration></note>"  # chord note: no advance
        "<harmony><root><root-step>E</root-step></root><kind>minor</kind></harmony>"
        "<note><duration>4</duration></note>"
        "</measure></part></score-partwise>"
    )
    seq = musicxml_to_hamon(xml)
    # only the first note advanced (4 div = 1 quarter) → beat 2, not 3
    assert seq.groups[0].position == Position(measure=1, beat=2.0)


def test_serializes_position_to_canonical_json():
    d = sequence_to_dict(musicxml_to_hamon(_SCORE))
    assert d["groups"][1]["position"] == {"measure": 1, "beat": 3.0}


def test_malformed_xml_returns_empty():
    assert musicxml_to_hamon("<not-closed>").groups == []


def test_function_harmony_without_root_is_skipped():
    xml = (
        '<score-partwise><part id="P1"><measure number="1">'
        "<harmony><function>V</function><kind>major</kind></harmony>"
        "</measure></part></score-partwise>"
    )
    assert musicxml_to_hamon(xml).groups == []
