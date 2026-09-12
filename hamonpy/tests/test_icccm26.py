"""The ICCCM'26 showcase examples as unit-test objects.

Each `ICCCM26/examples/*.hamon` is locked to its canonical JSON golden
(`ICCCM26/outputs/<name>.hamon.json`, exactly what `icccm26/roundtrip.py` writes),
must parse, and must round-trip (parse -> serialize -> parse is stable). A few
flagship-specific outcome checks pin the layered/positioned/meter semantics.

If you intentionally change an example, regenerate the goldens:
    cd ICCCM26 && python run.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hamonpy.ast import ChordSymbolSemantic, FiguredBassSemantic, RomanSemantic
from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_hamon_text, sequence_to_json

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "ICCCM26" / "examples"
OUTPUTS = ROOT / "ICCCM26" / "outputs"

_HAMON = sorted(EXAMPLES.glob("*.hamon"))


def test_examples_present():
    assert len(_HAMON) >= 5, "expected the ICCCM'26 showcase examples"


@pytest.mark.parametrize("path", _HAMON, ids=lambda p: p.stem)
def test_example_parses(path: Path):
    seq = parse_hamon_sequence(path.read_text(encoding="utf-8"))
    assert seq.groups, f"{path.name} produced no groups"


@pytest.mark.parametrize("path", _HAMON, ids=lambda p: p.stem)
def test_example_matches_canonical_json_golden(path: Path):
    gold = OUTPUTS / f"{path.stem}.hamon.json"
    assert gold.exists(), f"missing golden {gold.name} — run `cd ICCCM26 && python run.py`"
    fresh = sequence_to_json(parse_hamon_sequence(path.read_text(encoding="utf-8")))
    assert json.loads(fresh) == json.loads(gold.read_text(encoding="utf-8")), (
        f"{path.name} drifted from its canonical JSON — regenerate with "
        f"`cd ICCCM26 && python run.py`"
    )


@pytest.mark.parametrize("path", _HAMON, ids=lambda p: p.stem)
def test_example_round_trips(path: Path):
    seq = parse_hamon_sequence(path.read_text(encoding="utf-8"))
    reparsed = parse_hamon_sequence(sequence_to_hamon_text(seq))
    assert sequence_to_json(reparsed) == sequence_to_json(seq), (
        f"{path.name} is not stable under parse -> serialize -> parse"
    )


# ── flagship-specific outcomes (Love Walked In, mm. 25-31) ──────────────────
def _flagship():
    return parse_hamon_sequence((EXAMPLES / "flagship_love_walked_in.hamon").read_text(encoding="utf-8"))


def test_flagship_is_layered_chord_plus_roman():
    seq = _flagship()
    g0 = seq.groups[0]
    layers = {lbl.layer for lbl in g0.primary}
    assert layers == {"chord", "degree"}
    chord = next(l for l in g0.primary if l.layer == "chord")
    roman = next(l for l in g0.primary if l.layer == "degree")
    assert isinstance(chord.semantic, ChordSymbolSemantic)
    assert isinstance(roman.semantic, RomanSemantic)


def test_flagship_declares_common_time_and_key():
    seq = _flagship()
    assert seq.meters and (seq.meters[0].numerator, seq.meters[0].denominator) == (4, 4)
    assert seq.regions and seq.regions[0].key.tonic.note == "C"


def test_flagship_positions_are_in_meter():
    # every ts sits inside 4/4 → the validator is silent
    from hamonpy.validate import validate_positions
    assert validate_positions(_flagship()) == []


def test_mozart_example_is_figured_bass():
    seq = parse_hamon_sequence((EXAMPLES / "sat_mozart_fb.hamon").read_text(encoding="utf-8"))
    assert all(
        isinstance(lbl.semantic, FiguredBassSemantic)
        for g in seq.groups for lbl in g.primary
    )


# ---------------------------------------------------------------------------
# The committed xencoding report must match a fresh run
# ---------------------------------------------------------------------------
#
# The canonical `*.hamon.json` goldens above are guarded, but they only depend on the
# parser — so they stayed valid while `xencoding_report.json` and the poster figures,
# which depend on every *writer*, went four weeks stale without a single test noticing.
# That is what happened before ICCCM'26: the outputs were generated 2026-07-06 and the
# August work (extent, seconds clock, Harte writer, the quarter-note unit fix) moved the
# numbers underneath them. This asks the question the goldens do not.

def test_committed_xencoding_report_is_current():
    pytest.importorskip("matplotlib", reason="ICCCM26 package imports the figure module")
    import sys

    sys.path.insert(0, str(ROOT / "ICCCM26"))
    try:
        from icccm26.roundtrip import analyze_all, to_report_dict
    finally:
        sys.path.pop(0)

    committed = OUTPUTS / "xencoding_report.json"
    assert committed.exists(), "missing xencoding_report.json — run `cd ICCCM26 && python run.py`"
    fresh = to_report_dict(analyze_all())
    assert fresh == json.loads(committed.read_text(encoding="utf-8")), (
        "ICCCM26/outputs/xencoding_report.json is stale — the loss matrix on the poster "
        "no longer matches the code. Regenerate with `cd ICCCM26 && python run.py`."
    )
