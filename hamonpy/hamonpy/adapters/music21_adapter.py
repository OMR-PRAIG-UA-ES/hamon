"""music21 integration adapter for hamonpy.

Converts between hamon HamonSequence and music21 Stream objects.

Requires: music21 >= 9  (install with: pip install hamonpy[music21])

Usage:
    from hamonpy.adapters.music21_adapter import (
        music21_stream_to_hamon,
        hamon_to_music21_stream,
    )
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    import music21.stream
    import music21.harmony
    import music21.roman

from hamonpy.ast import (
    HamonSequence,
    HarmonyGroup,
    HarmonyLabel,
    ChordSymbolSemantic,
    RomanSemantic,
    NashvilleSemantic,
    FiguredBassSemantic,
    FunctionalSemantic,
    NoChordSemantic,
    TextSemantic,
    PitchClass,
    RenderingHints,
    Key,
    Position,
)
from hamonpy.normalize import (
    normalize_chord_symbol_from_surface,
    normalize_roman_from_parts,
    normalize_no_chord,
    normalize_text_from_surface,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_M21_ACC_TO_HAMON = {
    "-1": "flat", "-2": "doubleFlat",
    "1": "sharp", "2": "doubleSharp",
    "0": None,
}

_HAMON_ACC_TO_M21 = {
    "flat": -1, "doubleFlat": -2,
    "sharp": 1, "doubleSharp": 2,
    None: 0,
}

# hamon accidental → glyph used in music21 chord-figure / pitch strings
_ACC_GLYPH = {"flat": "b", "sharp": "#", "doubleFlat": "bb", "doubleSharp": "##"}


def _pitchclass_to_str(pc, *, flat_glyph: str = "b") -> str:
    """Render a hamon PitchClass as a music21 note string (e.g. ``"Bb"`` / ``"B-"``)."""
    glyph = {"flat": flat_glyph, "sharp": "#",
             "doubleFlat": flat_glyph * 2, "doubleSharp": "##"}
    return f"{pc.note}{glyph.get(pc.accidental or '', '')}"


def _pitch_to_pitchclass(pitch) -> PitchClass:
    """Convert a music21 Pitch (or string) to a hamon PitchClass."""
    try:
        name = pitch.name  # e.g. "C#", "Bb", "D"
    except AttributeError:
        name = str(pitch)
    if not name:
        return PitchClass(note="C")
    note = name[0].upper()
    acc_raw = name[1:] if len(name) > 1 else ""
    acc_map = {"#": "sharp", "b": "flat", "##": "doubleSharp", "bb": "doubleFlat",
               "-": "flat", "♭": "flat", "♯": "sharp"}
    accidental = acc_map.get(acc_raw)
    return PitchClass(note=note, accidental=accidental)


def _m21_quality_to_hamon_quality(m21_cs) -> tuple:
    """Map a music21 ChordSymbol to (quality, seventh, suspension)."""
    try:
        kind = m21_cs.chordKind or ""
    except AttributeError:
        kind = ""

    quality_map = {
        "major": ("major", None),
        "minor": ("minor", None),
        "augmented": ("augmented", None),
        "diminished": ("diminished", None),
        "dominant": ("major", "dom7"),
        "major-seventh": ("major", "maj7"),
        "minor-seventh": ("minor", "min7"),
        "diminished-seventh": ("diminished", "dim7"),
        "half-diminished": ("half-diminished", "hdim7"),
        "minor-major-seventh": ("minor", "maj7"),
        "suspended-fourth": ("major", None),  # suspension handled below
        "suspended-second": ("major", None),
        "major-minor": ("minor", "maj7"),
        "augmented-seventh": ("augmented", "dom7"),
    }
    quality, seventh = quality_map.get(kind, ("major", None))
    return quality, seventh


# ---------------------------------------------------------------------------
# music21 → hamon
# ---------------------------------------------------------------------------

def music21_stream_to_hamon(stream, sequence_system_hint: str = "cs") -> HamonSequence:
    """Convert a music21 Stream to a HamonSequence.

    Walks ``stream.flatten().getElementsByClass(['ChordSymbol', 'RomanNumeral'])``
    and converts each element to the appropriate HarmonySemantic.

    Args:
        stream: A ``music21.stream.Stream`` (Part, Score, or flat stream).
        sequence_system_hint: Override the system hint (default ``"cs"``).

    Returns:
        A ``HamonSequence`` with one group per harmony event.
    """
    try:
        import music21.harmony
        import music21.roman
    except ImportError as e:
        raise ImportError(
            "music21 is required: pip install hamonpy[music21]"
        ) from e

    groups: List[HarmonyGroup] = []

    # recurse() (vs flatten()) keeps each element's offset measure-relative, so a
    # position's beat can be recovered even without a TimeSignature.
    source = stream.recurse() if hasattr(stream, "recurse") else stream

    for el in source.getElementsByClass(["ChordSymbol", "RomanNumeral",
                                         "NoChord", "harmony.ChordSymbol",
                                         "roman.RomanNumeral"]):
        label = _m21_element_to_label(el)
        if label is not None:
            groups.append(HarmonyGroup(primary=[label], position=_element_position(el)))

    hint = sequence_system_hint or "cs"
    return HamonSequence(groups=groups, sequence_system_hint=hint)


def _element_position(el) -> Optional[Position]:
    """Time-aligned Position from a music21 element's measure context (or None)."""
    measure = getattr(el, "measureNumber", None)
    if not measure:
        return None
    beat = None
    try:
        b = float(el.beat)          # meter-aware when a TimeSignature is present
        if b == b:                  # not NaN
            beat = b
    except Exception:
        pass
    if beat is None:
        try:
            beat = float(el.offset) + 1.0   # offset is measure-relative under recurse()
        except (TypeError, ValueError):
            return None
    return Position(measure=int(measure), beat=beat)


