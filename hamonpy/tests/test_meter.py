"""Tests for the @meter directive (v0.4.0): parsing, round-trip, JSON, validation."""
from __future__ import annotations

import warnings

import pytest

from hamonpy.parse import HamonWarning, parse_hamon_sequence
from hamonpy.serialize import sequence_to_dict, sequence_to_hamon_text
from hamonpy.validate import validate_positions


def test_meter_parsed_into_sequence():
    seq = parse_hamon_sequence("@meter:4/4\nm:1,ts:1,cs:C")
    assert seq.meters is not None
    assert len(seq.meters) == 1
    m = seq.meters[0]
    assert (m.numerator, m.denominator, m.from_group) == (4, 4, 0)


def test_meter_change_records_from_group():
    seq = parse_hamon_sequence(
        "@meter:4/4\nm:1,ts:1,cs:C\nm:2,ts:1,cs:F\n@meter:2/2\nm:3,ts:1,cs:G"
    )
    assert [(m.numerator, m.denominator, m.from_group) for m in seq.meters] == [
        (4, 4, 0),
        (2, 2, 2),
    ]


def test_meter_round_trips():
    src = "@meter:4/4\nm:1,ts:1,cs:C\n@meter:2/2\nm:2,ts:1,cs:G\n"
    seq = parse_hamon_sequence(src)
    assert sequence_to_hamon_text(seq) == src


def test_meter_in_canonical_json():
    d = sequence_to_dict(parse_hamon_sequence("@meter:6/8\nm:1,ts:1,cs:C"))
    assert d["meters"] == [{"numerator": 6, "denominator": 8, "fromGroup": 0}]


def test_no_meters_key_when_absent():
    d = sequence_to_dict(parse_hamon_sequence("m:1,ts:1,cs:C"))
    assert "meters" not in d


@pytest.mark.parametrize("ts", ["1", "4", "4.5"])
def test_ts_in_range_no_warning(ts):
    assert validate_positions(parse_hamon_sequence(f"@meter:4/4\nm:1,ts:{ts},cs:C")) == []


@pytest.mark.parametrize("ts", ["5", "0", "6.5"])
def test_ts_out_of_range_warns(ts):
    msgs = validate_positions(parse_hamon_sequence(f"@meter:4/4\nm:1,ts:{ts},cs:C"))
    assert len(msgs) == 1
    assert "outside meter 4/4" in msgs[0]


def test_two_two_range():
    # ts:2.5 is valid in 2/2 (< 3); ts:3 is not.
    assert validate_positions(parse_hamon_sequence("@meter:2/2\nm:1,ts:2.5,cs:C")) == []
    assert len(validate_positions(parse_hamon_sequence("@meter:2/2\nm:1,ts:3,cs:C"))) == 1


def test_no_meter_means_no_validation():
    # Without a declared meter the range is unknown, so nothing is checked.
    assert validate_positions(parse_hamon_sequence("m:1,ts:99,cs:C")) == []


def test_meter_governs_until_next_change():
    # ts:3 is fine under 4/4 but out of range once 2/2 takes over.
    seq = parse_hamon_sequence(
        "@meter:4/4\nm:1,ts:3,cs:C\n@meter:2/2\nm:2,ts:3,cs:G"
    )
    msgs = validate_positions(seq)
    assert len(msgs) == 1
    assert "group 1" in msgs[0]


def test_parse_emits_hamonwarning_for_out_of_range():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parse_hamon_sequence("@meter:4/4\nm:1,ts:5,cs:C")
    assert any(issubclass(w.category, HamonWarning) for w in caught)
