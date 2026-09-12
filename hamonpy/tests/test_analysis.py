"""Model tests for the v0.2.0 analytical layer (see documentation/analysis.md).

These exercise the typed AST (construction proof that the new optional dataclasses
exist and round-trip) and validate the JSON example fixtures under
fixtures/analysis/ against the documented shapes.
"""

import json
from pathlib import Path

import pytest

from hamonpy.ast import (
    PitchClass,
    Key,
    TonalRegion,
    ToneSemantic,
    HarmonyAttributes,
    AppliedFunction,
    AlternativeAnalysis,
    HarmonyGroup,
    HarmonyLabel,
    HamonSequence,
    RomanSemantic,
    RenderingHints,
)

ANALYSIS_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "analysis"

VALID_MODES = {
    "major", "minor", "ionian", "dorian", "phrygian",
    "lydian", "mixolydian", "aeolian", "locrian",
}
VALID_REGION_KINDS = {"key", "region", "tonicization", "modulation"}
VALID_NHT = {
    "chord-tone", "passing", "neighbor", "upper-neighbor", "lower-neighbor",
    "incomplete-neighbor", "suspension", "retardation", "appoggiatura",
    "escape", "anticipation", "pedal", "cambiata", "changing-tone",
}
VALID_LAYERS = {"chord", "degree", "function", "bass", "melodic", "key", "tone"}


# ---------------------------------------------------------------------------
# Typed AST construction
# ---------------------------------------------------------------------------

def test_tonal_region_and_tonicization():
    region = TonalRegion(
        key=Key(tonic=PitchClass("G"), mode="major"),
        kind="tonicization",
        from_group=1,
        to_group=2,
        degree="V",
        parent=0,
    )
    assert region.kind == "tonicization"
    assert region.key.tonic == PitchClass("G")
    assert region.degree == "V"


def test_church_modes_for_modal_harmony():
    dorian = Key(tonic=PitchClass("D"), mode="dorian", label="D dorian")
    assert dorian.mode == "dorian"


def test_layered_functional_analysis():
    layers = ["key", "function", "degree", "bass"]
    surfaces = ["C", "D", "V7", "65"]
    group = HarmonyGroup(
        primary=[
            HarmonyLabel(
                surface=s,
                semantic=RomanSemantic(degree="V"),
                rendering=RenderingHints(),
                detected_system="rn",
                system="rn",
                layer=layer,
            )
            for s, layer in zip(surfaces, layers)
        ],
    )
    assert [lbl.layer for lbl in group.primary] == layers


def test_harmonic_and_nonharmonic_tones():
    passing = ToneSemantic(
        category="nonharmonic",
        pitch=PitchClass("F"),
        type="passing",
        metric="unaccented",
        approach="step-up",
        departure="step-up",
    )
    cambiata = ToneSemantic(category="nonharmonic", type="cambiata")
    assert passing.kind == "tone"
    assert passing.category == "nonharmonic"
    assert cambiata.type == "cambiata"


def test_omitted_fundamental_and_arpeggiation():
    omitted = HarmonyAttributes(omittedRoot=True, impliedRoot=PitchClass("G"))
    arp = HarmonyAttributes(arpeggiated=True)
    prolong = HarmonyAttributes(prolongation="passing", prolongs=0)
    applied = HarmonyAttributes(applied=AppliedFunction(target="V", chain=["V", "V"]), tonicizes="V")
    assert omitted.omittedRoot is True
    assert arp.arpeggiated is True
    assert prolong.prolongs == 0
    assert applied.applied.chain == ["V", "V"]


def test_alternative_whole_progression():
    alt = AlternativeAnalysis(
        groups=[],
        label="functional",
        system="fun",
        scope={"fromGroup": 0, "toGroup": 2},
    )
    seq = HamonSequence(groups=[], regions=[], alternative_analyses=[alt])
    assert seq.alternative_analyses[0].label == "functional"


# ---------------------------------------------------------------------------
# Fixture validation
# ---------------------------------------------------------------------------

def _fixture_files():
    return sorted(
        p for p in ANALYSIS_FIXTURES.glob("*.json") if not p.name.endswith(".expected.json")
    )


def test_nine_analytical_fixtures_present():
    assert len(_fixture_files()) == 9


def _check_label(lbl: dict):
    assert isinstance(lbl["surface"], str)
    if "layer" in lbl:
        assert lbl["layer"] in VALID_LAYERS
    sem = lbl.get("semantic")
    if sem and sem.get("kind") == "tone":
        assert sem["category"] in ("harmonic", "nonharmonic")
        if "type" in sem:
            assert sem["type"] in VALID_NHT
        if sem["category"] == "nonharmonic":
            assert "type" in sem
    attrs = lbl.get("attributes")
    if attrs and "applied" in attrs:
        assert isinstance(attrs["applied"]["target"], str)


@pytest.mark.parametrize("path", _fixture_files(), ids=lambda p: p.stem)
def test_analytical_fixture_valid(path: Path):
    raw = json.loads(path.read_text())
    seq = raw["sequence"]
    assert seq["version"] == "0.2.0"
    assert len(seq["groups"]) > 0

    for g in seq["groups"]:
        assert len(g["primary"]) > 0
        for lbl in g["primary"]:
            _check_label(lbl)
        for alt in g.get("alternatives", []):
            for lbl in alt:
                _check_label(lbl)

    for r in seq.get("regions", []):
        assert r["kind"] in VALID_REGION_KINDS
        assert isinstance(r["fromGroup"], int)
        assert r["key"]["tonic"]["note"] in "ABCDEFG"
        if "mode" in r["key"]:
            assert r["key"]["mode"] in VALID_MODES

    for a in seq.get("alternativeAnalyses", []):
        assert isinstance(a["groups"], list)
        for g in a["groups"]:
            for lbl in g["primary"]:
                _check_label(lbl)
