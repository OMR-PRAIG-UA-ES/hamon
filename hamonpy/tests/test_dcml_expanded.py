"""Tests for the DCML expanded-harmonies adapter (adapters/dcml_expanded.py)."""
from __future__ import annotations

from hamonpy.adapters.dcml_expanded import (
    expanded_tsv_text_to_hamon,
    extract_cadences,
    extract_phrase_ends,
)
from hamonpy.ast import RomanSemantic

# Minimal expanded DCML table: home key C major, a I–V7–I with a closing PAC
# and a phrase spanning the excerpt. quarterbeats are absolute quarter offsets.
EXPANDED_TSV = (
    "mc\tmn\tquarterbeats\tmn_onset\tchord\tnumeral\tform\tfigbass\trelativeroot\tlocalkey\tglobalkey\tcadence\tphraseend\n"
    "1\t1\t0\t0\tI\tI\t\t\t\tI\tC\t\t{\n"
    "1\t1\t5/2\t1/2\tV7\tV\t\t7\t\tI\tC\t\t\n"
    "2\t2\t4\t0\tI\tI\t\t\t\tI\tC\tPAC\t}\n"
)


def test_expanded_chords_and_positions():
    seq = expanded_tsv_text_to_hamon(EXPANDED_TSV)
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "V", "I"]
    assert all(isinstance(g.primary[0].semantic, RomanSemantic) for g in seq.groups)
    times = [(g.position.time.numerator, g.position.time.denominator) for g in seq.groups]
    assert times == [(0, 1), (5, 2), (4, 1)]


def test_expanded_home_region_from_localkey_globalkey():
    seq = expanded_tsv_text_to_hamon(EXPANDED_TSV)
    assert seq.regions and seq.regions[0].key.tonic.note == "C"


def test_extract_cadences():
    cads = extract_cadences(EXPANDED_TSV)
    assert [c.type for c in cads] == ["PAC"]
    assert (cads[0].position.time.numerator, cads[0].position.time.denominator) == (4, 1)


def test_extract_phrase_ends():
    phrases = extract_phrase_ends(EXPANDED_TSV)
    assert [p.marker for p in phrases] == ["{", "}"]


def test_falls_back_to_measure_beat_without_quarterbeats():
    tsv = (
        "mn\tmn_onset\tchord\tnumeral\tlocalkey\tglobalkey\n"
        "3\t1/2\tV\tV\tI\tC\n"
    )
    seq = expanded_tsv_text_to_hamon(tsv)
    pos = seq.groups[0].position
    assert pos.measure == 3
    # DCML writes onsets as fractions of a whole note: half a whole is the third
    # quarter-note beat, not beat 1.5.
    assert pos.beat == 3.0


def test_beat_unit_follows_the_time_signature():
    tsv = (
        "mn\tmn_onset\ttimesig\tchord\tnumeral\tlocalkey\tglobalkey\n"
        "1\t1/8\t6/8\tV\tV\tI\tC\n"
        "2\t1/4\t3/4\tI\tI\tI\tC\n"
    )
    seq = expanded_tsv_text_to_hamon(tsv)
    assert [g.position.beat for g in seq.groups] == [2.0, 2.0]


def test_quarterbeats_and_measure_beat_are_both_kept():
    """An expanded table states the position twice; neither statement is dropped."""
    seq = expanded_tsv_text_to_hamon(EXPANDED_TSV)
    assert [(g.position.measure, g.position.beat) for g in seq.groups] == [
        (1, 1.0), (1, 3.0), (2, 1.0),
    ]
    assert [(g.position.time.numerator, g.position.time.denominator) for g in seq.groups] == [
        (0, 1), (5, 2), (4, 1),
    ]
