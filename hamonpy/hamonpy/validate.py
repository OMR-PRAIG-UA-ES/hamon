"""Non-blocking validation of a parsed HamonSequence (v0.4.0).

Currently checks time-aligned positions against the declared meter: a group's
``ts`` (MEI ``data.BEAT``, 1-based) must fall inside the time signature in effect —
``ts`` spans ``[1, numerator + 1)``. A ``ts`` outside that range (e.g. ``ts:5`` in
``4/4``) yields a warning string; it never blocks parsing, since HAMON is a tolerant
exchange format that must round-trip imperfect sources.
"""

from __future__ import annotations

from typing import List, Optional

from .ast import HamonSequence, Meter


def _meter_for_group(meters: List[Meter], group_index: int) -> Optional[Meter]:
    """The time signature in effect for a group: the last ``@meter`` at or before it."""
    current: Optional[Meter] = None
    for meter in meters:
        if meter.from_group <= group_index:
            current = meter
        else:
            break
    return current


def validate_positions(seq: HamonSequence) -> List[str]:
    """Return a list of warning messages for ts values outside their meter's range.

    Empty when everything is in range or no meter is declared (without a meter the
    beat range is unknown, so nothing is checked)."""
    warnings: List[str] = []
    meters = seq.meters or []
    if not meters:
        return warnings

    for gi, group in enumerate(seq.groups):
        pos = group.position
        if pos is None or pos.beat is None:
            continue
        meter = _meter_for_group(meters, gi)
        if meter is None:
            continue
        # MEI data.BEAT: the downbeat is ts:1, the barline of the next measure is
        # ts:(numerator + 1). Anything at or past that spills into the next measure.
        upper = meter.numerator + 1
        if not (1 <= pos.beat < upper):
            where = f"m:{pos.measure}," if pos.measure is not None else ""
            warnings.append(
                f"group {gi} ({where}ts:{pos.beat}) is outside meter "
                f"{meter.numerator}/{meter.denominator} — ts must be in [1, {upper})"
            )
    return warnings
