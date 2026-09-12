"""Tests for the layered Humdrum adapter (hamonpy/adapters/humdrum.py) — STEPS 9.8.2."""
from __future__ import annotations

from hamonpy.adapters.humdrum import humdrum_to_hamon, key_modulation_to_hamon
from hamonpy.ast import (
    ChordSymbolSemantic, FiguredBassSemantic, FunctionalSemantic, Position, RomanSemantic,
)
from hamonpy.parse import parse_hamon_sequence

# A score with note, harmonic-analysis, functional and figured-bass spines.
MULTI = "\n".join([
    "**kern\t**harm\t**function\t**fb",
    "*\t*\t*\t*",
    "4c\tI\tT\t.",
    "=\t=\t=\t=",
    "4g\tV7\tD\t6-5",
    "4c\tI\tT\t.",
    "*-\t*-\t*-\t*-",
]) + "\n"

SINGLE = "**harm\nI\nV7\nI\n*-\n"


def test_multi_spine_layers_aligned():
    seq = humdrum_to_hamon(MULTI)
    assert seq.sequence_system_hint == "auto"
    assert len(seq.groups) == 3

    g0 = seq.groups[0].primary
    assert [l.layer for l in g0] == ["degree", "function"]
    assert isinstance(g0[0].semantic, RomanSemantic) and g0[0].semantic.degree == "I"
    assert isinstance(g0[1].semantic, FunctionalSemantic) and g0[1].semantic.chain == ["T"]


def test_function_spine_unshadows_D():
    seq = humdrum_to_hamon(MULTI)
    g1 = seq.groups[1].primary
    assert [l.layer for l in g1] == ["degree", "function", "bass"]
    # 'D' in the **function spine is the dominant, not a D-major chord.
    func = g1[1]
    assert isinstance(func.semantic, FunctionalSemantic) and func.semantic.chain == ["D"]
    assert not isinstance(func.semantic, ChordSymbolSemantic)


def test_fb_spine_is_figured_bass():
    seq = humdrum_to_hamon(MULTI)
    bass = seq.groups[1].primary[2]
    assert bass.layer == "bass"
    assert isinstance(bass.semantic, FiguredBassSemantic)
    assert bass.semantic.number == 6


def test_barlines_and_tandem_skipped():
    seq = humdrum_to_hamon(MULTI)
    # 3 harmony events despite the '=' barline and '*' tandem lines.
    assert len(seq.groups) == 3


def test_single_spine_has_no_layer_tag():
    seq = humdrum_to_hamon(SINGLE)
    assert seq.sequence_system_hint == "rn"
    assert len(seq.groups) == 3
    assert all(g.primary[0].layer is None for g in seq.groups)
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "V", "I"]


# ── the writer (hamonpy.export.hamon_to_humdrum) ───────────────────────────
def test_writer_lays_out_layers_as_spines_with_key_and_barlines():
    """A layered sequence becomes parallel spines, a `*C:` tandem states the key and
    `=N` barlines carry the measure — the reader then rebuilds groups, layers and key."""
    from hamonpy.export import hamon_to_humdrum
    seq = parse_hamon_sequence(
        "@meter:4/4\n@key:C\nm:25,ts:1,cs:C,rn:I\nm:25,ts:3,cs:A7,rn:V7/ii\n"
        "m:26,ts:1,cs:Dm7,rn:ii7\n@key:G\nm:27,ts:1,cs:G,rn:I")
    text = hamon_to_humdrum(seq)
    assert text.splitlines()[:4] == ["**mxhm\t**harm", "*C:\t*C:", "=25\t=25", "C\tI"]
    assert "=26\t=26" in text and "*G:\t*G:" in text and "A7\tV7/ii" in text
    back = humdrum_to_hamon(text)
    assert [[l.layer for l in g.primary] for g in back.groups] == [["chord", "degree"]] * 4
    assert [g.position.measure for g in back.groups] == [25, 25, 26, 27]
    assert [(r.kind, r.key.tonic.note, r.from_group) for r in back.regions] == [
        ("key", "C", 0), ("modulation", "G", 3)]
    assert back.groups[1].primary[1].semantic.secondary == "ii"


def test_writer_single_layer_is_a_single_spine():
    from hamonpy.export import hamon_to_humdrum
    assert hamon_to_humdrum(parse_hamon_sequence("@fb\n6-5\n7")) == "**fb\n6-5\n7\n*-\n"
    assert hamon_to_humdrum(parse_hamon_sequence("@rn\n@key:D:minor\ni\nV")) == "**harm\n*d:\ni\nV\n*-\n"


def test_reader_key_tandem_is_a_region():
    seq = humdrum_to_hamon("**harm\n*B-:\nI\nV7\n*-\n")
    assert seq.regions and seq.regions[0].kind == "key"
    assert (seq.regions[0].key.tonic.note, seq.regions[0].key.tonic.accidental) == ("B", "flat")
    assert seq.regions[0].key.mode == "major"


def test_empty_when_no_harmony_spines():
    seq = humdrum_to_hamon("**kern\n4c\n4d\n*-\n")
    assert seq.groups == []


# ---------------------------------------------------------------------------
# Time-aligned positions (v0.2.1): numbered barlines → HarmonyGroup.position
# ---------------------------------------------------------------------------

MEASURED = "\n".join([
    "**harm",
    "I",          # before any barline → no measure
    "=1",
    "IV",         # measure 1
    "V7",         # measure 1
    "=2",
    "I",          # measure 2
    "*-",
]) + "\n"


def test_positions_from_numbered_barlines():
    seq = humdrum_to_hamon(MEASURED)
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "IV", "V", "I"]
    assert [g.position for g in seq.groups] == [
        None,                    # before the first barline
        Position(measure=1),
        Position(measure=1),
        Position(measure=2),
    ]


def test_positions_absent_without_numbered_barlines():
    # MULTI uses bare '=' barlines (no number) → measure-level position unavailable.
    seq = humdrum_to_hamon(MULTI)
    assert all(g.position is None for g in seq.groups)


# ---------------------------------------------------------------------------
# key_modulation_dataset encoding: **text Roman analysis + 'KEY=>:degree'
# ---------------------------------------------------------------------------

KM = "\n".join([
    "**kern\t**text",
    "*C:\t*",
    "4c\tC=>:I",
    "4c\tI",          # repeated on the next note onset → collapsed
    "4f\tIV",
    "=1\t=1",
    "4d\td=>:i",      # modulation to D minor
    "4d\ti",
    "4a\tV7",
    "*-\t*-",
]) + "\n"


def test_key_modulation_regions_and_degrees():
    seq = key_modulation_to_hamon(KM)
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "IV", "i", "V"]
    sig = [(r.kind, r.key.tonic.note, r.key.tonic.accidental, r.key.mode) for r in seq.regions]
    assert sig == [("key", "C", None, "major"), ("modulation", "D", None, "minor")]
    assert seq.regions[0].to_group == 1 and seq.regions[1].from_group == 2


def test_key_modulation_flat_key_dash():
    # Humdrum 'B-' = B-flat; lowercase = minor.
    seq = key_modulation_to_hamon("**kern\t**text\n4c\tB-=>:I\n*-\t*-\n")
    assert seq.regions[0].key.tonic.note == "B"
    assert seq.regions[0].key.tonic.accidental == "flat"
    assert seq.regions[0].key.mode == "major"


def test_key_modulation_empty_without_text_spine():
    assert key_modulation_to_hamon("**kern\n4c\n*-\n").groups == []
