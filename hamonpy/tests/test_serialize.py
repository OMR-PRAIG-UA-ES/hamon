"""Tests for hamonpy.serialize (canonical JSON output)."""
from __future__ import annotations

import json
from pathlib import Path

from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import (
    sequence_to_dict,
    sequence_to_json,
    sequence_to_hamon_text,
)

ANALYSIS = Path(__file__).resolve().parents[2] / "fixtures" / "analysis"


def test_camelcase_and_drops_empty():
    d = sequence_to_dict(parse_hamon_sequence("@cs\nCΔ7"))
    g0 = d["groups"][0]["primary"][0]
    assert g0["detectedSystem"] == "cs"          # snake_case → camelCase
    assert "alternatives" not in d["groups"][0]  # empty list dropped
    assert g0["semantic"]["kind"] == "chordSymbol"


def test_matches_golden_for_analysis_fixtures():
    # The .hamon → JSON output must equal the round-trip goldens (shared with TS),
    # which proves serialize.py agrees with the canonical schema shape.
    for hamon in ANALYSIS.glob("*.hamon"):
        golden = json.loads((ANALYSIS / f"{hamon.stem}.expected.json").read_text())
        assert sequence_to_dict(parse_hamon_sequence(hamon.read_text())) == golden


def test_json_is_valid_and_pretty():
    s = sequence_to_json(parse_hamon_sequence("@rn\nI\nV7"))
    assert json.loads(s)["groups"][1]["primary"][0]["semantic"]["degree"] == "V"
    assert "\n" in s  # indented


# ---------------------------------------------------------------------------
# .hamon surface text serializer
# ---------------------------------------------------------------------------

def test_hamon_text_simple():
    text = sequence_to_hamon_text(parse_hamon_sequence("@cs\nC\nF\nG7"))
    assert text == "@cs\nC\nF\nG7\n"


def test_hamon_text_roundtrips_alternatives_and_version():
    src = "@version:0.2.0\n@rn\nii7\nV7 | bII7\nI"
    out = sequence_to_hamon_text(parse_hamon_sequence(src))
    # re-parsing the serialized text yields the same structure
    assert parse_hamon_sequence(out) == parse_hamon_sequence(src)


def test_hamon_text_roundtrips_layered_and_regions():
    for name in ("functional_layers", "tonal_regions"):
        src = (ANALYSIS / f"{name}.hamon").read_text()
        out = sequence_to_hamon_text(parse_hamon_sequence(src))
        assert parse_hamon_sequence(out) == parse_hamon_sequence(src)


def test_hamon_text_roundtrips_positions():
    # v0.4 position (leading, comma-separated): measure:beat, measure-only, time, ref.
    src = "@cs\nm:1,ts:1,C\nm:1,ts:3,G7\nm:2,ts:1.5,Am\nm:4,F\nt:5/4,D\nref:note-9,E"
    out = sequence_to_hamon_text(parse_hamon_sequence(src))
    assert out == src + "\n"                       # serialization is canonical/stable
    assert parse_hamon_sequence(out) == parse_hamon_sequence(src)
