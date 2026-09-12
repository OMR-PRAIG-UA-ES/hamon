"""Humdrum ``**harm`` adapter — Huron's harmonic-analysis representation → HamonSequence.

The ``**harm`` representation (David Huron; http://www.humdrum.org/rep/harm/) encodes a
functional analysis as Roman numerals with their own quality/inversion syntax, distinct
from HAMON's figured-bass Roman:

* numeral case = triad quality (upper = major, lower = minor);
* ``o`` = diminished, ``+`` = augmented;
* a seventh is marked by ``7`` (or the quality letters ``D7``/``M7``/``m7`` = dominant /
  major / minor seventh, ``d7`` = fully-diminished, ``h7`` = half-diminished);
* **inversions are letters** appended at the end — ``a`` root, ``b`` 1st, ``c`` 2nd,
  ``d`` 3rd — *not* figured-bass digits;
* a leading ``-``/``#`` alters the root; ``/X`` is a secondary (tonicized) target;
* parentheses ``(...)`` wrap an implied/parenthetical chord.

This is the format of ``napulen/haydn_op20_harm`` (``.hrm``) and TAVERN (``**harm`` in
``.krn``). :func:`harm_token_to_roman` translates one ``**harm`` token to a canonical
HAMON Roman surface (``°``/``ø``/``+`` + figured-bass tail); :func:`harm_to_hamon` reads a
whole Humdrum document's ``**harm`` spine, turning ``*key:`` tandems into ``TonalRegion``s
and barlines into measure ``Position``s.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import List, Optional

from hamonpy.ast import (
    HamonSequence, HarmonyGroup, HarmonyLabel, Key, PitchClass, Position,
    RenderingHints, TextSemantic, TonalRegion,
)
from hamonpy.parse import parse_hamon_sequence

# numeral [+ quality o/+] [+ seventh marker] [+ inversion letter a-d]
_HARM_RE = re.compile(
    r"^([#\-b]*)"            # 1 root accidentals
    r"([IVXivx]+)"           # 2 roman numeral
    r"(o|\+)?"               # 3 diminished / augmented
    r"(D7|M7|m7|d7|h7|7)?"   # 4 seventh marker
    r"([a-d])?$"             # 5 inversion letter
)
_TRIAD_FIG = {"a": "", "b": "6", "c": "64"}
_SEVENTH_FIG = {"a": "7", "b": "65", "c": "43", "d": "42", "": "7"}
_ACC = {"-": "b", "b": "b", "#": "#"}


def _harm_token_parts(token: str):
    """Return ``(primary_surface, secondary_roman_or_None)`` for a ``**harm`` token, or
    ``None`` if it is not a harmony token. The secondary is returned separately because
    HAMON's Roman grammar rejects flat-prefixed secondaries (e.g. ``/bII``)."""
    t = token.strip()
    if not t or t in (".", "*", "!"):
        return None
    # TAVERN prefixes each **harm token with a Humdrum **recip duration (e.g. "4I",
    # "2.V7"); Haydn does not. Strip a leading rhythm token — romans never start with a digit.
    t = re.sub(r"^\d+\.*", "", t)
    t = t.strip("()")  # implied/parenthetical chord — keep the chord, drop the parens
    primary, sep, secondary = t.partition("/")
    # Apply the **harm letter-inversion translation first (Ib → I6, V7d → V42,
    # viioD7 → vii°7). Its regex doesn't match an already-figured Roman (V65, ii43,
    # bII6) — those fall through to a direct parse, so the adapter is a superset.
    base = _harm_primary_to_roman(primary) or (primary if _is_roman(primary) else None)
    if base is None:
        return None
    sec = None
    if sep and secondary:
        s = _harm_primary_to_roman(secondary) or (secondary if _is_roman(secondary) else None)
        sec = s if s is not None else secondary
    return base, sec


def harm_token_to_roman(token: str) -> Optional[str]:
    """Translate one ``**harm`` token to a HAMON Roman surface (``X/Y`` form), or ``None``."""
    parts = _harm_token_parts(token)
    if parts is None:
        return None
    base, sec = parts
    return f"{base}/{sec}" if sec else base


