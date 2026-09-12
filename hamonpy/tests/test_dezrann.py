"""Tests for the Dezrann (.dez) adapter (hamonpy/adapters/dezrann.py)."""
from __future__ import annotations

import json

from hamonpy.adapters.dezrann import dez_to_hamon, hamon_to_dez
from hamonpy.ast import ChordSymbolSemantic, RomanSemantic, TextSemantic

DEZ_CHORDS = json.dumps({
    "labels": [
        {"type": "Harmony", "start": 0, "duration": 4, "tag": "Cmaj7"},
        {"type": "Harmony", "start": 4, "duration": 4, "tag": "F"},
        {"type": "Harmony", "start": 8, "tag": "G7"},
        {"type": "Cadence", "start": 12, "tag": "C:PAC"},
    ],
    "meta": {"producer": "test"},
})

DEZ_ROMAN = json.dumps({
    "labels": [
        {"type": "Chord", "start": 2.5, "tag": "V65"},
        {"type": "Chord", "start": 0, "tag": "I"},
    ],
})


def test_dez_chord_symbols_with_positions():
    seq = dez_to_hamon(DEZ_CHORDS, system="cs")
    # The Cadence label is not a harmony type → only 3 groups.
    assert [g.primary[0].surface for g in seq.groups] == ["Cmaj7", "F", "G7"]
    assert all(isinstance(g.primary[0].semantic, ChordSymbolSemantic) for g in seq.groups)
    times = [(g.position.time.numerator, g.position.time.denominator) for g in seq.groups]
    assert times == [(0, 1), (4, 1), (8, 1)]


def test_dez_labels_sorted_by_start_and_fractional_time():
    seq = dez_to_hamon(DEZ_ROMAN, system="rn")
    assert [g.primary[0].surface for g in seq.groups] == ["I", "V65"]
    assert isinstance(seq.groups[1].primary[0].semantic, RomanSemantic)
    # 2.5 quarters → 5/2
    t = seq.groups[1].position.time
    assert (t.numerator, t.denominator) == (5, 2)


def test_dez_unparseable_tag_falls_back_to_text():
    doc = json.dumps({"labels": [{"type": "Harmony", "start": 0, "tag": "?!garbage"}]})
    seq = dez_to_hamon(doc, system="cs")
    assert isinstance(seq.groups[0].primary[0].semantic, TextSemantic)


def test_round_trip_hamon_to_dez():
    seq = dez_to_hamon(DEZ_CHORDS, system="cs")
    out = json.loads(hamon_to_dez(seq))
    tags = [lb["tag"] for lb in out["labels"]]
    starts = [lb["start"] for lb in out["labels"]]
    assert tags == ["Cmaj7", "F", "G7"]
    assert starts == [0, 4, 8]
    # The durations the source stated survive; G7, which stated none, still states none.
    assert [lb.get("duration") for lb in out["labels"]] == [4, 4, None]


def test_stated_durations_are_read_into_the_label():
    seq = dez_to_hamon(DEZ_CHORDS, system="cs")
    extents = [g.primary[0].attributes and g.primary[0].attributes.duration for g in seq.groups]
    assert [(e.numerator, e.denominator) if e else None for e in extents] == [(4, 1), (4, 1), None]


def test_a_duration_is_never_invented_from_the_gap():
    """A harmony that stops before the next one begins (a rest, an N.C., a fermata
    close) is the case the implicit rule gets wrong. The writer used to fill the gap
    anyway, and the invented value came back on re-import looking like source data —
    so the round-trip reported no loss even when the real extent was different."""
    doc = json.dumps({"labels": [
        {"type": "Harmony", "start": 0, "tag": "Cmaj7"},      # says nothing about extent
        {"type": "Harmony", "start": 8, "tag": "G7"},
    ]})
    out = json.loads(hamon_to_dez(dez_to_hamon(doc, system="cs")))
    assert "duration" not in out["labels"][0]                 # not 8
