"""Smoke + outcome tests for use-cases/ — keeps the worked recipes from bit-rotting."""

from pathlib import Path

import pytest

from hamonpy.parse import parse_hamon_sequence
from hamonpy.ast import ChordSymbolSemantic, RomanSemantic

USE_CASES = Path(__file__).resolve().parents[2] / "use-cases"
_HAMON = sorted(USE_CASES.glob("**/*.hamon"))


def test_use_cases_present():
    assert len(_HAMON) >= 2


@pytest.mark.parametrize("path", _HAMON, ids=lambda p: p.parent.name)
def test_use_case_parses(path: Path):
    seq = parse_hamon_sequence(path.read_text())
    assert seq.groups, f"{path} produced no groups"


def test_roman_numeral_analysis_outcome():
    seq = parse_hamon_sequence((USE_CASES / "roman-numeral-analysis" / "progression.hamon").read_text())
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "IV", "V", "V", "I"]

    ton = next(r for r in seq.regions if r.kind == "tonicization")
    assert ton.degree == "V"
    assert ton.parent == 0
    assert ton.key.tonic.note == "G" and ton.key.mode == "major"

    v_of_v = seq.groups[2].primary[0].semantic
    assert isinstance(v_of_v, RomanSemantic) and v_of_v.secondary == "V"


def test_jazz_leadsheet_outcome():
    seq = parse_hamon_sequence((USE_CASES / "jazz-leadsheet" / "tune.hamon").read_text())
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["Dm7", "G7", "Cmaj7", "A7[of:ii]", "Dm7"]

    applied = seq.groups[3].primary[0]
    assert isinstance(applied.semantic, ChordSymbolSemantic)
    assert applied.semantic.root.note == "A" and applied.semantic.seventh == "dom7"
    assert applied.attributes is not None and applied.attributes.applied.target == "ii"


def test_berklee_jazz_outcome():
    seq = parse_hamon_sequence((USE_CASES / "berklee-jazz" / "changes.hamon").read_text())
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["Cmaj7", "Eø7[of:ii]", "A7b9[of:ii]", "Dm7", "G7b9b13", "Cmaj7"]

    # @key:C opens the home region (functional, not just a chord list)
    assert seq.regions[0].kind == "key"
    assert seq.regions[0].key.tonic.note == "C" and seq.regions[0].key.mode == "major"

    # the related ii–V of ii both carry the applied target ii
    assert seq.groups[1].primary[0].attributes.applied.target == "ii"   # Eø7
    assert seq.groups[2].primary[0].attributes.applied.target == "ii"   # A7b9

    # altered dominant tensions are captured as alterations
    a7 = seq.groups[2].primary[0].semantic
    assert isinstance(a7, ChordSymbolSemantic) and a7.seventh == "dom7"
    assert [a["degree"] for a in a7.alterations] == [9]
    g7 = seq.groups[4].primary[0].semantic
    assert [a["degree"] for a in g7.alterations] == [9, 13]


def test_time_aligned_positions_outcome():
    from hamonpy.ast import Position
    from hamonpy.serialize import sequence_to_hamon_text

    src = (USE_CASES / "time-aligned-positions" / "progression.hamon").read_text()
    seq = parse_hamon_sequence(src)
    assert [g.position for g in seq.groups] == [
        Position(measure=1, beat=1.0),
        Position(measure=1, beat=3.0),
        Position(measure=2, beat=1.0),
        Position(measure=2, beat=3.0),
        Position(measure=3, beat=1.0),
    ]
    # the @@ tags round-trip through the text serializer
    assert parse_hamon_sequence(sequence_to_hamon_text(seq)) == seq


# ---------------------------------------------------------------------------
# Per-dataset use-cases (synthetic fixtures, real adapters) — Phase 10.4
# ---------------------------------------------------------------------------

def test_when_in_rome_romantext():
    from hamonpy.adapters.romantext import romantext_file_to_hamon
    seq = romantext_file_to_hamon(str(USE_CASES / "when-in-rome" / "analysis.txt"))
    assert [r.kind for r in seq.regions] == ["key", "modulation"]
    assert seq.regions[1].key.tonic.note == "G"


