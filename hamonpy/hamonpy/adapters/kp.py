"""Kostka-Payne adapter — Temperley's KP corpus ``kp-chord-list`` → HamonSequence.

The Kostka-Payne corpus (David Temperley & Daniel Sleator; davidtemperley.com/kp-stats)
ships its harmonic analysis as a ``kp-chord-list`` file: 46 excerpts, each introduced by a
``% name`` line, followed by one chord-span per line in the Melisma harmony-analyser format

    <onset>  <offset>  -  <root>  <root_tpc>  <key>  <key_tpc>

where ``root`` is the chord root as a **chromatic interval above the key tonic** (0 = I,
2 = II, 5 = IV, 7 = V, 11 = VII …) and ``key`` is the **absolute** tonic pitch class
(0 = C … 11 = B). The two ``*_tpc`` columns are line-of-fifths spellings (unused here).

This is a **root-only** analysis — no chord quality or seventh is recorded — so each span
becomes an upper-case Roman *degree* (with a chromatic accidental where needed: ``bII``,
``#IV`` …), the key becomes a ``TonalRegion`` (a new ``key`` region per excerpt and on any
key change), and ``onset`` becomes a time ``Position``.
"""
from __future__ import annotations

import re
from fractions import Fraction as _Fraction
from typing import List, Optional

from hamonpy.ast import (
    Fraction, HamonSequence, HarmonyGroup, Key, PitchClass, Position, TonalRegion,
)
from hamonpy.parse import parse_hamon_sequence

# chromatic degree above the tonic -> upper-case Roman with accidental
_DEGREE = {0: "I", 1: "bII", 2: "II", 3: "bIII", 4: "III", 5: "IV",
           6: "#IV", 7: "V", 8: "bVI", 9: "VI", 10: "bVII", 11: "VII"}
# absolute pitch class -> (note, accidental) with a default (flat-side) spelling
_PC_SPELL = {0: ("C", None), 1: ("C", "sharp"), 2: ("D", None), 3: ("E", "flat"),
             4: ("E", None), 5: ("F", None), 6: ("F", "sharp"), 7: ("G", None),
             8: ("A", "flat"), 9: ("A", None), 10: ("B", "flat"), 11: ("B", None)}

_ROW_RE = re.compile(r"^\s*([\d.]+)\s+([\d.]+)\s+-\s+(\d+)\s+(-?\d+)\s+(\d+)\s+(-?\d+)\s*$")


def _key_of(pc: int) -> Key:
    note, acc = _PC_SPELL[pc % 12]
    return Key(tonic=PitchClass(note=note, accidental=acc), mode=None)


def _time(value: str) -> Optional[Fraction]:
    try:
        fr = _Fraction(value).limit_denominator(960)
    except (ValueError, ZeroDivisionError):
        return None
    return Fraction(numerator=fr.numerator, denominator=fr.denominator)


def kp_chord_list_to_hamon(text: str) -> HamonSequence:
    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    open_key: Optional[int] = None
    cur_key_pc: Optional[int] = None
    new_excerpt = True

    for line in text.splitlines():
        if line.startswith("%"):
            new_excerpt = True          # next chord opens a fresh key region
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        onset, _off, root_deg, _rtpc, key_pc, _ktpc = m.groups()
        key_pc = int(key_pc) % 12
        if new_excerpt or key_pc != cur_key_pc:
            gi = len(groups)
            if open_key is not None and gi > 0:
                regions[open_key].to_group = gi - 1
            # a new excerpt is a new piece (kind 'key'); a key change mid-excerpt is a modulation
            kind = "key" if (new_excerpt or open_key is None) else "modulation"
            regions.append(TonalRegion(key=_key_of(key_pc), kind=kind, from_group=gi))
            open_key = len(regions) - 1
            cur_key_pc = key_pc
            new_excerpt = False

        surface = _DEGREE[int(root_deg) % 12]
        label = parse_hamon_sequence("@rn\n" + surface).groups[0].primary[0]
        pos = _time(onset)
        groups.append(HarmonyGroup(
            primary=[label], position=Position(time=pos) if pos is not None else None))

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)


def kp_chord_list_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return kp_chord_list_to_hamon(fh.read())
