"""Harte chord-notation adapter.

Parses Harte-notation chord tokens (C:maj7, G:7, Ab:min/5, N, X) into
HamonSequence, and exports back to Harte text.

Reference: Harte et al. (2005), ISMIR.
"""
from __future__ import annotations

import io
import re
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from hamonpy.ast import (
    HamonSequence,
    HarmonyAttributes,
    HarmonyGroup,
    HarmonyLabel,
    ChordSymbolSemantic,
    NoChordSemantic,
    PitchClass,
    Position,
    RenderingHints,
    TextSemantic,
)
from hamonpy.normalize import normalize_chord_symbol_from_surface


# ---------------------------------------------------------------------------
# Shorthand vocabulary
# ---------------------------------------------------------------------------

_SHORTHAND_TO_HAMON: Dict[str, Tuple[str, Optional[str]]] = {
    # (quality, seventh_suffix or None→ no seventh)
    "maj":      ("major",         None),
    "min":      ("minor",         None),
    "dim":      ("diminished",    None),
    "aug":      ("augmented",     None),
    "maj7":     ("major",         "maj7"),
    "min7":     ("minor",         "min7"),
    "7":        ("major",         "dom7"),
    "dim7":     ("diminished",    "dim7"),
    "hdim7":    ("half-diminished", "hdim7"),
    "minmaj7":  ("minor",         "maj7"),
    "maj6":     ("major",         None),
    "min6":     ("minor",         None),
    "9":        ("major",         "dom7"),
    "maj9":     ("major",         "maj7"),
    "min9":     ("minor",         "min7"),
    "sus4":     ("major",         None),
    "sus2":     ("major",         None),
    "1":        ("major",         None),
    "5":        ("major",         None),
}

# Harte shorthand → canonical hamon suffix used in normalize_chord_symbol_from_surface
_SHORTHAND_TO_HAMON_SUFFIX: Dict[str, str] = {
    "maj":     "",
    "min":     "m",
    "dim":     "°",
    "aug":     "+",
    "maj7":    "maj7",
    "min7":    "m7",
    "7":       "7",
    "dim7":    "°7",
    "hdim7":   "ø7",
    "minmaj7": "mmaj7",
    "maj6":    "6",
    "min6":    "m6",
    "9":       "9",
    "maj9":    "maj9",
    "min9":    "m9",
    "11":      "11",
    "min11":   "m11",
    "maj11":   "maj11",
    "13":      "13",
    "min13":   "m13",
    "maj13":   "maj13",
    "sus4":    "sus4",
    "sus2":    "sus2",
    # A power chord is a triad with no third, and `1` is the root alone: HAMON says
    # that with `omits`, which is what lets both survive the trip back out.
    "1":       "no3no5",
    "5":       "no3",
}

_HAMON_QUALITY_TO_SHORTHAND: Dict[str, str] = {
    "major":          "maj",
    "minor":          "min",
    "diminished":     "dim",
    "augmented":      "aug",
    "half-diminished": "hdim7",
}

_HAMON_SEVENTH_TO_SHORTHAND: Dict[str, str] = {
    "maj7":  "maj7",
    "min7":  "min7",
    "dom7":  "7",
    "dim7":  "dim7",
    "hdim7": "hdim7",
}

_HAMON_SUSPENSION_TO_SHORTHAND: Dict[str, str] = {
    "sus4": "sus4",
    "sus2": "sus2",
}

_HARTE_ACCIDENTAL: Dict[str, str] = {"b": "b", "#": "#", "bb": "bb", "##": "##"}
_HAMON_TO_HARTE_ACC: Dict[str, str] = {
    "flat": "b", "sharp": "#", "double-flat": "bb", "double-sharp": "##", "natural": "",
}


# ---------------------------------------------------------------------------
# Bass: Harte names it as a scale degree, HAMON as a pitch
# ---------------------------------------------------------------------------
#
# Harte writes the bass as an interval above the root, spelled against the root's
# *major* scale (`/5`, `/b7`, `/#4`); HAMON's `bass` is a PitchClass. The two are
# interconvertible without guessing — the degree fixes the letter, the accidental
# fixes the pitch — so this is a mapping, not the kind of inference the position
# clocks refuse to do.

