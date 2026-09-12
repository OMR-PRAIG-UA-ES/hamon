"""BPS-FH adapter — Beethoven Piano Sonatas Functional Harmony (Chen & Su) → HamonSequence.

The BPS-FH dataset (https://github.com/Tsung-Ping/functional-harmony) ships one
``chords.xlsx`` per movement with seven unlabelled columns:

    onset | offset | key | degree | quality | inversion | roman

where ``key`` is a letter (upper = major, lower = minor) with ``-`` = flat / ``+`` =
sharp (e.g. ``A-`` = A♭ major, ``c+`` = C♯ minor); ``degree`` is a scale degree
(``1``–``7``, optionally ``-``/``+`` altered and ``P/S`` for a secondary, e.g. ``5/5``);
``quality`` ∈ {M, m, D7, M7, m7, d, d7, h7, a, a6}; ``inversion`` ∈ {0,1,2,3}; and the
last column is the analysts' Roman-numeral string.

This adapter reconstructs a **canonical HAMON Roman surface** from the structured
``degree``/``quality``/``inversion`` columns (so ``°``/``ø``/``+`` and figured-bass tails
match HAMON's grammar), parses it into the rn/degree layer, attaches each chord's onset
as a time ``Position``, and turns key changes into ``TonalRegion``s (first = home key,
later = modulation). Augmented-sixth chords (``a6``: It/Ger/Fr) have no HAMON Roman
vocabulary yet — their original label (``It+6``…) is preserved as the surface (text).

Reading ``.xlsx`` needs ``openpyxl`` (``pip install -e ./hamonpy[bps]``).
"""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction as _Fraction
from pathlib import Path
from typing import List, Optional

from hamonpy.ast import (
    Fraction, HamonSequence, HarmonyGroup, HarmonyLabel, Key, PitchClass,
    Position, RenderingHints, TextSemantic, TonalRegion,
)
from hamonpy.parse import parse_hamon_sequence

_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}

# quality -> (case, is_seventh, quality_glyph)
_QUALITY = {
    "M":  ("upper", False, ""),
    "m":  ("lower", False, ""),
    "a":  ("upper", False, "+"),
    "d":  ("lower", False, "°"),
    "D7": ("upper", True, ""),
    "M7": ("upper", True, ""),
    "m7": ("lower", True, ""),
    "d7": ("lower", True, "°"),
    "h7": ("lower", True, "ø"),
}
_TRIAD_FIG = {0: "", 1: "6", 2: "64"}
_SEVENTH_FIG = {0: "7", 1: "65", 2: "43", 3: "42"}


def _parse_key(s: str) -> Optional[Key]:
    s = (s or "").strip()
    if not s or not s[0].isalpha():
        return None
    mode = "minor" if s[0].islower() else "major"
    acc = {"-": "flat", "+": "sharp"}.get(s[1], None) if len(s) > 1 else None
    return Key(tonic=PitchClass(note=s[0].upper(), accidental=acc), mode=mode)


def _degree_part_to_roman(part: str, case: str) -> Optional[str]:
    part = part.strip()
    acc = ""
    if part and part[0] in "+-":
        acc = "#" if part[0] == "+" else "b"
        part = part[1:]
    if not part.isdigit() or int(part) not in _ROMAN:
        return None
    roman = _ROMAN[int(part)]
    return acc + (roman.lower() if case == "lower" else roman)


def _row_to_roman_parts(degree: str, quality: str, inversion: int):
    """Return ``(primary_surface, secondary_roman_or_None)`` for a BPS-FH row, or
    ``None`` for unsupported qualities (a6). ``primary_surface`` is a HAMON Roman the
    grammar parses on its own; the secondary is attached separately because HAMON's
    Roman grammar rejects flat-prefixed secondaries (e.g. ``/bVII``)."""
    if quality not in _QUALITY:
        return None  # a6 (augmented sixth) and any future quality
    case, is_seventh, glyph = _QUALITY[quality]
    primary, _, secondary = degree.partition("/")
    base = _degree_part_to_roman(primary, case)
    if base is None:
        return None
    fig = (_SEVENTH_FIG if is_seventh else _TRIAD_FIG).get(inversion, "7" if is_seventh else "")
    primary_surface = base + glyph + fig
    sec = _degree_part_to_roman(secondary, "upper") if secondary else None
    return primary_surface, sec


def _to_fraction(value) -> Optional[Fraction]:
    try:
        fr = _Fraction(float(value)).limit_denominator(960)
    except (TypeError, ValueError):
        return None
    return Fraction(numerator=fr.numerator, denominator=fr.denominator)


def _rows_to_hamon(rows) -> HamonSequence:
    """rows: iterable of (onset, key, degree, quality, inversion, roman_label)."""
    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    open_key: Optional[int] = None
    last_key_str: Optional[str] = None

    for onset, key_str, degree, quality, inversion, roman_label in rows:
        key_str = (str(key_str) if key_str is not None else "").strip()
        if key_str and key_str != last_key_str:
            key = _parse_key(key_str)
            if key is not None:
                gi = len(groups)
                if open_key is not None and gi > 0:
                    regions[open_key].to_group = gi - 1
                regions.append(TonalRegion(
                    key=key, kind=("key" if open_key is None else "modulation"), from_group=gi,
                ))
                open_key = len(regions) - 1
            last_key_str = key_str

        parts = _row_to_roman_parts(str(degree), str(quality).strip(), int(inversion))
        label = None
        if parts is not None:
            primary_surface, secondary = parts
            parsed = parse_hamon_sequence("@rn\n" + primary_surface).groups
            if parsed and parsed[0].primary[0].semantic.kind == "roman":
                label = parsed[0].primary[0]
                full = f"{primary_surface}/{secondary}" if secondary else primary_surface
                label = replace(label, surface=full)
                if secondary:
                    label = replace(label, semantic=replace(label.semantic, secondary=secondary))
        if label is None:  # a6 / unparseable: preserve the analysts' original label
            label = HarmonyLabel(
                surface=str(roman_label), semantic=TextSemantic(text=str(roman_label)),
                rendering=RenderingHints(), detected_system="text", system="text",
                sequence_system_hint="rn",
            )
        pos = _to_fraction(onset)
        groups.append(HarmonyGroup(
            primary=[label], position=Position(time=pos) if pos is not None else None,
        ))

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)


def bps_fh_chords_file_to_hamon(path: str) -> HamonSequence:
    """Convert one BPS-FH ``chords.xlsx`` (7 unlabelled columns) into a HamonSequence."""
    try:
        import pandas as pd  # noqa: PLC0415 - optional, only needed for .xlsx
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Reading BPS-FH .xlsx needs pandas+openpyxl: "
                          "pip install -e ./hamonpy[bps]") from exc
    df = pd.read_excel(path, header=None)
    rows = ((r[0], r[2], r[3], r[4], r[5], r[6]) for _, r in df.iterrows())
    return _rows_to_hamon(rows)


def bps_fh_movement_to_hamon(folder: str) -> HamonSequence:
    """Convert a BPS-FH movement folder (uses ``<folder>/chords.xlsx``)."""
    return bps_fh_chords_file_to_hamon(str(Path(folder) / "chords.xlsx"))
