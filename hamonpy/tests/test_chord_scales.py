"""Tests for chord-scale encoding (v0.3.0): per-chord [scale:…] + per-region @scale:."""
from __future__ import annotations

from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_hamon_text
from hamonpy.ast import ScaleSpec


def test_per_chord_scale_single():
    seq = parse_hamon_sequence("@cs\nG7[scale:altered]")
    scales = seq.groups[0].primary[0].attributes.scales
    assert scales == [ScaleSpec(name="altered")]


def test_per_chord_scale_multiple_and_hyphenated():
    seq = parse_hamon_sequence("@cs\nG7[scale:mixolydian][scale:lydian-dominant]")
    names = [s.name for s in seq.groups[0].primary[0].attributes.scales]
    assert names == ["mixolydian", "lydian-dominant"]


def test_per_chord_scale_coexists_with_applied():
    seq = parse_hamon_sequence("@cs\nA7[of:ii][scale:altered]")
    lbl = seq.groups[0].primary[0]
    assert lbl.attributes.applied.target == "ii"
    assert [s.name for s in lbl.attributes.scales] == ["altered"]


def test_per_region_scale_directive():
    src = "@key:C\n@scale:major,lydian\nCmaj7\n@key:D:dorian\n@scale:dorian\nDm7\n"
    seq = parse_hamon_sequence(src)
    assert [s.name for s in seq.regions[0].scales] == ["major", "lydian"]
    assert [s.name for s in seq.regions[1].scales] == ["dorian"]
    assert seq.regions[1].key.mode == "dorian"


def test_chord_scales_round_trip_through_text():
    src = (
        "@key:C\n@scale:major,lydian\n"
        "Cmaj7[scale:lydian]\n"
        "@key:D:dorian\n@scale:dorian\nDm7\n"
    )
    seq = parse_hamon_sequence(src)
    assert parse_hamon_sequence(sequence_to_hamon_text(seq)) == seq


def test_scale_in_canonical_json():
    from hamonpy.serialize import sequence_to_dict
    seq = parse_hamon_sequence("@cs\nDm7[scale:dorian]")
    d = sequence_to_dict(seq)
    attrs = d["groups"][0]["primary"][0]["attributes"]
    assert attrs["scales"] == [{"name": "dorian"}]
