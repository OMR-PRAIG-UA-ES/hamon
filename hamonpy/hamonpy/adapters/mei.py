"""MEI / HA-MEI adapter with analytical-layer support — STEPS 9.8.3.

MEI has no native element for tonal regions or non-harmonic tones, so the hamon
MEI customization (HA-MEI) carries the analytical layer on `<harm>` via the
`@type` token. This adapter reads those `<harm>` elements, in document order, and
reconstructs a hamon surface that the analytical parser turns into a
HamonSequence with regions, layers and ToneSemantic.

`<harm type="…">` content → hamon:

    key | region | modulation   -> `@key:<key>`        (opens a tonal region)
    tonicization                 -> `@key:<degree>`     (nested tonicization)
    function | degree | bass     -> `<type>:<content>`  (analytical layer)
    chord                        -> `chord:<content>`
    tone | melodic               -> `melodic:<content>` (HT/NHT, ToneSemantic)
    (anything else / absent)     -> `<content>`         (plain chord/roman/…)

Key content uses hamon key syntax (`C`, `A:minor`, `D:dorian`, a degree like `V`);
bare lowercase letters (`a`, `bb`) are read as minor keys for convenience.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from dataclasses import replace

from hamonpy.ast import (
    HamonSequence, HarmonyAttributes, HarmonyLabel, Key, Position, ToneSemantic, TonalRegion,
)
from hamonpy.parse import parse_hamon_sequence

_HARM_RE = re.compile(r"<harm\b([^>]*?)(?:/>|>([^<]*)</harm>)", re.IGNORECASE | re.DOTALL)
# Ordered scan of measures + harms, so a <harm>'s @tstamp resolves against the
# enclosing <measure @n>.
_MEASURE_OR_HARM_RE = re.compile(
    r"<measure\b([^>]*)>|<harm\b([^>]*?)(?:/>|>([^<]*)</harm>)",
    re.IGNORECASE | re.DOTALL,
)
_BARE_KEY_RE = re.compile(r"^([A-Ga-g])([#b♯♭]*)$")

# Recognised HA-MEI `<harm @type>` tokens (analytical layer + tonal-region markers).
# `@type` is an NMTOKENS set; any other token (e.g. an `omr`/`score` harmony-layer
# provenance token) is ignored here.
_KNOWN_TYPE_TOKENS = frozenset({
    "key", "region", "modulation", "tonicization", "tonicisation",
    "function", "degree", "bass", "chord", "tone", "melodic", "note",
})


def _attr(attrs: str, name: str) -> Optional[str]:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs, re.IGNORECASE)
    return m.group(1) if m else None


def _harm_position(attrs: str, measure: Optional[int]) -> Optional[Position]:
    """Time-aligned Position from a <harm>'s @startid / @tstamp (or None)."""
    startid = _attr(attrs, "startid")
    if startid:
        return Position(ref=startid)
    tstamp = _attr(attrs, "tstamp") or _attr(attrs, "tstamp.ges")
    if tstamp:
        try:
            return Position(measure=measure, beat=float(tstamp))
        except ValueError:
            return None
    return None


def _mei_key_to_surface(content: str) -> str:
    """Normalize a HA-MEI key string to hamon `@key:` syntax. Bare lowercase letter
    = minor (`a` → `A:minor`); uppercase = major; `:mode` / degrees pass through."""
    s = content.strip()
    m = _BARE_KEY_RE.match(s)
    if m:
        letter, accs = m.group(1), m.group(2)
        if letter.islower():
            return f"{letter.upper()}{accs}:minor"
        return f"{letter}{accs}"
    return s


def mei_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return mei_to_hamon(fh.read())


