"""Rock Corpus adapter — de Clercq & Temperley harmonic analyses (.har) → HamonSequence.

The Rock Corpus (http://rockcorpus.midside.com) encodes each song's harmony in a small
recursive DSL:

* ``Name: ...`` defines a *rule* (a section such as ``Vr``, ``Ch``); ``S:`` is the song,
  whose body expands every reference;
* ``$Name`` substitutes a rule, ``$Name*N`` repeats it N times;
* ``|`` separates measures; ``|*N`` (or a bare ``*N``) repeats the preceding measure to N
  measures total; within a measure, chords are space-separated and ``.`` marks a new beat;
* ``[Bb]`` sets the tonic (pitch only; mode is carried by the numerals), ``[12/8]`` a time
  signature (ignored); ``R`` is a rest; ``%`` starts a comment (whole-line or inline).

Chords are Roman numerals relative to the current tonic and mostly parse straight into
HAMON's rn layer; a few Rock-Corpus quality suffixes are normalised (``d7`` dominant
seventh → ``7``, ``h7`` half-diminished → ``ø7``). Tonics become ``TonalRegion``s and each
measure index becomes a ``Position``. Whatever stays un-parseable is preserved as text.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from hamonpy.ast import (
    HamonSequence, HarmonyGroup, HarmonyLabel, Key, PitchClass, Position,
    RenderingHints, TextSemantic, TonalRegion,
)
from hamonpy.parse import parse_hamon_sequence

_RULE_RE = re.compile(r"^\s*([A-Za-z][\w']*)\s*:\s*(.*)$")
_KEY_TOKEN = re.compile(r"^\[([A-Ga-g][#b]?)\]$")          # [Bb], [a]  — tonic pitch
_REF_RE = re.compile(r"^\$([A-Za-z][\w']*)(?:\*(\d+))?$")   # $Vr, $A*2
_REPEAT_RE = re.compile(r"^\|?\*(\d+)$")                    # |*4 or *4


def _strip_comment(line: str) -> str:
    return line.split("%", 1)[0].rstrip()


def _is_roman(surface: str) -> bool:
    try:
        g = parse_hamon_sequence("@rn\n" + surface).groups
    except Exception:  # noqa: BLE001
        return False
    return bool(g) and g[0].primary[0].semantic.kind == "roman"


def _rock_to_hamon_roman(tok: str) -> str:
    """Map Rock-Corpus quality letters HAMON's Roman grammar doesn't take to its glyphs:
    ``d`` = dominant seventh (drop it, the figure stays), ``h`` = half-diminished (→ ``ø``),
    ``x`` = diminished seventh (→ ``°``), ``o`` = diminished triad (→ ``°``)."""
    s = re.sub(r"d(?=\d)", "", tok)        # Id42 → I42, Id7 → I7
    s = s.replace("d7", "7")
    s = re.sub(r"h(?=\d)", "ø", s)          # iih43 → iiø43
    s = re.sub(r"x(?=\d)", "°", s)          # viix7 → vii°7
    s = re.sub(r"o(?=\d|/|$)", "°", s)      # iio → ii°, iio6 → ii°6, viio/ii → vii°/ii
    return s


def _chord_to_label(tok: str) -> Optional[HarmonyLabel]:
    """One Rock-Corpus chord token → a Roman (or text) label, or None for a rest."""
    if tok in (".", "R", "|"):
        return None
    candidate = tok if _is_roman(tok) else None
    if candidate is None:
        alt = _rock_to_hamon_roman(tok)
        candidate = alt if _is_roman(alt) else None
    if candidate is not None:
        from dataclasses import replace
        lab = parse_hamon_sequence("@rn\n" + candidate).groups[0].primary[0]
        return replace(lab, surface=tok)
    return HarmonyLabel(
        surface=tok, semantic=TextSemantic(text=tok), rendering=RenderingHints(),
        detected_system="text", system="text", sequence_system_hint="rn",
    )


def _parse_rules(text: str) -> Dict[str, List[str]]:
    rules: Dict[str, List[str]] = {}
    for raw in text.splitlines():
        line = _strip_comment(raw)
        m = _RULE_RE.match(line)
        if m:
            rules[m.group(1)] = m.group(2).split()
    return rules


def _expand(tokens: List[str], rules: Dict[str, List[str]], depth: int = 0) -> List[str]:
    """Recursively expand $rule references (with optional *N repetition)."""
    if depth > 64:
        return []
    out: List[str] = []
    for tok in tokens:
        ref = _REF_RE.match(tok)
        if ref and ref.group(1) in rules:
            times = int(ref.group(2) or 1)
            expanded = _expand(rules[ref.group(1)], rules, depth + 1)
            out.extend(expanded * times)
        else:
            out.append(tok)
    return out


def _tonic(pitch: str) -> Key:
    acc = {"#": "sharp", "b": "flat"}.get(pitch[1:2], None) if len(pitch) > 1 else None
    return Key(tonic=PitchClass(note=pitch[0].upper(), accidental=acc), mode=None)


def rock_corpus_to_hamon(text: str) -> HamonSequence:
    rules = _parse_rules(text)
    if "S" not in rules:
        return HamonSequence(groups=[])
    stream = _expand(rules["S"], rules)

    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    open_key: Optional[int] = None
    measure = 0
    current: List[str] = []

    def flush(times: int) -> None:
        nonlocal measure
        for _ in range(max(times, 1)):
            measure += 1
            for tok in current:
                lab = _chord_to_label(tok)
                if lab is not None:
                    groups.append(HarmonyGroup(primary=[lab], position=Position(measure=measure)))

    for tok in stream:
        km = _KEY_TOKEN.match(tok)
        if km:
            gi = len(groups)
            if open_key is not None and gi > 0:
                regions[open_key].to_group = gi - 1
            regions.append(TonalRegion(
                key=_tonic(km.group(1)), kind=("key" if open_key is None else "modulation"),
                from_group=gi))
            open_key = len(regions) - 1
            continue
        if tok.startswith("[") and tok.endswith("]"):
            continue  # time signature or other bracket directive
        rep = _REPEAT_RE.match(tok)
        if rep:
            flush(int(rep.group(1)))
            current = []
            continue
        if tok == "|":
            flush(1)
            current = []
            continue
        current.append(tok)
    flush(1)  # trailing measure

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)


def rock_corpus_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return rock_corpus_to_hamon(fh.read())
