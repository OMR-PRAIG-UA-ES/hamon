"""ms3 adapter — drive Johannes Hentschel's ``ms3`` MuseScore parser into HAMON.

``ms3`` (https://johentsch.github.io/ms3) parses MuseScore 3/4 files
(``.mscx``/``.mscz``) without a lossy round-trip and extracts harmony labels
following the **DCML annotation standard**, producing *expanded* harmony tables
(a pandas DataFrame with ``chord``/``numeral``/``form``/``figbass``/``changes``/
``relativeroot``/``localkey``/``globalkey``/``quarterbeats``/``cadence``/… ).

This adapter bridges those tables into HAMON by delegating to the DCML expanded
adapter (:mod:`hamonpy.adapters.dcml_expanded`), so time alignment, regions and
cadence extraction all come for free:

  * :func:`ms3_score_to_hamon` — open a score with ms3 and convert its expanded
    harmonies (requires ``pip install ms3``; ms3 is an optional dependency).
  * :func:`ms3_expanded_to_hamon` — convert an already-extracted expanded table:
    a pandas DataFrame, anything with a ``to_csv`` method, or a list of row dicts
    (handy for testing without MuseScore/ms3 installed).
"""
from __future__ import annotations

import csv
import io
from typing import Any, List

from hamonpy.ast import HamonSequence
from hamonpy.adapters.dcml_expanded import (
    expanded_tsv_text_to_hamon,
    extract_cadences,
    extract_phrase_ends,
)

__all__ = [
    "ms3_score_to_hamon",
    "ms3_expanded_to_hamon",
    "extract_cadences",
    "extract_phrase_ends",
]


def _table_to_tsv(table: Any) -> str:
    """Render an expanded harmony table as DCML TSV text.

    Accepts a pandas DataFrame (or any object exposing ``to_csv``) or a list of
    row dicts (column order = keys of the first row).
    """
    if hasattr(table, "to_csv"):
        return table.to_csv(sep="\t", index=False)
    if isinstance(table, list):
        rows: List[dict] = [r for r in table if isinstance(r, dict)]
        if not rows:
            return ""
        fieldnames: List[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
    raise TypeError(
        "ms3_expanded_to_hamon expects a pandas DataFrame, an object with "
        f"to_csv(), or a list of row dicts — got {type(table).__name__}"
    )


def ms3_expanded_to_hamon(table: Any) -> HamonSequence:
    """Convert an ms3 *expanded* harmonies table to a time-aligned HamonSequence."""
    return expanded_tsv_text_to_hamon(_table_to_tsv(table))


def ms3_score_to_hamon(path: str) -> HamonSequence:
    """Open a MuseScore file with ms3 and convert its expanded harmonies.

    Requires the optional ``ms3`` dependency (``pip install ms3``). Raises
    :class:`ImportError` with install guidance when ms3 is unavailable.
    """
    try:
        import ms3  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without ms3
        raise ImportError(
            "ms3 is required for ms3_score_to_hamon(); install it with "
            "`pip install ms3` (see https://johentsch.github.io/ms3)."
        ) from exc

    score = ms3.Score(path)
    expanded = score.mscx.expanded  # DCML expanded harmonies DataFrame
    return ms3_expanded_to_hamon(expanded)
