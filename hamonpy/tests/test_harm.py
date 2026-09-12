"""Tests for the Humdrum **harm adapter (hamonpy.adapters.harm)."""
from __future__ import annotations

from hamonpy.adapters.harm import harm_token_to_roman, harm_to_hamon


def test_letter_inversions_to_figured_bass():
    assert harm_token_to_roman("I") == "I"
    assert harm_token_to_roman("Ib") == "I6"
    assert harm_token_to_roman("Ic") == "I64"
    assert harm_token_to_roman("V7") == "V7"
    assert harm_token_to_roman("V7b") == "V65"
    assert harm_token_to_roman("V7d") == "V42"


def test_quality_markers():
    assert harm_token_to_roman("viio") == "vii°"
    assert harm_token_to_roman("viioD7") == "vii°7"      # o + seventh → fully-dim 7
    assert harm_token_to_roman("viih7") == "viiø7"       # half-diminished
    assert harm_token_to_roman("V+") == "V+"


def test_accidentals_secondary_and_neapolitan():
    assert harm_token_to_roman("V7/V") == "V7/V"
    assert harm_token_to_roman("viioD7/ii") == "vii°7/ii"
    assert harm_token_to_roman("N") == "bII"
    assert harm_token_to_roman("Nb") == "bII6"


def test_recip_prefix_and_parens_stripped():
    # TAVERN duration prefix + Haydn parentheses
    assert harm_token_to_roman("4I") == "I"
    assert harm_token_to_roman("2.V7b") == "V65"
    assert harm_token_to_roman("(Ic)") == "I64"


def test_standard_figured_roman_passes_through():
    assert harm_token_to_roman("V65") == "V65"
    assert harm_token_to_roman("bII6") == "bII6"


def test_non_harmony_tokens_return_none():
    assert harm_token_to_roman(".") is None
    assert harm_token_to_roman("") is None


def test_harm_to_hamon_spine_with_key_and_barlines():
    doc = "\n".join([
        "**harm\t**kern",
        "*f:\t*",
        "i\t4F",
        "=2\t=2",
        "V7b\t4G",
        "*G:\t*",          # modulation
        "I\t4g",
        "*-\t*-",
    ])
    seq = harm_to_hamon(doc)
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["i", "V65", "I"]
    assert seq.sequence_system_hint == "rn"
    # home key f minor, modulation to G major
    assert seq.regions[0].kind == "key" and seq.regions[0].key.tonic.note == "F"
    assert seq.regions[0].key.mode == "minor"
    assert seq.regions[1].kind == "modulation" and seq.regions[1].key.tonic.note == "G"
    # measure position picked up from the barline
    assert seq.groups[1].position.measure == 2


def test_flat_secondary_attaches_to_semantic():
    seq = harm_to_hamon("**harm\nV7/-II\n*-\n")
    label = seq.groups[0].primary[0]
    assert label.semantic.kind == "roman"
    assert label.semantic.secondary == "bII"
    assert label.surface == "V7/bII"