_LETTERS = "CDEFGAB"
_LETTER_PC: Dict[str, int] = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_MAJOR_SCALE_SEMITONES: Dict[int, int] = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
_ACC_OFFSET: Dict[str, int] = {"": 0, "b": -1, "bb": -2, "#": 1, "##": 2}
_OFFSET_ACC: Dict[int, str] = {0: "", -1: "b", -2: "bb", 1: "#", 2: "##"}
_ACC_NAME: Dict[int, Optional[str]] = {
    0: None, -1: "flat", -2: "double-flat", 1: "sharp", 2: "double-sharp",
}


def _simple_degree(degree: int) -> int:
    """9/11/13 name the same letter as 2/4/6 — fold them into one octave."""
    return ((degree - 1) % 7) + 1


def _pitch_pc(pitch: PitchClass) -> int:
    glyph = _HAMON_TO_HARTE_ACC.get(pitch.accidental or "", "")
    return (_LETTER_PC[pitch.note] + _ACC_OFFSET.get(glyph, 0)) % 12


def _degree_to_pitch(root: PitchClass, acc_glyph: str, degree: int) -> Optional[PitchClass]:
    """The pitch a Harte bass degree names above ``root`` (``/b7`` on C → Bb)."""
    simple = _simple_degree(degree)
    letter = _LETTERS[(_LETTERS.index(root.note) + simple - 1) % 7]
    target = (_pitch_pc(root) + _MAJOR_SCALE_SEMITONES[simple] + _ACC_OFFSET.get(acc_glyph, 0)) % 12
    offset = ((target - _LETTER_PC[letter] + 6) % 12) - 6
    if offset not in _ACC_NAME:
        return None
    return PitchClass(note=letter, accidental=_ACC_NAME[offset])


def _pitch_to_degree(root: PitchClass, bass: PitchClass) -> Optional[str]:
    """The Harte bass degree for ``bass`` above ``root`` (C, Bb → ``b7``), or None.

    Always the simple degree: HAMON's bass is a pitch class, which does not record
    the octave that told ``/9`` apart from ``/2``. The two name the same pitch, so a
    compound bass comes back as its simple degree — a re-spelling, and `report.py`
    finds nothing to report because the semantics are identical."""
    simple = ((_LETTERS.index(bass.note) - _LETTERS.index(root.note)) % 7) + 1
    expected = (_pitch_pc(root) + _MAJOR_SCALE_SEMITONES[simple]) % 12
    offset = ((_pitch_pc(bass) - expected + 6) % 12) - 6
    if offset not in _OFFSET_ACC:
        return None
    return f"{_OFFSET_ACC[offset]}{simple}"


# ---------------------------------------------------------------------------
# Parsing a single Harte token
# ---------------------------------------------------------------------------

# The bass is a scale degree, and a degree may be altered (`/b7`, `/#4`) — not just
# a bare number. Admitting digits only used to drop the whole line: no match, no
# label, no group, so `report.py` never saw a loss to report either.
#
# Strict Harte spells the bass as a degree, but BPSD and SWD spell it as a note name
# (`C:min7/G`), so that is a dialect we read too: the bass is then already a pitch.
#
# Groups: root, root accidental, shorthand, degree list, bass accidental, bass degree,
# bass note name, bass note accidental. The shorthand stops at `(` so that the degree
# list is read on its own.
_TOKEN_RE = re.compile(
    r"^([A-G])([#b]{1,2})?"
    r"(?::([^/(]*)(?:\(([^)]*)\))?)?"
    r"(?:/(?:([#b]{0,2})(\d+)|([A-G])([#b]{1,2})?))?$"
)

# One entry of a degree list: `b7`, `#11`, `9`, or `*3` (remove the degree).
_DEGREE_RE = re.compile(r"^(\*)?([#b]{0,2})(\d+)$")

_ACC_GLYPH_NAME: Dict[str, str] = {
    "b": "flat", "#": "sharp", "bb": "double-flat", "##": "double-sharp",
}


