"""The capability model: semantic vs text, and writers that really write their format.

The loss matrix reports what a format can say in its **own** vocabulary. Two things can
quietly break that claim, and both have happened, so both are pinned here:

1. Crediting a format for holding an opaque string. MEI's `<harm>` accepts any character
   data, so a HAMON label parked in it round-trips perfectly and says nothing about MEI.
2. A writer that does not write its format — LilyPond emitted a placeholder `c1` with
   the harmonies in `% hamon-surface:` comments, so its round-trip read our own comments
   back and reported the format as far more faithful than it is.
"""
from __future__ import annotations

import pytest

from pathlib import Path

from hamonpy.capability import (
    CAPABILITY, SEMANTIC_CAPABILITY, TEXT_CAPABILITY, capability_table_markdown,
    holds_as_text, native_loss,
)
from hamonpy.report import project_native
from hamonpy.serialize import sequence_to_dict, sequence_to_hamon_text

ROOT = Path(__file__).resolve().parents[2]
from hamonpy.cli import convert_text
from hamonpy.parse import parse_hamon_sequence
from hamonpy.report import WRITERS, write_to

_CS_SEQ = "@cs\nDm7\nG7\nCmaj7\nF"
_RN_SEQ = "@rn\n@key:C\nI\nvi\nii7\nV7"


def test_capability_is_the_semantic_table():
    assert CAPABILITY is SEMANTIC_CAPABILITY


def test_mei_does_not_claim_roman_semantically():
    """MEI holds Roman numerals as `<harm>` text, which is a workaround, not a vocabulary.

    Crediting it natively is what made the loss matrix report MEI as lossless for an
    analysis it cannot structurally express. Closing this for real means proposing a
    semantic HAMON encoding for MEI (STATUS.md → "New MEI harmony encoding")."""
    assert "roman" not in SEMANTIC_CAPABILITY["mei"]
    assert "roman" in holds_as_text("mei")
    assert "figuredbass" in SEMANTIC_CAPABILITY["mei"]  # <fb>/<f> IS structured


def test_text_capability_never_overlaps_the_semantic_one():
    for fmt, text_aspects in TEXT_CAPABILITY.items():
        assert not (text_aspects & SEMANTIC_CAPABILITY[fmt]), (
            f"{fmt}: an aspect cannot be both structured and text-only")


@pytest.mark.parametrize("fmt", [f for f in WRITERS])
def test_every_writer_emits_its_own_format(fmt: str):
    """No writer may depend on an embedded HAMON surface to round-trip.

    Each format is fed content its capability actually covers, then written in `native`
    mode — which strips the embedded surface before re-reading. A writer that only
    escrows returns nothing here."""
    cap = CAPABILITY.get(fmt, set())
    if "root" in cap:
        source = _CS_SEQ
    elif "roman" in cap:
        source = _RN_SEQ
    else:
        pytest.skip(f"{fmt} carries no label aspect natively (its labels are opaque text)")

    seq = parse_hamon_sequence(source)
    text = write_to(seq, fmt, mode="native")
    assert "hamon-surface" not in text, f"{fmt} still escrows the HAMON surface"
    assert len(convert_text(text, fmt).groups) >= len(seq.groups), (
        f"{fmt} loses its harmonies once the embedded HAMON surface is gone")


def test_humdrum_carries_key_and_applied_on_romans():
    """`**harm` spells `V7/ii` and a `*C:` tandem states the key — both native."""
    seq = parse_hamon_sequence("@rn\n@key:C\nI\nV7/ii\nii\nV7\nI")
    lost = native_loss(sequence_to_dict(seq), "@key:C", "humdrum")
    assert "key" not in lost and "applied" not in lost
    text = write_to(seq, "humdrum", mode="native")
    assert "*C:" in text and "V7/ii" in text
    back = convert_text(text, "humdrum")
    assert back.regions and back.regions[0].key.tonic.note == "C"


def test_documentation_table_is_the_model():
    """`documentation/index.md` shows the capability matrix; it is rendered from the
    table in `hamonpy/capability.py`, and this is what keeps the two from drifting."""
    doc = (ROOT / "documentation" / "index.md").read_text(encoding="utf-8")
    assert capability_table_markdown() in doc, (
        "documentation/index.md no longer matches hamonpy.capability — paste the output "
        "of capability_table_markdown() over the table")


def test_native_projection_keeps_what_the_writer_can_place():
    """Projecting to a format strips the aspects it cannot say and nothing else: a score
    format is handed the position and the layers, and only the writer decides."""
    seq = parse_hamon_sequence(
        "@meter:4/4\n@key:C\nm:3,ts:3,cs:A7[of:ii][scale:altered],rn:V7/ii[inv:1]\n"
        "melodic:F[NHT:passing][dur:1/2]")
    mei = sequence_to_hamon_text(project_native(seq, "mei"))
    assert "m:3,ts:3,cs:A7" in mei and "@key:" not in mei and "@meter:4/4" in mei
    assert "[of:" not in mei and "[scale:" not in mei and "rn:" not in mei
    assert "melodic:" not in mei                         # a tone is not an MEI harmony
    harte = project_native(seq, "harte")
    assert [l.surface for g in harte.groups for l in g.primary] == ["A7"]
    romantext = sequence_to_hamon_text(project_native(seq, "romantext"))
    assert "rn:V7/ii[inv:1]" in romantext and "cs:" not in romantext
    musicxml = sequence_to_hamon_text(project_native(seq, "musicxml"))
    assert "rn:V7[inv:1]" in musicxml                    # a numeral, but no applied target


def test_native_projection_remaps_regions_to_surviving_groups():
    seq = parse_hamon_sequence("@rn\n@key:C\nI\n@key:V\nI\nV7")
    seq = parse_hamon_sequence("@auto\n@key:C\nCmaj7\n@key:G\nI\nV7")
    # RomanText drops the chord symbol in group 0, so the G region moves to group 0.
    projected = project_native(seq, "romantext")
    assert len(projected.groups) == 2
    assert projected.regions and projected.regions[-1].key.tonic.note == "G"
    assert projected.regions[-1].from_group == 0


def test_applied_on_a_chord_symbol_is_hamon_only():
    """`A7[of:ii]` states chord *and* function on one label. Humdrum carries `applied` on
    a Roman numeral, but `**mxhm` has no way to say what A7 is the dominant of."""
    seq = parse_hamon_sequence("@cs\nDm7\nA7[of:ii]")
    d = sequence_to_dict(seq)
    assert native_loss(d, "", "humdrum")["applied"] == 1
    assert native_loss(d, "", "romantext")["applied"] == 1
    assert "applied" not in native_loss(d, "", "hamon")


def test_dcml_carries_a_metric_onset():
    """DCML places every row (`mn`/`mn_onset`/`quarterbeats`), and since the writer emits
    those columns the matrix must not charge DCML with losing an onset it holds."""
    from hamonpy.capability import POSITION_NATIVE, position_loss
    d = sequence_to_dict(parse_hamon_sequence("@rn\nm:1,ts:1,I\nm:2,ts:1,V"))
    assert "dcml" in POSITION_NATIVE
    assert position_loss(d, "dcml") == 0
    assert position_loss(d, "harte") == 2
