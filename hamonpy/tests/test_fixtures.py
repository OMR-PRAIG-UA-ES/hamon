"""Data-driven fixture tests — mirrors the shared fixtures corpus.

Each fixture JSON is discovered automatically; each format source becomes a
separate parametrized test case.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import pytest

from hamonpy.adapters.formats import read_harmony_labels_from_file
from hamonpy.parse import parse_hamon_sequence

FIXTURES_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "fixtures")
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_fixture_jsons(root: str) -> List[str]:
    results: List[str] = []
    for dirpath, _dirs, files in os.walk(root):
        # fixtures/analysis/ holds v0.2.0 analytical-layer fixtures (model JSON + .hamon
        # + golden .expected.json), validated by the dedicated analysis suites.
        if os.path.basename(dirpath) == "analysis":
            continue
        for fn in files:
            if fn.endswith(".json") and not fn.startswith("._"):
                results.append(os.path.join(dirpath, fn))
    results.sort()
    return results


def _matches_object(actual: Any, expected: Any) -> bool:
    """Recursive toMatchObject-style check: every key in *expected* must exist
    in *actual* with a matching value; *actual* may have extra keys/attrs."""
    if isinstance(expected, dict):
        if isinstance(actual, dict):
            return all(
                k in actual and _matches_object(actual[k], v)
                for k, v in expected.items()
            )
        # Check dataclass / object attributes
        return all(
            hasattr(actual, k) and _matches_object(getattr(actual, k), v)
            for k, v in expected.items()
        )
    if isinstance(expected, list):
        if not isinstance(actual, (list, tuple)):
            return False
        if len(actual) < len(expected):
            return False
        return all(_matches_object(a, e) for a, e in zip(actual, expected))
    return actual == expected


# ---------------------------------------------------------------------------
# Collect parametrized cases
# ---------------------------------------------------------------------------

_TestCase = Tuple[str, str, str, str, str, Dict]  # (fixture_id, fmt, snippet_path, hint, src_hint, expected)

def _collect_cases() -> List[_TestCase]:
    cases: List[_TestCase] = []
    if not os.path.isdir(FIXTURES_ROOT):
        return cases
    for json_path in _find_fixture_jsons(FIXTURES_ROOT):
        fixture_dir = os.path.dirname(json_path)
        with open(json_path, encoding="utf-8") as fh:
            fx = json.load(fh)
        fixture_id = fx["id"]
        global_hint = fx.get("sequenceSystemHint", "")
        for fmt, src in fx.get("sources", {}).items():
            snippet_path = os.path.join(fixture_dir, src["file"])
            src_hint = src.get("sequenceSystemHint", global_hint)
            cases.append((fixture_id, fmt, snippet_path, src_hint, fx["expected"]))
    return cases


_CASES = _collect_cases()

_ids = [f"{c[0]}/{c[1]}" for c in _CASES]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fixtures_root_exists():
    assert os.path.isdir(FIXTURES_ROOT), f"Fixtures root not found: {FIXTURES_ROOT}"


def test_fixture_jsons_found():
    assert len(_find_fixture_jsons(FIXTURES_ROOT)) >= 38


@pytest.mark.parametrize("fixture_id,fmt,snippet_path,hint,expected", _CASES, ids=_ids)
def test_fixture_source(fixture_id: str, fmt: str, snippet_path: str, hint: str, expected: Dict):
    assert os.path.isfile(snippet_path), f"Snippet not found: {snippet_path}"

    labels = read_harmony_labels_from_file(fmt, snippet_path)
    assert labels, (
        f"[{fixture_id}/{fmt}] read_harmony_labels returned no labels from {snippet_path}"
    )

    hamon_input = "\n".join(labels)
    seq_text = f"@{hint}\n{hamon_input}" if hint else hamon_input
    seq = parse_hamon_sequence(seq_text)

    expected_groups = expected["groups"]
    assert len(seq.groups) >= len(expected_groups), (
        f"[{fixture_id}/{fmt}] expected ≥{len(expected_groups)} groups, got {len(seq.groups)}"
    )

    for gi, eg in enumerate(expected_groups):
        ag = seq.groups[gi]
        for li, exp_sem in enumerate(eg["primary"]):
            assert li < len(ag.primary), (
                f"[{fixture_id}/{fmt}] group {gi}: expected primary[{li}] but only {len(ag.primary)} items"
            )
            actual_sem = ag.primary[li].semantic
            assert actual_sem is not None, (
                f"[{fixture_id}/{fmt}] group {gi} primary[{li}]: semantic is None"
            )
            assert _matches_object(actual_sem, exp_sem), (
                f"[{fixture_id}/{fmt}] group {gi} primary[{li}] mismatch\n"
                f"  expected: {exp_sem}\n"
                f"  actual:   {actual_sem}"
            )
