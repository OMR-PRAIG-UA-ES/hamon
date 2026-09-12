"""Tests for the BPS-FH adapter (hamonpy.adapters.bps_fh).

These exercise the pure column→Roman logic with synthetic rows, so they need no
.xlsx file and no pandas/openpyxl (the dataset itself is git-ignored).
"""
from __future__ import annotations

from hamonpy.adapters.bps_fh import (
    _parse_key, _row_to_roman_parts, _rows_to_hamon,
)


def test_parse_key_major_minor_and_accidentals():
    assert _parse_key("C").mode == "major" and _parse_key("C").tonic.note == "C"
    assert _parse_key("c").mode == "minor"
    abk = _parse_key("A-")
    assert abk.tonic.note == "A" and abk.tonic.accidental == "flat" and abk.mode == "major"
    cs = _parse_key("c+")
    assert cs.tonic.accidental == "sharp" and cs.mode == "minor"


def test_row_to_roman_basic_and_inversions():
    assert _row_to_roman_parts("1", "m", 0) == ("i", None)
    assert _row_to_roman_parts("5", "D7", 0) == ("V7", None)
    assert _row_to_roman_parts("5", "D7", 1) == ("V65", None)
    assert _row_to_roman_parts("5", "D7", 2) == ("V43", None)
    assert _row_to_roman_parts("1", "M", 1) == ("I6", None)
    assert _row_to_roman_parts("2", "d", 1) == ("ii°6", None)
    assert _row_to_roman_parts("7", "h7", 0) == ("viiø7", None)
    assert _row_to_roman_parts("7", "d7", 1) == ("vii°65", None)


def test_row_to_roman_accidentals_and_secondary():
    assert _row_to_roman_parts("-2", "M", 0) == ("bII", None)
    assert _row_to_roman_parts("+4", "d", 0) == ("#iv°", None)
    assert _row_to_roman_parts("5/5", "D7", 0) == ("V7", "V")
    assert _row_to_roman_parts("5/-7", "D7", 0) == ("V7", "bVII")


def test_augmented_sixth_returns_none():
    assert _row_to_roman_parts("6", "a6", 0) is None


def test_rows_to_hamon_builds_labels_regions_and_positions():
    rows = [
        (0, "C", "1", "M", 0, "I"),
        (4, "C", "5", "D7", 1, "V65"),
        (8, "G", "5", "D7", 0, "V7"),       # modulation to G
        (12, "G", "6", "a6", 0, "Gr+6"),    # augmented sixth -> text
    ]
    seq = _rows_to_hamon(rows)
    assert len(seq.groups) == 4
    assert seq.sequence_system_hint == "rn"
    # roman labels
    assert seq.groups[0].primary[0].semantic.kind == "roman"
    assert seq.groups[1].primary[0].surface == "V65"
    # secondary preserved on roman semantic when present is exercised elsewhere
    # augmented sixth kept as text, original label preserved
    assert seq.groups[3].primary[0].semantic.kind == "text"
    assert seq.groups[3].primary[0].surface == "Gr+6"
    # positions (time in quarters)
    assert seq.groups[2].position.time.numerator == 8
    # regions: home key C, modulation to G
    assert seq.regions and seq.regions[0].kind == "key"
    assert seq.regions[0].key.tonic.note == "C"
    assert seq.regions[1].kind == "modulation"
    assert seq.regions[1].key.tonic.note == "G"


def test_flat_secondary_attaches_to_semantic():
    # HAMON's Roman grammar rejects '/bVII' directly; the adapter attaches it.
    seq = _rows_to_hamon([(0, "C", "5/-7", "D7", 3, "V42/bVII")])
    label = seq.groups[0].primary[0]
    assert label.semantic.kind == "roman"
    assert label.semantic.secondary == "bVII"
    assert label.surface == "V42/bVII"
