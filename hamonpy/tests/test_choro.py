"""Tests for the DCML Choro Songbook adapter (hamonpy.adapters.choro).

Data-driven over the committed extract in use-cases/choro/.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from hamonpy.adapters import choro
from hamonpy.ast import ChordSymbolSemantic, Key, PitchClass
from hamonpy.normalize import degree_to_pitch
from hamonpy.parse import parse_hamon_sequence

CHORO = Path(__file__).resolve().parents[2] / "use-cases" / "choro"
PIECES = choro.read_tsv((CHORO / "choro-extract.tsv").read_text(encoding="utf-8"))

_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ACC = {"sharp": 1, "flat": -1, "double-sharp": 2, "double-flat": -2, "natural": 0, None: 0}


def _pc(pitch):
    return (_PC[pitch.note] + _ACC[pitch.accidental]) % 12


def _cs_root(chord):
    seq = parse_hamon_sequence("@cs\n" + choro.normalize_chord(chord))
    sem = seq.groups[0].primary[0].semantic
    return _pc(sem.root) if isinstance(sem, ChordSymbolSemantic) else None


def _parse_key(text):
    m = re.match(r"^([A-G])([#b]?)(m?)$", text.strip())
    acc = {"#": "sharp", "b": "flat", "": None}[m.group(2)]
    return Key(tonic=PitchClass(note=m.group(1), accidental=acc),
               mode="minor" if m.group(3) == "m" else "major")


def test_extract_present():
    assert PIECES, "the choro extract should contain pieces"
    for fn in PIECES:
        assert (CHORO / "transcriptions" / fn).exists(), f"missing transcription {fn}"


def test_normalize_chord_7M():
    assert choro.normalize_chord("Bb7M") == "Bbmaj7"
    assert choro.normalize_chord("C7M(#11)") == "Cmaj7(#11)"


def test_grammar_features():
    # `.` holds the previous chord; `$ref*N` repeats; empty bars sustain
    defs = "P0: C . | G7 |\nPartA: $P0*2\nS[C, 2/4]: $PartA"
    assert choro.expand_transcription(defs) == ["C", "C", "G7", "C", "C", "G7"]


@pytest.mark.parametrize("fn", [p for p in PIECES if p != "1_forro_de_gala_WF.txt"])
def test_transcription_matches_tsv(fn):
    txt = (CHORO / "transcriptions" / fn).read_text(encoding="utf-8")
    assert choro.expand_transcription(txt) == [r["chord"] for r in PIECES[fn]]


def test_known_inconsistency_is_flagged():
    # this piece's transcription and table disagree — the adapter must surface it
    fn = "1_forro_de_gala_WF.txt"
    txt = (CHORO / "transcriptions" / fn).read_text(encoding="utf-8")
    assert choro.expand_transcription(txt) != [r["chord"] for r in PIECES[fn]]


def test_chord_matches_harte_root():
    for rows in PIECES.values():
        for r in rows:
            ha = (r.get("harte") or "").strip()
            if not ha or ha == "N" or r["chord"] == "NC":
                continue
            hseq = choro.harte_text_to_hamon(ha)
            b = _pc(hseq.groups[0].primary[0].semantic.root) if hseq.groups else None
            if b is None:
                continue
            assert _cs_root(r["chord"]) == b, f"{r['chord']} vs harte {ha}"


def test_chord_matches_roman_in_key():
    for rows in PIECES.values():
        for r in rows:
            rn, lk = r["rn_chord"].strip(), r["local_key"].strip()
            m = re.match(r"^([b#]*)([iIvV]+)", rn)
            if not rn or not lk or not m or r["chord"] == "NC":
                continue
            rn_pc = _pc(degree_to_pitch(_parse_key(lk), list(m.group(1)), m.group(2)))
            assert _cs_root(r["chord"]) == rn_pc, f"{r['chord']} vs {rn} in {lk}"


def test_tsv_piece_to_hamon_positions():
    fn = "1_assanhado_WF.txt"
    seq = choro.tsv_piece_to_hamon(PIECES[fn], "chord")
    assert len(seq.groups) == len(PIECES[fn])
    assert seq.groups[0].position is not None and seq.groups[0].position.measure == 1


def test_cli_detects_and_converts_choro():
    from hamonpy import cli

    txt = CHORO / "transcriptions" / "1_assanhado_WF.txt"
    tsv = CHORO / "choro-extract.tsv"
    assert cli.detect_file_format(txt) == "choro"
    assert cli.detect_file_format(tsv) == "choro"
    # a .txt transcription converts to its single-piece sequence
    assert len(cli.convert_file(txt).groups) == len(PIECES["1_assanhado_WF.txt"])
    # the merged .tsv converts to every piece's chords, concatenated
    assert len(cli.convert_file(tsv).groups) == sum(len(r) for r in PIECES.values())