def _parse_degrees(text: str) -> Optional[List[Tuple[bool, str, int]]]:
    """``"b5,*3"`` → ``[(False, "b", 5), (True, "", 3)]``; None if any entry is unreadable."""
    items: List[Tuple[bool, str, int]] = []
    for raw in text.split(","):
        m = _DEGREE_RE.match(raw.strip())
        if not m:
            return None
        items.append((bool(m.group(1)), m.group(2), int(m.group(3))))
    return items


def _with_tension(fields: dict, acc: str, degree: int) -> None:
    """Add one stated degree above the chord's own tones to ``fields``.

    An altered tension (`b9`, `#11`) is an alteration; a plain 9/11/13 is an extension
    once a seventh is there to stack on, and an `add` before that; a 6 is the sixth."""
    if acc:
        fields["alterations"].append(
            {"accidental": _ACC_GLYPH_NAME[acc], "degree": degree, "glyph": acc})
    elif degree == 6:
        fields["extensions"].append(6)
    elif degree in (9, 11, 13) and fields["seventh"]:
        fields["extensions"].append(degree)
    else:
        fields["adds"].append(degree)


def _apply_degrees(sem: ChordSymbolSemantic, items: List[Tuple[bool, str, int]]) -> ChordSymbolSemantic:
    """A shorthand plus a degree list: the list edits the shorthand (`C:min(*3)`, `C:7(b9)`)."""
    fields = {
        "extensions": list(sem.extensions or []), "alterations": list(sem.alterations or []),
        "adds": list(sem.adds or []), "omits": list(sem.omits or []), "seventh": sem.seventh,
    }
    for remove, acc, degree in items:
        if remove:
            if degree not in fields["omits"]:
                fields["omits"].append(degree)
        else:
            _with_tension(fields, acc, degree)
    return replace(sem, **{k: (v or None) if k != "seventh" else v for k, v in fields.items()})


def _complete_chord(root: PitchClass, items: List[Tuple[bool, str, int]]) -> ChordSymbolSemantic:
    """A degree list with no shorthand *is* the chord: the root plus what is listed.

    Nothing is implied. A third that is not listed is an omitted third (`F#:(b5,b7)` has
    no A#), and the same for the fifth; the HAMON AST says that with `omits`."""
    stated = {(acc, degree) for remove, acc, degree in items if not remove}
    removed = {degree for remove, _acc, degree in items if remove}
    third = next((a for a, d in stated if d == 3), None)
    fifth = next((a for a, d in stated if d == 5), None)
    seventh_acc = next((a for a, d in stated if d == 7), None)

    quality = "minor" if third == "b" else "major"
    seventh: Optional[str] = None
    if seventh_acc is not None:
        if quality == "minor" and fifth == "b" and seventh_acc == "bb":
            quality, seventh = "diminished", "dim7"
        elif quality == "minor" and fifth == "b" and seventh_acc == "b":
            quality, seventh = "half-diminished", "hdim7"
        elif seventh_acc == "":
            seventh = "maj7"
        else:
            seventh = "min7" if quality == "minor" else "dom7"
    elif quality == "minor" and fifth == "b":
        quality = "diminished"
    elif third == "" and fifth == "#":
        quality = "augmented"

    suspensions = None
    if third is None:
        if any(d == 4 and a == "" for a, d in stated):
            suspensions = [4]
        elif any(d == 2 and a == "" for a, d in stated):
            suspensions = [2]

    fields = {"extensions": [], "alterations": [], "adds": [], "seventh": seventh}
    for acc, degree in sorted(stated, key=lambda p: p[1]):
        if degree in (1, 3, 7) or (degree == 5 and (acc == "" or quality in ("diminished", "augmented", "half-diminished"))):
            continue
        if suspensions and degree == suspensions[0] and not acc:
            continue
        _with_tension(fields, acc, degree)

    omits = [d for d in (3, 5) if d not in {d for _a, d in stated} or d in removed]
    if suspensions:
        omits = [d for d in omits if d != 3]
    return ChordSymbolSemantic(
        root=root, quality=quality, seventh=seventh,
        extensions=fields["extensions"] or None, alterations=fields["alterations"] or None,
        suspensions=suspensions, adds=fields["adds"] or None, omits=omits or None,
    )


