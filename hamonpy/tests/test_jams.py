"""Tests for the JAMS ↔ HAMON adapter (chord + key_mode, Harte values)."""
from __future__ import annotations

import json

from hamonpy.adapters.jams import (
    hamon_to_jams,
    hamon_to_jams_dict,
    jams_to_hamon,
)
from hamonpy.ast import ChordSymbolSemantic, NoChordSemantic
from hamonpy.parse import parse_hamon_sequence

REAL_JAMS = {
    "file_metadata": {"jams_version": "0.3.4"},
    "annotations": [
        {"namespace": "chord", "data": [
            {"time": 0.0, "duration": 2.0, "value": "C:maj7", "confidence": 1.0},
            {"time": 2.0, "duration": 2.0, "value": "D:min7", "confidence": 1.0},
            {"time": 4.0, "duration": 2.0, "value": "G:7"},
            {"time": 6.0, "duration": 2.0, "value": "N"},
        ]},
        {"namespace": "key_mode", "data": [{"time": 0, "duration": 8, "value": "C:major"}]},
    ],
    "sandbox": {},
}


# ── reading ─────────────────────────────────────────────────────────────────
def test_reads_chord_namespace_in_order():
    seq = jams_to_hamon(REAL_JAMS)
    kinds = [g.primary[0].semantic.kind for g in seq.groups]
    assert kinds == ["chordSymbol", "chordSymbol", "chordSymbol", "noChord"]
    first = seq.groups[0].primary[0].semantic
    assert isinstance(first, ChordSymbolSemantic)
    assert first.root.note == "C" and first.seventh == "maj7"
    assert isinstance(seq.groups[3].primary[0].semantic, NoChordSemantic)


def test_reads_observations_sorted_by_time():
    doc = {"annotations": [{"namespace": "chord", "data": [
        {"time": 4.0, "value": "G:7"}, {"time": 0.0, "value": "C:maj"},
    ]}]}
    seq = jams_to_hamon(doc)
    assert [g.primary[0].semantic.root.note for g in seq.groups] == ["C", "G"]


def test_reads_key_mode_as_region():
    seq = jams_to_hamon(REAL_JAMS)
    assert seq.regions and seq.regions[0].kind == "key"
    assert seq.regions[0].key.tonic.note == "C" and seq.regions[0].key.mode == "major"


def test_reads_chord_harte_namespace():
    doc = {"annotations": [{"namespace": "chord_harte",
                            "data": [{"time": 0, "value": "A:min"}]}]}
    seq = jams_to_hamon(doc)
    assert seq.groups[0].primary[0].semantic.root.note == "A"


def test_accepts_json_string():
    seq = jams_to_hamon(json.dumps(REAL_JAMS))
    assert len(seq.groups) == 4


# ── writing ─────────────────────────────────────────────────────────────────
def test_writes_chord_annotation_with_harte_values():
    seq = parse_hamon_sequence("@cs\nDm7\nG7\nCmaj7")
    doc = hamon_to_jams_dict(seq)
    chord = next(a for a in doc["annotations"] if a["namespace"] == "chord")
    assert [o["value"] for o in chord["data"]] == ["D:min7", "G:7", "C:maj7"]


def test_unstated_clock_is_null_not_invented():
    """A sequence with no `s:` gets no times — the writer does not number the groups.

    It used to write the group index as `time` and `1` as `duration`, which reads
    downstream as real audio seconds."""
    seq = parse_hamon_sequence("@cs\nDm7\nG7\nCmaj7")
    chord = next(a for a in hamon_to_jams_dict(seq)["annotations"]
                 if a["namespace"] == "chord")
    assert [o["time"] for o in chord["data"]] == [None, None, None]
    assert [o["duration"] for o in chord["data"]] == [None, None, None]


def test_stated_clock_is_written_through():
    seq = parse_hamon_sequence("@cs\ns:12.5,Dm7[dur:1.5s]\ns:14,G7[dur:2s]")
    chord = next(a for a in hamon_to_jams_dict(seq)["annotations"]
                 if a["namespace"] == "chord")
    assert [o["time"] for o in chord["data"]] == [12.5, 14.0]
    assert [o["duration"] for o in chord["data"]] == [1.5, 2.0]


def test_writes_key_mode_from_region():
    seq = parse_hamon_sequence("@cs\n@key:A:minor\nAm\nE7")
    doc = hamon_to_jams_dict(seq)
    key = next(a for a in doc["annotations"] if a["namespace"] == "key_mode")
    assert key["data"][0]["value"] == "A:minor"


def test_no_key_mode_annotation_without_regions():
    doc = hamon_to_jams_dict(parse_hamon_sequence("@cs\nC\nG"))
    assert all(a["namespace"] != "key_mode" for a in doc["annotations"])


def test_output_is_valid_jams_shaped_json():
    seq = parse_hamon_sequence("@cs\nC\nAm\nF\nG")
    doc = json.loads(hamon_to_jams(seq))
    assert "file_metadata" in doc and "annotations" in doc and "sandbox" in doc
    assert doc["file_metadata"]["jams_version"]
    assert doc["annotations"][0]["namespace"] == "chord"


# ── round-trip (semantics preserved through Harte chord values) ─────────────
def test_semantics_round_trip_hamon_jams_hamon():
    seq = parse_hamon_sequence("@cs\nDm7\nG7\nCmaj7\nNC")
    back = jams_to_hamon(hamon_to_jams(seq))
    assert [
        (g.primary[0].semantic.kind, getattr(g.primary[0].semantic, "root", None)
         and g.primary[0].semantic.root.note)
        for g in back.groups
    ] == [("chordSymbol", "D"), ("chordSymbol", "G"), ("chordSymbol", "C"), ("noChord", None)]