def _m21_element_to_label(el) -> Optional[HarmonyLabel]:
    """Convert a single music21 harmony element to a HarmonyLabel."""
    try:
        import music21.harmony
        import music21.roman
    except ImportError:
        return None

    surface = _m21_element_surface(el)

    # Roman numeral
    if hasattr(el, "scaleDegree") and hasattr(el, "romanNumeral"):
        return _roman_numeral_to_label(el, surface)

    # ChordSymbol / NoChord
    if isinstance(el, music21.harmony.NoChord):
        sem, rendering, _ = normalize_no_chord()
        return HarmonyLabel(surface=surface or "N.C.", semantic=sem,
                            rendering=rendering, detected_system="cs",
                            system="cs", sequence_system_hint="cs")

    if surface:
        result = normalize_chord_symbol_from_surface(surface)
        if result:
            semantic, rendering, _detected = result
            return HarmonyLabel(surface=surface, semantic=semantic,
                                rendering=rendering, detected_system="cs",
                                system="cs", sequence_system_hint="cs")

    return None


def _m21_element_surface(el) -> str:
    """Try to extract the surface chord string from a music21 element."""
    # music21 ChordSymbol stores the figure in .figure or .chordKindStr
    for attr in ("figure", "chordKindStr", "pitchedCommonName", "commonName"):
        val = getattr(el, attr, None)
        if val:
            return str(val)
    return ""


def _roman_numeral_to_label(el, surface: str) -> Optional[HarmonyLabel]:
    """Convert a music21 RomanNumeral element to a HarmonyLabel."""
    try:
        degree = el.romanNumeral or ""
        if not degree:
            return None
        prefix_accs: List[str] = []
        if hasattr(el, "frontAlterationTransposeInterval") and el.frontAlterationTransposeInterval:
            semitones = el.frontAlterationTransposeInterval.semitones
            if semitones < 0:
                prefix_accs = ["b"] * abs(semitones)
            elif semitones > 0:
                prefix_accs = ["#"] * semitones

        secondary: Optional[str] = None
        if hasattr(el, "secondaryRomanNumeral") and el.secondaryRomanNumeral:
            secondary = el.secondaryRomanNumeral.romanNumeral

        tail = ""
        if hasattr(el, "frontAlterationString"):
            pass  # already in prefix_accs

        result = normalize_roman_from_parts(degree, prefix_accs, tail, secondary)
        semantic, rendering, _detected = result
        lbl_surface = surface or f"{''.join(prefix_accs)}{degree}"
        local_key = _m21_key_to_hamon(getattr(el, "key", None))
        return HarmonyLabel(surface=lbl_surface, semantic=semantic,
                            rendering=rendering, detected_system="rn",
                            system="rn", sequence_system_hint="rn",
                            local_key=local_key)
    except Exception:
        return None


