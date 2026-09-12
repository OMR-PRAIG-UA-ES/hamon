"""Tests for the HA-MEI analytical adapter (hamonpy/adapters/mei.py) — STEPS 9.8.3."""
from __future__ import annotations

import re

from hamonpy.adapters.mei import mei_to_hamon, hamon_to_mei
from hamonpy.parse import parse_hamon_sequence
from hamonpy.ast import (
    ChordSymbolSemantic, FunctionalSemantic, RomanSemantic, ToneSemantic, PitchClass,
    Position,
)
from hamonpy.serialize import sequence_to_dict


def _region_sig(seq):
    return [(r.kind, r.key.tonic.note, r.key.tonic.accidental, r.key.mode, r.degree, r.parent)
            for r in (seq.regions or [])]


def _group_sig(seq):
    return [[(l.layer, type(l.semantic).__name__, getattr(l.semantic, "degree", None)
             or getattr(l.semantic, "chain", None) or getattr(l.semantic, "type", None))
             for l in g.primary] for g in seq.groups]

# A HA-MEI fragment: a C-major region that tonicizes the dominant, with a
# functional layer and a non-harmonic passing tone.
MEI = """
<music><body><mdiv><score><section><measure>
  <harm type="hamon:key" tstamp="1">C</harm>
  <harm type="degree" tstamp="1">I</harm>
  <harm type="hamon:tonicization" tstamp="2">V</harm>
  <harm type="degree" tstamp="2">V7/V</harm>
  <harm type="function" tstamp="2">D</harm>
  <harm type="tone" tstamp="2.5">F[NHT:passing]</harm>
  <harm type="hamon:key" tstamp="3">A:minor</harm>
  <harm tstamp="3">iv</harm>
</measure></section></score></mdiv></body></music>
"""


def test_key_regions_and_modulation():
    seq = mei_to_hamon(MEI)
    assert seq.regions is not None
    kinds = [(r.kind, r.key.tonic.note, r.key.mode) for r in seq.regions]
    assert ("key", "C", "major") in kinds
    assert ("tonicization", "G", "major") in kinds        # V of C major
    assert ("modulation", "A", "minor") in kinds          # @key:A:minor


def test_tonicization_has_degree_and_parent():
    seq = mei_to_hamon(MEI)
    ton = next(r for r in seq.regions if r.kind == "tonicization")
    assert ton.degree == "V"
    assert ton.parent == 0
    assert ton.key.tonic == PitchClass("G")


def test_layers_and_function_unshadowed():
    seq = mei_to_hamon(MEI)
    # find the function-layer label (D = dominant, not a D chord)
    func = next(l for g in seq.groups for l in g.primary if l.layer == "function")
    assert isinstance(func.semantic, FunctionalSemantic)
    assert func.semantic.chain == ["D"]
    deg = next(l for g in seq.groups for l in g.primary if l.layer == "degree")
    assert isinstance(deg.semantic, RomanSemantic)


def test_non_harmonic_tone():
    seq = mei_to_hamon(MEI)
    tone = next(l for g in seq.groups for l in g.primary
                if isinstance(l.semantic, ToneSemantic))
    assert tone.semantic.category == "nonharmonic"
    assert tone.semantic.type == "passing"
    assert tone.semantic.pitch == PitchClass("F")
    assert tone.layer == "melodic"


def test_label_attribute_form():
    seq = mei_to_hamon('<harm type="chordSymbol" label="CΔ7"/>')
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root == PitchClass("C") and sem.seventh == "maj7"


def test_empty_when_no_harm():
    assert mei_to_hamon("<music><note pname='c'/></music>").groups == []


# ---------------------------------------------------------------------------
# Export (HamonSequence → HA-MEI <harm>) — Phase 8.1 (Python)
# ---------------------------------------------------------------------------

def test_export_emits_expected_harms():
    out = hamon_to_mei(mei_to_hamon(MEI))
    assert '<harm type="hamon:key">C</harm>' in out
    assert '<harm type="hamon:tonicization">V</harm>' in out
    assert '<harm type="hamon:modulation">A:minor</harm>' in out
    # the source's @tstamp comes back on the element, so match type and content only
    assert re.search(r'<harm type="function"[^>]*>D</harm>', out)
    assert re.search(r'<harm type="degree"[^>]*>V7/V</harm>', out)
    assert re.search(r'<harm type="tone"[^>]*>F\[NHT:passing\]</harm>', out)


def test_export_roundtrip_preserves_regions_and_layers():
    seq1 = mei_to_hamon(MEI)
    seq2 = mei_to_hamon(hamon_to_mei(seq1))
    assert _region_sig(seq1) == _region_sig(seq2)
    assert _group_sig(seq1) == _group_sig(seq2)


def test_export_tone_harmonic_renders_HT():
    seq = mei_to_hamon('<harm type="tone">C[HT]</harm>')
    out = hamon_to_mei(seq)
    assert '<harm type="tone">C[HT]</harm>' in out


