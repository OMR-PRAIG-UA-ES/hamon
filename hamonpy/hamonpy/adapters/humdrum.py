"""Humdrum (**kern family) adapter with analytical-layer support — STEPS 9.8.2.

Unlike `formats.read_harmony_labels` (which flattens every harmony spine into one
deduplicated list of surface strings), this adapter preserves the *spine layout*:
each harmony spine becomes an analytical layer, and co-temporal tokens (one data
line) become one HarmonyGroup whose primary labels are tagged with their layer.

Spine → layer:
    **harm      -> degree     (Roman-numeral harmonic analysis)
    **function  -> function   (Riemann T/S/D functional analysis)
    **fb        -> bass       (figured bass)
    **mxhm / **jazz / **irb / **harte -> chord   (chord symbols)
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from hamonpy.ast import (
    ChordSymbolSemantic,
    FiguredBassSemantic,
    FunctionalSemantic,
    HamonSequence,
    HarmonyGroup,
    HarmonyLabel,
    Key,
    NashvilleSemantic,
    PitchClass,
    Position,
    RenderingHints,
    TextSemantic,
    TonalRegion,
)
from hamonpy.parse import parse_hamon_sequence
from hamonpy.adapters.formats import _normalize_kern_token
from hamonpy.adapters.dcml import _dcml_surface_to_roman

_SPINE_LAYER: Dict[str, str] = {
    "harm": "degree",
    "function": "function",
    "fb": "bass",
    "mxhm": "chord",
    "jazz": "chord",
    "irb": "chord",
    "harte": "chord",
}
_LAYER_SYSTEM: Dict[str, str] = {
    "degree": "rn", "function": "fun", "bass": "fb", "chord": "cs",
}
_FUNC_TOKEN_RE = re.compile(r"^(T|S|D|P|PD|SD|DD)$")
# TAVERN and other **function encodings write predominant as a bare "P"; HAMON's
# vocabulary calls it "PD". The glyph is kept as the surface, the meaning normalized.
_FUNC_ALIAS = {"P": "PD"}
# A spine token may carry a leading **recip duration ("4I", "8.V", "2T"). It is rhythm,
# not harmony, and has to come off before the label is parsed — without this, "4I" falls
# through to opaque text and "4Ib" lexes as the Nashville degree 4, silently wrong.
#
# The prefix comes off only when what is left behind is a label that spine could hold:
# a Roman numeral for **harm, a functional token for **function. Anything else keeps its
# leading digit, so figured bass ("6-5") survives, and so does a Nashville degree ("2m")
# parked in a **harm spine by a workaround export.
_RECIP_RE = re.compile(r"^\d+\.*(?=[^\d.])")
_ROMAN_RE = re.compile(r"^[b#]*(?:III|II|IV|I|VII|VI|V|iii|ii|iv|i|vii|vi|v)")

# **harm spells inversion with a trailing letter — a root position, b first, c second,
# d third — where HAMON (and every Roman-numeral convention it speaks) uses the figured
# bass. Without this, "Ib" and "iib" fall through to opaque text.
_INVERSION_RE = re.compile(
    r"^([b#]*(?:III|II|IV|I|VII|VI|V|iii|ii|iv|i|vii|vi|v)[o+\u00B0\u00F8]?)"
    r"(7|9|11|13)?([abcd])$")
_INVERSION_FIGURE = {
    ("triad", "a"): "", ("triad", "b"): "6", ("triad", "c"): "64",
    ("7th", "a"): "7", ("7th", "b"): "65", ("7th", "c"): "43", ("7th", "d"): "42",
}


def _expand_harm_inversion(token: str) -> str:
    """`Ib` -> `I6`, `V7b` -> `V65`, `iic` -> `ii64`. Unchanged if it is not that shape."""
    m = _INVERSION_RE.match(token)
    if not m:
        return token
    degree, seventh, letter = m.groups()
    figure = _INVERSION_FIGURE.get(("7th" if seventh == "7" else "triad", letter))
    if figure is None:          # 9/11/13 inversions, or a triad "d": leave it alone
        return token
    return degree + figure
_SPINE_RE = re.compile(r"^\*\*(harm|function|fb|mxhm|jazz|irb|harte)$", re.IGNORECASE)


def humdrum_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return humdrum_to_hamon(fh.read())


def _label_from_token(surface: str, layer: str) -> HarmonyLabel:
    """Normalize a single spine token into a layer-tagged HarmonyLabel."""
    norm = _normalize_kern_token(surface)
    # Duration first, then spelling: the token off the page is "4Ib", so the recip has
    # to go before the inversion letter can be recognized.
    stripped = _RECIP_RE.sub("", norm, count=1)
    if stripped != norm and (
            (layer == "degree" and _ROMAN_RE.match(stripped))
            or (layer == "function" and _FUNC_TOKEN_RE.match(stripped))):
        norm = stripped
    if layer == "degree":
        norm = _expand_harm_inversion(norm)
    sub = parse_hamon_sequence(norm)
    base = sub.groups[0].primary[0] if sub.groups and sub.groups[0].primary else None
    if base is None:
        from hamonpy.ast import TextSemantic
        base = HarmonyLabel(surface=norm, semantic=TextSemantic(text=norm),
                            rendering=RenderingHints(), detected_system="text", system="text")

    semantic = base.semantic
    # The **function spine intends a functional token, but 'D' is shadowed by NOTE.
    if layer == "function" and _FUNC_TOKEN_RE.match(norm) and not isinstance(
            semantic, FunctionalSemantic):
        semantic = FunctionalSemantic(chain=[_FUNC_ALIAS.get(norm, norm)])
    # The **fb spine is figured bass, even when a number lexes as a Nashville degree.
    if layer == "bass" and isinstance(semantic, NashvilleSemantic):
        semantic = FiguredBassSemantic(
            number=semantic.number, prefixAccidentals=semantic.prefixAccidentals, tail=semantic.tail,
        )

    return HarmonyLabel(
        surface=norm,
        semantic=semantic,
        rendering=base.rendering,
        detected_system=_LAYER_SYSTEM.get(layer, base.detected_system),
        system=_LAYER_SYSTEM.get(layer, base.system),
        layer=layer,
    )


def humdrum_to_hamon(text: str) -> HamonSequence:
    """Parse a Humdrum file with one or more harmony spines into a layered HamonSequence."""
    lines = text.splitlines()

    # Locate the exclusive-interpretation line that declares the spines.
    header_idx = -1
    for i, line in enumerate(lines):
        if "**" in line and any(_SPINE_RE.match(tok.strip()) for tok in line.split("\t")):
            header_idx = i
            break
    if header_idx < 0:
        return HamonSequence(groups=[])

    header_cols = lines[header_idx].split("\t")
    # column index -> layer
    col_layer: Dict[int, str] = {}
    for ci, tok in enumerate(header_cols):
        m = _SPINE_RE.match(tok.strip())
        if m:
            col_layer[ci] = _SPINE_LAYER[m.group(1).lower()]

    layers_used = set(col_layer.values())
    single_layer = next(iter(layers_used)) if len(layers_used) == 1 else None

    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    current_measure: Optional[int] = None
    for line in lines[header_idx + 1:]:
        if not line or re.match(r"^\*-(\t\*-)*$", line):
            if re.match(r"^\*-(\t\*-)*$", line):
                break
            continue
        if line[0] == "=":                       # barline → measure number (e.g. "=24")
            bm = re.match(r"^=+(\d+)", line.split("\t")[0])
            if bm:
                current_measure = int(bm.group(1))
            continue
        if line[0] == "*":
            # A `*C:` / `*b-:` tandem interpretation states the key from here on: the
            # first one is the home key, a later one a modulation.
            for tok in line.split("\t"):
                km = _KEY_TANDEM_RE.match(tok.strip())
                if km:
                    key = _parse_humdrum_key(km.group(1))
                    if key is not None and not (regions and regions[-1].from_group == len(groups)):
                        regions.append(TonalRegion(
                            key=key, kind="key" if not regions else "modulation",
                            from_group=len(groups)))
                    break
            continue
        if line[0] == "!":
            continue
        cols = line.split("\t")
        labels: List[HarmonyLabel] = []
        for ci, layer in col_layer.items():
            tok = cols[ci].strip() if ci < len(cols) else ""
            if tok and tok != ".":
                lbl = _label_from_token(tok, layer)
                # With a single harmony spine there is no "stack" — drop the layer tag
                # so the output matches a plain single-system reading.
                if single_layer is not None:
                    lbl.layer = None
                labels.append(lbl)
        if labels:
            position = Position(measure=current_measure) if current_measure is not None else None
            groups.append(HarmonyGroup(primary=labels, position=position))

    hint = _LAYER_SYSTEM[single_layer] if single_layer else "auto"
    return HamonSequence(groups=groups, sequence_system_hint=hint, regions=regions or None)


# ---------------------------------------------------------------------------
# Key / modulation dataset (DDMAL): **text Roman analysis + 'KEY=>:degree'
# ---------------------------------------------------------------------------

_HKEY_RE = re.compile(r"^([A-Ga-g])([#-]*)$")          # Humdrum key: 'C', 'd', 'B-', 'f#'
_KEY_TANDEM_RE = re.compile(r"^\*([A-Ga-g][#-]*):$")   # '*C:' tandem
_MODULATION_RE = re.compile(r"^([A-Ga-g][#-]*)=>:?(.*)$")  # 'C=>:I', 'd=>:i', 'B-=>:I', 'C=>'


def _parse_humdrum_key(s: str):
    m = _HKEY_RE.match(s.strip())
    if not m:
        return None
    letter, accs = m.group(1), m.group(2)
    mode = "major" if letter.isupper() else "minor"
    off = accs.count("#") - accs.count("-")
    acc = {1: "sharp", 2: "double-sharp", -1: "flat", -2: "double-flat"}.get(off)
    return Key(tonic=PitchClass(note=letter.upper(), accidental=acc), mode=mode)


def _degree_label(tok: str) -> HarmonyLabel:
    res = _dcml_surface_to_roman(tok)
    if res is not None:
        semantic, rendering, _ = res
    else:
        semantic, rendering = TextSemantic(text=tok), RenderingHints()
    return HarmonyLabel(surface=tok, semantic=semantic, rendering=rendering,
                        detected_system="rn", system="rn", sequence_system_hint="rn")


def key_modulation_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return key_modulation_to_hamon(fh.read())


def key_modulation_to_hamon(text: str) -> HamonSequence:
    """Parse the DDMAL key_modulation_dataset encoding: a Roman-numeral analysis in
    `**text` spines, with the home key as a `*KEY:` tandem and modulations marked
    inline as `KEY=>:degree`. Produces degrees as groups and key changes as
    `TonalRegion`s (first = home key, later = modulations)."""
    lines = text.splitlines()
    header_idx = -1
    for i, line in enumerate(lines):
        cols = line.split("\t")
        if any(c.strip() == "**text" for c in cols):
            header_idx = i
            break
    if header_idx < 0:
        return HamonSequence(groups=[])

    text_cols = [i for i, c in enumerate(lines[header_idx].split("\t")) if c.strip() == "**text"]

    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    open_idx: Optional[int] = None
    pending_home = None
    prev_deg: Optional[str] = None     # collapse consecutive repeats of the same label

    def open_region(key, kind: str):
        nonlocal open_idx
        gi = len(groups)
        if open_idx is not None and gi > 0:
            regions[open_idx].to_group = gi - 1
        regions.append(TonalRegion(key=key, kind=kind, from_group=gi))
        open_idx = len(regions) - 1

    for line in lines[header_idx + 1:]:
        if not line or re.match(r"^\*-(\t\*-)*$", line):
            if re.match(r"^\*-(\t\*-)*$", line):
                break
            continue
        if line.startswith("!"):
            continue
        if line.startswith("*"):
            for tok in line.split("\t"):
                km = _KEY_TANDEM_RE.match(tok.strip())
                if km and open_idx is None and not groups and pending_home is None:
                    pending_home = _parse_humdrum_key(km.group(1))
            continue
        if line.startswith("="):
            continue

        cols = line.split("\t")
        tok = ""
        for ci in text_cols:
            v = cols[ci].strip() if ci < len(cols) else ""
            if v and v != ".":
                tok = v
                break
        if not tok:
            continue

        mod = _MODULATION_RE.match(tok)
        if mod:
            key = _parse_humdrum_key(mod.group(1))
            if key is not None:
                open_region(key, "key" if open_idx is None else "modulation")
            deg = mod.group(2).strip()
            if deg:                       # the key changed → always a new event
                groups.append(HarmonyGroup(primary=[_degree_label(deg)]))
                prev_deg = deg
        else:
            if open_idx is None and pending_home is not None:
                open_region(pending_home, "key")
            if tok != prev_deg:           # collapse the spine's per-note repeats
                groups.append(HarmonyGroup(primary=[_degree_label(tok)]))
                prev_deg = tok

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)