def _m21_key_to_hamon(m21_key) -> Optional[Key]:
    """Convert a ``music21.key.Key`` to a hamon ``Key`` (or ``None``)."""
    if m21_key is None:
        return None
    try:
        tonic = _pitch_to_pitchclass(m21_key.tonic)
        mode = getattr(m21_key, "mode", None) or "major"
        return Key(tonic=tonic, mode=mode)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# hamon → music21
# ---------------------------------------------------------------------------

def hamon_to_music21_stream(seq: HamonSequence):
    """Convert a HamonSequence to a music21 Stream.

    Creates native ``ChordSymbol``, ``RomanNumeral`` or ``NoChord`` objects from
    the primary hamon label of each group.

    Placement uses ``HarmonyGroup.position`` (schema 0.2.1) when available:

    - if every group has a ``measure`` position, the elements are inserted into
      ``music21.stream.Measure`` objects at offset ``beat - 1`` (so ``measureNumber``
      and ``beat`` round-trip via ``music21_stream_to_hamon``);
    - else if every group has an absolute ``time`` position, elements are inserted
      at ``time × 4`` quarter-note offsets in a flat Part;
    - otherwise they fall back to sequential one-quarter-apart offsets.

    Roman numerals are resolved against a key derived from the sequence's
    analytical ``regions`` (or a label's ``local_key``).

    Returns:
        A ``music21.stream.Part`` containing the harmony events.
    """
    try:
        import music21.stream
        import music21.harmony
        import music21.roman
    except ImportError as e:
        raise ImportError(
            "music21 is required: pip install hamonpy[music21]"
        ) from e

    part = music21.stream.Part()
    groups = seq.groups

    def primary_element(gi, group):
        label = group.primary[0] if group.primary else None
        if label is None:
            return None
        return _label_to_m21_element(label, key=_key_for_group(seq, gi, label))

    # Measure mode: every group carries a measure number.
    if groups and all(g.position and g.position.measure is not None for g in groups):
        measures = {}
        for gi, group in enumerate(groups):
            el = primary_element(gi, group)
            if el is None:
                continue
            num = group.position.measure
            meas = measures.get(num)
            if meas is None:
                meas = music21.stream.Measure(number=num)
                measures[num] = meas
            beat = group.position.beat if group.position.beat is not None else 1.0
            meas.insert(beat - 1.0, el)
        for num in sorted(measures):
            part.append(measures[num])
        return part

    # Time mode: every group carries an absolute fractional time, in quarter notes —
    # which is already music21's own offset unit, so it goes in as it is. (This used to
    # multiply by 4, reading `time` as whole notes: a DCML or Dezrann source, both of
    # which write quarters, came out four times too late.)
    if groups and all(g.position and g.position.time is not None for g in groups):
        for gi, group in enumerate(groups):
            el = primary_element(gi, group)
            if el is None:
                continue
            t = group.position.time
            part.insert(t.numerator / t.denominator, el)
        return part

    # Fallback: sequential, one quarter note per event.
    offset = 0.0
    for gi, group in enumerate(groups):
        el = primary_element(gi, group)
        if el is not None:
            part.insert(offset, el)
            offset += 1.0
    return part


def _label_to_m21_element(label: HarmonyLabel, key=None):
    """Convert a single HarmonyLabel to a music21 harmony element."""
    try:
        import music21.harmony
        import music21.roman
    except ImportError:
        return None

    sem = label.semantic

    if isinstance(sem, NoChordSemantic):
        return music21.harmony.NoChord()

    if isinstance(sem, ChordSymbolSemantic):
        return _chord_symbol_to_m21(sem, label.surface)

    if isinstance(sem, RomanSemantic):
        return _roman_to_m21(sem, label.surface, key=key)

    return None


def _key_for_group(seq: HamonSequence, gi: int, label: HarmonyLabel):
    """Resolve the prevailing music21 key for group ``gi`` (or ``None``).

    A label's ``local_key`` wins; otherwise the innermost diatonic ``TonalRegion``
    (kind ``key`` / ``region`` / ``modulation``) covering the group is used.
    Tonicizations are intentionally skipped here — they are encoded as the
    ``secondary`` of the roman figure (e.g. ``V/V``), not as the prevailing key.
    """
    if label.local_key is not None:
        return _hamon_key_to_m21(label.local_key)

    best = None
    for region in (seq.regions or []):
        if region.kind not in ("key", "region", "modulation"):
            continue
        to = region.to_group if region.to_group is not None else gi
        if region.from_group <= gi <= to:
            # innermost = latest-starting region that still covers gi
            if best is None or region.from_group >= best.from_group:
                best = region
    return _hamon_key_to_m21(best.key) if best is not None else None