def _is_roman(surface: str) -> bool:
    try:
        parsed = parse_hamon_sequence("@rn\n" + surface).groups
    except Exception:  # noqa: BLE001 - grammar raises on stray '[' etc.; treat as non-Roman
        return False
    return bool(parsed) and parsed[0].primary[0].semantic.kind == "roman"


_NEAPOLITAN_RE = re.compile(r"^N([a-d])?$")


def _harm_primary_to_roman(part: str) -> Optional[str]:
    nm = _NEAPOLITAN_RE.match(part)            # Neapolitan = ♭II (major triad)
    if nm:
        return "bII" + _TRIAD_FIG.get(nm.group(1) or "a", "")
    m = _HARM_RE.match(part)
    if not m:
        return None
    acc_raw, numeral, qual, seventh, inv = m.groups()
    accidentals = "".join(_ACC.get(c, "") for c in acc_raw)
    glyph = {"o": "°", "+": "+"}.get(qual or "", "")
    if seventh == "d7":
        glyph = "°"
    elif seventh == "h7":
        glyph = "ø"
    is_seventh = seventh is not None
    if is_seventh:
        fig = _SEVENTH_FIG.get(inv or "", "7")
    else:
        fig = _TRIAD_FIG.get(inv or "a", "")
    return f"{accidentals}{numeral}{glyph}{fig}"


def _harm_label(token: str) -> HarmonyLabel:
    parts = _harm_token_parts(token)
    if parts is not None:
        primary, secondary = parts
        try:
            parsed = parse_hamon_sequence("@rn\n" + primary).groups
        except Exception:  # noqa: BLE001
            parsed = []
        if parsed and parsed[0].primary[0].semantic.kind == "roman":
            label = parsed[0].primary[0]
            full = f"{primary}/{secondary}" if secondary else primary
            label = replace(label, surface=full)
            if secondary:
                label = replace(label, semantic=replace(label.semantic, secondary=secondary))
            return label
    # not translatable to a HAMON Roman: preserve the original token as text
    return HarmonyLabel(
        surface=token.strip(), semantic=TextSemantic(text=token.strip()),
        rendering=RenderingHints(), detected_system="text", system="text",
        sequence_system_hint="rn",
    )


_KEY_TANDEM = re.compile(r"^\*([A-Ga-g])([#\-]*):$")


def _parse_harm_key(tok: str) -> Optional[Key]:
    m = _KEY_TANDEM.match(tok.strip())
    if not m:
        return None
    letter, acc = m.groups()
    mode = "minor" if letter.islower() else "major"
    accidental = {"-": "flat", "#": "sharp"}.get(acc[:1], None) if acc else None
    return Key(tonic=PitchClass(note=letter.upper(), accidental=accidental), mode=mode)


def harm_to_hamon(text: str) -> HamonSequence:
    """Read the ``**harm`` spine of a Humdrum document into a Roman HamonSequence."""
    lines = text.splitlines()
    header_idx = next(
        (i for i, ln in enumerate(lines)
         if "**" in ln and any(c.strip() == "**harm" for c in ln.split("\t"))), -1)
    if header_idx < 0:
        return HamonSequence(groups=[])
    harm_col = next(i for i, c in enumerate(lines[header_idx].split("\t"))
                    if c.strip() == "**harm")

    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    open_key: Optional[int] = None
    measure: Optional[int] = None

    for ln in lines[header_idx + 1:]:
        if re.match(r"^\*-(\t\*-)*$", ln):
            break
        if not ln:
            continue
        cols = ln.split("\t")
        cell = cols[harm_col].strip() if harm_col < len(cols) else ""
        if ln[0] == "=":
            bm = re.match(r"^=+(\d+)", cols[0])
            if bm:
                measure = int(bm.group(1))
            continue
        if ln[0] == "!":
            continue
        if ln[0] == "*":
            key = _parse_harm_key(cell)
            if key is not None:
                gi = len(groups)
                if open_key is not None and gi > 0:
                    regions[open_key].to_group = gi - 1
                regions.append(TonalRegion(
                    key=key, kind=("key" if open_key is None else "modulation"), from_group=gi))
                open_key = len(regions) - 1
            continue
        if not cell or cell == ".":
            continue
        label = _harm_label(cell)
        groups.append(HarmonyGroup(
            primary=[label], position=Position(measure=measure) if measure is not None else None))

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)


def harm_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return harm_to_hamon(fh.read())
