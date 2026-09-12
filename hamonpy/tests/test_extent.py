"""Extent (v0.4.1): `[dur:…]` and `[endref:…]` — how long a harmony lasts.

The extent sits on the LABEL, not the group, so two `alternatives` can segment the same
passage differently. It is only ever set from what a source STATED: absent means unknown,
and the rule that a harmony runs to the next group stays a computation. See
`documentation/positions.md`.
"""
from __future__ import annotations

from dataclasses import replace

from hamonpy.ast import Fraction, HarmonyAttributes
from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_dict, sequence_to_hamon_text


def _extent(label):
    return label.attributes.duration if label.attributes else None


def _pair(fraction):
    return (fraction.numerator, fraction.denominator) if fraction else None


# ---------------------------------------------------------------------------
# Surface → AST
# ---------------------------------------------------------------------------

def test_dur_accepts_fractions_integers_and_decimals():
    seq = parse_hamon_sequence("@cs\nC[dur:3/4]\nF[dur:2]\nG7[dur:1.5]")
    assert [_pair(_extent(g.primary[0])) for g in seq.groups] == [(3, 4), (2, 1), (3, 2)]


def test_endref_is_the_structural_counterpart_of_ref():
    label = parse_hamon_sequence("@cs\nref:note-1,C[endref:note-12]").groups[0].primary[0]
    assert label.attributes.endRef == "note-12"


def test_both_at_once_and_alongside_other_attributes():
    label = parse_hamon_sequence("@cs\nA7[of:ii][dur:4][endref:n9]").groups[0].primary[0]
    assert _pair(label.attributes.duration) == (4, 1)
    assert label.attributes.endRef == "n9"
    assert label.attributes.applied.target == "ii"      # the existing attributes still work


def test_an_unreadable_duration_is_ignored_not_guessed():
    label = parse_hamon_sequence("@cs\nC[dur:soon]").groups[0].primary[0]
    assert _extent(label) is None
    assert label.surface == "C[dur:soon]"               # but the surface still round-trips


# ---------------------------------------------------------------------------
# AST → surface
# ---------------------------------------------------------------------------

def test_text_round_trip_is_stable():
    text = "@cs\nCmaj7[dur:4]\nA7[dur:2][endref:n9]\n"
    assert sequence_to_hamon_text(parse_hamon_sequence(text)) == text


def test_an_adapter_set_extent_reaches_the_text():
    """An adapter that read the extent from a source sets the attribute without touching
    the surface. Without this the text serialization would drop the very thing the extent
    work exists to keep."""
    seq = parse_hamon_sequence("@cs\nDm7")
    label = seq.groups[0].primary[0]
    label.attributes = HarmonyAttributes(duration=Fraction(numerator=3, denominator=2), endRef="x1")

    text = sequence_to_hamon_text(seq)
    assert text == "@cs\nDm7[dur:3/2][endref:x1]\n"

    back = parse_hamon_sequence(text).groups[0].primary[0]
    assert _pair(_extent(back)) == (3, 2)
    assert back.attributes.endRef == "x1"


def test_whole_numbers_are_written_bare():
    seq = parse_hamon_sequence("@cs\nC")
    seq.groups[0].primary[0].attributes = HarmonyAttributes(duration=Fraction(numerator=4, denominator=1))
    assert sequence_to_hamon_text(seq) == "@cs\nC[dur:4]\n"


def test_the_extent_is_not_written_twice():
    seq = parse_hamon_sequence("@cs\nC[dur:4]")
    label = seq.groups[0].primary[0]
    label.attributes = replace(label.attributes, endRef="n2")
    assert sequence_to_hamon_text(seq) == "@cs\nC[dur:4][endref:n2]\n"


# ---------------------------------------------------------------------------
# JSON, and what the extent is FOR
# ---------------------------------------------------------------------------

def test_json_carries_the_extent_so_the_lossy_report_can_see_it():
    """`report.py` diffs the canonical dicts. Until the extent was in the AST it could
    never be a finding, so a target that dropped it round-tripped clean."""
    attrs = sequence_to_dict(parse_hamon_sequence("@cs\nC[dur:3/4][endref:n1]"))["groups"][0]["primary"][0]["attributes"]
    assert attrs["duration"] == {"numerator": 3, "denominator": 4}
    assert attrs["endRef"] == "n1"


def test_alternatives_can_segment_the_same_passage_differently():
    """The reason the extent is on the label. One analyst hears a V lasting two bars;
    the other hears V then V7. Both readings start at the same point, so a duration on
    the GROUP could not hold them."""
    seq = parse_hamon_sequence("@rn\nm:1,ts:1,V[dur:8]|V[dur:4]")
    group = seq.groups[0]
    assert _pair(_extent(group.primary[0])) == (8, 1)
    assert _pair(_extent(group.alternatives[0][0])) == (4, 1)


def test_a_sequence_without_extents_is_unchanged():
    """Absent means unknown. Nothing infers a duration from the next group's onset."""
    seq = parse_hamon_sequence("@cs\nm:1,ts:1,C\nm:2,ts:1,F")
    assert all(_extent(g.primary[0]) is None for g in seq.groups)
