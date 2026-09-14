"""Tests for the RomanText adapter (hamonpy/adapters/romantext.py)."""
from __future__ import annotations

from hamonpy.adapters.romantext import romantext_to_hamon
from hamonpy.ast import RomanSemantic

RT = """Composer: Test
Title: Demo
Time Signature: 4/4

m1 C: I b2 IV b3 V7
m2 vi b2 ii6 b3 V
m5-6 = m1-2
m7 G: I b2 V/V b3 V
m8 I
"""


def test_degrees_and_repeat_skipped():
    seq = romantext_to_hamon(RT)
    degrees = [g.primary[0].semantic.degree for g in seq.groups]
    assert degrees == ["I", "IV", "V", "vi", "ii", "V", "I", "V", "V", "I"]


def test_inline_key_changes_become_regions():
    seq = romantext_to_hamon(RT)
    sig = [(r.kind, r.key.tonic.note, r.key.mode) for r in seq.regions]
    assert sig == [("key", "C", "major"), ("modulation", "G", "major")]
    assert seq.regions[0].from_group == 0
    assert seq.regions[1].from_group == 6      # after the 6 C-major chords (m1+m2)


def test_minor_key_and_secondary():
    seq = romantext_to_hamon("m1 d: i b2 V65/iv")
    assert seq.regions[0].key.tonic.note == "D" and seq.regions[0].key.mode == "minor"
    sec = seq.groups[1].primary[0].semantic
    assert isinstance(sec, RomanSemantic) and sec.secondary == "iv"


def test_non_roman_token_kept_as_text():
    seq = romantext_to_hamon("m1 C: Cad64 b2 V")
    # 'Cad64' is not a Roman numeral; it is preserved as a text label.
    from hamonpy.ast import TextSemantic
    assert isinstance(seq.groups[0].primary[0].semantic, TextSemantic)
    assert seq.groups[0].primary[0].surface == "Cad64"


def test_headers_ignored():
    seq = romantext_to_hamon("Composer: X\nTitle: Y\n\nm1 C: I")
    assert len(seq.groups) == 1 and seq.groups[0].primary[0].semantic.degree == "I"


def test_positions_come_from_the_measure_and_beat_tokens():
    """RomanText states where each label is; reading it back must keep that."""
    seq = romantext_to_hamon("m1 b1 Eb: I b3 V6 b4.5 viio6/V\nm17 V7\n")
    assert [(g.position.measure, g.position.beat) for g in seq.groups] == [
        (1, 1.0), (1, 3.0), (1, 4.5), (17, 1.0),
    ]
