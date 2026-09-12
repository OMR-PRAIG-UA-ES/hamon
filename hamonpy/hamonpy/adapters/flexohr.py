"""FlexOHR integration adapter for hamonpy.

Converts between HAMON's harmony AST and **FlexOHR** (DCMLab's *Flexible and
Extensible Object for Harmony Representation*, ``flexohr`` on PyPI). Scoped to the
core of the two shared systems — **chord symbols** and **Roman numerals** — so a
HAMON label can be handed to FlexOHR's object model (and back) for the
analysis-side of the collaboration, with HAMON as the wire format.

Requires: flexohr >= 1  (install with: pip install hamonpy[flexohr])

Usage:
    from hamonpy.adapters.flexohr import (
        hamon_to_flexohr,          # HamonSequence -> list[flexohr.OHR]
        flexohr_to_hamon,          # list[flexohr.OHR] -> HamonSequence
        hamon_semantic_to_ohr,     # one chordSymbol/roman semantic -> OHR
        ohr_to_hamon_semantic,     # one OHR -> semantic
    )

Scope / limitations (first cut):
- Chord symbols round-trip root, quality+seventh, suspensions and slash bass.
  Extensions / alterations / adds / omits are not carried into FlexOHR yet.
- Roman numerals map degree (+ accidentals), triad/seventh quality and the
  figured-bass inversion, in a key context (default C major, overridable).
  Applied/secondary chains, pedal, and parenthesised changes are out of scope.
"""
from __future__ import annotations

import re
from typing import List, Optional

from hamonpy.ast import (
    ChordSymbolSemantic,
    HamonSequence,
    HarmonyGroup,
    HarmonyLabel,
    PitchClass,
    RenderingHints,
    RomanSemantic,
)

try:  # optional dependency
    import flexohr  # noqa: F401
    import flexohr.codecs.dcml  # noqa: F401  (side-effect: registers the "dcml" codec)
    from flexohr import OHR
    from flexohr.harmony.harmony_enums import ChordQuality, Inversion, CollectionType, ToneFunction
    from flexohr.paradigms.pitchspace import SPC
    from flexohr.paradigms.pitchspace.scale import Scale
    from flexohr.paradigms.pitchspace.scale_degrees import SD

    _HAVE_FLEXOHR = True
except ImportError:  # pragma: no cover - exercised only when flexohr is absent
    _HAVE_FLEXOHR = False


def _require() -> None:
    if not _HAVE_FLEXOHR:
        raise ImportError(
            "flexohr is not installed. Install it with `pip install hamonpy[flexohr]`."
        )


# --------------------------------------------------------------------------- #
# Pitch classes  (HAMON PitchClass <-> FlexOHR SpecificPitchClass)
# --------------------------------------------------------------------------- #

_ACC_TO_GLYPH = {
    "sharp": "#", "double-sharp": "##",
    "flat": "b", "double-flat": "bb",
    "natural": "", None: "",
}
_GLYPH_TO_ACC = {
    "#": "sharp", "##": "double-sharp",
    "b": "flat", "bb": "double-flat", "": None,
}


def _pc_to_spc(pc: PitchClass):
    return SPC(pc.note + _ACC_TO_GLYPH.get(pc.accidental, ""))


def _spc_to_pc(spc) -> PitchClass:
    name = spc.name  # "C", "F#", "Bb", "Ebb", "C##"
    return PitchClass(note=name[0], accidental=_GLYPH_TO_ACC.get(name[1:]))


# --------------------------------------------------------------------------- #
# Chord quality  (HAMON (quality, seventh) <-> FlexOHR ChordQuality)
# --------------------------------------------------------------------------- #

# (hamon quality, hamon seventh) -> flexohr ChordQuality member name
_CQ_FROM_HAMON = {
    ("major", None): "major_triad",
    ("minor", None): "minor_triad",
    ("diminished", None): "diminished_triad",
    ("augmented", None): "augmented_triad",
    ("major", "dom7"): "dominant_seventh",
    ("minor", "min7"): "minor_seventh",
    ("major", "maj7"): "major_seventh",
    ("minor", "maj7"): "minor_major_seventh",
    ("diminished", "dim7"): "diminished_seventh",
    ("half-diminished", "hdim7"): "half_diminished_seventh",
    ("augmented", "maj7"): "augmented_major_seventh",
    ("augmented", "dom7"): "augmented_seventh",
}
_CQ_TO_HAMON = {v: k for k, v in _CQ_FROM_HAMON.items()}