def mei_to_hamon(text: str) -> HamonSequence:
    """Parse MEI/HA-MEI `<harm>` elements into a layered HamonSequence with regions."""
    lines: List[str] = []
    # Position per group-producing line (region directives produce no group).
    group_positions: List[Optional[Position]] = []
    group_end_refs: List[Optional[str]] = []
    current_measure: Optional[int] = None

    for m in _MEASURE_OR_HARM_RE.finditer(text):
        if m.group(1) is not None:  # <measure ...>
            n = _attr(m.group(1), "n")
            current_measure = int(n) if n and n.isdigit() else (current_measure or 0) + 1
            continue

        attrs, inner = m.group(2), m.group(3)
        content = (inner or "").strip() or (_attr(attrs, "label") or "").strip()
        if not content:
            continue
        content = _xml_unescape(content)  # the writer escapes; mirror it (PD->T, R&B, …)
        # `@type` is an NMTOKENS set (space-separated). It may carry an `omr`/`score`
        # provenance token marking the harmony layer; we ignore that here and keep the
        # HA-MEI analytical/region token (function/degree/key/tonicization/...).
        type_tokens = [tok.replace("hamon:", "") for tok in (_attr(attrs, "type") or "").lower().split()]
        t = next((tok for tok in type_tokens if tok in _KNOWN_TYPE_TOKENS), "")

        if t in ("key", "region", "modulation"):
            lines.append(f"@key:{_mei_key_to_surface(content)}")
            continue  # region directive — no group
        if t in ("tonicization", "tonicisation"):
            lines.append(f"@key:{content}")
            continue

        if t in ("function", "degree", "bass"):
            label = f"{ {'function': 'fn', 'degree': 'rn', 'bass': 'fb'}[t] }:{content}"
        elif t == "chord":
            label = f"cs:{content}"
        elif t in ("tone", "melodic", "note"):
            label = f"melodic:{content}"
        else:
            label = content
        position = _harm_position(attrs, current_measure)
        # Two <harm>s on the same @tstamp are two readings of one moment (a chord symbol
        # and its Roman numeral): one layered group, as the writer laid them out.
        if (position is not None and group_positions and position == group_positions[-1]
                and lines and not lines[-1].startswith("@")):
            lines[-1] += f",{label}"
            continue
        lines.append(label)
        group_positions.append(position)
        group_end_refs.append(_attr(attrs, "endid"))

    if not lines:
        return HamonSequence(groups=[])

    seq = parse_hamon_sequence("@version:0.2.0\n@auto\n" + "\n".join(lines))

    # The surface parser labels every absolute @key: as kind "key"; normalize the
    # 2nd+ key regions to "modulation" (consistent with the DCML adapter).
    seen_key = False
    for r in seq.regions or []:
        if r.kind in ("key", "region"):
            if seen_key:
                r.kind = "modulation"
            seen_key = True

    # Attach each group-producing line's position and extent to its group (same order).
    for i, (pos, end_ref) in enumerate(zip(group_positions, group_end_refs)):
        if i >= len(seq.groups):
            break
        if pos is not None:
            seq.groups[i].position = pos
        # @endid is the structural counterpart of @startid: where the harmony ends.
        # (@tstamp2 is a measure+beat offset, so reading it needs the meter — not yet.)
        if end_ref and seq.groups[i].primary:
            label = seq.groups[i].primary[0]
            label.attributes = (replace(label.attributes, endRef=end_ref)
                                if label.attributes else HarmonyAttributes(endRef=end_ref))
    return seq


# ---------------------------------------------------------------------------
# Export — HamonSequence → MEI/HA-MEI <harm> elements (STEPS 8.1, Python)
# ---------------------------------------------------------------------------

