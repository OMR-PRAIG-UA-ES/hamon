"""Round-trip tests for the format exporters (hamonpy.export + report writers)."""
from __future__ import annotations

import pytest

from hamonpy.parse import parse_hamon_sequence
from hamonpy.report import WRITERS, lossy_report, write_to

# Complex sample: applied function + alterations live inside the surface.
# NB: surfaces are distinct — the regex extractors (abc/lilypond/musescore) dedup
# repeated surface strings, so a repeated chord would not survive that round-trip.
CS_SAMPLE = "@cs\nCmaj7\nA7b9[of:ii]\nDm7\nG7b9b13\nFmaj7\n"
# Plain triads/sevenths: fully recovered even by surface-normalizing readers.
SIMPLE_SAMPLE = "@cs\nCmaj7\nDm7\nG7\nC\n"
RN_SAMPLE = "@rn\nI\nV7\nvi\nIV\nV\nI\n"

# Readers that re-parse the embedded surface with the full HAMON parser, so even
# applied/alteration detail round-trips losslessly.
#
# LilyPond used to be in this list, and it did not belong: it was "lossless" only because
# the exporter wrote a placeholder `c1` and parked every harmony in `% hamon-surface:`
# comments, which the reader read straight back. The exporter now emits real
# `\chordmode`, so what it cannot spell exactly (an altered dominant like `A7b9`) becomes
# a skip and is reported as the loss it is. Extending the writer/reader pair to
# LilyPond's step-alteration syntax (`a:7.9-`) would earn it a place back here.
FULL_PARSER_FORMATS = ["hamon", "musicxml", "abc", "musescore"]
#: Formats whose vocabulary covers plain chords but not every altered one.
PLAIN_ONLY_FORMATS = ["lilypond"]
# Readers that re-normalize the surface (chord-symbol only): lossless on plain chords.
NORMALIZING_FORMATS = ["humdrum", "ireal"]


@pytest.mark.parametrize("target", FULL_PARSER_FORMATS)
def test_complex_chord_symbol_roundtrip_lossless(target):
    seq = parse_hamon_sequence(CS_SAMPLE)
    rep = lossy_report(seq, target)
    assert rep.error is None, rep.error
    assert rep.lossless, rep.summary()


@pytest.mark.parametrize("target", PLAIN_ONLY_FORMATS)
def test_alterations_a_format_cannot_spell_are_reported_not_faked(target):
    """LilyPond declines `A7b9` rather than writing a plain `a:7` that means another chord.

    The point is not that it is lossy — it is that the loss is *stated*. Before this, the
    same export claimed to be lossless because the reader was recovering our comments."""
    rep = lossy_report(parse_hamon_sequence(CS_SAMPLE), target)
    assert rep.error is None, rep.error
    assert not rep.lossless
    assert "hamon-surface" not in (rep.output_text or "")


@pytest.mark.parametrize("target", FULL_PARSER_FORMATS + PLAIN_ONLY_FORMATS + NORMALIZING_FORMATS)
def test_plain_chord_symbol_roundtrip_lossless(target):
    seq = parse_hamon_sequence(SIMPLE_SAMPLE)
    rep = lossy_report(seq, target)
    assert rep.error is None, rep.error
    assert rep.lossless, rep.summary()


def test_romantext_preserves_roman_surfaces():
    seq = parse_hamon_sequence(RN_SAMPLE)
    text = write_to(seq, "romantext")
    surfaces = [l.surface for g in seq.groups for l in g.primary]
    for s in surfaces:
        assert s in text, f"{s} missing from romantext export:\n{text}"
    rep = lossy_report(seq, "romantext")
    assert rep.error is None
    # group count preserved on re-import
    reparsed = sum(len(g.primary) for g in parse_hamon_sequence(RN_SAMPLE).groups)
    assert reparsed == len(surfaces)


def test_every_writer_produces_text():
    seq = parse_hamon_sequence(CS_SAMPLE)
    for target in WRITERS:
        assert isinstance(write_to(seq, target), str), f"{target} did not return str"
    # Formats that can carry chord symbols must be non-empty for a cs sequence.
    # (dcml/romantext are roman-oriented and legitimately empty for pure chord symbols.)
    for target in ["hamon", "musicxml", "lilypond", "abc", "musescore",
                   "humdrum", "ireal", "harte", "dezrann"]:
        assert write_to(seq, target).strip(), f"{target} produced empty output"


def test_surface_formats_embed_every_surface():
    seq = parse_hamon_sequence(CS_SAMPLE)
    for target in ["abc", "musescore", "ireal", "humdrum"]:
        text = write_to(seq, target)
        for g in seq.groups:
            for label in g.primary:
                assert label.surface in text, f"{label.surface} missing from {target} export"
