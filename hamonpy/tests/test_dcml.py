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


# ---------------------------------------------------------------------------
# Positions — the writer emits the expanded table's columns (2026-09-14)
# ---------------------------------------------------------------------------

def test_export_places_its_rows():
    """A positioned Roman analysis lands in DCML with `mn`/`mn_onset`/`quarterbeats` in
    front of the chord columns — the columns ms3 writes and `dcml_expanded` reads. Each
    cell is written only when HAMON holds it: no clock is derived from another."""
    seq = parse_hamon_sequence("@rn\n@meter:4/4\nm:1,ts:1,ii7\nm:3,ts:3,t:10/1,V7/ii[dur:2]")
    tsv = hamon_to_dcml_tsv(seq)
    assert tsv.splitlines()[0].split("\t")[:6] == [
        "mn", "quarterbeats", "duration_qb", "mn_onset", "timesig", "chord"]
    rows = _rows(tsv)
    assert [(r["mn"], r["mn_onset"], r["timesig"]) for r in rows] == [
        ("1", "0", "4/4"), ("3", "1/2", "4/4")]
    assert [r["quarterbeats"] for r in rows] == ["", "10"]
    assert [r["duration_qb"] for r in rows] == ["", "2"]


def test_export_onset_uses_the_meter_beat_unit():
    """DCML's `mn_onset` is a fraction of a whole note: beat 2 of 6/8 is `1/8`."""
    rows = _rows(hamon_to_dcml_tsv(parse_hamon_sequence("@rn\n@meter:6/8\nm:1,ts:2,V")))
    assert (rows[0]["mn_onset"], rows[0]["timesig"]) == ("1/8", "6/8")


def test_export_without_positions_stays_the_plain_table():
    tsv = hamon_to_dcml_tsv(parse_hamon_sequence("@rn\nI\nIV\nV"))
    assert tsv.splitlines()[0].startswith("chord\t")


def test_positions_round_trip_through_dcml():
    """DCML → HAMON → DCML keeps measure, beat and quarterbeats: the written table is
    read back by the expanded adapter, which the sniffer picks from the header."""
    from hamonpy.cli import convert_text, detect_format
    text = ("mn\tmn_onset\tquarterbeats\tglobalkey\tlocalkey\tchord\n"
            "1\t0\t0\tC\tI\tii7\n3\t1/2\t10\tC\tI\tV7\n")
    out = hamon_to_dcml_tsv(convert_text(text, "dcml_expanded"))
    assert detect_format(None, out) == "dcml_expanded"
    back = convert_text(out, "dcml_expanded")
    assert [(g.position.measure, g.position.beat, g.position.time.numerator)
            for g in back.groups] == [(1, 1.0, 0), (3, 3.0, 10)]


def test_split_tail_major_seventh_spellings():
    """`maj7` (HAMON) and `M7` (a DCML surface re-parsed by the native projection) are
    both DCML's form `M` with figbass `7`."""
    from hamonpy.adapters.dcml import _split_tail
    assert _split_tail("maj7") == ("M", "7", "")
    assert _split_tail("M7") == ("M", "7", "")
    assert _split_tail("M65") == ("M", "65", "")
    assert _split_tail("m7") == ("m", "7", "")
