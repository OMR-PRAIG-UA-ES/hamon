"""partitura adapter — CPJKU/partitura Score ↔ HamonSequence.

partitura (https://github.com/CPJKU/partitura) is a Python package for symbolic
music processing. Its score model has a ``Harmony`` base class with
``RomanNumeral`` and ``ChordSymbol`` subclasses; each is a ``TimedObject``
anchored in divisions, with onset time recoverable in quarters via
``part.quarter_map(obj.start.t)``.

This adapter:
  * :func:`partitura_part_to_hamon` — iterate a part's ``Harmony`` objects, map
    each onset to a HarmonyGroup :class:`Position` (absolute quarter offset) and
    parse the harmony text into a typed label.
  * :func:`hamon_to_partitura_part` — build a partitura ``Part`` and add one
    harmony object per group (``RomanNumeral`` for the Roman-numeral system,
    plain ``Harmony`` otherwise — the text round-trips either way).

partitura is an optional dependency (``pip install partitura``).
"""
from __future__ import annotations

from fractions import Fraction as _Fraction
from typing import List, Optional

from hamonpy.ast import (
    Fraction,
    HamonSequence,
    HarmonyGroup,
    HarmonyLabel,
    Position,
    RenderingHints,
    RomanSemantic,
    TextSemantic,
)
from hamonpy.parse import parse_hamon_sequence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _harmony_text(obj) -> Optional[str]:
    """Recover a harmony surface string from a partitura Harmony object."""
    text = getattr(obj, "text", None)
    if text:
        return str(text)
    # ChordSymbol carries root/kind/bass instead of free text.
    root = getattr(obj, "root", None)
    if root is not None:
        surface = str(root) + (str(getattr(obj, "kind", "") or ""))
        bass = getattr(obj, "bass", None)
        if bass:
            surface += "/" + str(bass)
        return surface
    return None


def _onset_position(part, obj) -> Optional[Position]:
    try:
        quarters = float(part.quarter_map(obj.start.t))
    except Exception:  # noqa: BLE001 - missing time map / object → no position
        return None
    fr = _Fraction(str(quarters)).limit_denominator(1000000)
    return Position(time=Fraction(numerator=fr.numerator, denominator=fr.denominator))


def _parse_surface(surface: str, system: str) -> HarmonyLabel:
    surface = surface.strip()
    try:
        sub = parse_hamon_sequence(f"@{system}\n{surface}")
        if sub.groups and sub.groups[0].primary:
            return sub.groups[0].primary[0]
    except Exception:  # noqa: BLE001
        pass
    return HarmonyLabel(
        surface=surface, semantic=TextSemantic(text=surface),
        rendering=RenderingHints(), detected_system="text", system="text",
    )


# ---------------------------------------------------------------------------
# partitura → HAMON
# ---------------------------------------------------------------------------

def partitura_part_to_hamon(part, *, system: str = "auto") -> HamonSequence:
    """Convert a partitura ``Part`` (or anything with ``iter_all``) to HAMON.

    Iterates all ``Harmony`` objects (including ``RomanNumeral`` / ``ChordSymbol``
    subclasses), parses each one's text into a typed label and attaches a
    time-aligned :class:`Position`. Groups are ordered by onset.
    """
    import partitura.score as pscore

    harmonies = list(part.iter_all(pscore.Harmony, include_subclasses=True))
    harmonies.sort(key=lambda h: h.start.t)

    groups: List[HarmonyGroup] = []
    for obj in harmonies:
        surface = _harmony_text(obj)
        if not surface:
            continue
        groups.append(HarmonyGroup(
            primary=[_parse_surface(surface, system)],
            position=_onset_position(part, obj),
        ))

    hint = None if system == "auto" else system
    return HamonSequence(groups=groups, sequence_system_hint=hint)


# ---------------------------------------------------------------------------
# HAMON → partitura
# ---------------------------------------------------------------------------

def hamon_to_partitura_part(
    seq: HamonSequence,
    *,
    part_id: str = "P0",
    part_name: str = "HAMON harmonies",
    divs_per_quarter: int = 4,
):
    """Build a partitura ``Part`` carrying one harmony object per group.

    Onsets come from each group's ``Position.time`` (quarters) when present,
    else the running group index. Roman-numeral labels become ``RomanNumeral``
    objects; everything else becomes a plain ``Harmony`` (its surface text).
    """
    import partitura.score as pscore

    part = pscore.Part(part_id, part_name, quarter_duration=divs_per_quarter)

    for gi, group in enumerate(seq.groups):
        if not group.primary:
            continue
        label = group.primary[0]
        pos = group.position
        quarters = (
            (pos.time.numerator / pos.time.denominator)
            if (pos and pos.time is not None) else float(gi)
        )
        start = int(round(quarters * divs_per_quarter))

        if isinstance(label.semantic, RomanSemantic):
            obj = pscore.RomanNumeral(label.surface)
        else:
            obj = pscore.Harmony(label.surface)
        part.add(obj, start=start, end=start + divs_per_quarter)

    return part
