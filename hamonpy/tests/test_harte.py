"""Tests for the Harte chord notation adapter."""
from __future__ import annotations

import pytest

from hamonpy.adapters.harte import (
    harte_text_to_hamon,
    hamon_to_harte_text,
    harte_token_to_hamon_label,
    _SHORTHAND_TO_HAMON_SUFFIX,
)
from hamonpy.ast import ChordSymbolSemantic, NoChordSemantic, PitchClass, TextSemantic
from hamonpy.parse import parse_hamon_sequence


# ---------------------------------------------------------------------------
# Token parsing
# ---------------------------------------------------------------------------

def test_parse_C_maj():
    label = harte_token_to_hamon_label("C:maj")
    assert label is not None
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root == PitchClass(note="C")
    assert sem.quality == "major"
    assert sem.seventh is None


def test_parse_G_dom7():
    label = harte_token_to_hamon_label("G:7")
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "G"
    assert sem.quality == "major"
    assert sem.seventh == "dom7"


def test_parse_Ab_maj7():
    label = harte_token_to_hamon_label("Ab:maj7")
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "A"
    assert sem.root.accidental == "flat"
    assert sem.seventh == "maj7"


def test_parse_D_min7():
    label = harte_token_to_hamon_label("D:min7")
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root.note == "D"
    assert sem.quality == "minor"
    assert sem.seventh == "min7"


def test_parse_B_hdim7():
    label = harte_token_to_hamon_label("B:hdim7")
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.quality == "half-diminished"


def test_parse_no_chord_N():
    label = harte_token_to_hamon_label("N")
    assert label is not None
    assert isinstance(label.semantic, NoChordSemantic)


def test_parse_unknown_X_returns_none():
    assert harte_token_to_hamon_label("X") is None


def test_parse_sus4():
    label = harte_token_to_hamon_label("C:sus4")
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.suspensions is not None and 4 in sem.suspensions


# ---------------------------------------------------------------------------
# Multi-line text parsing
# ---------------------------------------------------------------------------

def test_parse_multi_line():
    text = "C:maj\nG:7\nF:maj\n"
    seq = harte_text_to_hamon(text)
    assert len(seq.groups) == 3
    roots = [g.primary[0].semantic.root.note for g in seq.groups]
    assert roots == ["C", "G", "F"]


def test_parse_with_timestamps():
    text = "0.000\t2.000\tC:maj\n2.000\t4.000\tG:7\n"
    seq = harte_text_to_hamon(text)
    assert len(seq.groups) == 2
    assert seq.groups[0].primary[0].semantic.root.note == "C"
    assert seq.groups[1].primary[0].semantic.root.note == "G"


def test_parse_skips_comments():
    text = "# opening chord\nC:maj\n# transition\nG:7\n"
    seq = harte_text_to_hamon(text)
    assert len(seq.groups) == 2


def test_parse_skips_N_as_group():
    text = "C:maj\nN\nG:7\n"
    seq = harte_text_to_hamon(text)
    assert len(seq.groups) == 3
    assert isinstance(seq.groups[1].primary[0].semantic, NoChordSemantic)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_basic():
    seq = parse_hamon_sequence("@cs\nC\nG7\nAm")
    harte = hamon_to_harte_text(seq)
    lines = [l for l in harte.strip().splitlines() if l]
    assert lines[0] == "C:maj"
    assert lines[1] == "G:7"
    assert lines[2] == "A:min"


def test_export_maj7():
    seq = parse_hamon_sequence("@cs\nCmaj7")
    harte = hamon_to_harte_text(seq)
    assert "C:maj7" in harte


