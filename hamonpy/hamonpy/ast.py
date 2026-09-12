from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Union

# ---------------------------------------------------------------------------
# Primitive types
# ---------------------------------------------------------------------------

SequenceSystem = Literal["auto", "cs", "rn", "ns", "fb", "fun", "text"]
DetectedSystem = Literal["cs", "rn", "ns", "fb", "fun", "text", "unknown"]
NoteClass = Literal["A", "B", "C", "D", "E", "F", "G"]
Accidental = Literal["sharp", "flat", "double-sharp", "double-flat", "natural"]
ChordQuality = Literal["major", "minor", "diminished", "augmented", "half-diminished"]
SeventhQuality = Literal["dom7", "maj7", "min7", "dim7", "hdim7"]


@dataclass(frozen=True)
class PitchClass:
    note: NoteClass
    accidental: Optional[Accidental] = None


# ---------------------------------------------------------------------------
# Rendering hints (preserve original glyphs for round-trip fidelity)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RenderingHints:
    qualityGlyph: Optional[str] = None   # e.g. "m", "-", "°", "ø", "+"
    seventhGlyph: Optional[str] = None   # e.g. "Δ", "M", "maj", "7"
    accidentalGlyphs: Optional[Dict[str, str]] = None  # accidental → glyph
    rawParts: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Semantic kinds
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChordSymbolSemantic:
    kind: Literal["chordSymbol"] = field(default="chordSymbol", init=False)
    root: PitchClass = field(default_factory=lambda: PitchClass("C"))
    quality: ChordQuality = "major"
    seventh: Optional[SeventhQuality] = None
    extensions: Optional[List[int]] = None
    alterations: Optional[List[dict]] = None
    suspensions: Optional[List[Optional[int]]] = None
    adds: Optional[List[int]] = None
    omits: Optional[List[int]] = None
    bass: Optional[PitchClass] = None


@dataclass(frozen=True)
class RomanSemantic:
    degree: str
    kind: Literal["roman"] = field(default="roman", init=False)
    prefixAccidentals: Optional[List[str]] = None
    tail: Optional[str] = None
    secondary: Optional[str] = None


@dataclass(frozen=True)
class NashvilleSemantic:
    number: int
    kind: Literal["nashville"] = field(default="nashville", init=False)
    prefixAccidentals: Optional[List[str]] = None
    tail: Optional[str] = None
    secondary: Optional[str] = None


@dataclass(frozen=True)
class FiguredBassSemantic:
    number: int
    kind: Literal["figuredBass"] = field(default="figuredBass", init=False)
    prefixAccidentals: Optional[List[str]] = None
    tail: Optional[str] = None


@dataclass(frozen=True)
class FunctionalSemantic:
    chain: List[str]
    kind: Literal["functional"] = field(default="functional", init=False)


@dataclass(frozen=True)
class NoChordSemantic:
    kind: Literal["noChord"] = field(default="noChord", init=False)


@dataclass(frozen=True)
class TextSemantic:
    text: str
    kind: Literal["text"] = field(default="text", init=False)


# ---------------------------------------------------------------------------
# Analytical layer (v0.2.0) — see documentation/analysis.md and hamon-schema.json.
# Additive and optional; 0.1.0 documents/round-trips are unaffected.
# ---------------------------------------------------------------------------

Mode = Literal[
    "major", "minor",
    "ionian", "dorian", "phrygian", "lydian", "mixolydian", "aeolian", "locrian",
]
AnalyticalLayer = Literal["chord", "degree", "function", "bass", "melodic", "key", "tone"]
NonHarmonicType = Literal[
    "chord-tone", "passing", "neighbor", "upper-neighbor", "lower-neighbor",
    "incomplete-neighbor", "suspension", "retardation", "appoggiatura",
    "escape", "anticipation", "pedal", "cambiata", "changing-tone",
]
Motion = Literal[
    "step-up", "step-down", "leap-up", "leap-down", "repeat", "common-tone", "resolve"
]
RegionKind = Literal["key", "region", "tonicization", "modulation"]


@dataclass(frozen=True)
class Key:
    tonic: PitchClass
    mode: Optional[Mode] = None        # default "major"
    label: Optional[str] = None


@dataclass(frozen=True)
class Meter:
    """A time signature (v0.4.0), declared with ``@meter:N/D`` at the start and at
    every metric change. ``numerator`` is the beat count and thus fixes the valid
    range of a group's ``ts`` (MEI ``data.BEAT``): ``ts`` spans ``[1, numerator + 1)``.
    ``from_group`` is the index of the first group it governs."""
    numerator: int
    denominator: int
    from_group: int


@dataclass
class TonalRegion:
    key: Key
    kind: RegionKind
    from_group: int
    to_group: Optional[int] = None
    degree: Optional[str] = None       # tonicized degree relative to parent key
    parent: Optional[int] = None       # index into regions of the enclosing region
    label: Optional[str] = None
    scales: Optional[List["ScaleSpec"]] = None  # chord-scale(s) valid over this region


@dataclass(frozen=True)
class ToneSemantic:
    category: Literal["harmonic", "nonharmonic"]
    kind: Literal["tone"] = field(default="tone", init=False)
    pitch: Optional[PitchClass] = None
    type: Optional[NonHarmonicType] = None   # required when category == "nonharmonic"
    metric: Optional[Literal["accented", "unaccented"]] = None
    approach: Optional[Motion] = None
    departure: Optional[Motion] = None
    voice: Optional[str] = None


