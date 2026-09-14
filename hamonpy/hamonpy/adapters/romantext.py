"""RomanText adapter — When-in-Rome / RomanText (.rntxt) → HamonSequence.

RomanText (Tymoczko, Gotham, Sapp) encodes a functional analysis as lines like

    m0 b2 d: i
    m1 iiø2 b2 V65
    m17 viio b2 ii65/IV b3 viio64/IV

i.e. `m<measure> [b<beat>] [<key>:] <roman> …`. Inline key tokens (`d:`, `C:`,
`f#:`) become tonal regions (first = home key, later = modulation), and each
Roman numeral becomes a degree-system label carrying the measure and beat it was
written on. `mX = mY` repeat lines are skipped.

Used by the When-in-Rome use-case; see `datasets/manifest.json` (`when_in_rome`).
"""
from __future__ import annotations

import re
from typing import List, Optional

from hamonpy.ast import (
    HamonSequence, HarmonyGroup, HarmonyLabel, Position, RenderingHints, TextSemantic,
    TonalRegion,
)
from hamonpy.adapters.dcml import _parse_dcml_global_key, _dcml_surface_to_roman

_MEASURE_RE = re.compile(r"^m\d")
_MEASURE_NUMBER_RE = re.compile(r"^m(\d+)")      # 'm17', and the 'm17a' of a first ending
_KEY_RE = re.compile(r"^([A-Ga-g][#b-]*):$")     # 'C:', 'd:', 'f#:', 'Bb:'
_BEAT_RE = re.compile(r"^b[\d.]+$")
_REPEAT_RE = re.compile(r"=\s*m")


def romantext_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return romantext_to_hamon(fh.read())


def romantext_to_hamon(text: str) -> HamonSequence:
    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    open_key: Optional[int] = None

    for raw in text.splitlines():
        s = raw.strip()
        if not s or not _MEASURE_RE.match(s):
            continue                       # header / blank / metadata
        if _REPEAT_RE.search(s):
            continue                       # 'm5-6 = m1-2' repeat shorthand

        tokens = s.split()
        # `m17 viio b2 ii65/IV` says where it is; a reader that drops that turns a
        # time-aligned analysis into a bare list. The measure opens on its downbeat and
        # a `b` token moves the cursor for the labels that follow it.
        number = _MEASURE_NUMBER_RE.match(tokens[0])
        measure = int(number.group(1)) if number else None
        beat: Optional[float] = 1.0

        for tok in tokens[1:]:             # skip the measure-id token
            if _BEAT_RE.match(tok):
                beat = float(tok[1:])
                continue
            km = _KEY_RE.match(tok)
            if km:
                key = _parse_dcml_global_key(tok[:-1])
                if key is None:
                    continue
                gi = len(groups)
                if open_key is not None and gi > 0:
                    regions[open_key].to_group = gi - 1
                regions.append(TonalRegion(
                    key=key, kind=("key" if open_key is None else "modulation"), from_group=gi,
                ))
                open_key = len(regions) - 1
                continue

            res = _dcml_surface_to_roman(tok)
            if res is not None:
                semantic, rendering, _detected = res
            else:
                semantic, rendering = TextSemantic(text=tok), RenderingHints()
            groups.append(HarmonyGroup(primary=[HarmonyLabel(
                surface=tok, semantic=semantic, rendering=rendering,
                detected_system="rn", system="rn", sequence_system_hint="rn",
            )], position=Position(measure=measure, beat=beat) if measure is not None else None))

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)
