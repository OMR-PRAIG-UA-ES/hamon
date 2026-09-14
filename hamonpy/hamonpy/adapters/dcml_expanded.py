"""DCML *expanded*-harmonies adapter — Johannes Hentschel's time-aligned standard.

This targets the **expanded** harmony TSV tables of the DCML harmony annotation
standard (Hentschel, Neuwirth & Rohrmeier) — e.g. *"The Annotated Mozart
Sonatas: Score, Harmony, and Cadence"* (TISMIR 2021,
https://doi.org/10.5334/tismir.63) and the *Annotated Corpus of Tonal Piano
Music from the Long 19th Century* — and the tables emitted by ``ms3`` (see
``ms3_adapter.py``).

It builds on the plain DCML adapter (:mod:`hamonpy.adapters.dcml`): the
chord-surface and localkey/relativeroot → :class:`TonalRegion` logic is shared
and unchanged. What this module adds is what makes the Hentschel corpora
distinctive over a bare chord list:

  * **Time alignment** — every chord group gets a :class:`Position` from the
    ``quarterbeats`` column (an absolute offset in quarter notes from the start
    of the piece, often written as a fraction like ``"129/2"``), falling back to
    the ``mc``/``mn`` measure number plus ``mn_onset``.
  * **Extent** — when the table states ``duration_qb`` (the annotated length in
    quarters), it lands on the label as ``attributes.duration``. Absent means unknown;
    the rule that a harmony runs to the next one is a computation, never stored.
  * **Cadences** (``cadence`` column: PAC/IAC/HC/DC/EC/…) and **phrase ends**
    (``phraseend`` column: ``{`` / ``}`` / ``}{``) are recognised and exposed via
    :func:`extract_cadences` / :func:`extract_phrase_ends`. HAMON's AST has no
    cadence node yet, so they are returned alongside the sequence rather than
    folded into groups (future work — see ``documentation/dcml.md``).

HAMON does not redistribute the corpora; see ``datasets/manifest.json``.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from fractions import Fraction as _Fraction
from typing import List, Optional, Tuple

from hamonpy.ast import Fraction, HamonSequence, HarmonyAttributes, Position
from hamonpy.adapters.dcml import (
    _dcml_row_to_surface,
    _dcml_surface_to_roman,
    dcml_tsv_text_to_hamon,
)


# ---------------------------------------------------------------------------
# Side-channel records (no HAMON AST node yet)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Cadence:
    """A DCML ``cadence`` annotation (e.g. ``PAC``, ``HC``) at a position."""
    type: str
    position: Optional[Position] = None


@dataclass(frozen=True)
class PhraseBoundary:
    """A DCML ``phraseend`` marker (``{`` open, ``}`` close, ``}{`` both)."""
    marker: str
    position: Optional[Position] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rows(data: str) -> List[dict]:
    """Read DCML TSV (text or file path) into a list of row dicts."""
    text = data
    if isinstance(data, str) and "\n" not in data and data.strip().endswith((".tsv", ".csv")):
        with open(data, encoding="utf-8") as fh:
            text = fh.read()
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def _parse_fraction(s: str) -> Optional[_Fraction]:
    s = (s or "").strip()
    if not s or s == ".":
        return None
    try:
        return _Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


def _beat_unit(row: dict) -> int:
    """How many beats there are to a whole note, from the row's ``timesig``.

    DCML writes within-measure onsets as fractions **of a whole note**, so turning
    one into a beat number needs the beat unit: 4 in 4/4 or 3/4, 8 in 6/8. Simple
    meters only — a compound meter's beat is the dotted unit, which this does not
    model, so 6/8 counts eighths. Defaults to quarters when the row is silent.
    """
    timesig = (row.get("timesig") or "").strip()
    if "/" in timesig:
        try:
            return int(timesig.split("/", 1)[1])
        except ValueError:
            pass
    return 4


def _row_measure_beat(row: dict) -> Tuple[Optional[int], Optional[float]]:
    """Measure number and 1-based beat from ``mc``/``mn`` + ``mn_onset``, if stated."""
    measure_raw = (row.get("mn") or row.get("mc") or "").strip()
    if not measure_raw:
        return None, None
    try:
        measure = int(measure_raw)
    except ValueError:
        return None, None
    onset = _parse_fraction(row.get("mn_onset") or row.get("mc_onset") or "")
    if onset is None:
        return measure, None
    return measure, float(onset) * _beat_unit(row) + 1.0


def _row_position(row: dict) -> Optional[Position]:
    """Best-effort :class:`Position` for one DCML row.

    An expanded table states the position twice: ``quarterbeats`` is an absolute
    offset from the start of the piece, and ``mc``/``mn`` + ``mn_onset`` say the
    same thing as a measure and a beat within it. Both are kept — the absolute
    offset is what aligns two analyses of the same piece, the measure and beat
    are what a musician reads — so a row that carries both yields both.
    """
    measure, beat = _row_measure_beat(row)
    qb = _parse_fraction(row.get("quarterbeats", ""))
    if qb is not None:
        return Position(measure=measure, beat=beat,
                        time=Fraction(numerator=qb.numerator, denominator=qb.denominator))
    if measure is not None:
        return Position(measure=measure, beat=beat)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def expanded_tsv_text_to_hamon(text: str) -> HamonSequence:
    """Convert expanded DCML TSV text to a time-aligned HamonSequence.

    Chords and tonal regions are produced by the shared DCML adapter; each
    resulting group is annotated with a :class:`Position` from its source row
    (rows are matched in order, using the same chord-row filter as the DCML
    adapter so positions line up with groups).
    """
    seq = dcml_tsv_text_to_hamon(text)

    rows: List[dict] = []
    for row in _rows(text):
        surface = _dcml_row_to_surface(row)
        if surface is None or _dcml_surface_to_roman(surface) is None:
            continue
        rows.append(row)

    for group, row in zip(seq.groups, rows):
        pos = _row_position(row)
        if pos is not None:
            group.position = pos
        # `duration_qb` is the annotated extent, in quarters — the same unit as
        # `quarterbeats` and as HAMON's `time`. Only read when the table states it.
        extent = _parse_fraction(row.get("duration_qb", ""))
        if extent is not None and group.primary:
            label = group.primary[0]
            duration = Fraction(numerator=extent.numerator, denominator=extent.denominator)
            label.attributes = (replace(label.attributes, duration=duration)
                                if label.attributes else HarmonyAttributes(duration=duration))
    return seq


def expanded_tsv_to_hamon(path: str) -> HamonSequence:
    """Convert an expanded DCML TSV *file* to a time-aligned HamonSequence."""
    with open(path, encoding="utf-8") as fh:
        return expanded_tsv_text_to_hamon(fh.read())


def extract_cadences(data: str) -> List[Cadence]:
    """Return the ``cadence`` annotations (with positions) from expanded TSV."""
    out: List[Cadence] = []
    for row in _rows(data):
        cad = (row.get("cadence") or "").strip()
        if cad and cad != ".":
            out.append(Cadence(type=cad, position=_row_position(row)))
    return out


def extract_phrase_ends(data: str) -> List[PhraseBoundary]:
    """Return the ``phraseend`` markers (with positions) from expanded TSV."""
    out: List[PhraseBoundary] = []
    for row in _rows(data):
        marker = (row.get("phraseend") or "").strip()
        if marker and marker != ".":
            out.append(PhraseBoundary(marker=marker, position=_row_position(row)))
    return out