def test_distant_listening_corpus_dcml():
    from hamonpy.adapters.dcml import dcml_tsv_to_hamon
    seq = dcml_tsv_to_hamon(str(USE_CASES / "distant-listening-corpus" / "harmonies.tsv"))
    kinds = [r.kind for r in seq.regions]
    assert "tonicization" in kinds and "modulation" in kinds
    ton = next(r for r in seq.regions if r.kind == "tonicization")
    assert ton.key.tonic.note == "G" and ton.degree == "V"


def test_jazz_harmony_treebank():
    from hamonpy.adapters.treebank import treebank_json_to_hamon
    seq = treebank_json_to_hamon(str(USE_CASES / "jazz-harmony-treebank" / "treebank.json"))
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert "Cmaj7" in surfaces and "Eø7" in surfaces


def test_key_modulation_regions():
    from hamonpy.adapters.humdrum import key_modulation_file_to_hamon
    seq = key_modulation_file_to_hamon(str(USE_CASES / "key-modulation" / "snippet.krn"))
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "IV", "V", "I", "IV", "V"]
    assert [(r.kind, r.key.tonic.note) for r in seq.regions] == [("key", "C"), ("modulation", "G")]


def test_jazzmus_berklee_dezrann_pipeline():
    import json
    from hamonpy.adapters.humdrum import humdrum_file_to_hamon
    from hamonpy.adapters.dezrann import hamon_to_dez, dez_to_hamon

    base = USE_CASES / "jazzmus-berklee-dezrann"

    # 1. JAZZMUS (Humdrum **jazz) → HAMON raw changes
    raw = humdrum_file_to_hamon(str(base / "chart.krn"))
    assert [g.primary[0].surface for g in raw.groups] == ["Cmaj7", "A7", "Dm7", "Db7", "Cmaj7"]

    # 2. The Berklee analysis stored in HAMON: region + tritone sub + time anchors
    seq = parse_hamon_sequence((base / "analysis.hamon").read_text())
    assert seq.regions[0].key.tonic.note == "C"
    sub = seq.groups[3].primary[0]                      # Db7[of:I] — flat-rooted subV7/I
    assert sub.semantic.root.note == "D" and sub.semantic.root.accidental == "flat"
    assert sub.attributes.applied.target == "I"         # the grammar fix: not swallowed
    assert [(g.position.time.numerator) for g in seq.groups] == [0, 4, 8, 12, 16]

    # 3. HAMON → Dezrann (time-aligned labels), and back
    labels = json.loads(hamon_to_dez(seq))["labels"]
    assert [(l["start"], l["tag"]) for l in labels] == [
        (0, "Cmaj7"), (4, "A7b9[of:ii]"), (8, "Dm7"), (12, "Db7[of:I]"), (16, "Cmaj7")
    ]
    assert [g.primary[0].surface for g in dez_to_hamon(hamon_to_dez(seq), system="cs").groups] == \
        ["Cmaj7", "A7b9[of:ii]", "Dm7", "Db7[of:I]", "Cmaj7"]


def test_applied_function_on_word_led_and_flat_root_chords():
    """Regression for the bracket-swallowing bug fixed 2026-06-15."""
    for surface, target in [("Dm7[of:V]", "V"), ("Cmaj7[of:I]", "I"),
                            ("Bb7[of:I]", "I"), ("Em7b5[of:ii]", "ii"),
                            ("Db7[of:I]", "I")]:
        seq = parse_hamon_sequence("@cs\n" + surface)
        lbl = seq.groups[0].primary[0]
        assert isinstance(lbl.semantic, ChordSymbolSemantic), surface
        assert lbl.attributes is not None and lbl.attributes.applied.target == target, surface
    # parenthesised tension list stays one chord (comma no longer splits it)
    seq = parse_hamon_sequence("@cs\nA7(b9,b13)[of:ii]")
    assert len(seq.groups) == 1
    assert seq.groups[0].primary[0].attributes.applied.target == "ii"


def test_interactive_melodic_analysis_tones():
    from hamonpy.adapters.mei import mei_file_to_hamon
    from hamonpy.ast import ToneSemantic
    seq = mei_file_to_hamon(str(USE_CASES / "interactive-melodic-analysis" / "analysis.mei"))
    tones = [g.primary[0].semantic for g in seq.groups
             if isinstance(g.primary[0].semantic, ToneSemantic)]
    assert [t.type for t in tones] == ["chord-tone", "passing", "chord-tone", "neighbor"]