def _text_label(token: str) -> HarmonyLabel:
    """A token we could not read, kept as text rather than dropped: the surface survives
    and `report.py` sees what a writer then fails to carry."""
    return HarmonyLabel(
        surface=token, semantic=TextSemantic(text=token), rendering=RenderingHints(),
        detected_system="cs", system="cs", sequence_system_hint="cs",
    )


def harte_token_to_hamon_label(token: str) -> Optional[HarmonyLabel]:
    """Parse a single Harte token into a HarmonyLabel, or None to skip."""
    t = token.strip()
    if t in ("N", "N.C.", "NC"):
        sem = NoChordSemantic()
        return HarmonyLabel(surface=t, semantic=sem, rendering=RenderingHints(),
                            detected_system="cs", system="cs", sequence_system_hint="cs")
    if t in ("X", ""):
        return None

    m = _TOKEN_RE.match(t)
    if not m:
        return _text_label(t)

    note = m.group(1)
    acc = m.group(2) or ""
    shorthand = (m.group(3) or "").strip()
    degree_list = m.group(4)
    bass_acc = m.group(5) or ""
    bass_degree = m.group(6)

    items = None
    if degree_list is not None:
        items = _parse_degrees(degree_list)
        if items is None:
            return _text_label(t)

    if items is not None and not shorthand:
        # No shorthand: the degree list is the whole chord.
        root = PitchClass(note=note, accidental=_ACC_NAME[_ACC_OFFSET[acc]])
        semantic: ChordSymbolSemantic = _complete_chord(root, items)
        rendering = RenderingHints()
    else:
        suffix = _SHORTHAND_TO_HAMON_SUFFIX.get(shorthand or "maj")
        if suffix is None:
            # An unknown shorthand would parse as the bare triad, a different chord.
            return _text_label(t)
        result = normalize_chord_symbol_from_surface(f"{note}{acc}{suffix}", strict=True)
        if result is None:
            return _text_label(t)
        semantic, rendering, _detected = result
        if items is not None and isinstance(semantic, ChordSymbolSemantic):
            semantic = _apply_degrees(semantic, items)

    if isinstance(semantic, ChordSymbolSemantic):
        bass = None
        if bass_degree is not None:
            bass = _degree_to_pitch(semantic.root, bass_acc, int(bass_degree))
        elif m.group(7) is not None:
            bass = PitchClass(note=m.group(7), accidental=_ACC_NAME[_ACC_OFFSET[m.group(8) or ""]])
        if bass is not None:
            semantic = replace(semantic, bass=bass)
    return HarmonyLabel(
        surface=t, semantic=semantic, rendering=rendering,
        detected_system="cs", system="cs", sequence_system_hint="cs",
    )


def _shorthand_to_tail(shorthand: str) -> str:
    """Map a Harte shorthand to the hamon chord-symbol tail string."""
    sh = shorthand.strip().rstrip(")")
    # Handle extended degree lists like (*3,b7) — keep as opaque tail
    if sh.startswith("(") or "," in sh or "*" in sh:
        return sh
    mapping = _SHORTHAND_TO_HAMON.get(sh)
    if mapping is None:
        return sh
    quality, seventh = mapping
    # Build tail tokens
    toks: List[str] = []
    if quality == "minor":
        toks.append("m")
    elif quality == "diminished":
        toks.append("°")
    elif quality == "augmented":
        toks.append("+")
    elif quality == "half-diminished":
        toks.append("ø")
    if seventh == "maj7":
        if quality == "minor":
            toks = ["m", "maj7"]
        else:
            toks.append("maj7")
    elif seventh == "min7":
        toks.append("7")
    elif seventh == "dom7":
        toks.append("7")
    elif seventh == "dim7":
        toks.append("°7")
    elif seventh == "hdim7":
        toks = ["ø7"]
    if sh == "sus4":
        toks = ["sus4"]
    elif sh == "sus2":
        toks = ["sus2"]
    return "".join(toks)


# ---------------------------------------------------------------------------
# Public API — parsing
# ---------------------------------------------------------------------------

