"""Tests for the Kostka-Payne adapter (hamonpy.adapters.kp)."""
from __future__ import annotations

from hamonpy.adapters.kp import kp_chord_list_to_hamon

# Two short excerpts: G major (key pc 7) then C major (key pc 0).
SAMPLE = """% bach.annamin
 0.000  2.608 -  0  1  7  7
 2.608  3.913 -  5  4  7  0
 5.217  6.521 - 11  7  7  6
 7.826  8.260 -  7  5  7  2
% beet.rondo
 0.000  1.000 -  0  1  0  0
 1.000  2.000 -  2  2  0  2
"""


def test_root_degrees_to_roman():
    seq = kp_chord_list_to_hamon(SAMPLE)
    surfaces = [g.primary[0].surface for g in seq.groups]
    # 0->I, 5->IV, 11->VII, 7->V (G excerpt); 0->I, 2->II (C excerpt)
    assert surfaces == ["I", "IV", "VII", "V", "I", "II"]
    assert all(g.primary[0].semantic.kind == "roman" for g in seq.groups)


def test_key_regions_per_excerpt():
    seq = kp_chord_list_to_hamon(SAMPLE)
    assert seq.regions is not None
    # first region G major-ish (mode unknown), opens a new 'key' region per excerpt
    assert seq.regions[0].kind == "key" and seq.regions[0].key.tonic.note == "G"
    assert seq.regions[0].key.mode is None
    second = [r for r in seq.regions if r.from_group == 4]
    assert second and second[0].key.tonic.note == "C" and second[0].kind == "key"


def test_onset_becomes_time_position():
    seq = kp_chord_list_to_hamon(SAMPLE)
    # 2.608 -> Fraction near 2.608
    assert seq.groups[1].position is not None
    assert seq.groups[1].position.time is not None


def test_accidental_degrees():
    seq = kp_chord_list_to_hamon("% x\n 0 1 - 1 0 0 0\n 1 2 - 6 0 0 0\n 2 3 - 8 0 0 0\n")
    assert [g.primary[0].surface for g in seq.groups] == ["bII", "#IV", "bVI"]
