"""MusicXML harmony adapter with time-aligned positions (schema 0.2.1).

`musicxml_to_hamon` builds a HamonSequence from `<harmony>` elements and attaches
each group's `HarmonyGroup.position` (measure + beat) using the MusicXML time
model: `<divisions>` sets the divisions-per-quarter, elapsed time accumulates from
`<note>` (non-chord) / `<forward>` / `<backup>` durations within the measure, and a
`<harmony><offset>` (in divisions) shifts the harmony from the current position.

The surface strings match `formats._extract_musicxml` (shared helpers); this adapter
adds the positional structure that the flat surface extractor cannot represent.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from hamonpy.ast import HamonSequence, HarmonyGroup, Position
from hamonpy.parse import parse_hamon_sequence
from hamonpy.adapters.formats import _accidental_from_alter, _normalize_musicxml_kind


def musicxml_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return musicxml_to_hamon(fh.read())


def _text(el: ET.Element, path: str) -> Optional[str]:
    child = el.find(path)
    return child.text.strip() if child is not None and child.text else None


def _dur(el: ET.Element) -> int:
    d = _text(el, "duration")
    try:
        return int(round(float(d))) if d else 0
    except ValueError:
        return 0


def _harmony_surface(harm: ET.Element) -> Optional[str]:
    """Reconstruct a hamon chord surface from a <harmony> element (or None)."""
    step = _text(harm, "root/root-step")
    if not step:
        return None
    alter = _text(harm, "root/root-alter")
    root = f"{step}{_accidental_from_alter(float(alter)) if alter else ''}"

    kind_el = harm.find("kind")
    kind_raw = ""
    if kind_el is not None:
        kind_raw = (kind_el.get("text") or (kind_el.text or "").strip())
    kind = _normalize_musicxml_kind(kind_raw)

    bass_step = _text(harm, "bass/bass-step")
    bass = ""
    if bass_step:
        bass_alter = _text(harm, "bass/bass-alter")
        bass = f"/{bass_step}{_accidental_from_alter(float(bass_alter)) if bass_alter else ''}"

    return f"{root}{kind}{bass}"


def musicxml_to_hamon(text: str) -> HamonSequence:
    """Parse MusicXML `<harmony>` elements into a positioned HamonSequence."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return HamonSequence(groups=[])

    groups: List[HarmonyGroup] = []
    divisions = 1  # persists across measures until redefined

    for measure in root.iter("measure"):
        try:
            measure_num: Optional[int] = int(measure.get("number"))
        except (TypeError, ValueError):
            measure_num = None
        elapsed = 0  # divisions elapsed from the start of this measure

        for el in list(measure):
            if el.tag == "attributes":
                d = _text(el, "divisions")
                if d:
                    try:
                        divisions = int(d)
                    except ValueError:
                        pass
            elif el.tag == "harmony":
                surface = _harmony_surface(el)
                if not surface:
                    continue
                off = _text(el, "offset")
                try:
                    off_div = float(off) if off else 0.0
                except ValueError:
                    off_div = 0.0
                parsed = parse_hamon_sequence(f"@cs\n{surface}")
                if not parsed.groups:
                    continue
                group = parsed.groups[0]
                if measure_num is not None:
                    group.position = Position(
                        measure=measure_num,
                        beat=(elapsed + off_div) / divisions + 1,
                    )
                groups.append(group)
            elif el.tag == "note":
                if el.find("chord") is None:
                    elapsed += _dur(el)
            elif el.tag == "forward":
                elapsed += _dur(el)
            elif el.tag == "backup":
                elapsed -= _dur(el)

    return HamonSequence(groups=groups, sequence_system_hint="cs")
