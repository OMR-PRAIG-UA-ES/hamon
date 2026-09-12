"""Corpus QA: the fixture .hamon files must stay exemplary.

Every fixture surface must parse without errors, carry no opaque (text-kind)
labels — a fixture whose label falls back to text is either a parser gap or a
typo in the fixture — and declare no positions outside its meter. (Legitimate
*text* harmonies would be added to the allowlist below.)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hamonpy.parse import parse_hamon_sequence
from hamonpy.validate import validate_positions

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

#: Fixtures whose surfaces intentionally contain opaque text labels.
OPAQUE_ALLOWLIST: set[str] = set()

HAMON_FILES = sorted(FIXTURES.rglob("*.hamon"))


def test_corpus_is_nonempty():
    assert len(HAMON_FILES) > 20


@pytest.mark.parametrize("path", HAMON_FILES, ids=lambda p: str(p.relative_to(FIXTURES)))
def test_fixture_surface_is_exemplary(path: Path):
    seq = parse_hamon_sequence(path.read_text(encoding="utf-8"))

    assert validate_positions(seq) == []

    if str(path.relative_to(FIXTURES)) in OPAQUE_ALLOWLIST:
        return
    opaque = [
        lab.surface
        for g in seq.groups
        for lab in [*g.primary, *(lab for alt in g.alternatives for lab in alt)]
        if lab.semantic.kind == "text"
    ]
    assert opaque == [], f"opaque (text) labels in {path.name}: {opaque}"