@dataclass(frozen=True)
class ScaleSpec:
    """A chord-scale (jazz/Berklee): the recommended scale for a chord or region.

    ``name`` is an open vocabulary (e.g. the church modes, plus ``altered``,
    ``lydian-dominant``, ``locrian-natural-2``, ``whole-tone``, ``diminished-hw``,
    ``diminished-wh``, ``harmonic-minor``, ``melodic-minor``, ``bebop-dominant``,
    ``blues`` …). ``tonic`` is the scale's tonic when it differs from the implied
    one (the chord root / region key); ``pitches`` may list the scale's pitch
    classes explicitly for non-standard scales."""
    name: str
    tonic: Optional[PitchClass] = None
    pitches: Optional[List[PitchClass]] = None


@dataclass(frozen=True)
class AppliedFunction:
    target: str                        # degree the applied chord resolves to (e.g. "V")
    chain: Optional[List[str]] = None  # stacked secondaries, outermost first


@dataclass(frozen=True)
class HarmonyAttributes:
    inversion: Optional[int] = None
    omittedRoot: Optional[bool] = None      # fundamental omitida (implied root)
    rootless: Optional[bool] = None
    impliedRoot: Optional[PitchClass] = None
    arpeggiated: Optional[bool] = None      # despliegue / broken-chord unfolding
    prolongation: Optional[
        Literal["arpeggiation", "pedal", "neighbor", "passing", "prolongation"]
    ] = None
    prolongs: Optional[int] = None
    pedal: Optional[bool] = None
    tonicizes: Optional[str] = None
    applied: Optional[AppliedFunction] = None
    scales: Optional[List[ScaleSpec]] = None   # chord-scale(s) valid over this chord
    # --- extent (v0.4.1): how long this reading lasts. On the LABEL, not the group,
    # so two `alternatives` can segment the same passage differently. Only ever set
    # from what a source STATED; absent means "unknown", and the implicit rule (runs
    # to the next group) is a computation, never stored. See documentation/positions.md.
    duration: Optional[Fraction] = None     # extent in quarter notes, like Position.time
    # The extent inherits the clock of the source that stated it (v0.5): `[dur:3/4]` is
    # quarter notes, `[dur:1.85s]` is seconds — one key, an optional suffix. The two are
    # separate fields for the same reason `Position.time` and `Position.seconds` are:
    # crossing the clocks needs a tempo map, so neither is derived from the other.
    durationSeconds: Optional[float] = None  # extent in seconds, like Position.seconds
    endRef: Optional[str] = None            # score object it ends on (MEI @endid)


HarmonySemantic = Union[
    ChordSymbolSemantic,
    RomanSemantic,
    NashvilleSemantic,
    FiguredBassSemantic,
    FunctionalSemantic,
    ToneSemantic,
    NoChordSemantic,
    TextSemantic,
]


# ---------------------------------------------------------------------------
# Sequence structure
# ---------------------------------------------------------------------------

@dataclass
class HarmonyLabel:
    surface: str
    semantic: HarmonySemantic
    rendering: RenderingHints
    detected_system: DetectedSystem
    system: DetectedSystem
    sequence_system_hint: Optional[SequenceSystem] = None
    # --- analytical layer (v0.2.0), all optional ---
    layer: Optional[AnalyticalLayer] = None
    local_key: Optional[Key] = None
    attributes: Optional[HarmonyAttributes] = None


@dataclass(frozen=True)
class Fraction:
    numerator: int
    denominator: int


@dataclass(frozen=True)
class Position:
    """Time-aligned position of a HarmonyGroup (v0.2.1). All fields optional:
    ``measure``+``beat`` mirror an MEI ``@tstamp``; ``time`` is an absolute
    fractional offset in quarter notes; ``seconds`` is physical time (v0.5);
    ``ref`` points at a score-object id (MEI ``@startid``).

    The clocks **coexist** and none is derived from another: a position holds
    whichever ones the source stated, and an absent one means unknown. In a
    recording the seconds are the certain datum and the bar is an estimate; in
    a score it is the other way round."""
    measure: Optional[int] = None
    beat: Optional[float] = None
    time: Optional[Fraction] = None
    seconds: Optional[float] = None
    ref: Optional[str] = None


@dataclass
class HarmonyGroup:
    primary: List[HarmonyLabel]
    alternatives: List[List[HarmonyLabel]] = field(default_factory=list)
    position: Optional[Position] = None   # time-aligned position (v0.2.1), when known


@dataclass(frozen=True)
class AlternativeAnalysis:
    groups: List[HarmonyGroup]
    label: Optional[str] = None
    system: Optional[DetectedSystem] = None
    scope: Optional[dict] = None       # {"fromGroup": int, "toGroup": int}


@dataclass
class HamonSequence:
    groups: List[HarmonyGroup]
    sequence_system_hint: Optional[SequenceSystem] = None
    version: Optional[str] = None
    # --- analytical layer (v0.2.0), all optional ---
    meters: Optional[List[Meter]] = None          # time-signature changes (v0.4.0)
    regions: Optional[List[TonalRegion]] = None
    alternative_analyses: Optional[List[AlternativeAnalysis]] = None