def _hamon_chord_quality(sem: ChordSymbolSemantic):
    """The FlexOHR ChordQuality for a HAMON chord-symbol semantic."""
    if sem.suspensions:
        return ChordQuality.suspended_fourth if 4 in sem.suspensions else ChordQuality.suspended_second
    name = _CQ_FROM_HAMON.get((sem.quality, sem.seventh))
    if name is None:
        raise ValueError(
            f"no FlexOHR ChordQuality for HAMON quality={sem.quality!r} seventh={sem.seventh!r}"
        )
    return ChordQuality[name]


def _chord_symbol_to_ohr(sem: ChordSymbolSemantic):
    ohr = OHR.from_chord_quality(_hamon_chord_quality(sem), root=_pc_to_spc(sem.root), inversion=0)
    if sem.bass is not None:
        ohr = ohr.with_(bass=_pc_to_spc(sem.bass))
    return ohr


def _ohr_to_chord_symbol(ohr) -> ChordSymbolSemantic:
    root = _spc_to_pc(ohr.component("r").value)
    cq = ohr.get_property("chord_quality")
    suspensions = None
    if cq == ChordQuality.suspended_fourth:
        quality, seventh, suspensions = "major", None, [4]
    elif cq == ChordQuality.suspended_second:
        quality, seventh, suspensions = "major", None, [2]
    else:
        quality, seventh = _CQ_TO_HAMON.get(cq.name, ("major", None))
    return ChordSymbolSemantic(
        root=root,
        quality=quality,
        seventh=seventh,
        suspensions=suspensions,
        bass=_ohr_bass_pc(ohr),
    )


def _ohr_bass_pc(ohr) -> Optional[PitchClass]:
    """The slash bass, if the chord is inverted; else None."""
    inv = ohr.get_property("inversion")
    if inv is None or inv == Inversion.root_position:
        return None
    try:
        bass = ohr.resolve().component(tone_function=ToneFunction.bass)
    except Exception:
        return None
    return _spc_to_pc(bass.value) if bass is not None else None


# --------------------------------------------------------------------------- #
# Roman numerals  (HAMON RomanSemantic <-> FlexOHR roman OHR in a key context)
# --------------------------------------------------------------------------- #

_FIGBASS_RE = re.compile(r"(65|64|43|42|7|6|2)")
_QUAL_SYM_RE = re.compile(r"(°|o|\+|%|maj|M|Δ)")


def _key_scale(key: Optional[str]):
    """A FlexOHR major/minor Scale for the tonal context (default C major).

    ``key`` is a pitch name; its case sets the mode (``C`` major, ``a`` minor).
    """
    key = key or "C"
    minor = key[:1].islower()
    m = re.match(r"^([A-Ga-g])([#b]*)", key)
    tonic = SPC((m.group(1).upper() + m.group(2)) if m else "C")
    coll = CollectionType.natural_minor if minor else CollectionType.major
    return Scale.from_collection_type(coll, tonic)


def _roman_quality_inversion(degree: str, tail: Optional[str]):
    tail = tail or ""
    letters = degree.lstrip("#b♯♭-")
    base_minor = letters.islower()
    sym_m = _QUAL_SYM_RE.search(tail)
    sym = sym_m.group(1) if sym_m else ""
    fb_m = _FIGBASS_RE.search(tail)
    figbass = fb_m.group(1) if fb_m else ""
    has_seventh = figbass in {"7", "65", "43", "42", "2"} or "7" in tail

    if not has_seventh:
        if sym in ("°", "o"):
            cq = "diminished_triad"
        elif sym == "+":
            cq = "augmented_triad"
        else:
            cq = "minor_triad" if base_minor else "major_triad"
    else:
        if sym in ("°", "o"):
            cq = "diminished_seventh"
        elif sym == "%":
            cq = "half_diminished_seventh"
        elif sym == "+":
            cq = "augmented_seventh"
        elif sym in ("maj", "M", "Δ"):
            cq = "minor_major_seventh" if base_minor else "major_seventh"
        else:
            cq = "minor_seventh" if base_minor else "dominant_seventh"

    inversion = Inversion.from_format(figbass, "dcml") if figbass else Inversion.root_position
    return ChordQuality[cq], inversion


def _roman_to_ohr(sem: RomanSemantic, key: Optional[str] = None):
    scale = _key_scale(key)
    numeral = "".join(sem.prefixAccidentals or []) + sem.degree
    root = SD.from_format(numeral, "dcml", reference_ohr=scale)
    cq, inversion = _roman_quality_inversion(sem.degree, sem.tail)
    return OHR.from_chord_quality(cq, root=root, reference_ohr=scale,
                                  inversion=_inv_int(inversion))