def _times(columns: List[str]) -> Tuple[Optional[float], Optional[float]]:
    """The ``start`` and ``end`` columns of a ``.lab`` line, in seconds.

    A ``.lab`` line is ``start end label``; the plain ``label`` form has no columns,
    and thus no position and no extent. Seconds are stored as stated and never
    converted to a metric position or to quarter notes: the recording states the
    seconds, the bar and the beat would be a guess."""
    values: List[float] = []
    for column in columns[:2]:
        try:
            values.append(float(column))
        except ValueError:
            return (None, None)
    start = values[0] if values else None
    end = values[1] if len(values) > 1 else None
    return (start, end)


def harte_text_to_hamon(text: str) -> HamonSequence:
    """Parse Harte-format text (one chord per line, with or without timestamps)."""
    groups: List[HarmonyGroup] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Leading timestamp columns (tab or space separated floats), then the label.
        parts = re.split(r"\s+", line)
        token = parts[-1] if parts else line
        label = harte_token_to_hamon_label(token)
        if label is not None:
            start, end = _times(parts[:-1])
            position = Position(seconds=start) if start is not None else None
            if start is not None and end is not None and end > start:
                # Harte states the end, so the extent is stated too, in the same clock.
                label.attributes = replace(label.attributes or HarmonyAttributes(),
                                           durationSeconds=end - start)
            groups.append(HarmonyGroup(primary=[label], position=position))
    return HamonSequence(groups=groups, sequence_system_hint="cs")


def harte_file_to_hamon(path: str) -> HamonSequence:
    with open(path, encoding="utf-8") as fh:
        return harte_text_to_hamon(fh.read())


# ---------------------------------------------------------------------------
# Public API — exporting
# ---------------------------------------------------------------------------

def _fmt_seconds(value: float) -> str:
    """A time column in the ``.lab`` convention: six decimals, as the corpora write it."""
    return f"{value:.6f}"


def _timed_rows(seq: HamonSequence) -> Optional[List[Tuple[float, float, str]]]:
    """``(start, end, token)`` per group, or ``None`` if the sequence cannot state them all.

    A ``.lab`` is a positional-column format: every line is ``start end label``, so the
    columns are all-or-nothing for the whole file. A group that states no `s:` onset, or
    a label with no `[dur:…s]` extent, leaves an end this writer refuses to invent —
    deriving it from the next onset is what the Dezrann writer was cured of. One such
    group and the file falls back to bare tokens, losing the seconds the others had;
    `report.py` reports that as the loss it is."""
    rows: List[Tuple[float, float, str]] = []
    for group in seq.groups:
        token = next((t for t in (_label_to_harte_token(lbl) for lbl in group.primary) if t), None)
        if token is None:
            continue
        start = group.position.seconds if group.position else None
        extent = next((lbl.attributes.durationSeconds for lbl in group.primary
                       if lbl.attributes and lbl.attributes.durationSeconds is not None), None)
        if start is None or extent is None:
            return None
        rows.append((start, start + extent, token))
    return rows


def hamon_to_harte_text(seq: HamonSequence) -> str:
    """Serialize a HamonSequence to Harte-notation text, one harmony per line.

    Emits the timed ``start end label`` form when **every** harmony states both an `s:`
    onset and a `[dur:…s]` extent — which is what a sequence imported from a ``.lab``
    has, so that round-trip is lossless. Anything else is written as bare tokens: see
    :func:`_timed_rows` for why the columns are all-or-nothing."""
    rows = _timed_rows(seq)
    if rows:
        lines = [f"{_fmt_seconds(start)}\t{_fmt_seconds(end)}\t{token}" for start, end, token in rows]
        return "\n".join(lines) + "\n"

    lines = []
    for group in seq.groups:
        for label in group.primary:
            tok = _label_to_harte_token(label)
            if tok:
                lines.append(tok)
                break
    return "\n".join(lines) + ("\n" if lines else "")


def _label_to_harte_token(label: HarmonyLabel) -> Optional[str]:
    sem = label.semantic
    if isinstance(sem, NoChordSemantic):
        return "N"
    if not isinstance(sem, ChordSymbolSemantic):
        return None

    root_note = sem.root.note
    root_acc = _HAMON_TO_HARTE_ACC.get(sem.root.accidental or "", sem.root.accidental or "")
    shorthand = _semantic_to_shorthand(sem)
    bass = _pitch_to_degree(sem.root, sem.bass) if sem.bass else None
    tail = f"/{bass}" if bass else ""
    return f"{root_note}{root_acc}:{shorthand}{_degree_list(sem, shorthand)}{tail}"


