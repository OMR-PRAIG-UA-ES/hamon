from hamonpy.parse import parse_hamon_sequence
from hamonpy.ast import (
    ChordSymbolSemantic, RomanSemantic, NashvilleSemantic,
    FiguredBassSemantic, FunctionalSemantic, NoChordSemantic, PitchClass,
)


def test_chord_symbol_basic():
    seq = parse_hamon_sequence("@cs\nCΔ7\nAm7\nG7")
    assert len(seq.groups) == 3
    assert seq.sequence_system_hint == "cs"

    sem0 = seq.groups[0].primary[0].semantic
    assert isinstance(sem0, ChordSymbolSemantic)
    assert sem0.root == PitchClass(note="C")
    assert sem0.quality == "major"
    assert sem0.seventh == "maj7"

    sem1 = seq.groups[1].primary[0].semantic
    assert isinstance(sem1, ChordSymbolSemantic)
    assert sem1.quality == "minor"
    assert sem1.seventh == "min7"

    sem2 = seq.groups[2].primary[0].semantic
    assert isinstance(sem2, ChordSymbolSemantic)
    assert sem2.quality == "major"
    assert sem2.seventh == "dom7"


def test_chord_symbol_flat_root():
    seq = parse_hamon_sequence("@cs\nBb")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root == PitchClass(note="B", accidental="flat")
    assert sem.quality == "major"


def test_chord_symbol_slash_bass():
    seq = parse_hamon_sequence("@cs\nG7/B")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.seventh == "dom7"
    assert sem.bass == PitchClass(note="B")


def test_chord_symbol_suspended():
    seq = parse_hamon_sequence("@cs\nCsus4\nCsus2")
    assert seq.groups[0].primary[0].semantic.suspensions == [4]
    assert seq.groups[1].primary[0].semantic.suspensions == [2]


def test_chord_symbol_hdim():
    seq = parse_hamon_sequence("@cs\nBø7")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.quality == "half-diminished"
    assert sem.seventh == "hdim7"


def test_no_omit_not_eaten_as_natural():
    # Regression: the surface-fallback regex used to eat the ASCII natural `n` in `Cno3`,
    # reading C♮ + `o3` (diminished) instead of C + `no3` (omit 3). `n` now only counts as
    # a natural when no letter follows it.
    seq = parse_hamon_sequence("@cs\nCno3")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.quality == "major"
    assert sem.omits == [3]
    assert sem.root == PitchClass(note="C")   # not C-natural
    # A real ASCII natural (not followed by a letter) still parses.
    n7 = parse_hamon_sequence("@cs\nCn7").groups[0].primary[0].semantic
    assert n7.root == PitchClass(note="C", accidental="natural")
    assert n7.seventh == "dom7"


def test_paren_tension_list_note_led():
    # NOTE-led root ('G' lexes as NOTE): the chordSymbol path already shielded the
    # comma via parenGroup. Altered tensions lift into `alterations`.
    seq = parse_hamon_sequence("@cs\nG7(b9,b13)")
    assert len(seq.groups[0].primary) == 1
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert [a["degree"] for a in sem.alterations] == [9, 13]


def test_paren_tension_list_word_led():
    # Regression: 'Cm' lexes as one WORD, so the chord takes the text path where a
    # bare comma used to split 'Cm7(9,11)' into two labels ('Cm7(9' + '11)'). The
    # balanced paren group now stays intact and the tensions lift into `extensions`.
    seq = parse_hamon_sequence("@cs\nCm7(9,11)")
    assert len(seq.groups[0].primary) == 1
    label = seq.groups[0].primary[0]
    assert label.surface == "Cm7(9,11)"
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.quality == "minor"
    assert sem.seventh == "min7"
    assert sem.extensions == [9, 11]


def test_paren_tension_list_does_not_break_chord_list():
    # A real comma-separated list of WORD-led chords must still split into two.
    seq = parse_hamon_sequence("@cs\nCm7,Dm7")
    assert [lbl.surface for lbl in seq.groups[0].primary] == ["Cm7", "Dm7"]


def test_roman_numeral():
    seq = parse_hamon_sequence("@rn\nI\nii\nV7")
    assert seq.groups[0].primary[0].semantic.degree == "I"
    assert seq.groups[1].primary[0].semantic.degree == "ii"
    v7 = seq.groups[2].primary[0].semantic
    assert v7.degree == "V"
    assert v7.tail == "7"


