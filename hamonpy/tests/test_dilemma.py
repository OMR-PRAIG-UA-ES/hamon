"""Tests for the DiLeMMa pitch-array adapter (adapters/dilemma.py)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hamonpy.adapters.dilemma import (
    collapse,
    detect_dialect,
    extract_cadences,
    extract_phrase_ends,
    extract_spans,
    pitch_array_text_to_hamon,
)
from hamonpy.ast import RomanSemantic
from hamonpy.cli import detect_format

# A DLC pitch array: one row per note, the harmony repeated on every note it covers.
# Three harmonies (I, V7/V, V) over seven notes, home key C major, closing on a PAC.
DLC_TSV = (
    "pitch\tunfolded_harmony_index\tquarterbeats_playthrough\tmn\tbeat_float\ta_isOnset"
    "\tchord\tnumeral\tform\tfigbass\tchanges\trelativeroot\tlocalkey\tglobalkey"
    "\tcadence\tcadence_type\tphraseend\n"
    "60\t0\t0\t1\t1.0\tTrue\tI\tI\t\t\t\t\tI\tC\t\t\t{\n"
    "64\t0\t0\t1\t1.0\tTrue\tI\tI\t\t\t\t\tI\tC\t\t\t\n"
    "67\t0\t0\t1\t1.0\tTrue\tI\tI\t\t\t\t\tI\tC\t\t\t\n"
    "62\t1\t2\t1\t3.0\tTrue\tV7/V\tV\t\t7\t\tV\tI\tC\t\t\t\n"
    "71\t1\t2\t1\t3.0\tTrue\tV7/V\tV\t\t7\t\tV\tI\tC\t\t\t\n"
    "67\t2\t4\t2\t1.0\tTrue\tV\tV\t\t\t\t\tI\tC\tPAC\tPAC\t}\n"
    "59\t2\t4\t2\t1.0\tFalse\tV\tV\t\t\t\t\tI\tC\t\t\t\n"
)

# An AugmentedNet pitch array: keys are absolute and music21-spelled (B- = B flat),
# every harmony states its own duration, and `Cad` is the cadential six-four.
AN_TSV = (
    "s_midi\ta_annotationNumber\tj_offset\ta_measure\tmn_onset\ta_romanNumeral"
    "\ta_simpleNumeral\ta_localKey\ta_tonicizedKey\ta_duration\n"
    "65\t0\t0.0\t1\t0\tI\tI\tF\tF\t1.0\n"
    "69\t0\t0.0\t1\t0\tI\tI\tF\tF\t1.0\n"
    "60\t1\t1.0\t1\t1\tCad\tI\tF\tF\t2.0\n"
    "72\t2\t3.0\t2\t0\tV7/V\tV\tF\tC\t1.0\n"
    "70\t3\t4.0\t2\t1\tV\tV\tB-\tB-\t2.0\n"
)


# ---------------------------------------------------------------------------
# DLC dialect
# ---------------------------------------------------------------------------

def test_dlc_collapses_the_note_grid_to_one_group_per_harmony():
    seq = pitch_array_text_to_hamon(DLC_TSV)
    assert len(seq.groups) == 3                       # not seven, one per note
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "V", "V"]
    assert all(isinstance(g.primary[0].semantic, RomanSemantic) for g in seq.groups)


def test_dlc_positions_come_from_quarterbeats():
    seq = pitch_array_text_to_hamon(DLC_TSV)
    times = [(g.position.time.numerator, g.position.time.denominator) for g in seq.groups]
    assert times == [(0, 1), (2, 1), (4, 1)]


def test_dlc_measure_and_beat_when_there_are_no_quarterbeats():
    tsv = DLC_TSV.replace("quarterbeats_playthrough", "unused_offset")
    seq = pitch_array_text_to_hamon(tsv)
    pos = seq.groups[1].position
    assert (pos.measure, pos.beat) == (1, 3.0)        # beat_float is already 1-based


def test_dlc_keys_and_applied_chord():
    seq = pitch_array_text_to_hamon(DLC_TSV)
    assert seq.regions and seq.regions[0].key.tonic.note == "C"
    assert seq.groups[1].primary[0].attributes.applied.target == "V"


def test_dlc_cadences_and_phrase_ends():
    assert [c.type for c in extract_cadences(DLC_TSV)] == ["PAC"]
    assert [p.marker for p in extract_phrase_ends(DLC_TSV)] == ["{", "}"]


def test_dlc_spans_are_derived_from_the_next_onset():
    spans = extract_spans(DLC_TSV)
    assert [s.source for s in spans] == ["derived"] * 3
    assert [(s.duration.numerator, s.duration.denominator) for s in spans[:2]] == [(2, 1), (2, 1)]
    # The array never says where the last harmony ends, so we do not invent it.
    assert spans[-1].duration is None


# ---------------------------------------------------------------------------
# AugmentedNet dialect
# ---------------------------------------------------------------------------

def test_an_groups_and_cadential_six_four():
    seq = pitch_array_text_to_hamon(AN_TSV)
    assert len(seq.groups) == 4
    assert [g.primary[0].surface for g in seq.groups] == ["I", "V(64)", "V7/V", "V"]


def test_an_absolute_keys_become_dcml_degrees():
    rows = collapse(AN_TSV)
    assert [r["globalkey"] for r in rows] == ["F"] * 4      # first localKey is home
    assert [r["localkey"] for r in rows] == ["I", "I", "I", "IV"]   # B- major = IV of F
    assert [r["relativeroot"] for r in rows] == ["", "", "V", ""]   # tonicized C = V of F


def test_an_spans_are_explicit():
    spans = extract_spans(AN_TSV)
    assert [s.source for s in spans] == ["explicit"] * 4
    assert [(s.duration.numerator, s.duration.denominator) for s in spans] == [
        (1, 1), (2, 1), (1, 1), (2, 1),
    ]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def test_detect_dialect():
    assert detect_dialect(DLC_TSV.split("\n")[0].split("\t")) == "dlc"
    assert detect_dialect(AN_TSV.split("\n")[0].split("\t")) == "an"
    assert detect_dialect(["mn", "chord", "globalkey"]) is None


@pytest.mark.parametrize("text", [DLC_TSV, AN_TSV])
def test_cli_detects_pitch_arrays(text):
    assert detect_format(Path("array.tsv"), text) == "dilemma"
    assert detect_format(None, text) == "dilemma"       # extension-less, by content


def test_plain_dcml_tables_are_not_mistaken_for_pitch_arrays():
    expanded = (
        "mc\tmn\tquarterbeats\tmn_onset\tchord\tnumeral\tlocalkey\tglobalkey\n"
        "1\t1\t0\t0\tI\tI\tI\tC\n"
    )
    assert detect_format(Path("harmonies.tsv"), expanded) == "dcml_expanded"
    with pytest.raises(ValueError, match="not a DiLeMMa pitch array"):
        collapse(expanded)
