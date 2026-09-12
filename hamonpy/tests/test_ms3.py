"""Tests for the ms3 adapter (hamonpy/adapters/ms3_adapter.py).

The DataFrame/dict bridge is tested without ms3 or MuseScore installed; the
file-loading path is exercised only when ms3 is available.
"""
from __future__ import annotations

import importlib.util

import pytest

from hamonpy.adapters.ms3_adapter import ms3_expanded_to_hamon, ms3_score_to_hamon

# An ms3 "expanded" table is a DataFrame; a list of row dicts stands in for it.
EXPANDED_ROWS = [
    {"quarterbeats": "0", "chord": "I", "numeral": "I", "localkey": "I", "globalkey": "C"},
    {"quarterbeats": "4", "chord": "V7", "numeral": "V", "figbass": "7", "localkey": "I", "globalkey": "C"},
    {"quarterbeats": "8", "chord": "I", "numeral": "I", "localkey": "I", "globalkey": "C"},
]


def test_expanded_rows_to_hamon():
    seq = ms3_expanded_to_hamon(EXPANDED_ROWS)
    assert [g.primary[0].semantic.degree for g in seq.groups] == ["I", "V", "I"]
    times = [(g.position.time.numerator, g.position.time.denominator) for g in seq.groups]
    assert times == [(0, 1), (4, 1), (8, 1)]


def test_accepts_to_csv_objects():
    class _FakeDataFrame:
        def to_csv(self, sep="\t", index=False):
            return (
                f"quarterbeats{sep}chord{sep}numeral{sep}localkey{sep}globalkey\n"
                f"0{sep}I{sep}I{sep}I{sep}C\n"
            )

    seq = ms3_expanded_to_hamon(_FakeDataFrame())
    assert seq.groups[0].primary[0].semantic.degree == "I"


def test_score_loader_without_ms3_raises_importerror():
    if importlib.util.find_spec("ms3") is not None:
        pytest.skip("ms3 is installed; ImportError path not exercised")
    with pytest.raises(ImportError):
        ms3_score_to_hamon("nonexistent.mscx")