def test_roman_flat_prefix():
    seq = parse_hamon_sequence("@rn\nbVII")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "VII"
    assert sem.prefixAccidentals == ["b"]


def test_roman_secondary():
    seq = parse_hamon_sequence("@rn\nV/V\nV7/IV")
    assert seq.groups[0].primary[0].semantic.secondary == "V"
    v7_iv = seq.groups[1].primary[0].semantic
    assert v7_iv.secondary == "IV"
    assert v7_iv.tail == "7"


def test_figured_bass():
    seq = parse_hamon_sequence("@fb\n6-5\n4-3")
    fb0 = seq.groups[0].primary[0].semantic
    assert isinstance(fb0, FiguredBassSemantic)
    assert fb0.number == 6
    assert fb0.tail == "-5"


def test_nashville():
    seq = parse_hamon_sequence("@ns\n1\n2m\n5")
    assert seq.groups[0].primary[0].semantic.number == 1
    ns2m = seq.groups[1].primary[0].semantic
    assert isinstance(ns2m, NashvilleSemantic)
    assert ns2m.number == 2
    assert ns2m.tail == "m"


def test_functional():
    seq = parse_hamon_sequence("@fun\nT\nPD->T")
    assert seq.groups[0].primary[0].semantic.chain == ["T"]
    assert seq.groups[1].primary[0].semantic.chain == ["PD", "T"]


def test_no_chord():
    seq = parse_hamon_sequence("@cs\nN.C.")
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, NoChordSemantic)


def test_alternatives_and_lists():
    seq = parse_hamon_sequence("@cs\nCΔ7|Am7,Bb")
    assert len(seq.groups) == 1
    assert seq.groups[0].primary[0].surface == "CΔ7"
    assert len(seq.groups[0].alternatives) == 1
    assert len(seq.groups[0].alternatives[0]) == 2


def test_surface_preserved():
    seq = parse_hamon_sequence("@cs\nCΔ7\nCmaj7\nCM7")
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["CΔ7", "Cmaj7", "CM7"]
    # All normalize to maj7
    for g in seq.groups:
        assert g.primary[0].semantic.seventh == "maj7"


def test_minor_major_seventh_spellings_agree():
    """Regression: `Cmmaj7` and `CmM7` read as C dominant 7 — the wrong chord.

    The chord-tail tokenizer's generic word rule swallowed `mmaj` whole and left a
    bare `7`, so the quality never registered as minor and the seventh defaulted to
    dominant. The parenthesized and Δ spellings were right all along, which is why
    only the letter-led ones drifted."""
    seq = parse_hamon_sequence("@cs\nCmmaj7\nCmMaj7\nCmM7\nCminMaj7\nCm(maj7)\nCmΔ7\nC-maj7")
    for group in seq.groups:
        sem = group.primary[0].semantic
        assert sem.quality == "minor", group.primary[0].surface
        assert sem.seventh == "maj7", group.primary[0].surface


def test_minor_major_seventh_does_not_swallow_plain_minor_seventh():
    seq = parse_hamon_sequence("@cs\nCm7\nCmaj7\nCm")
    qualities = [(g.primary[0].semantic.quality, g.primary[0].semantic.seventh)
                 for g in seq.groups]
    assert qualities == [("minor", "min7"), ("major", "maj7"), ("minor", None)]


def test_parenthesized_add_omit_sus():
    # Regression: '(add9)', '(no3)', '(sus4)' raised a parse error — the keywords lex as
    # their own tokens (ADD/OMIT/NO/SUS), which parenItem did not accept, although the
    # EBNF's parenItem includes any word. They must equal their unparenthesized twins.
    seq = parse_hamon_sequence("@cs\nC(add9)\nC(no3)\nC(omit5)\nC7(sus4)")
    sems = [g.primary[0].semantic for g in seq.groups]
    assert all(isinstance(s, ChordSymbolSemantic) for s in sems)
    assert sems[0].adds == [9]
    assert sems[1].omits == [3]
    assert sems[2].omits == [5]
    assert sems[3].suspensions == [4]
    # Surfaces (and their parens) round-trip losslessly.
    assert [g.primary[0].surface for g in seq.groups] == ["C(add9)", "C(no3)", "C(omit5)", "C7(sus4)"]
