"""Serialize a HamonSequence to the canonical JSON form (grammar/hamon-schema.json).

`to_canonical` recursively turns dataclasses into dicts, converts snake_case field
names to the schema's camelCase, and drops None / empty values — yielding the same
shape the JSON Schema describes (and that the TS AST produces natively).
"""
from __future__ import annotations

import dataclasses
import json
import re
from typing import Any, Optional

from .ast import HamonSequence


def _camel(key: str) -> str:
    return re.sub(r"_([a-z])", lambda m: m.group(1).upper(), key)


def to_canonical(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        out = {}
        for key in value:
            cv = to_canonical(value[key])
            if cv is None:
                continue
            if isinstance(cv, (list, dict)) and len(cv) == 0:
                continue
            out[_camel(key)] = cv
        return out
    if isinstance(value, (list, tuple)):
        return [to_canonical(v) for v in value]
    return value


def sequence_to_dict(seq: HamonSequence) -> dict:
    """Return the canonical (schema-shaped, camelCase) dict for a HamonSequence."""
    return to_canonical(seq)


def sequence_to_json(seq: HamonSequence, indent: int = 2) -> str:
    """Return the canonical JSON string for a HamonSequence."""
    return json.dumps(sequence_to_dict(seq), indent=indent, ensure_ascii=False)


def sequence_to_hamon_text(seq: HamonSequence) -> str:
    """Serialize a HamonSequence back to its ``.hamon`` surface text.

    Reconstructs the exact line-oriented surface form: an optional
    ``@version:`` line, an optional ``@<system>`` hint line, the ``@key:`` /
    region directives (re-emitted before the group they open), then one line per
    group.  Within a group, co-temporal (layered) labels are joined with
    ``" , "`` and alternatives with ``" | "`` — the same separators the parser
    consumes, so ``parse_hamon_sequence(sequence_to_hamon_text(seq))`` round-trips.
    """
    lines: list[str] = []
    if seq.version:
        lines.append(f"@version:{seq.version}")
    if seq.sequence_system_hint:
        lines.append(f"@{seq.sequence_system_hint}")

    # Index meter + region directives by the group they open.
    meters_at: dict[int, list] = {}
    for meter in (seq.meters or []):
        meters_at.setdefault(meter.from_group, []).append(meter)
    regions_at: dict[int, list] = {}
    for region in (seq.regions or []):
        regions_at.setdefault(region.from_group, []).append(region)

    for gi, group in enumerate(seq.groups):
        for meter in meters_at.get(gi, []):
            lines.append(f"@meter:{meter.numerator}/{meter.denominator}")
        for region in regions_at.get(gi, []):
            lines.append(f"@key:{_render_key_target(region)}")
            if region.scales:
                lines.append("@scale:" + ",".join(s.name for s in region.scales))
        primary = ",".join(_label_surface(label) for label in group.primary)
        alts = [
            ",".join(_label_surface(label) for label in alt)
            for alt in (group.alternatives or [])
        ]
        body = " | ".join([primary, *alts]) if alts else primary
        postag = _render_position(group.position)  # v0.4: position first
        lines.append(f"{postag},{body}" if postag else body)

    return "\n".join(lines) + "\n"


# canonical internal layer role → v0.4 short tag
_LAYER_TO_TAG = {"chord": "cs", "degree": "rn", "nashville": "ns",
                 "bass": "fb", "function": "fn"}


def _label_surface(label) -> str:
    """The label's surface, prefixed with its v0.4 layer tag when it has one and
    suffixed with any extent an adapter set programmatically.

    A parsed label already carries `[dur:…]`/`[endref:…]` inside its surface, so those
    are left alone. An adapter that read the extent from a source (Dezrann `duration`,
    DCML `duration_qb`, AugmentedNet `a_duration`, MEI `@endid`) sets the attribute
    without touching the surface — and without this the text serialization would drop
    the very thing the extent work exists to keep.
    """
    surface = label.surface
    attributes = getattr(label, "attributes", None)
    if attributes is not None:
        duration = getattr(attributes, "duration", None)
        if duration is not None and "[dur:" not in surface:
            surface += f"[dur:{_render_fraction(duration)}]"
        seconds = getattr(attributes, "durationSeconds", None)
        if seconds is not None and "[dur:" not in surface:
            surface += f"[dur:{_fmt_num(seconds)}s]"
        end_ref = getattr(attributes, "endRef", None)
        if end_ref and "[endref:" not in surface:
            surface += f"[endref:{end_ref}]"

    layer = getattr(label, "layer", None)
    if layer:
        return f"{_LAYER_TO_TAG.get(layer, layer)}:{surface}"
    return surface


def _render_fraction(fraction) -> str:
    """A Fraction as a surface value: whole numbers bare (`4`), the rest as `3/4`."""
    if fraction.denominator == 1:
        return str(fraction.numerator)
    return f"{fraction.numerator}/{fraction.denominator}"


def _fmt_num(n: float) -> str:
    """Render a beat without a trailing ``.0`` (3.0 → '3', 1.5 → '1.5')."""
    return str(int(n)) if float(n).is_integer() else str(n)


def _render_position(pos) -> Optional[str]:
    """Render a Position as leading, comma-separated items:
    ``m:25,ts:1`` · ``t:5/4`` · ``s:12.34`` · ``ref:note-9``."""
    if pos is None:
        return None
    parts = []
    if pos.measure is not None:
        parts.append(f"m:{pos.measure}")
    if pos.beat is not None:
        parts.append(f"ts:{_fmt_num(pos.beat)}")
    if pos.time is not None:
        parts.append(f"t:{pos.time.numerator}/{pos.time.denominator}")
    if pos.seconds is not None:
        parts.append(f"s:{_fmt_num(pos.seconds)}")
    if pos.ref:
        parts.append(f"ref:{pos.ref}")
    return ",".join(parts) if parts else None


_PITCH_GLYPH = {"flat": "b", "sharp": "#", "double-flat": "bb", "double-sharp": "##"}


def _render_key_target(region) -> str:
    """Render a TonalRegion's keyDecl target (e.g. ``C``, ``A:minor``, ``V``)."""
    # Tonicizations carry the tonicized scale degree, e.g. "@key:V".
    if region.degree:
        return region.degree
    key = region.key
    target = f"{key.tonic.note}{_PITCH_GLYPH.get(key.tonic.accidental or '', '')}"
    if key.mode and key.mode != "major":
        target += f":{key.mode}"
    return target
