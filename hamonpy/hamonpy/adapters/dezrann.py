"""Dezrann (.dez) adapter — Algomus/Dezrann label JSON ↔ HamonSequence.

Dezrann (Foscarin, Giraud, Rigaux et al.; https://www.dezrann.net and the
TISMIR Dezrann paper, https://doi.org/10.5334/tismir.212) is a web platform for
time-aligned access to annotated music corpora. Its native ``.dez`` files are
JSON with a mandatory ``labels`` array and an optional ``meta`` block. Each
label is anchored on *musical time* measured in **quarter notes from the start
of the piece** (``start``, the only mandatory field; optional ``duration``).

Dezrann is deliberately agnostic to the harmony ontology: the harmonic content
of a label lives in its ``tag`` (e.g. a chord symbol ``"Cmaj7"`` or a Roman
numeral ``"V65"``), while ``type`` names the annotation family (``"Harmony"``,
``"Chord"``, ``"Cadence"``, ``"Tonality"``, ...). HAMON is the missing
normalisation layer: this adapter parses those tags into HAMON's typed AST and
keeps Dezrann's quarter-note anchor as a HarmonyGroup ``Position``.

  * :func:`dez_to_hamon` — read the harmony-bearing labels of a ``.dez``
    document; each ``start`` becomes a ``Position`` (absolute fractional
    ``time`` in quarters) and each ``tag`` is parsed into a typed label.
  * :func:`hamon_to_dez` — serialise a HamonSequence back to ``.dez`` JSON,
    one label per group (``start`` from the group ``Position`` when known, else
    the running group index).

HAMON does not redistribute Dezrann corpora; see ``datasets/manifest.json``.
"""
from __future__ import annotations

import json
from dataclasses import replace as _replace
from fractions import Fraction as _Fraction
from typing import Iterable, List, Optional, Union

from hamonpy.ast import (
    Fraction,
    HamonSequence,
    HarmonyAttributes,
    HarmonyGroup,
    HarmonyLabel,
    Position,
    RenderingHints,
    TextSemantic,
)
from hamonpy.parse import parse_hamon_sequence

#: Label ``type`` values whose ``tag`` carries a harmony surface, by default.
DEFAULT_HARMONY_TYPES = ("harmony", "chord", "chords")

DezDocument = Union[str, dict]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quarter_to_time(value) -> Optional[Fraction]:
    """A Dezrann ``start`` (quarter notes) → a HAMON :class:`Fraction` time."""
    if value is None:
        return None
    try:
        fr = _Fraction(str(value)).limit_denominator(1000000)
    except (ValueError, ZeroDivisionError):
        return None
    return Fraction(numerator=fr.numerator, denominator=fr.denominator)


def _time_to_number(time: Fraction):
    """A HAMON :class:`Fraction` → a JSON number (int when integral)."""
    if time.denominator == 1:
        return time.numerator
    return time.numerator / time.denominator


def _parse_tag(surface: str, system: str) -> HarmonyLabel:
    """Parse one Dezrann ``tag`` into a typed label; fall back to text."""
    surface = surface.strip()
    try:
        sub = parse_hamon_sequence(f"@{system}\n{surface}")
        if sub.groups and sub.groups[0].primary:
            return sub.groups[0].primary[0]
    except Exception:  # noqa: BLE001 — any malformed tag degrades to text
        pass
    return HarmonyLabel(
        surface=surface, semantic=TextSemantic(text=surface),
        rendering=RenderingHints(), detected_system="text", system="text",
    )


def _load(data: DezDocument) -> dict:
    if isinstance(data, dict):
        return data
    text = data
    if isinstance(data, str) and "\n" not in data and data.strip().endswith(".dez"):
        with open(data, encoding="utf-8") as fh:
            text = fh.read()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API — Dezrann → HAMON
# ---------------------------------------------------------------------------

def dez_file_to_hamon(path: str, **kwargs) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return dez_to_hamon(fh.read(), **kwargs)


