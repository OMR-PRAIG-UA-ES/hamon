"""Tests for the DCML TSV adapter (hamonpy/adapters/dcml.py)."""
from __future__ import annotations

import textwrap

import pytest

from hamonpy.adapters.dcml import (
    dcml_tsv_text_to_hamon,
    hamon_to_dcml_tsv,
)
from hamonpy.ast import RomanSemantic
from hamonpy.parse import parse_hamon_sequence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TSV_HEADER = "chord\tnumeral\tform\tfigbass\tchanges\trelativeroot\tlocalkey\tglobalkey\n"


def _tsv(*rows: str) -> str:
    return TSV_HEADER + "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------

def test_parse_tonic_I():
    text = _tsv("I\tI\t\t\t\t\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    assert len(seq.groups) == 1
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "I"
    assert not sem.tail
    assert not sem.secondary


def test_parse_secondary_dominant_V7_IV():
    text = _tsv("V7/IV\tV\t\t7\t\tIV\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    assert len(seq.groups) == 1
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "V"
    assert sem.tail == "7"
    assert sem.secondary == "IV"


def test_parse_supertonic_minor_seventh():
    text = _tsv("iim7\tii\tm\t7\t\t\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "ii"
    assert sem.tail == "m7"


def test_parse_neapolitan_bII():
    text = _tsv("bII\tII\t\t\t\t\ti\tc")
    seq = dcml_tsv_text_to_hamon(text)
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "II"
    assert sem.prefixAccidentals == ["b"]


def test_parse_half_diminished_ii_percent_7():
    text = _tsv("ii%7\tii\t%\t7\t\t\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "ii"
    assert "ø" in (sem.tail or "")


def test_parse_phrase_boundary_rows_skipped():
    text = _tsv("@start\t\t\t\t\t\tI\tC", "I\tI\t\t\t\t\tI\tC", "@end\t\t\t\t\t\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    assert len(seq.groups) == 1


def test_parse_multiple_chords():
    text = _tsv("I\tI\t\t\t\t\tI\tC", "IV\tIV\t\t\t\t\tI\tC", "V7\tV\t\t7\t\t\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    assert len(seq.groups) == 3
    degrees = [g.primary[0].semantic.degree for g in seq.groups]  # type: ignore[attr-defined]
    assert degrees == ["I", "IV", "V"]


def test_system_hint_is_rn():
    text = _tsv("I\tI\t\t\t\t\tI\tC")
    seq = dcml_tsv_text_to_hamon(text)
    assert seq.sequence_system_hint == "rn"


# ---------------------------------------------------------------------------
# Tonal-region tests (localkey / relativeroot → TonalRegion) — STEPS 9.8.1
# ---------------------------------------------------------------------------

def test_localkey_home_region():
    seq = dcml_tsv_text_to_hamon(_tsv("I\tI\t\t\t\t\tI\tC", "V\tV\t\t\t\t\tI\tC"))
    assert seq.regions and len(seq.regions) == 1
    r = seq.regions[0]
    assert r.kind == "key" and r.from_group == 0
    assert r.key.tonic.note == "C" and r.key.mode == "major"


def test_localkey_change_is_modulation():
    seq = dcml_tsv_text_to_hamon(
        _tsv("I\tI\t\t\t\t\tI\tC", "I\tI\t\t\t\t\tV\tC", "V\tV\t\t\t\t\tV\tC")
    )
    kinds = [(r.kind, r.key.tonic.note) for r in seq.regions]
    assert kinds == [("key", "C"), ("modulation", "G")]
    assert seq.regions[0].to_group == 0       # home key closes when V opens
    assert seq.regions[1].from_group == 1


def test_relativeroot_creates_tonicization_and_applied():
    seq = dcml_tsv_text_to_hamon(
        _tsv("I\tI\t\t\t\t\tI\tC", "V7/V\tV\t\t7\t\tV\tI\tC", "V\tV\t\t\t\t\tI\tC")
    )
    ton = next(r for r in seq.regions if r.kind == "tonicization")
    assert ton.degree == "V" and ton.parent == 0
    assert ton.key.tonic.note == "G" and ton.key.mode == "major"   # V of C major

    applied = seq.groups[1].primary[0]
    assert applied.attributes is not None
    assert applied.attributes.applied.target == "V"
    assert applied.semantic.secondary == "V"   # surface '/V' still on the RomanSemantic


def test_minor_global_key_local_degree():
    # global a-minor, localkey III → C major (relative major), via mode-aware degree→pitch
    seq = dcml_tsv_text_to_hamon(_tsv("I\tI\t\t\t\t\tIII\ta"))
    r = seq.regions[0]
    assert r.key.tonic.note == "C" and r.key.tonic.accidental is None
    assert r.key.mode == "major"


def test_no_regions_when_no_key_columns():
    seq = dcml_tsv_text_to_hamon(_tsv("I\tI\t\t\t\t\t\t"))
    assert seq.regions is None


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

def test_export_simple():
    seq = parse_hamon_sequence("@rn\nI\nIV\nV7")
    tsv = hamon_to_dcml_tsv(seq)
    lines = tsv.strip().splitlines()
    assert lines[0].startswith("chord\t")
    chords = [l.split("\t")[0] for l in lines[1:]]
    assert chords == ["I", "IV", "V7"]


def test_export_secondary():
    seq = parse_hamon_sequence("@rn\nV7/IV")
    tsv = hamon_to_dcml_tsv(seq)
    lines = tsv.strip().splitlines()
    row = dict(zip(lines[0].split("\t"), lines[1].split("\t")))
    assert row["chord"] == "V7/IV"
    assert row["numeral"] == "V"
    assert row["figbass"] == "7"
    assert row["relativeroot"] == "IV"


def test_export_numeral_keeps_the_accidental():
    """DCML's `numeral` is `bVII`, not `VII`: the accidental is part of the degree."""
    tsv = hamon_to_dcml_tsv(parse_hamon_sequence("@rn\nbVII7\n#iv°7"))
    lines = tsv.strip().splitlines()
    rows = [dict(zip(lines[0].split("\t"), l.split("\t"))) for l in lines[1:]]
    assert [r["numeral"] for r in rows] == ["bVII", "#iv"]
    assert [r["chord"] for r in rows] == ["bVII7", "#ivo7"]


def test_roundtrip_I_IV_V():
    original = "@rn\nI\nIV\nV"
    seq = parse_hamon_sequence(original)
    tsv = hamon_to_dcml_tsv(seq)
    seq2 = dcml_tsv_text_to_hamon(tsv)
    assert len(seq2.groups) == len(seq.groups)
    for g1, g2 in zip(seq.groups, seq2.groups):
        s1: RomanSemantic = g1.primary[0].semantic  # type: ignore[assignment]
        s2: RomanSemantic = g2.primary[0].semantic  # type: ignore[assignment]
        assert s1.degree == s2.degree


def test_roundtrip_secondary_dominant():
    seq = parse_hamon_sequence("@rn\nV7/IV")
    tsv = hamon_to_dcml_tsv(seq)
    seq2 = dcml_tsv_text_to_hamon(tsv)
    sem: RomanSemantic = seq2.groups[0].primary[0].semantic  # type: ignore[assignment]
    assert sem.degree == "V"
    assert sem.tail == "7"
    assert sem.secondary == "IV"


# ---------------------------------------------------------------------------
# Region export tests (TonalRegion → localkey/globalkey/relativeroot) — STEPS 9.8.1
# ---------------------------------------------------------------------------

def _rows(tsv: str):
    lines = tsv.strip().splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, l.split("\t"))) for l in lines[1:]]


def test_export_no_key_columns_without_regions():
    tsv = hamon_to_dcml_tsv(parse_hamon_sequence("@rn\nI\nIV\nV"))
    assert "localkey" not in tsv.splitlines()[0]
    assert "globalkey" not in tsv.splitlines()[0]


def test_export_emits_localkey_and_globalkey():
    text = _tsv(
        "I\tI\t\t\t\t\tI\tC",
        "I\tI\t\t\t\t\tV\tC",   # modulation to the dominant
        "V\tV\t\t\t\t\tV\tC",
    )
    tsv = hamon_to_dcml_tsv(dcml_tsv_text_to_hamon(text))
    rows = _rows(tsv)
    assert all(r["globalkey"] == "C" for r in rows)
    assert [r["localkey"] for r in rows] == ["I", "V", "V"]


def test_export_emits_relativeroot_from_tonicization():
    text = _tsv(
        "I\tI\t\t\t\t\tI\tC",
        "V7/V\tV\t\t7\t\tV\tI\tC",
        "V\tV\t\t\t\t\tI\tC",
    )
    rows = _rows(hamon_to_dcml_tsv(dcml_tsv_text_to_hamon(text)))
    assert rows[1]["relativeroot"] == "V"
    assert rows[1]["localkey"] == "I"


def test_export_minor_localkey_lowercase():
    # Home key I (C major), then a modulation to vi (A minor) — lowercase = minor.
    text = _tsv(
        "I\tI\t\t\t\t\tI\tC",
        "i\ti\t\t\t\t\tvi\tC",
    )
    rows = _rows(hamon_to_dcml_tsv(dcml_tsv_text_to_hamon(text)))
    assert [r["localkey"] for r in rows] == ["I", "vi"]
    assert all(r["globalkey"] == "C" for r in rows)


def test_region_roundtrip_preserves_keys():
    text = _tsv(
        "I\tI\t\t\t\t\tI\tC",
        "V7/V\tV\t\t7\t\tV\tI\tC",
        "V\tV\t\t\t\t\tV\tC",
    )
    seq1 = dcml_tsv_text_to_hamon(text)
    seq2 = dcml_tsv_text_to_hamon(hamon_to_dcml_tsv(seq1))

    def sig(seq):
        return [
            (r.kind, r.key.tonic.note, r.key.tonic.accidental, r.key.mode, r.degree)
            for r in (seq.regions or [])
        ]

    assert sig(seq1) == sig(seq2)
