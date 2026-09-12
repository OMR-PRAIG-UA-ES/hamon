"""DiLeMMa *pitch-array* adapter — the note-level training tables of ``dilemmadata``.

`dilemmadata <https://github.com/johentsch/dilemmadata>`_ (Johannes Hentschel) is the
data infrastructure behind the AnalysisGNN multitask analysis models. It ships **pitch
arrays**: TSV tables where *one row is one note* and the analytical annotations are
repeated on every note they cover. Harmony is therefore not a list of labels here — it
is a column, and its rhythm is a flag on the note grid.

Two dialects live side by side in ``pitch_arrays/``, and this module reads both:

``DLC`` (``pitch_arrays/DLC/<subcorpus>/*.tsv``)
    Derived from the Distant Listening Corpus, so the label columns are plain DCML
    (``chord``, ``numeral``, ``form``, ``figbass``, ``changes``, ``relativeroot``,
    ``localkey``, ``globalkey``) plus ``cadence`` / ``phraseend`` / ``pedal``. Notes
    are tied to their harmony by ``unfolded_harmony_index``, and positioned by
    ``quarterbeats_playthrough``.

``AN`` (``pitch_arrays/AN/{training,validation,test}/*_joint.tsv``)
    Derived from AugmentedNet (Nápoles López et al.), so the label columns are that
    project's (``a_romanNumeral``, ``a_localKey``, ``a_tonicizedKey``, ``a_duration``,
    …), grouped by ``a_annotationNumber``. Keys are **absolute** and written
    music21-style (``B-`` = B flat); they are converted to DCML's relative degrees
    here so both dialects reach HAMON through the same path. AugmentedNet's ``Cad``
    (cadential six-four) is written as DCML's ``V(64)``.
    The companion ``*_slices.tsv`` files carry no harmony and are not read.

The strategy is to **collapse** the note grid back to one row per harmony and hand the
result to the DCML *expanded* adapter (:mod:`hamonpy.adapters.dcml_expanded`), so
chord surfaces, tonal regions and positions are produced by exactly the same code as
for the corpora these arrays were derived from.

What the pitch arrays add over those corpora is **harmonic rhythm**: the AN dialect
states each harmony's duration outright (``a_duration``), and in the DLC dialect it
follows from consecutive onsets. HAMON's :class:`~hamonpy.ast.Position` is onset-only,
so durations are returned on the side by :func:`extract_spans` rather than folded into
the sequence (same treatment as cadences and phrase ends — see ``documentation/dcml.md``).

HAMON does not redistribute the corpora; see ``datasets/manifest.json``.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from fractions import Fraction as _Fraction
from typing import Dict, List, Optional

from hamonpy.ast import Fraction, HamonSequence, Key, Position
from hamonpy.adapters.dcml import (
    _dcml_row_to_surface,
    _dcml_surface_to_roman,
    _parse_dcml_global_key,
)
from hamonpy.adapters.dcml_expanded import (
    Cadence,
    PhraseBoundary,
    _parse_fraction,
    _row_position,
    _rows,
    expanded_tsv_text_to_hamon,
)
from hamonpy.normalize import pitch_to_degree

#: The DCML-expanded columns a collapsed row carries (the order they are written in).
_COLLAPSED_FIELDS = [
    "quarterbeats", "mn", "mn_onset",
    "chord", "numeral", "form", "figbass", "changes", "relativeroot",
    "localkey", "globalkey", "pedal", "cadence", "phraseend", "duration_qb",
]

#: AugmentedNet Roman numerals that are not DCML surfaces, and their DCML spelling.
_AN_SURFACE_ALIASES = {"Cad": "V(64)", "Cad64": "V(64)"}


# ---------------------------------------------------------------------------
# Side-channel records (no HAMON AST node yet)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HarmonySpan:
    """How long one harmony lasts — the harmonic rhythm HAMON cannot yet encode.

    ``duration`` is in quarter notes, like ``quarterbeats``; it is ``None`` for the
    last harmony of a DLC piece, whose end the pitch array does not state. ``source``
    is ``"explicit"`` when the corpus gives the duration (AN's ``a_duration``) and
    ``"derived"`` when it was computed from the next harmony's onset (DLC).
    """
    position: Optional[Position]
    duration: Optional[Fraction]
    source: str


# ---------------------------------------------------------------------------
# Dialect detection
# ---------------------------------------------------------------------------

def detect_dialect(fieldnames) -> Optional[str]:
    """``"dlc"``, ``"an"`` or ``None`` for the given pitch-array column names."""
    cols = set(fieldnames or ())
    if "unfolded_harmony_index" in cols:
        return "dlc"
    if "a_annotationNumber" in cols and "a_romanNumeral" in cols:
        return "an"
    return None


def looks_like_pitch_array(head: str) -> bool:
    """True when *head* (the first bytes of a TSV) is a DiLeMMa pitch array."""
    first = head.lstrip().split("\n", 1)[0]
    return detect_dialect(first.split("\t")) is not None


# ---------------------------------------------------------------------------
# Collapsing the note grid to one row per harmony
# ---------------------------------------------------------------------------

def _blank(value: Optional[str]) -> str:
    v = (value or "").strip()
    return "" if v in (".", "None", "nan") else v


def _first_per_group(rows: List[dict], key: str) -> List[dict]:
    """The first row of each run of *key* (the harmony index/number), in order."""
    out: List[dict] = []
    seen = None
    for row in rows:
        value = _blank(row.get(key))
        if not value or value == seen:
            continue
        out.append(row)
        seen = value
    return out


def _collapse_dlc(rows: List[dict]) -> List[dict]:
    collapsed: List[dict] = []
    for row in _first_per_group(rows, "unfolded_harmony_index"):
        beat = _parse_fraction(_blank(row.get("beat_float")))
        collapsed.append({
            # ``_row_position`` reads mn_onset as a 0-based beat offset, so beat_float - 1
            # gives back the pitch array's own 1-based beat.
            "quarterbeats": _blank(row.get("quarterbeats_playthrough")),
            "mn": _blank(row.get("mn")) or _blank(row.get("mc")),
            "mn_onset": str(beat - 1) if beat is not None else "",
            "chord": _blank(row.get("chord")),
            "numeral": _blank(row.get("numeral")),
            "form": _blank(row.get("form")),
            "figbass": _blank(row.get("figbass")),
            "changes": _blank(row.get("changes")),
            "relativeroot": _blank(row.get("relativeroot")),
            "localkey": _blank(row.get("localkey")),
            "globalkey": _blank(row.get("globalkey")),
            "pedal": _blank(row.get("pedal")),
            "cadence": _blank(row.get("cadence")) or _blank(row.get("cadence_type")),
            "phraseend": _blank(row.get("phraseend")),
            "duration_qb": "",
        })
    return collapsed


def _m21_key_name(name: str) -> str:
    """music21 key spelling → DCML's (``B-`` → ``Bb``); case still carries the mode."""
    return _blank(name).replace("-", "b")


def _an_key(name: str) -> Optional[Key]:
    return _parse_dcml_global_key(_m21_key_name(name))


def _collapse_an(rows: List[dict]) -> List[dict]:
    collapsed: List[dict] = []
    global_key: Optional[Key] = None
    global_name = ""

    for row in _first_per_group(rows, "a_annotationNumber"):
        surface = _blank(row.get("a_romanNumeral"))
        surface = _AN_SURFACE_ALIASES.get(surface, surface)

        local_key = _an_key(row.get("a_localKey", ""))
        if global_key is None and local_key is not None:
            # AugmentedNet numerals are relative to the local key; the first one is
            # the piece's home key, which is what DCML calls the globalkey.
            global_key, global_name = local_key, _m21_key_name(row.get("a_localKey", ""))

        localkey = ""
        if global_key is not None and local_key is not None:
            localkey = pitch_to_degree(global_key, local_key.tonic, local_key.mode)

        relativeroot = ""
        tonicized = _an_key(row.get("a_tonicizedKey", ""))
        if (local_key is not None and tonicized is not None
                and _m21_key_name(row.get("a_tonicizedKey", "")) != _m21_key_name(row.get("a_localKey", ""))):
            relativeroot = pitch_to_degree(local_key, tonicized.tonic, tonicized.mode)

        collapsed.append({
            "quarterbeats": _blank(row.get("j_offset")),
            "mn": _blank(row.get("a_measure")),
            "mn_onset": _blank(row.get("mn_onset")),
            "chord": surface,
            "numeral": _blank(row.get("a_simpleNumeral")),
            "form": "",
            "figbass": "",
            "changes": "",
            "relativeroot": relativeroot,
            "localkey": localkey,
            "globalkey": global_name,
            "pedal": "",
            "cadence": "",
            "phraseend": "",
            "duration_qb": _blank(row.get("a_duration")),
        })
    return collapsed


def collapse(data: str) -> List[dict]:
    """Read a pitch array (text or file path) as one DCML-expanded row per harmony."""
    rows = _rows(data)
    dialect = detect_dialect(rows[0].keys() if rows else ())
    if dialect == "dlc":
        return _collapse_dlc(rows)
    if dialect == "an":
        return _collapse_an(rows)
    raise ValueError(
        "not a DiLeMMa pitch array: expected an 'unfolded_harmony_index' (DLC) or "
        "'a_annotationNumber' (AugmentedNet) column"
    )


def collapsed_to_tsv(rows: List[dict]) -> str:
    """Serialize collapsed rows as DCML *expanded* TSV text."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_COLLAPSED_FIELDS, delimiter="\t",
                            lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pitch_array_text_to_hamon(text: str) -> HamonSequence:
    """Convert pitch-array TSV text to a time-aligned HamonSequence.

    One group per harmony (not per note), positioned by its onset, with the tonal
    regions the DCML adapter derives from ``localkey`` / ``relativeroot``.
    """
    return expanded_tsv_text_to_hamon(collapsed_to_tsv(collapse(text)))


def pitch_array_to_hamon(path: str) -> HamonSequence:
    """Convert a pitch-array TSV *file* to a time-aligned HamonSequence."""
    with open(path, encoding="utf-8") as fh:
        return pitch_array_text_to_hamon(fh.read())


def extract_cadences(data: str) -> List[Cadence]:
    """The ``cadence`` annotations of a pitch array (DLC dialect only)."""
    rows = collapse(data)
    return [Cadence(type=r["cadence"], position=_row_position(r))
            for r in rows if r.get("cadence")]


def extract_phrase_ends(data: str) -> List[PhraseBoundary]:
    """The ``phraseend`` markers of a pitch array (DLC dialect only)."""
    rows = collapse(data)
    return [PhraseBoundary(marker=r["phraseend"], position=_row_position(r))
            for r in rows if r.get("phraseend")]


def extract_spans(data: str) -> List[HarmonySpan]:
    """The onset **and duration** of every harmony, index-aligned with the groups of
    :func:`pitch_array_text_to_hamon`.

    Rows are filtered exactly as the DCML adapter filters them, so ``spans[i]`` is the
    span of ``sequence.groups[i]``.
    """
    rows = [r for r in collapse(data)
            if (s := _dcml_row_to_surface(r)) is not None and _dcml_surface_to_roman(s) is not None]

    onsets = [_parse_fraction(r.get("quarterbeats", "")) for r in rows]
    spans: List[HarmonySpan] = []
    for i, row in enumerate(rows):
        explicit = _parse_fraction(row.get("duration_qb", ""))
        if explicit is not None:
            duration, source = explicit, "explicit"
        else:
            nxt = onsets[i + 1] if i + 1 < len(onsets) else None
            here = onsets[i]
            duration = (nxt - here) if (nxt is not None and here is not None) else None
            source = "derived"
        spans.append(HarmonySpan(
            position=_row_position(row),
            duration=_to_fraction(duration),
            source=source,
        ))
    return spans


def _to_fraction(value: Optional[_Fraction]) -> Optional[Fraction]:
    if value is None:
        return None
    return Fraction(numerator=value.numerator, denominator=value.denominator)


#: Column reference, for readers coming from the DCML corpora.
COLUMN_MAP: Dict[str, Dict[str, str]] = {
    "dlc": {
        "group": "unfolded_harmony_index", "onset": "quarterbeats_playthrough",
        "measure": "mn", "beat": "beat_float", "chord": "chord",
        "localkey": "localkey", "globalkey": "globalkey", "relativeroot": "relativeroot",
        "cadence": "cadence", "phraseend": "phraseend", "pedal": "pedal",
    },
    "an": {
        "group": "a_annotationNumber", "onset": "j_offset",
        "measure": "a_measure", "beat": "mn_onset", "chord": "a_romanNumeral",
        "localkey": "a_localKey", "globalkey": "(first a_localKey)",
        "relativeroot": "a_tonicizedKey", "duration": "a_duration",
    },
}
