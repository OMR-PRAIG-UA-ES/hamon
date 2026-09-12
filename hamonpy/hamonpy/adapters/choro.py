"""Adapter for the DCML *Choro Songbook Corpus* (github.com/DCMLab/choro).

The corpus describes the same music **twice**, which is exactly why HAMON is useful
here — it makes the two representations comparable:

* ``choro.tsv`` — every piece merged into one table, **one row per chord onset**,
  with the chord in three encodings (``chord`` absolute, ``rn_chord`` Roman, ``harte``
  Harte) plus ``local_key``, ``bar_no`` and the form columns (``phrase``/``part``),
  keyed by ``filename``.
* ``transcriptions/<piece>.txt`` — a compact **form grammar**:

  ``P<n>: bar | bar | …``   a *phrase*: bars split by ``|``; an empty bar or ``.``
  holds the previous chord; a bar may hold several space-separated chords.
  ``PartX[key]: $P1 $P2``   a *part*: a sequence of ``$``-references.
  ``S[key, meter]: $Intro $PartA …``   the *song*: parts/phrases in order,
  where ``$ref*N`` repeats a reference ``N`` times.

Expanding the song grammar to its flat chord-onset sequence should reproduce the
``chord`` column of the TSV — the consistency check in ``use-cases/choro/``.

This adapter only parses; the cross-checks (transcription↔TSV, chord↔Harte↔Roman)
live in the use-case, built on the parsed models.
"""
from __future__ import annotations

import csv
import io
import re
from collections import OrderedDict
from typing import Dict, List

from hamonpy.ast import HamonSequence, HarmonyGroup, Position
from hamonpy.parse import parse_hamon_sequence
from hamonpy.adapters.harte import harte_text_to_hamon


# Brazilian songbook notation writes a major seventh as `7M` (e.g. `Bb7M`,
# `C7M(#11)`); HAMON's chord grammar spells it `maj7`.
def normalize_chord(chord: str) -> str:
    """Map corpus chord glyphs to HAMON surface syntax (``7M`` → ``maj7``)."""
    return re.sub(r"7M", "maj7", chord.strip())


# ---------------------------------------------------------------------------
# transcriptions/<piece>.txt — the form grammar
# ---------------------------------------------------------------------------

_REF = re.compile(r"^\$(\w+)(?:\*(\d+))?$")


def _parse_definitions(text: str) -> "OrderedDict[str, str]":
    """`LABEL[annot]: BODY` lines → {label: body} (the `[...]` annotation dropped)."""
    defs: "OrderedDict[str, str]" = OrderedDict()
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        label, body = line.split(":", 1)
        label = re.sub(r"\[.*?\]", "", label).strip()
        defs[label] = body.strip()
    return defs


def _expand(label: str, defs: Dict[str, str], seen: tuple = ()) -> List[str]:
    if label in seen or label not in defs:  # guard against reference cycles
        return []
    body = defs[label]
    out: List[str] = []
    if "$" in body:  # a reference sequence (a Part, or the song S)
        for token in body.split():
            m = _REF.match(token)
            if m:
                out += _expand(m.group(1), defs, seen + (label,)) * int(m.group(2) or 1)
    else:  # a phrase: bars split by "|", chords split by whitespace
        for bar in body.split("|"):
            out += bar.split()
    return out


def expand_transcription(text: str, top: str = "S") -> List[str]:
    """Flat chord-onset surfaces of a `.txt` transcription (the song, expanded).

    Empty bars and ``.`` hold the previous chord, so they are resolved to that
    chord — giving one surface per onset, aligned with the TSV's ``chord`` column.
    """
    defs = _parse_definitions(text)
    onsets = _expand(top, defs)
    resolved: List[str] = []
    prev = None
    for chord in onsets:
        chord = prev if chord == "." else chord
        resolved.append(chord)
        prev = chord
    return resolved


def transcription_to_hamon(text: str) -> HamonSequence:
    """Parse a `.txt` transcription into a HamonSequence of chord symbols."""
    surfaces = [normalize_chord(c) for c in expand_transcription(text)]
    body = "\n".join(surfaces)
    return parse_hamon_sequence("@cs\n" + body) if body else HamonSequence(groups=[])


# ---------------------------------------------------------------------------
# choro.tsv — the merged table
# ---------------------------------------------------------------------------

def read_tsv(text: str) -> "OrderedDict[str, List[dict]]":
    """Group the merged ``choro.tsv`` rows by piece (``filename``), in file order."""
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    pieces: "OrderedDict[str, List[dict]]" = OrderedDict()
    for row in reader:
        pieces.setdefault(row["filename"], []).append(row)
    return pieces


_COLUMN_SYSTEM = {"chord": "cs", "rn_chord": "rn", "harte": "harte"}


def tsv_piece_to_hamon(rows: List[dict], column: str = "chord") -> HamonSequence:
    """One piece's rows → HamonSequence, from the chosen encoding column.

    ``column`` is ``chord`` (absolute chord symbols, the default), ``rn_chord``
    (Roman numerals) or ``harte`` (Harte). Each group keeps the ``bar_no`` as its
    position.
    """
    if column not in _COLUMN_SYSTEM:
        raise ValueError(f"column must be one of {sorted(_COLUMN_SYSTEM)}; got {column!r}")
    surfaces = [r[column].strip() for r in rows if r.get(column, "").strip()]
    if column == "harte":
        seq = harte_text_to_hamon("\n".join(surfaces))
    else:
        prefix = "@" + _COLUMN_SYSTEM[column]
        norm = surfaces if column == "rn_chord" else [normalize_chord(s) for s in surfaces]
        seq = parse_hamon_sequence(prefix + "\n" + "\n".join(norm)) if norm else HamonSequence(groups=[])
    # attach bar positions (best-effort; some rows may lack a numeric bar_no)
    for group, row in zip(seq.groups, rows):
        bar = row.get("bar_no", "")
        if bar and str(bar).strip().lstrip("-").isdigit():
            group.position = Position(measure=int(float(bar)))
    return seq
