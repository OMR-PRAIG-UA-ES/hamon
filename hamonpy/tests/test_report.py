"""Tests for the lossy-conversion report (hamonpy.report)."""
from __future__ import annotations

from hamonpy.parse import parse_hamon_sequence
from hamonpy.report import lossy_report, WRITERS


SAMPLE = "@cs\nCmaj7\nA7b9[of:ii]\nDm7\nG7b9b13\nCmaj7\n"


def test_hamon_roundtrip_is_lossless():
    seq = parse_hamon_sequence(SAMPLE)
    rep = lossy_report(seq, "hamon")
    assert rep.error is None
    assert rep.lossless, rep.summary()
    assert rep.semantic == []


def test_harte_drops_alterations_and_applied():
    seq = parse_hamon_sequence(SAMPLE)
    rep = lossy_report(seq, "harte")
    assert rep.error is None
    assert not rep.lossless
    paths = {f.path for f in rep.semantic}
    # b9 alteration and the applied function should be flagged as lost.
    assert any("alterations" in p for p in paths)
    assert any("attributes" in p for p in paths)


def test_unknown_target_raises():
    seq = parse_hamon_sequence(SAMPLE)
    try:
        lossy_report(seq, "midi")
    except ValueError as exc:
        assert "midi" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for non-writer target")


def test_every_registered_writer_runs_without_error():
    seq = parse_hamon_sequence(SAMPLE)
    for target in WRITERS:
        rep = lossy_report(seq, target)
        assert rep.error is None, f"{target}: {rep.error}"


def test_to_dict_shape():
    seq = parse_hamon_sequence(SAMPLE)
    d = lossy_report(seq, "harte").to_dict()
    assert d["target"] == "harte"
    assert set(d) >= {"target", "sourceGroups", "lossless", "semanticLoss", "notationalDiff"}


# ---------------------------------------------------------------------------
# What the target INVENTED (the reverse pass over the output)
# ---------------------------------------------------------------------------


def test_the_canonical_roundtrip_invents_nothing():
    # The reference row: HAMON → HAMON must add as little as it loses. If this ever fails,
    # the reverse pass is reporting noise and not a finding.
    rep = lossy_report(parse_hamon_sequence(SAMPLE), "hamon")
    assert rep.invented == [], rep.summary()
    assert rep.faithful


def test_a_value_the_source_never_said_is_reported():
    # The MEI reader stamps `@version:0.2.0` onto every sequence it reconstructs, so a
    # source that declares no version comes back carrying one. Walking the source keys
    # alone could not see it: nothing was lost, something was gained.
    rep = lossy_report(parse_hamon_sequence(SAMPLE), "mei")
    assert rep.error is None
    assert any(f.path == "version" for f in rep.invented), rep.summary()
    assert all(f.kind == "added" for f in rep.invented)
    assert all(f.source is None and f.output is not None for f in rep.invented)


def test_invented_is_not_a_loss():
    # `lossless` means nothing was LOST, and that meaning is unchanged: an addition does
    # not make a conversion lossy. `faithful` is the stricter question.
    rep = lossy_report(parse_hamon_sequence(SAMPLE), "mei")
    assert rep.invented
    assert not rep.faithful
    # …and `lost` holds only the losses, never the additions.
    assert all(f.kind != "added" for f in rep.lost)
    assert sorted(rep.lost + rep.invented, key=id) == sorted(rep.semantic, key=id)


def test_to_dict_separates_loss_from_invention():
    d = lossy_report(parse_hamon_sequence(SAMPLE), "mei").to_dict()
    assert set(d) >= {"lossless", "faithful", "semanticLoss", "invented", "notationalDiff"}
    assert all(e["kind"] != "added" for e in d["semanticLoss"])
    assert all(e["kind"] == "added" for e in d["invented"])


def test_summary_names_what_was_invented():
    text = lossy_report(parse_hamon_sequence(SAMPLE), "mei").summary()
    assert "invented by the target" in text
    assert "version" in text


# ---------------------------------------------------------------------------
# Aligned list diff (a loss in the MIDDLE must not cascade)
# ---------------------------------------------------------------------------

from hamonpy.report import _diff  # noqa: E402
from hamonpy.serialize import sequence_to_dict  # noqa: E402


def _semantic_diff(source_text: str, output_text: str):
    """The semantic findings of diffing two hand-written sequences, standing in for a
    round-trip whose target lost or moved something."""
    findings = []
    _diff(sequence_to_dict(parse_hamon_sequence(source_text)),
          sequence_to_dict(parse_hamon_sequence(output_text)), "", findings)
    return [f for f in findings if not f.notational]


def test_a_group_lost_in_the_middle_is_one_finding_not_a_cascade():
    # Comparing position by position, the Dm7 that went missing shifted every later group
    # by one, and the report read "D became G, G became A, A became F" plus a dropped Fmaj7
    # that is in fact still there: ten findings, all of them false, and none of them naming
    # the chord that was actually lost.
    found = _semantic_diff("@cs\nCmaj7\nDm7\nG7\nAm7\nFmaj7\n", "@cs\nCmaj7\nG7\nAm7\nFmaj7\n")
    assert [(f.kind, f.path, f.summary) for f in found] == [("dropped", "groups[1]", "Dm7")]


def test_a_loss_at_the_tail_still_reports_one_per_item():
    # The case the corpus does hit, and which position-by-position already got right.
    found = _semantic_diff("@cs\nCmaj7\nDm7\nG7\n", "@cs\nCmaj7\n")
    assert [f.summary for f in found] == ["Dm7", "G7"]
    assert {f.kind for f in found} == {"dropped"}


def test_the_same_groups_in_another_order_are_one_reordering():
    # Not a loss and not a change: everything is there, somewhere else. Reported once for
    # the whole list, naming what moved -- the alternative is one "changed" per position.
    found = _semantic_diff("@cs\nCmaj7\nDm7\nG7\nAm7\n", "@cs\nAm7\nCmaj7\nDm7\nG7\n")
    assert len(found) == 1
    assert found[0].kind == "reordered"
    assert found[0].path == "groups"
    assert "Am7 [3] → [0]" in found[0].summary


def test_alignment_does_not_cost_the_field_level_detail():
    # An item that merely CHANGED does not anchor, so it lands in a gap -- where the second
    # pass pairs it with the same-kind item facing it and diffs the fields. Losing that
    # would trade one cascade for another.
    found = _semantic_diff("@cs\nCmaj7\nDm7\nG7\n", "@cs\nCmaj7\nDm\nG7\n")
    assert len(found) == 1
    assert found[0].path == "groups[1].primary[0].semantic.seventh"
    assert found[0].summary == "min7"


def test_a_long_sequence_falls_back_instead_of_going_quadratic():
    # Above the cap the diff compares position by position again, on purpose: the alignment
    # is O(n·m) and a sequence that long makes a cascade obvious anyway. It must still be a
    # report and not a crash.
    long_seq = "@cs\n" + "\n".join(["Cmaj7"] * 900) + "\n"
    assert _semantic_diff(long_seq, long_seq) == []
