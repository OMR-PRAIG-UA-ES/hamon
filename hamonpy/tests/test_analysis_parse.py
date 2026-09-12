"""End-to-end surface-parsing tests for the v0.2.0 analytical grammar (Python).

Mirrors the shared analysis corpus: @key: regions, layer tags,
bracketed attributes and HT/NHT tones parse from the .hamon surface into the AST.
"""

from hamonpy.parse import parse_hamon_sequence
from hamonpy.ast import (
    ChordSymbolSemantic, FiguredBassSemantic, FunctionalSemantic, RomanSemantic, ToneSemantic, PitchClass,
)


def test_key_regions_and_modulation():
    seq = parse_hamon_sequence("@rn\n@key:C\nI\nvi\n@key:G\nV7\nI")
    assert len(seq.groups) == 4
    assert seq.regions is not None and len(seq.regions) == 2
    r0, r1 = seq.regions
    assert r0.kind == "key" and r0.from_group == 0 and r0.to_group == 1
    assert r0.key.tonic == PitchClass("C") and r0.key.mode == "major"
    assert r1.kind == "key" and r1.from_group == 2
    assert r1.key.tonic == PitchClass("G")


def test_tonicization_with_computed_tonic():
    seq = parse_hamon_sequence("@rn\n@key:C\nI\n@key:V\nV7/V\nV\n@key:C\nI")
    assert len(seq.groups) == 4
    ton = next(r for r in seq.regions if r.kind == "tonicization")
    assert ton.degree == "V"
    assert ton.parent == 0
    assert ton.key.tonic == PitchClass("G")  # V of C major = G
    assert ton.from_group == 1 and ton.to_group == 2

    sem = seq.groups[1].primary[0].semantic
    assert isinstance(sem, RomanSemantic)
    assert sem.degree == "V" and sem.secondary == "V"


def test_altered_tonicization_tonic():
    seq = parse_hamon_sequence("@rn\n@key:C\nI\n@key:bVI\nI")
    ton = next(r for r in seq.regions if r.kind == "tonicization")
    assert ton.degree == "bVI"
    assert ton.key.tonic == PitchClass(note="A", accidental="flat")  # bVI of C = Ab


def test_flat_prefixed_secondary():
    # The flat secondary '/bVII' lexes as one WORD (maximal munch); the grammar's
    # rnSecondary WORD alternative + normalizer must still produce a Roman.
    for surface, sec in [("V/bVII", "bVII"), ("V42/bVII", "bVII"),
                         ("viiø7/bII", "bII"), ("V/#iv", "#iv"), ("V7/IV", "IV")]:
        label = parse_hamon_sequence("@rn\n" + surface).groups[0].primary[0]
        assert isinstance(label.semantic, RomanSemantic), surface
        assert label.detected_system == "rn", surface
        assert label.semantic.secondary == sec, surface
        assert label.surface == surface


def test_modal_region():
    seq = parse_hamon_sequence("@rn\n@key:D:dorian\ni\nIV\nbVII\ni")
    assert seq.regions[0].kind == "key"
    assert seq.regions[0].key.tonic == PitchClass("D")
    assert seq.regions[0].key.mode == "dorian"
    assert len(seq.groups) == 4


def test_layered_functional_analysis():
    seq = parse_hamon_sequence("@auto\nfn:D,rn:V7,fb:6")
    assert len(seq.groups) == 1
    labels = seq.groups[0].primary
    assert [l.layer for l in labels] == ["function", "degree", "bass"]
    assert isinstance(labels[0].semantic, FunctionalSemantic)
    assert labels[0].semantic.chain == ["D"]
    assert isinstance(labels[1].semantic, RomanSemantic)
    assert labels[1].semantic.degree == "V" and labels[1].semantic.tail == "7"
    assert isinstance(labels[2].semantic, FiguredBassSemantic)
    assert labels[2].semantic.number == 6
    assert labels[0].surface == "D"  # v0.4: surface is bare, the tag lives in `layer`


def test_omitted_fundamental_and_inversion():
    seq = parse_hamon_sequence("@rn\nviio7[no1]\nI64[inv:2]")
    assert seq.groups[0].primary[0].attributes.omittedRoot is True
    assert seq.groups[1].primary[0].attributes.inversion == 2
    assert seq.groups[0].primary[0].surface == "viio7[no1]"
    # The ASCII diminished mark must not knock the label out of the roman system
    # (WORD's maximal munch used to swallow 'viio' whole -> text).
    sem = seq.groups[0].primary[0].semantic
    assert sem.kind == "roman"
    assert sem.degree == "vii"
    assert sem.tail == "o7"


def test_ascii_diminished_roman_variants():
    seq = parse_hamon_sequence("@rn\nviio\niio6\nV7/viio")
    kinds = [g.primary[0].semantic.kind for g in seq.groups]
    assert kinds == ["roman", "roman", "roman"]
    assert seq.groups[0].primary[0].semantic.tail == "o"
    assert seq.groups[1].primary[0].semantic.tail == "o6"
    assert seq.groups[2].primary[0].semantic.secondary == "viio"


def test_arpeggiation_pedal_applied():
    seq = parse_hamon_sequence("@cs\nC[arp]\nG[ped]\nD7[of:V]")
    assert seq.groups[0].primary[0].attributes.arpeggiated is True
    assert isinstance(seq.groups[0].primary[0].semantic, ChordSymbolSemantic)
    assert seq.groups[1].primary[0].attributes.pedal is True
    assert seq.groups[2].primary[0].attributes.applied.target == "V"


def test_harmonic_and_nonharmonic_tones():
    seq = parse_hamon_sequence("@auto\nmelodic:E[HT] , melodic:F[NHT:passing] , melodic:G[HT]")
    labels = seq.groups[0].primary
    assert [l.layer for l in labels] == ["melodic", "melodic", "melodic"]
    assert isinstance(labels[0].semantic, ToneSemantic)
    assert labels[0].semantic.category == "harmonic"
    assert labels[0].semantic.pitch == PitchClass("E")
    assert labels[1].semantic.category == "nonharmonic"
    assert labels[1].semantic.type == "passing"
    assert labels[1].semantic.pitch == PitchClass("F")


def test_plain_v010_unchanged():
    seq = parse_hamon_sequence("@cs\nCΔ7\nAm7\nG7")
    assert len(seq.groups) == 3
    assert seq.regions is None
    assert seq.groups[0].primary[0].layer is None
    assert seq.groups[0].primary[0].attributes is None
    sem = seq.groups[0].primary[0].semantic
    assert isinstance(sem, ChordSymbolSemantic)
    assert sem.root == PitchClass("C") and sem.seventh == "maj7"