def test_export_wrap_in_measure():
    out = hamon_to_mei(mei_to_hamon('<harm type="chordSymbol">CΔ7</harm>'), wrap=True)
    assert out.startswith("<measure>") and out.rstrip().endswith("</measure>")
    assert "CΔ7" in out


def test_export_plain_label_has_no_type():
    out = hamon_to_mei(mei_to_hamon('<harm>V7</harm>'))
    assert "<harm>V7</harm>" in out


# ---------------------------------------------------------------------------
# Time-aligned positions (v0.2.1): @tstamp / @startid → HarmonyGroup.position
# ---------------------------------------------------------------------------

_MEI_POSITIONS = (
    '<measure n="1"><harm tstamp="1">C</harm><harm tstamp="3">Am</harm></measure>'
    '<measure n="2"><harm startid="note-9">F</harm><harm tstamp="2.5">G7</harm></measure>'
)


def test_positions_from_tstamp_and_startid():
    seq = mei_to_hamon(_MEI_POSITIONS)
    assert [g.primary[0].surface for g in seq.groups] == ["C", "Am", "F", "G7"]
    assert [g.position for g in seq.groups] == [
        Position(measure=1, beat=1.0),
        Position(measure=1, beat=3.0),
        Position(ref="note-9"),
        Position(measure=2, beat=2.5),
    ]


def test_position_absent_when_no_anchor():
    seq = mei_to_hamon("<harm>CΔ7</harm>")
    assert seq.groups[0].position is None


def test_region_directives_do_not_consume_positions():
    # A key directive produces a region (not a group); the chord that follows must
    # still receive its own @tstamp position.
    seq = mei_to_hamon(
        '<measure n="4">'
        '<harm type="key">G</harm>'
        '<harm tstamp="2">D7</harm>'
        '</measure>'
    )
    assert [g.primary[0].surface for g in seq.groups] == ["D7"]
    assert seq.groups[0].position == Position(measure=4, beat=2.0)


def test_position_serializes_to_canonical_json():
    seq = mei_to_hamon('<measure n="1"><harm tstamp="1.5">C</harm></measure>')
    d = sequence_to_dict(seq)
    assert d["groups"][0]["position"] == {"measure": 1, "beat": 1.5}


def test_type_token_set_ignores_omr_provenance():
    """`@type` is an NMTOKENS set: the OMR harmony layer may be marked with an `omr`
    token. hamonpy ignores that provenance token and keeps the HA-MEI analytical token
    (so MEI import stays consistent)."""
    # `omr` alone is not an analytical token → plain chord label, no layer.
    seq = mei_to_hamon('<harm type="omr" facs="#zone-p0-2">G7</harm>')
    assert len(seq.groups) == 1
    lab = seq.groups[0].primary[0]
    assert lab.layer is None
    assert isinstance(lab.semantic, ChordSymbolSemantic)
    assert lab.semantic.root.note == "G"

    # `omr` may coexist with an analytical token; the analytical one still wins.
    seq2 = mei_to_hamon('<harm type="omr function">T</harm>')
    lab2 = seq2.groups[0].primary[0]
    assert lab2.layer == "function"
    assert isinstance(lab2.semantic, FunctionalSemantic)


def test_harm_content_is_xml_unescaped_on_reimport():
    # Regression: the writer escapes <harm> content ('PD->T' → 'PD-&gt;T') but the
    # reader returned the raw inner text, so re-importing our own MEI raised on any
    # label with &<>" — e.g. every functional chain.
    seq = parse_hamon_sequence("@fun\nPD->T")
    out = hamon_to_mei(seq)
    assert "PD-&gt;T" in out
    back = mei_to_hamon(out)
    sem = back.groups[0].primary[0].semantic
    assert sem.kind == "functional"
    assert sem.chain == ["PD", "T"]


def test_writer_places_harmonies_in_measures_with_tstamp():
    """A positioned, layered sequence comes out as `<measure n>`s with `@tstamp`s, and
    reads back as the same groups, layers and positions — the placement MEI can state."""
    from hamonpy.parse import parse_hamon_sequence
    seq = parse_hamon_sequence("@meter:4/4\n@key:C\nm:25,ts:1,cs:C,rn:I\nm:25,ts:4.5,cs:A7,rn:V7/ii\n"
                               "m:26,ts:1,cs:Dm7,rn:ii7")
    text = hamon_to_mei(seq, wrap=True)
    assert '<measure n="25">' in text and '<measure n="26">' in text
    assert '<harm type="chord" tstamp="1">C</harm>' in text
    assert '<harm type="degree" tstamp="4.5">V7/ii</harm>' in text
    back = mei_to_hamon(text)
    assert [[l.layer for l in g.primary] for g in back.groups] == [["chord", "degree"]] * 3
    assert [(g.position.measure, g.position.beat) for g in back.groups] == [(25, 1.0), (25, 4.5), (26, 1.0)]
