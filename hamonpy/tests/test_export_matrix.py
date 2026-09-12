"""Export matrix QA: every fixture surface must export to every target format.

`lossy_report` is allowed to report *loss* (that is its job — not every format can
carry every layer), but it must never crash and never fail to re-read its own
output (`rep.error is None`). This is the hub guarantee: any corpus that parses
can be pushed through any exporter.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hamonpy.parse import parse_hamon_sequence
from hamonpy.report import WRITERS, lossy_report

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
HAMON_FILES = sorted(FIXTURES.rglob("*.hamon"))


@pytest.mark.parametrize("target", WRITERS)
def test_every_fixture_exports_to(target: str):
    failures = []
    for path in HAMON_FILES:
        seq = parse_hamon_sequence(path.read_text(encoding="utf-8"))
        try:
            rep = lossy_report(seq, target)
        except Exception as e:  # noqa: BLE001 - collecting, not hiding
            failures.append(f"{path.name}: CRASH {type(e).__name__}: {e}")
            continue
        if rep.error is not None:
            failures.append(f"{path.name}: {rep.error}")
    assert not failures, f"{len(failures)} fixture(s) failed → {target}:\n" + "\n".join(failures[:10])
