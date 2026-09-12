"""Execute the use-cases/notebooks/ tours so the worked stories can't bit-rot.

The tours are jupytext ``.py:percent`` files — valid Python — so we run them as
plain scripts (no notebook kernel needed). Tours that need an optional dependency
declare it via a module-level ``REQUIRES`` marker in a comment; we skip them when
the dependency is missing.
"""

import importlib.util
import runpy
from pathlib import Path

import pytest

NOTEBOOKS = Path(__file__).resolve().parents[2] / "use-cases" / "notebooks"
_TOURS = sorted(NOTEBOOKS.glob("*.py"))

# Tours whose execution needs an optional dependency.
_OPTIONAL_DEPS = {"02_dcml_ms3_tour.py": "ms3", "03_flexohr_tour.py": "flexohr"}


def test_tours_present():
    assert len(_TOURS) >= 2, f"expected notebook tours under {NOTEBOOKS}"


@pytest.mark.parametrize("path", _TOURS, ids=lambda p: p.stem)
def test_tour_runs(path: Path):
    dep = _OPTIONAL_DEPS.get(path.name)
    if dep and importlib.util.find_spec(dep) is None:
        pytest.skip(f"{path.name} needs optional dependency {dep!r}")
    # Runs every cell top-to-bottom; the inline asserts in each tour are the checks.
    runpy.run_path(str(path), run_name="__main__")