def _hamon_key_to_m21(key):
    """Convert a hamon ``Key`` to a ``music21.key.Key`` (or ``None``)."""
    if key is None:
        return None
    try:
        import music21.key
    except ImportError:
        return None
    tonic = _pitchclass_to_str(key.tonic, flat_glyph="-")
    mode = key.mode or "major"
    try:
        return music21.key.Key(tonic, mode)
    except Exception:
        return None


def _chord_symbol_to_m21(sem: ChordSymbolSemantic, surface: str):
    """Build a music21 ChordSymbol from a ChordSymbolSemantic.

    Constructs a music21 chord figure from the semantic fields — quality +
    seventh, suspensions, added tones and a slash bass — which music21 parses
    natively. Falls back to the raw surface if the figure is unparseable.
    """
    try:
        import music21.harmony
    except ImportError:
        return None

    figure = _chord_symbol_figure(sem)
    try:
        return music21.harmony.ChordSymbol(figure)
    except Exception:
        pass
    # Fallback 1: root + kind constructor (no extensions)
    kind_map = {
        ("major", None): "major",
        ("minor", None): "minor",
        ("augmented", None): "augmented",
        ("diminished", None): "diminished",
        ("major", "maj7"): "major-seventh",
        ("minor", "min7"): "minor-seventh",
        ("major", "dom7"): "dominant",
        ("diminished", "dim7"): "diminished-seventh",
        ("half-diminished", "hdim7"): "half-diminished",
        ("minor", "maj7"): "minor-major-seventh",
    }
    chord_kind = kind_map.get((sem.quality or "major", sem.seventh), "major")
    try:
        return music21.harmony.ChordSymbol(
            root=_pitchclass_to_str(sem.root, flat_glyph="-"), kind=chord_kind
        )
    except Exception:
        return music21.harmony.ChordSymbol(surface)


def _chord_symbol_figure(sem: ChordSymbolSemantic) -> str:
    """Render a ChordSymbolSemantic as a music21-parseable chord figure."""
    figure = _pitchclass_to_str(sem.root)  # "b"/"#" glyphs

    # Suspensions replace the third; quality/seventh otherwise drive the suffix.
    if sem.suspensions:
        for s in sem.suspensions:
            figure += f"sus{s}" if s else "sus"
        if sem.seventh in ("dom7", "min7", "maj7"):
            figure += "7"
    else:
        suffix_map = {
            ("major", None): "",
            ("minor", None): "m",
            ("augmented", None): "+",
            ("diminished", None): "dim",
            ("major", "maj7"): "maj7",
            ("minor", "min7"): "m7",
            ("major", "dom7"): "7",
            ("diminished", "dim7"): "dim7",
            ("half-diminished", "hdim7"): "m7b5",
            ("minor", "maj7"): "m(maj7)",
            ("augmented", "dom7"): "+7",
        }
        figure += suffix_map.get((sem.quality or "major", sem.seventh), "")

    for ext in (sem.extensions or []):
        figure += str(ext)
    for alt in (sem.alterations or []):
        glyph = alt.get("glyph") or _ACC_GLYPH.get(alt.get("accidental"), "")
        figure += f"{glyph}{alt.get('degree', '')}"
    for add in (sem.adds or []):
        figure += f"add{add}"
    if sem.bass is not None:
        figure += "/" + _pitchclass_to_str(sem.bass)

    return figure


def _roman_to_m21(sem: RomanSemantic, surface: str, key=None):
    """Build a music21 RomanNumeral from a RomanSemantic.

    Secondary targets (``sem.secondary``) become a ``/`` figure (e.g. ``V/IV``)
    and inversion figures in ``sem.tail`` (``7``/``65``/``43``/``6`` …) are
    preserved. When a ``key`` is supplied the numeral resolves to concrete
    pitches in that key.
    """
    try:
        import music21.roman
    except ImportError:
        return None

    prefix = "".join(sem.prefixAccidentals or [])
    figure = f"{prefix}{sem.degree}{sem.tail or ''}"
    if sem.secondary:
        figure += f"/{sem.secondary}"
    try:
        if key is not None:
            return music21.roman.RomanNumeral(figure, key)
        return music21.roman.RomanNumeral(figure)
    except Exception:
        try:
            return music21.roman.RomanNumeral(f"{prefix}{sem.degree}")
        except Exception:
            return None