def test_export_flat_root():
    seq = parse_hamon_sequence("@cs\nBb")
    harte = hamon_to_harte_text(seq)
    assert "Bb:maj" in harte


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_roundtrip_simple():
    tokens = ["C:maj", "G:7", "F:maj", "A:min7"]
    text = "\n".join(tokens) + "\n"
    seq = harte_text_to_hamon(text)
    out = hamon_to_harte_text(seq)
    out_tokens = [l for l in out.strip().splitlines() if l]
    assert len(out_tokens) == len(tokens)
    for original, exported in zip(tokens, out_tokens):
        orig_label = harte_token_to_hamon_label(original)
        out_label = harte_token_to_hamon_label(exported)
        assert orig_label is not None and out_label is not None
        orig_sem: ChordSymbolSemantic = orig_label.semantic  # type: ignore[assignment]
        out_sem: ChordSymbolSemantic = out_label.semantic  # type: ignore[assignment]
        assert orig_sem.root.note == out_sem.root.note
        assert orig_sem.quality == out_sem.quality
        assert orig_sem.seventh == out_sem.seventh


# ---------------------------------------------------------------------------
# Vocabulary sweep — the whole shorthand table, not a sample of it
# ---------------------------------------------------------------------------
#
# `test_roundtrip_simple` above used four shorthands that all happened to survive,
# and compared only root/quality/seventh. That is why ten of the nineteen shorthands
# could silently degrade (`C:9` → `C:7`, `C:maj6` → `C:maj`, `C:minmaj7` → `C:7`)
# while the suite stayed green. These sweep the table instead.

_BASSES = ["Ab:min/5", "C:maj/b7", "F#:min7/b3", "Bb:maj/3", "Eb:7/#4"]


@pytest.mark.parametrize("shorthand", sorted(_SHORTHAND_TO_HAMON_SUFFIX))
def test_every_shorthand_round_trips_exactly(shorthand: str):
    token = f"C:{shorthand}"
    out = hamon_to_harte_text(harte_text_to_hamon(token + "\n")).strip()
    assert out == token


@pytest.mark.parametrize("token", _BASSES)
def test_bass_degree_round_trips_exactly(token: str):
    """A Harte bass is an altered scale degree — `/b7`, not just `/7`.

    Admitting bare digits only used to drop the whole line: no match, no label, no
    group, so not even `report.py` saw a loss."""
    out = hamon_to_harte_text(harte_text_to_hamon(token + "\n")).strip()
    assert out == token


def test_timed_lab_file_is_byte_for_byte_lossless():
    """The claim the `.lab` writer exists to make, over the full vocabulary."""
    tokens = [f"C:{sh}" for sh in sorted(_SHORTHAND_TO_HAMON_SUFFIX)] + ["N"] + _BASSES
    src = "".join(f"{i}.000000\t{i + 1}.000000\t{tok}\n" for i, tok in enumerate(tokens))
    assert hamon_to_harte_text(harte_text_to_hamon(src)) == src


def test_minor_major_seventh_is_not_a_dominant():
    """`C:minmaj7` came back `C:7` — a wrong chord, not a simplified one.

    The tokenizer swallowed `mmaj` as one word and left a bare `7`."""
    sem = harte_token_to_hamon_label("C:minmaj7").semantic
    assert sem.quality == "minor"
    assert sem.seventh == "maj7"


# ---------------------------------------------------------------------------
# Issue #2 — a bass spelled as a note name (BPSD, SWD) used to drop the whole line
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("note_token, degree_token", [
    ("C:min7/G", "C:min7/5"),
    ("Bb:maj/D", "Bb:maj/3"),
    ("Bb:maj/Db", "Bb:maj/b3"),
    ("F#:7/C#", "F#:7/5"),
])
def test_note_name_bass_is_the_same_chord_as_the_degree_bass(note_token, degree_token):
    by_note = harte_token_to_hamon_label(note_token).semantic
    by_degree = harte_token_to_hamon_label(degree_token).semantic
    assert isinstance(by_note, ChordSymbolSemantic)
    assert by_note.bass is not None
    assert by_note == by_degree


def test_note_name_bass_keeps_the_line():
    assert len(harte_text_to_hamon("C:min7/G\n").groups) == 1


