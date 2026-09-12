"""Tests for the partitura adapter (hamonpy/adapters/partitura_adapter.py).

All tests skip gracefully when partitura is not installed (optional dependency:
``pip install partitura``).
"""
from __future__ import annotations

import pytest

pt = pytest.importorskip("partitura", reason="partitura not installed; skipping")

import partitura.score as pscore  # noqa: E402

from hamonpy.adapters.partitura_adapter import (  # noqa: E402
    partitura_part_to_hamon,
    hamon_to_partitura_part,
)
from hamonpy.ast import RomanSemantic  # noqa: E402


def _roman_part():
    part = pscore.Part("P0", "test", quarter_duration=1)
    part.add(pscore.RomanNumeral("V65"), start=2, end=3)
    part.add(pscore.RomanNumeral("I"), start=0, end=1)
    return part


def test_part_to_hamon_orders_by_onset_and_parses_roman():
    seq = partitura_part_to_hamon(_roman_part(), system="rn")
    surfaces = [g.primary[0].surface for g in seq.groups]
    assert surfaces == ["I", "V65"]
    assert all(isinstance(g.primary[0].semantic, RomanSemantic) for g in seq.groups)
    # onsets recovered in quarters
    assert seq.groups[0].position.time.numerator == 0
    assert seq.groups[1].position.time.numerator == 2


def test_round_trip_hamon_to_partitura():
    seq = partitura_part_to_hamon(_roman_part(), system="rn")
    part = hamon_to_partitura_part(seq)
    harmonies = list(part.iter_all(pscore.Harmony, include_subclasses=True))
    texts = sorted(getattr(h, "text", "") for h in harmonies)
    assert texts == ["I", "V65"]
