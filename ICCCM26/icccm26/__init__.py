"""ICCCM26 — HAMON as a lossless harmony interlingua (poster companion code).

This small package takes a handful of representative harmony examples (a layered
chord-symbol + Roman analysis, a Roman-numeral / DCML analysis, figured bass,
Nashville numbers, plus a synthetic "pangram") and asks, of every supported
encoding, what it cannot say about them in its own vocabulary — aspect by aspect,
from the capability table in ``hamonpy.capability``. That count is HAMON's
*explainable encoding* (xencoding): loss you can point at and name.

Each example is also round-tripped through every writer (``hamonpy.report``); that
number travels alongside as writer health, not as the headline.

Public API:
    from icccm26.roundtrip import analyze_all, analyze_example
    from icccm26.figure import build_figures
"""

from .roundtrip import analyze_all, analyze_example, ExampleResult, TargetResult

__all__ = ["analyze_all", "analyze_example", "ExampleResult", "TargetResult"]