def _degree_list(sem: ChordSymbolSemantic, shorthand: str) -> str:
    """What the shorthand does not already say, as a Harte degree list (`(*3,b5)`).

    The reader turns `*n` into `omits`, an altered degree into `alterations` and a plain
    one into `adds`/`extensions`, so writing them back is what makes a chord read from a
    degree list survive the trip. The shorthand already carries the power-chord
    omissions, the sixth, and the tensions up to the one it names."""
    stated: List[str] = []
    consumed = {"1": {3, 5}, "5": {3}}.get(shorthand, set())
    for degree in sem.omits or []:
        if degree not in consumed:
            stated.append(f"*{degree}")
    for alt in sem.alterations or []:
        glyph = alt.get("glyph") or _HAMON_TO_HARTE_ACC.get(alt.get("accidental") or "", "")
        stated.append(f"{glyph}{alt.get('degree')}")
    for degree in sem.adds or []:
        stated.append(str(degree))
    named = re.search(r"(\d+)$", shorthand)
    reach = int(named.group(1)) if named and int(named.group(1)) > 7 else 0
    for degree in sem.extensions or []:
        implied = degree == 6 and shorthand.endswith("6") or 0 < degree <= reach
        if not implied:
            stated.append(str(degree))
    return f"({','.join(stated)})" if stated else ""


# The extended shorthands, keyed by (quality, seventh) — Harte spells the tension in
# the shorthand itself (`maj9`, `min11`, `13`), so an extension the AST carries has a
# name here or it is dropped on the way out. It used to be dropped: `C:9` came back
# `C:7` because the writer only ever looked at quality and seventh.
_EXTENDED_SHORTHAND: Dict[Tuple[str, Optional[str]], Dict[int, str]] = {
    ("major", "dom7"): {9: "9", 11: "11", 13: "13"},
    ("major", "maj7"): {9: "maj9", 11: "maj11", 13: "maj13"},
    ("minor", "min7"): {9: "min9", 11: "min11", 13: "min13"},
}

# A sixth chord has no seventh, so it is named by the extension alone.
_SIXTH_SHORTHAND: Dict[str, str] = {"major": "maj6", "minor": "min6"}


def _semantic_to_shorthand(sem: ChordSymbolSemantic) -> str:
    quality = sem.quality or "major"
    seventh = sem.seventh
    suspensions = sem.suspensions  # list of ints, e.g. [4] or [2]
    extensions = sem.extensions or []
    omits = set(sem.omits or [])

    if suspensions:
        n = suspensions[0]
        return f"sus{n}" if n else "sus4"

    # The root alone, and the third-less power chord: HAMON states them as omissions.
    # Only when the quality is the default major: a minor chord with no third is still
    # minor, and `5` would have written it back as a major one.
    if not seventh and not extensions and quality == "major":
        if omits >= {3, 5}:
            return "1"
        if 3 in omits:
            return "5"

    if seventh:
        # Highest stated tension wins — Harte's shorthand implies the ones below it.
        for degree in (13, 11, 9):
            if degree in extensions:
                named = _EXTENDED_SHORTHAND.get((quality, seventh), {}).get(degree)
                if named:
                    return named
        if quality == "major" and seventh == "maj7":
            return "maj7"
        if quality == "minor" and seventh == "maj7":
            return "minmaj7"
        if quality == "minor" and seventh == "min7":
            return "min7"
        if quality == "major" and seventh == "dom7":
            return "7"
        if quality == "diminished" and seventh == "dim7":
            return "dim7"
        if quality == "half-diminished" and seventh == "hdim7":
            return "hdim7"
        # fallback
        return _HAMON_SEVENTH_TO_SHORTHAND.get(seventh, "7")

    if 6 in extensions and quality in _SIXTH_SHORTHAND:
        return _SIXTH_SHORTHAND[quality]

    return _HAMON_QUALITY_TO_SHORTHAND.get(quality, "maj")