def _inv_int(inv) -> int:
    return {"root_position": 0, "first": 1, "second": 2, "third": 3, "fourth": 4}.get(
        getattr(inv, "name", ""), 0
    )


# figbass canonical strings for rebuilding a HAMON tail
_INV_FIGBASS_TRIAD = {"root_position": "", "first": "6", "second": "64"}
_INV_FIGBASS_SEVENTH = {"root_position": "7", "first": "65", "second": "43", "third": "2"}
# flexohr ChordQuality -> (symbol, has_seventh, is_minor_case)
_CQ_ROMAN = {
    "major_triad": ("", False, False),
    "minor_triad": ("", False, True),
    "diminished_triad": ("o", False, True),
    "augmented_triad": ("+", False, False),
    "dominant_seventh": ("", True, False),
    "minor_seventh": ("", True, True),
    "major_seventh": ("M", True, False),
    "minor_major_seventh": ("M", True, True),
    "diminished_seventh": ("o", True, True),
    "half_diminished_seventh": ("%", True, True),
    "augmented_seventh": ("+", True, False),
    "augmented_major_seventh": ("+M", True, False),
}


def _ohr_to_roman(ohr) -> RomanSemantic:
    chord = ohr.ohr("b")  # descend to the chord leaf under the key Scale
    sd = chord.component("r").value
    cq = chord.get_property("chord_quality")
    inv = chord.get_property("inversion")

    sym, has_seventh, is_minor = _CQ_ROMAN.get(cq.name, ("", False, False))
    # Split the accidental prefix off first, then case only the Roman letters.
    numeral = sd.to_format("dcml")  # e.g. "V", "bVII", "vii"
    acc_m = re.match(r"^([#b♯♭-]*)(.*)$", numeral)
    prefix_str, letters = (acc_m.group(1), acc_m.group(2)) if acc_m else ("", numeral)
    degree = letters.lower() if is_minor else letters.upper()
    prefix = list(prefix_str) if prefix_str else None

    figmap = _INV_FIGBASS_SEVENTH if has_seventh else _INV_FIGBASS_TRIAD
    tail = sym + figmap.get(getattr(inv, "name", "root_position"), "")
    return RomanSemantic(
        degree=degree,
        prefixAccidentals=prefix,
        tail=tail or None,
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def hamon_semantic_to_ohr(semantic, key: Optional[str] = None):
    """Convert one HAMON chordSymbol/roman semantic to a FlexOHR ``OHR``."""
    _require()
    if isinstance(semantic, ChordSymbolSemantic):
        return _chord_symbol_to_ohr(semantic)
    if isinstance(semantic, RomanSemantic):
        return _roman_to_ohr(semantic, key)
    raise ValueError(f"FlexOHR adapter supports chordSymbol and roman only, not {getattr(semantic, 'kind', semantic)!r}")


def ohr_to_hamon_semantic(ohr):
    """Convert one FlexOHR ``OHR`` to a HAMON semantic (chordSymbol or roman)."""
    _require()
    # A roman OHR carries a key Scale as its reference; a bare chord's reference is a pitch.
    ref = ohr.ref() if hasattr(ohr, "ref") else None
    is_roman = ref is not None and ref.get_property("collection_type") is not None
    return _ohr_to_roman(ohr) if is_roman else _ohr_to_chord_symbol(ohr)


def hamon_to_flexohr(seq: HamonSequence, key: Optional[str] = None) -> List["OHR"]:
    """Convert a HamonSequence's primary chord/roman labels to a list of ``OHR``."""
    _require()
    out: List[OHR] = []
    for group in seq.groups:
        for label in group.primary:
            if isinstance(label.semantic, (ChordSymbolSemantic, RomanSemantic)):
                out.append(hamon_semantic_to_ohr(label.semantic, key))
    return out


def flexohr_to_hamon(ohrs: List["OHR"]) -> HamonSequence:
    """Convert a list of FlexOHR ``OHR`` objects to a HamonSequence (one group each)."""
    _require()
    groups: List[HarmonyGroup] = []
    for ohr in ohrs:
        sem = ohr_to_hamon_semantic(ohr)
        system = "rn" if isinstance(sem, RomanSemantic) else "cs"
        label = HarmonyLabel(
            surface="",
            semantic=sem,
            rendering=RenderingHints(),
            detected_system=system,
            system=system,
        )
        groups.append(HarmonyGroup(primary=[label]))
    return HamonSequence(groups=groups)