@pytest.mark.parametrize("token", ["C:foo", "H:maj", "C:maj/", "C:(b5", "C:(b5,zz)"])
def test_unreadable_token_is_kept_as_text_not_dropped(token):
    seq = harte_text_to_hamon(token + "\n")
    assert len(seq.groups) == 1
    assert isinstance(seq.groups[0].primary[0].semantic, TextSemantic)
    assert seq.groups[0].primary[0].surface == token


def test_unreadable_token_does_not_become_a_different_chord():
    # `C:foo` used to come out as a plain C major triad.
    assert not isinstance(harte_token_to_hamon_label("C:foo").semantic, ChordSymbolSemantic)


# ---------------------------------------------------------------------------
# Issue #3 — degree lists: the complete chord, and `*n` as an omission
# ---------------------------------------------------------------------------

def test_degree_list_without_shorthand_does_not_imply_a_third():
    sem = harte_token_to_hamon_label("F#:(b5,b7)").semantic
    assert sem.omits == [3]
    assert sem.seventh == "dom7"
    assert [a["degree"] for a in sem.alterations] == [5]


def test_degree_list_with_a_third_has_no_omission():
    sem = harte_token_to_hamon_label("C:(3,5,b7)").semantic
    assert (sem.quality, sem.seventh, sem.omits) == ("major", "dom7", None)


@pytest.mark.parametrize("token, quality, seventh", [
    ("C:(b3,b5)", "diminished", None),
    ("C:(b3,b5,bb7)", "diminished", "dim7"),
    ("C:(b3,b5,b7)", "half-diminished", "hdim7"),
    ("C:(3,#5)", "augmented", None),
])
def test_degree_list_names_the_quality(token, quality, seventh):
    sem = harte_token_to_hamon_label(token).semantic
    assert (sem.quality, sem.seventh) == (quality, seventh)


def test_omission_in_a_degree_list_goes_to_omits():
    sem = harte_token_to_hamon_label("C:min(*3)").semantic
    assert (sem.quality, sem.omits) == ("minor", [3])


def test_degree_list_after_a_shorthand_adds_to_it():
    sem = harte_token_to_hamon_label("C:min7(b9)").semantic
    assert (sem.quality, sem.seventh) == ("minor", "min7")
    assert [a["degree"] for a in sem.alterations] == [9]


def test_degree_list_pitches_in_music21():
    m21 = pytest.importorskip("music21")
    from hamonpy.adapters.music21_adapter import hamon_to_music21_stream

    def pitches(token):
        stream = hamon_to_music21_stream(harte_text_to_hamon(token + "\n"))
        (h,) = stream.recurse().getElementsByClass("Harmony")
        return " ".join(p.name for p in h.pitches)

    assert pitches("F#:(b5,b7)") == "F# C E"
    assert pitches("C:min(*3)") == "C G"


# ---------------------------------------------------------------------------
# Issue #3 (writer) — what the reader takes from a degree list must be written back
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("token", [
    "C:min(*3)",
    "C:7(*3,b5)",        # what F#:(b5,b7) reads as: no third, flat fifth, minor seventh
    "C:min7(b9)",
    "C:7(#9,b13)",
    "C:maj(9)",
    "C:min(*5)",
    "C:7(*3,b5)/b7",
])
def test_degree_list_round_trips_exactly(token):
    seq = harte_text_to_hamon(token + "\n")
    assert hamon_to_harte_text(seq).strip() == token


def test_complete_chord_degree_list_is_written_and_read_back_as_the_same_chord():
    first = harte_text_to_hamon("F#:(b5,b7)\n")
    again = harte_text_to_hamon(hamon_to_harte_text(first))
    assert again.groups[0].primary[0].semantic == first.groups[0].primary[0].semantic


def test_degree_list_writer_leaves_shorthand_covered_degrees_alone():
    # `9` names the ninth, `1` and `5` name their omissions, `maj6` the sixth.
    for token in ("C:9", "C:1", "C:5", "C:maj6"):
        assert hamon_to_harte_text(harte_text_to_hamon(token + "\n")).strip() == token