_ACC_GLYPH = {"sharp": "#", "flat": "b", "double-sharp": "##", "double-flat": "bb", "natural": ""}
_LAYER_TYPES = {"function", "degree", "bass", "chord", "melodic"}


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _xml_unescape(s: str) -> str:
    """Reverse of _xml_escape (entity order matters: &amp; last)."""
    return (s.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def _key_to_surface(key: Key) -> str:
    """A Key → hamon @key: content: 'C', 'A:minor', 'D:dorian'."""
    name = key.tonic.note + _ACC_GLYPH.get(key.tonic.accidental or "", "")
    mode = key.mode or "major"
    return name if mode in ("major", "ionian") else f"{name}:{mode}"


def _tone_to_content(sem: ToneSemantic) -> str:
    pitch = (sem.pitch.note + _ACC_GLYPH.get(sem.pitch.accidental or "", "")) if sem.pitch else ""
    if sem.category == "harmonic":
        return f"{pitch}[HT]"
    t = sem.type
    return f"{pitch}[NHT:{t}]" if t and t != "chord-tone" else f"{pitch}[NHT]"


def _label_content(label: HarmonyLabel) -> str:
    """The bare <harm> content for a label (layer prefix stripped from the surface)."""
    sem = label.semantic
    if isinstance(sem, ToneSemantic):
        return _tone_to_content(sem)
    surface = label.surface or ""
    if label.layer and surface.startswith(f"{label.layer}:"):
        return surface[len(label.layer) + 1:]
    return surface


def _label_type(label: HarmonyLabel) -> Optional[str]:
    if isinstance(label.semantic, ToneSemantic):
        return "tone"
    if label.layer in _LAYER_TYPES:
        return label.layer
    # plain labels carry no @type; the importer auto-detects the system.
    return None


def _region_harm(r: TonalRegion) -> str:
    if r.kind == "tonicization":
        content = r.degree or _key_to_surface(r.key)
        return f'<harm type="hamon:tonicization">{_xml_escape(content)}</harm>'
    rtype = "hamon:modulation" if r.kind == "modulation" else "hamon:key"
    return f'<harm type="{rtype}">{_xml_escape(_key_to_surface(r.key))}</harm>'


def hamon_to_mei(seq: HamonSequence, wrap: bool = False) -> str:
    """Serialize a HamonSequence to HA-MEI <harm> elements (the analytical layer).

    Tonal regions are emitted as `<harm type="hamon:key|modulation|tonicization">`
    just before the group where they start; each label becomes a `<harm>` carrying
    its analytical layer (`@type`), its beat (`@tstamp`) and bare content. Round-trips
    with `mei_to_hamon`. With `wrap=True` the elements are nested in `<measure>`s — one
    per measure the positions name, or a single anonymous one for an unpositioned
    sequence — for a self-contained fragment.
    """
    regions = seq.regions or []
    # regions starting at each group index, key/modulation before tonicization
    starts: dict = {}
    for ri, r in enumerate(regions):
        starts.setdefault(r.from_group, []).append((0 if r.kind != "tonicization" else 1, ri, r))
    for gi in starts:
        starts[gi].sort(key=lambda t: (t[0], t[1]))

    lines: List[Tuple[Optional[int], str]] = []   # (measure, element)
    for gi, group in enumerate(seq.groups):
        pos = group.position
        measure = pos.measure if pos is not None else None
        tstamp = ""
        if pos is not None and pos.beat is not None:
            beat = pos.beat
            tstamp = f' tstamp="{int(beat) if float(beat).is_integer() else beat}"'
        for _prio, _ri, r in starts.get(gi, []):
            lines.append((measure, _region_harm(r)))
        for label in group.primary:
            content = _label_content(label)
            if not content:
                continue
            t = _label_type(label)
            attr = f' type="{t}"' if t else ""
            lines.append((measure, f"<harm{attr}{tstamp}>{_xml_escape(content)}</harm>"))
    # regions anchored past the last group (open-ended trailing regions)
    for gi in sorted(starts):
        if gi >= len(seq.groups):
            for _prio, _ri, r in starts[gi]:
                lines.append((None, _region_harm(r)))

    if not wrap:
        body = "\n".join(el for _, el in lines)
        return body + ("\n" if body else "")
    if not any(m is not None for m, _ in lines):
        return "<measure>\n" + "\n".join(el for _, el in lines) + "\n</measure>\n"
    out: List[str] = []
    current: Optional[int] = None
    for measure, el in lines:
        if measure is not None and measure != current:
            if current is not None:
                out.append("</measure>")
            out.append(f'<measure n="{measure}">')
            current = measure
        elif current is None:            # an unpositioned lead-in before the first bar
            out.append("<measure>")
            current = 0
        out.append(el)
    out.append("</measure>")
    return "\n".join(out) + "\n"
