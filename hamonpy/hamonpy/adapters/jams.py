"""JAMS ↔ HAMON adapter.

JAMS (JSON Annotated Music Specification, https://jams.readthedocs.io) is a JSON
container for time-aligned MIR annotations. For harmony it uses the ``chord`` (or
``chord_harte``) namespace whose values are **Harte** chord labels, plus ``key_mode``
for keys; observations are stamped in **audio seconds**.

We reuse the Harte chord parser/serializer for the labels and map ``key_mode`` to a
HAMON tonal region. Since v0.5 the audio timestamps survive the trip: an observation's
``time`` becomes ``Position.seconds`` (``s:``) and its ``duration`` the label's extent in
the same clock (``[dur:1.5s]``). What a group does not state is written back as a
placeholder, because JAMS requires both fields and cannot say "unknown".

Dependency-free: we read/write the JAMS JSON structure directly (no ``jams`` package).
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import List, Optional, Union

from ..ast import (HamonSequence, HarmonyAttributes, HarmonyGroup, Key, PitchClass,
                   Position, TonalRegion)
from .harte import (
    _HAMON_TO_HARTE_ACC,
    _label_to_harte_token,
    harte_token_to_hamon_label,
)

JAMS_VERSION = "0.3.4"
_CHORD_NAMESPACES = ("chord", "chord_harte")

# Harte/JAMS accidental glyph ('#'/'b') ↔ HAMON accidental name.
_HARTE_TO_HAMON_ACC = {"#": "sharp", "b": "flat", "##": "double-sharp", "bb": "double-flat"}


# ---------------------------------------------------------------------------
# Reading — JAMS → HAMON
# ---------------------------------------------------------------------------

def _key_from_value(value: str) -> Optional[Key]:
    """Parse a JAMS ``key_mode`` value (e.g. ``"C:major"``, ``"Bb:minor"``, ``"C"``)."""
    if not value or value in ("N", "X"):
        return None
    tonic, _, mode = value.partition(":")
    note = tonic[:1].upper()
    if not note or note not in "ABCDEFG":
        return None
    acc_glyph = tonic[1:]
    accidental = _HARTE_TO_HAMON_ACC.get(acc_glyph)
    return Key(tonic=PitchClass(note=note, accidental=accidental), mode=(mode or "major"))


def _annotations(doc: dict) -> list:
    anns = doc.get("annotations")
    return anns if isinstance(anns, list) else []


def _seconds(value) -> Optional[float]:
    """A JAMS time-valued field as a float, or ``None`` when it states nothing."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value)


def _position_from_obs(obs: dict) -> Optional[Position]:
    """A JAMS observation's ``time`` (audio seconds) as a HAMON position.

    Seconds are the only clock JAMS states, so they are stored as stated — no
    metric position is inferred from them."""
    time = _seconds(obs.get("time"))
    return None if time is None else Position(seconds=time)


def jams_to_hamon(source: Union[str, dict]) -> HamonSequence:
    """Parse a JAMS document (JSON text or already-decoded dict) into a HamonSequence."""
    doc = source if isinstance(source, dict) else json.loads(source)

    # chord annotation (first one in a known namespace) → ordered groups
    chord_obs: List[dict] = []
    for ann in _annotations(doc):
        if ann.get("namespace") in _CHORD_NAMESPACES:
            data = ann.get("data")
            if isinstance(data, list):
                chord_obs = sorted(data, key=lambda o: o.get("time") or 0)
            break

    groups: List[HarmonyGroup] = []
    for obs in chord_obs:
        label = harte_token_to_hamon_label(str(obs.get("value", "")))
        if label is not None:
            duration = _seconds(obs.get("duration"))
            if duration is not None:
                label.attributes = replace(label.attributes or HarmonyAttributes(),
                                           durationSeconds=duration)
            groups.append(HarmonyGroup(primary=[label], position=_position_from_obs(obs)))

    # key_mode annotation → a global tonal region (first key value)
    regions: List[TonalRegion] = []
    for ann in _annotations(doc):
        if ann.get("namespace") == "key_mode":
            for obs in sorted(ann.get("data", []), key=lambda o: o.get("time") or 0):
                key = _key_from_value(str(obs.get("value", "")))
                if key is not None:
                    regions.append(TonalRegion(key=key, kind="key", from_group=0))
                    break
            break

    return HamonSequence(
        groups=groups,
        sequence_system_hint="cs",
        regions=regions or None,
    )


def jams_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return jams_to_hamon(fh.read())


# ---------------------------------------------------------------------------
# Writing — HAMON → JAMS
# ---------------------------------------------------------------------------

def _key_to_value(key: Key) -> str:
    acc = _HAMON_TO_HARTE_ACC.get(key.tonic.accidental or "", key.tonic.accidental or "")
    return f"{key.tonic.note}{acc}:{key.mode or 'major'}"


def hamon_to_jams_dict(seq: HamonSequence) -> dict:
    """Build the JAMS document (as a dict) for a HamonSequence.

    Emits a ``chord`` annotation (Harte values) and, when the sequence has tonal
    regions, a ``key_mode`` annotation; one observation per group. A group's stated
    ``s:`` seconds become its ``time`` and a stated ``[dur:…s]`` its ``duration``.

    **An unstated clock is written as ``null``, never as a number.** This writer used
    to fall back to the group's index for ``time`` and to ``1`` for ``duration``, which
    a JAMS consumer reads as real audio timestamps — a sequence positioned in bars came
    out claiming its harmonies land one second apart. That is the invention the Dezrann
    writer was cured of and the Harte writer refuses; ``report.py`` was duly flagging it
    as ``added``. The cost is that a HAMON sequence with no audio clock produces a JAMS
    document that is *not* schema-valid, since JAMS requires a numeric ``time``: the
    format has no way to say "unknown", and saying nothing beats saying something false.
    """
    chord_data = []
    for group in seq.groups:
        token = next((_label_to_harte_token(lbl) for lbl in group.primary
                      if _label_to_harte_token(lbl)), None)
        if token:
            seconds = group.position.seconds if group.position else None
            extent = next((lbl.attributes.durationSeconds for lbl in group.primary
                           if lbl.attributes and lbl.attributes.durationSeconds is not None), None)
            chord_data.append({"time": seconds, "duration": extent,
                               "value": token, "confidence": None})

    def _meta():
        return {
            "corpus": "", "version": seq.version or "",
            "annotator": {}, "annotation_tools": "hamonpy", "annotation_rules": "",
            "validation": "", "data_source": "HAMON", "curator": {"name": "", "email": ""},
        }

    annotations = [{
        "namespace": "chord",
        "data": chord_data,
        "annotation_metadata": _meta(),
        "sandbox": {},
        "time": 0, "duration": None,
    }]

    key_data = [
        {"time": 0, "duration": None, "value": _key_to_value(r.key), "confidence": None}
        for r in (seq.regions or []) if r.kind == "key"
    ]
    if key_data:
        annotations.append({
            "namespace": "key_mode",
            "data": key_data,
            "annotation_metadata": _meta(),
            "sandbox": {},
            "time": 0, "duration": None,
        })

    return {
        "file_metadata": {
            "title": "", "artist": "", "release": "", "duration": None,
            "identifiers": {}, "jams_version": JAMS_VERSION,
        },
        "annotations": annotations,
        "sandbox": {},
    }


def hamon_to_jams(seq: HamonSequence) -> str:
    """Serialize a HamonSequence to a JAMS JSON string."""
    return json.dumps(hamon_to_jams_dict(seq), indent=2, ensure_ascii=False) + "\n"
