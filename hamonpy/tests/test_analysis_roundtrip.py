"""Data-driven round-trip suite for the analytical layer (Python side).

Parses every fixtures/analysis/<id>.hamon surface file and compares it against the
checked-in golden <id>.expected.json — the canonical semantics any implementation
of the standard must reproduce, so these also pin conformance on whole sequences.
"""

import dataclasses
import json
import re
from pathlib import Path

import pytest

from hamonpy.parse import parse_hamon_sequence

ANALYSIS_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "analysis"


def _camel(key: str) -> str:
    return re.sub(r"_([a-z])", lambda m: m.group(1).upper(), key)


def to_canonical(value):
    """Recursively: dataclasses→dicts, snake_case→camelCase keys, drop None/empty, so the
    Python AST serializes to the same shape as the TS (camelCase) AST."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        out = {}
        for key in value:
            cv = to_canonical(value[key])
            if cv is None:
                continue
            if isinstance(cv, (list, dict)) and len(cv) == 0:
                continue
            out[_camel(key)] = cv
        return out
    if isinstance(value, (list, tuple)):
        return [to_canonical(v) for v in value]
    return value


_HAMON_FILES = sorted(ANALYSIS_DIR.glob("*.hamon"))


def test_hamon_for_every_model_fixture():
    json_ids = sorted(
        p.stem for p in ANALYSIS_DIR.glob("*.json") if not p.name.endswith(".expected.json")
    )
    hamon_ids = sorted(p.stem for p in _HAMON_FILES)
    assert hamon_ids == json_ids


@pytest.mark.parametrize("hamon_path", _HAMON_FILES, ids=lambda p: p.stem)
def test_surface_roundtrip(hamon_path: Path):
    surface = hamon_path.read_text()
    parsed = to_canonical(parse_hamon_sequence(surface))
    golden = json.loads((ANALYSIS_DIR / f"{hamon_path.stem}.expected.json").read_text())
    assert parsed == golden