def dez_to_hamon(
    data: DezDocument,
    *,
    harmony_types: Iterable[str] = DEFAULT_HARMONY_TYPES,
    system: str = "auto",
) -> HamonSequence:
    """Convert a Dezrann ``.dez`` document to a HamonSequence.

    *data* may be a parsed dict, JSON text, or a ``.dez`` file path. Only labels
    whose ``type`` is in *harmony_types* (case-insensitive) and that carry a
    non-empty ``tag`` are converted; groups are emitted in ``start`` order with a
    time-aligned :class:`Position`. *system* is the parser hint for each tag
    (``"auto"`` lets HAMON detect cs/rn/…; pass ``"rn"``/``"cs"`` to force one).
    """
    doc = _load(data)
    wanted = {t.lower() for t in harmony_types}

    rows = []
    for label in doc.get("labels", []):
        if not isinstance(label, dict):
            continue
        if str(label.get("type", "")).lower() not in wanted:
            continue
        tag = label.get("tag")
        if not tag:
            continue
        rows.append((label.get("start"), str(tag), label.get("duration")))

    # A label with no `start` states no time — it used to default to 0, which the
    # importer then stored as a real onset. Document order is the only ordering an
    # untimed document has, so a document missing any start is not reordered at all.
    if all(r[0] is not None for r in rows):
        rows.sort(key=lambda r: _Fraction(str(r[0])))

    groups: List[HarmonyGroup] = []
    for start, tag, duration in rows:
        lab = _parse_tag(tag, system)
        time = _quarter_to_time(start)
        extent = _quarter_to_time(duration)
        if extent is not None:
            # Dezrann counts in quarters, like HAMON's `time`, so it transfers as it is.
            lab.attributes = (_replace(lab.attributes, duration=extent)
                              if lab.attributes else HarmonyAttributes(duration=extent))
        groups.append(HarmonyGroup(
            primary=[lab],
            position=Position(time=time) if time is not None else None,
        ))

    hint = None if system == "auto" else system
    return HamonSequence(groups=groups, sequence_system_hint=hint)


# ---------------------------------------------------------------------------
# Public API — HAMON → Dezrann
# ---------------------------------------------------------------------------

def hamon_to_dez(
    seq: HamonSequence,
    *,
    label_type: str = "Harmony",
    indent: Optional[int] = 2,
    meta: Optional[dict] = None,
) -> str:
    """Serialise a HamonSequence to Dezrann ``.dez`` JSON text.

    One label per group: ``start`` comes from the group ``Position.time`` (in quarters)
    when the group states one, and is **omitted otherwise** — never the running group
    index, which is what it used to be. The index is not a musical time: a sequence
    positioned in bars came out claiming its harmonies fall one quarter apart, and the
    re-import read that back as source data. Same invention as the ``duration`` below,
    and the same cure. ``start`` is nominally mandatory in ``.dez``, so an untimed
    sequence yields a document a strict consumer may reject; that beats one it accepts
    and misreads.
    """
    starts: List[Optional[Fraction]] = []
    for gi, group in enumerate(seq.groups):
        pos = group.position
        starts.append(pos.time if (pos and pos.time is not None) else None)

    labels = []
    for gi, group in enumerate(seq.groups):
        if not group.primary:
            continue
        time = starts[gi]
        label = {"type": label_type, "tag": group.primary[0].surface}
        if time is not None:
            label["start"] = _time_to_number(time)

        # `duration` is written only when the label STATES its extent. It used to be
        # recomputed from the gap to the next group, which is right only when the harmony
        # fills that gap — and, worse, came back on re-import looking like source data, so
        # the round-trip reported no loss even when the original duration was different.
        # `duration` is optional in .dez; leaving it out says "unknown", which is true.
        attributes = getattr(group.primary[0], "attributes", None)
        extent = getattr(attributes, "duration", None) if attributes else None
        if extent is not None:
            label["duration"] = (extent.numerator / extent.denominator
                                 if extent.denominator != 1 else extent.numerator)
        labels.append(label)

    doc = {"labels": labels, "meta": meta or {"producer": "hamonpy", "layout": []}}
    return json.dumps(doc, indent=indent, ensure_ascii=False)
