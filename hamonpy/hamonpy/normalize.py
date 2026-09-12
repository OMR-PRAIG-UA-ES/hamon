"""HAMON normalize — pure Python, no ANTLR dependencies."""
from __future__ import annotations

import re
from fractions import Fraction as _PyFraction
from typing import Dict, List, Optional, Tuple

from .ast import (
    Accidental, AppliedFunction, ChordQuality, ChordSymbolSemantic, DetectedSystem,
    FiguredBassSemantic, Fraction, FunctionalSemantic, HarmonyAttributes, HarmonySemantic,
    Key, NashvilleSemantic, NoChordSemantic, PitchClass, RenderingHints,
    RomanSemantic, ScaleSpec, SeventhQuality, TextSemantic,
)

# ---------------------------------------------------------------------------
# Accidental helpers
# ---------------------------------------------------------------------------

_GLYPH_TO_ACC: Dict[str, Accidental] = {
    "#": "sharp", "♯": "sharp",
    "b": "flat",  "♭": "flat",
    "x": "double-sharp", "𝄪": "double-sharp",
    "𝄫": "double-flat",
    "n": "natural", "♮": "natural",
}

def _to_accidental(glyph: str) -> Optional[Accidental]:
    return _GLYPH_TO_ACC.get(glyph)

def _normalize_pitch(note: str, acc_glyph: Optional[str]) -> Tuple[PitchClass, RenderingHints]:  # type: ignore[type-arg]
    if not acc_glyph:
        return PitchClass(note=note), RenderingHints()  # type: ignore[arg-type]
    acc = _to_accidental(acc_glyph)
    if acc is None:
        return PitchClass(note=note), RenderingHints()  # type: ignore[arg-type]
    return (
        PitchClass(note=note, accidental=acc),  # type: ignore[arg-type]
        RenderingHints(accidentalGlyphs={acc: acc_glyph}),
    )

# ---------------------------------------------------------------------------
# Quality helpers
# ---------------------------------------------------------------------------

def _set_quality(mark: str, r: Dict) -> Optional[ChordQuality]:
    if mark in ("maj", "Maj", "MAJ", "M"):
        r["qualityGlyph"] = mark; return "major"
    if mark in ("min", "Min", "MIN", "m", "-", "−"):
        r["qualityGlyph"] = "-" if mark == "−" else mark; return "minor"
    if mark in ("dim", "Dim", "DIM", "o", "°"):
        r["qualityGlyph"] = mark; return "diminished"
    if mark == "ø":
        r["qualityGlyph"] = mark; return "half-diminished"
    if mark in ("aug", "Aug", "AUG", "+"):
        r["qualityGlyph"] = mark; return "augmented"
    return None

# ---------------------------------------------------------------------------
# Seventh helpers
# ---------------------------------------------------------------------------

def _parse_seventh_like(part: str, saw_explicit_major: bool, r: Dict):
    """Returns (seventh, extra_extensions) or (None, [])."""
    md = re.match(r"^Δ([0-9]+)?$", part)
    if md:
        r["seventhGlyph"] = "Δ"
        n = int(md.group(1)) if md.group(1) else 7
        if n == 7: return "maj7", []
        if n in (9, 11, 13): return "maj7", [n]
        return "maj7", []

    mm = re.match(r"^(maj|Maj|MAJ|M)([0-9]+)$", part)
    if mm:
        r["seventhGlyph"] = mm.group(1)
        r.setdefault("qualityGlyph", mm.group(1))
        n = int(mm.group(2))
        if n == 7: return "maj7", []
        if n in (9, 11, 13): return "maj7", [n]
        return "maj7", []

    try:
        n = int(part)
        if n == 7:
            r["seventhGlyph"] = "7"; return "dom7", []
        if n in (9, 11, 13):
            r["seventhGlyph"] = str(n); return "dom7", [n]
    except ValueError:
        pass

    return None, []

def _coerce_seventh(quality: ChordQuality, seventh: SeventhQuality, saw_explicit_major: bool) -> SeventhQuality:
    if quality == "major" and saw_explicit_major and seventh == "dom7":
        return "maj7"
    if seventh != "dom7":
        return seventh
    if quality == "minor": return "min7"
    if quality == "diminished": return "dim7"
    if quality == "half-diminished": return "hdim7"
    return seventh

# ---------------------------------------------------------------------------
# Alteration / add-omit-sus helpers
# ---------------------------------------------------------------------------

def _parse_alteration(part: str):
    m = re.match(r"^([#b♯♭x𝄪𝄫n♮])([0-9]+)$", part)
    if not m: return None, None, None
    glyph, deg = m.group(1), int(m.group(2))
    acc = _to_accidental(glyph)
    return acc, deg, glyph

def _parse_add_omit_sus(part: str):
    m = re.match(r"^(add|omit|no|sus)([0-9]+)?$", part, re.IGNORECASE)
    if not m: return None, None
    kind = m.group(1).lower()
    n = int(m.group(2)) if m.group(2) else None
    return kind, n

# ---------------------------------------------------------------------------
# tokenizeChordTail
# ---------------------------------------------------------------------------

_KNOWN_QUAL = re.compile(r"^(maj|Maj|MAJ|min|Min|MIN|dim|Dim|DIM|aug|Aug|AUG|sus|Sus|SUS|add|Add|ADD|omit|Omit|OMIT|no|No|NO)")

def _tokenize_chord_tail(tail: str) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(tail):
        rest = tail[i:]

        # Parenthesised tension lists: the parens/commas are pure grouping — skip
        # them so the tensions inside are tokenised (and lifted) like the stacked
        # form. Reaches WORD-led chords (e.g. Dm7(9)) via the surface path.
        if rest[0] in "(),":
            i += 1; continue

        # Minor + major-seventh compound: mmaj7 / mMaj7 / mM7 / minMaj7.
        # It has to be split before the generic word rule below, which would
        # swallow "mmaj" whole and leave a bare "7" — reading a minor-major
        # seventh as a dominant one. (The dash-led spellings, -maj7 and -M7,
        # already split because "-" is not a letter.)
        minmaj = re.match(r"^(min|Min|MIN|m)(maj|Maj|MAJ|M)([0-9]+)", rest)
        if minmaj:
            out.append(minmaj.group(1))
            out.append(minmaj.group(2) + minmaj.group(3))
            i += len(minmaj.group(0)); continue

        # maj7 / M7 as single token
        maj7 = re.match(r"^(maj|Maj|MAJ|M)([0-9]+)", rest)
        if maj7:
            out.append(maj7.group(0)); i += len(maj7.group(0)); continue

        # Unicode marks
        for uni in ("Δ", "°", "ø", "♯", "♭", "𝄪", "𝄫", "♮"):
            if rest.startswith(uni):
                uni_ext = re.match(r"^" + re.escape(uni) + r"[0-9]*", rest)
                tok = uni_ext.group(0) if uni_ext else uni
                out.append(tok); i += len(tok); break
        else:
            # add/omit/no/sus + optional number
            aos = re.match(r"^(add|omit|no|sus)([0-9]+)?", rest, re.IGNORECASE)
            if aos and re.match(r"^(add|omit|no|sus)", rest, re.IGNORECASE):
                out.append(aos.group(0)); i += len(aos.group(0)); continue

            # accidental + digit
            acc_dig = re.match(r"^[#b♯♭x𝄪𝄫n♮][0-9]+", rest)
            if acc_dig:
                out.append(acc_dig.group(0)); i += len(acc_dig.group(0)); continue

            # word (quality token etc.)
            word = re.match(r"^[a-zA-Z]+", rest)
            if word:
                out.append(word.group(0)); i += len(word.group(0)); continue

            # number
            num = re.match(r"^[0-9]+", rest)
            if num:
                out.append(num.group(0)); i += len(num.group(0)); continue

            # single symbol
            out.append(rest[0]); i += 1

    return out

# ---------------------------------------------------------------------------
# Main normalize functions (called by parse_visitor.py)
# ---------------------------------------------------------------------------

def _rendering_to_dict(rh: RenderingHints) -> Dict:
    """Convert RenderingHints to a plain dict, dropping None values."""
    return {k: v for k, v in rh.__dict__.items() if v is not None}


def _expand_paren_groups(parts: List[str]) -> List[str]:
    """Flatten parenthesised tension lists into ordinary chord-tail tokens.

    A paren group reaches us as a single ``getText()`` token like ``(b9,b13)``;
    splitting on comma and re-tokenizing each item lets the normal alteration /
    extension matchers lift the tensions into the semantic (alterations,
    extensions) instead of dropping them into ``rawParts``. The exact glyphs are
    still preserved on the label ``surface``, so this only enriches semantics.
    """
    out: List[str] = []
    for t in parts:
        if len(t) >= 2 and t.startswith("(") and t.endswith(")"):
            for piece in t[1:-1].split(","):
                piece = piece.strip()
                if piece:
                    out.extend(_tokenize_chord_tail(piece))
        else:
            out.append(t)
    return out


def normalize_chord_symbol_from_ctx(note: str, acc_glyph: Optional[str], parts: List[str],
                                     bass_note: Optional[str], bass_acc_glyph: Optional[str]):
    root, r0 = _normalize_pitch(note, acc_glyph)
    r: Dict = _rendering_to_dict(r0)

    bass: Optional[PitchClass] = None
    if bass_note:
        bass, rb = _normalize_pitch(bass_note, bass_acc_glyph)
        r.update(_rendering_to_dict(rb))

    quality: Optional[ChordQuality] = None
    seventh: Optional[SeventhQuality] = None
    extensions: List[int] = []
    alterations = []
    adds: List[int] = []
    omits: List[int] = []
    suspensions: List[Optional[int]] = []
    saw_explicit_major = False

    for t in _expand_paren_groups(parts):
        # Combined quality+seventh tokens produced by _tokenize_chord_tail
        if t in ("ø7", "ø"):
            if t == "ø7":
                quality = "half-diminished"; seventh = "hdim7"; r["qualityGlyph"] = "ø"; continue
            else:
                quality = "half-diminished"; r["qualityGlyph"] = "ø"; continue
        if t in ("°7", "°"):
            if t == "°7":
                quality = "diminished"; seventh = "dim7"; r["qualityGlyph"] = "°"; continue
            else:
                quality = "diminished"; r["qualityGlyph"] = "°"; continue

        sev, exts = _parse_seventh_like(t, saw_explicit_major, r)
        if sev:
            seventh = sev
            extensions.extend(exts)
            continue

        q = _set_quality(t, r)
        if q:
            quality = q
            if t in ("maj", "Maj", "MAJ", "M"):
                saw_explicit_major = True
            continue

        acc, deg, glyph = _parse_alteration(t)
        if acc and deg is not None and glyph:
            alterations.append({"accidental": acc, "degree": deg, "glyph": glyph})
            r.setdefault("accidentalGlyphs", {})[acc] = glyph
            continue

        kind, n = _parse_add_omit_sus(t)
        if kind:
            if kind == "add" and n is not None: adds.append(n)
            elif kind in ("omit", "no") and n is not None: omits.append(n)
            elif kind == "sus": suspensions.append(n)
            r.setdefault("rawParts", []).append(t)
            continue

        try:
            n_int = int(t)
            if n_int in (6, 9, 11, 13):
                extensions.append(n_int); continue
        except ValueError:
            pass

        r.setdefault("rawParts", []).append(t)

    if quality is None:
        quality = "major"

    if not seventh and any(x in (9, 11, 13) for x in extensions):
        seventh = "dom7"
        r["seventhGlyph"] = r.get("seventhGlyph") or str(next(x for x in extensions if x in (9, 11, 13)))

    if seventh:
        seventh = _coerce_seventh(quality, seventh, saw_explicit_major)

    rendering = RenderingHints(
        qualityGlyph=r.get("qualityGlyph"),
        seventhGlyph=r.get("seventhGlyph"),
        accidentalGlyphs=r.get("accidentalGlyphs"),
        rawParts=r.get("rawParts"),
    )

    semantic = ChordSymbolSemantic(
        root=root,
        quality=quality,
        seventh=seventh or None,
        extensions=extensions or None,
        alterations=alterations or None,
        adds=adds or None,
        omits=omits or None,
        suspensions=suspensions or None,
        bass=bass,
    )
    return semantic, rendering, "cs"


def normalize_chord_symbol_from_surface(surface: str):
    """Fallback: parse a chord symbol from its raw surface string (no ANTLR context)."""
    # The ASCII natural `n` only counts as an accidental when a letter does NOT follow it,
    # so `Cno3` reads as C + `no3` (omit 3), not C♮ + `o3` (diminished). See _accidental note.
    m = re.match(r"^([A-G])([#b♯♭x𝄪𝄫♮]|n(?![A-Za-z]))?", surface)
    if not m:
        return None
    note = m.group(1)
    acc_glyph = m.group(2)
    head = surface[m.end():]

    bass_note = bass_acc_glyph = None
    slash_ix = head.find("/")
    if slash_ix >= 0:
        before, after = head[:slash_ix], head[slash_ix + 1:]
        head = before
        mb = re.match(r"^([A-G])([#b♯♭x𝄪𝄫♮]|n(?![A-Za-z]))?", after)
        if mb:
            bass_note = mb.group(1)
            bass_acc_glyph = mb.group(2)

    parts = _tokenize_chord_tail(head)
    return normalize_chord_symbol_from_ctx(note, acc_glyph, parts, bass_note, bass_acc_glyph)


def normalize_roman_from_parts(degree: str, prefix_accidentals: List[str],
                                tail: str, secondary: Optional[str]):
    semantic = RomanSemantic(
        degree=degree,
        prefixAccidentals=prefix_accidentals or None,
        tail=tail or None,
        secondary=secondary or None,
    )
    return semantic, RenderingHints(), "rn"


def normalize_number_harmony_from_parts(number: int, prefix_accidentals: List[str],
                                         tail: str, secondary: Optional[str]):
    looks_figured = bool(re.search(r"[-−]\d", tail))
    kind: str = "figuredBass" if looks_figured else "nashville"
    if looks_figured:
        semantic = FiguredBassSemantic(
            number=number,
            prefixAccidentals=prefix_accidentals or None,
            tail=tail or None,
        )
    else:
        semantic = NashvilleSemantic(
            number=number,
            prefixAccidentals=prefix_accidentals or None,
            tail=tail or None,
            secondary=secondary or None,
        )
    return semantic, RenderingHints(), "fb" if looks_figured else "ns"


def normalize_functional_from_chain(chain: List[str]):
    return FunctionalSemantic(chain=chain), RenderingHints(), "fun"


def normalize_no_chord():
    return NoChordSemantic(), RenderingHints(), "unknown"


_ROMAN_DEGREES_RE = re.compile(r"^(III|VII|IV|VI|II|I|iii|vii|iv|vi|ii|i|v|V)")
_ROMAN_WITH_QUALITY_RE = re.compile(
    r"^(III|VII|IV|VI|II|I|iii|vii|iv|vi|ii|i|v|V)"
    r"(m7|maj7|Maj7|M7|°7|ø7|%7|\+7|m|°|ø|%|\+)"
    r"(?:/([A-Za-z]+))?$"
)


def normalize_text_from_surface(text: str, quoted: bool):
    if not quoted:
        # bVII / bbIV — flat-prefix Roman numeral swallowed as WORD by maximal munch
        m_flat = re.match(r"^(b{1,2}|♭{1,2}|𝄫)", text)
        if m_flat:
            prefix_glyphs = m_flat.group(0)
            rest = text[len(prefix_glyphs):]
            rm = _ROMAN_DEGREES_RE.match(rest)
            if rm:
                degree = rm.group(1)
                tail = rest[len(degree):]
                secondary = None
                slash_m = re.match(r"^/([A-Za-z]+)", tail)
                if slash_m:
                    sec_rm = _ROMAN_DEGREES_RE.match(slash_m.group(1))
                    if sec_rm:
                        secondary = sec_rm.group(1)
                        tail = tail[len(slash_m.group(0)):]
                prefix_accidentals = (
                    [prefix_glyphs] if prefix_glyphs == "𝄫" else list(prefix_glyphs)
                )
                sem = RomanSemantic(degree=degree, prefixAccidentals=prefix_accidentals,
                                    tail=tail or None, secondary=secondary)
                return sem, RenderingHints(), "rn"

        # Roman numeral + tail where WORD maximal munch merged degree+quality
        # e.g. iim7 → WORD(iim)+INT(7), Vm7 → WORD(Vm)+INT(7)
        rm2 = _ROMAN_WITH_QUALITY_RE.match(text)
        if rm2:
            degree2 = rm2.group(1)
            tail2 = rm2.group(2)
            secondary2_str = rm2.group(3)
            secondary2: Optional[str] = None
            if secondary2_str:
                sec_m = _ROMAN_DEGREES_RE.match(secondary2_str)
                if sec_m:
                    secondary2 = sec_m.group(1)
            return normalize_roman_from_parts(degree2, [], tail2, secondary2)

        # Chord-symbol heuristic
        if _looks_like_chord_symbol(text):
            result = normalize_chord_symbol_from_surface(text)
            if result:
                return result

    return TextSemantic(text=text), RenderingHints(), "text"


def _looks_like_chord_symbol(surface: str) -> bool:
    m = re.match(r"^([A-G])([#b♯♭x𝄪𝄫♮]|n(?![A-Za-z]))?", surface)
    if not m:
        return False
    rest = surface[m.end():]
    if not rest:
        return True
    if re.search(r"[0-9]", rest): return True
    if re.search(r"[Δ°ø+\-−/()]", rest): return True
    if re.match(r"^(maj|min|dim|aug|sus|add|omit|no)", rest, re.IGNORECASE): return True
    if re.match(r"^[Mmo]", rest): return True
    return False


# ===========================================================================
# Analytical layer (v0.2.0).
# ===========================================================================

_LETTER_ORDER = ["C", "D", "E", "F", "G", "A", "B"]
_LETTER_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
# Scale-degree semitone offsets per mode, so degree→pitch is correct in minor and
# the church modes (used for DCML minor global keys and modal tonicizations).
_MODE_STEPS = {
    "major": [0, 2, 4, 5, 7, 9, 11], "ionian": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10], "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}

_KNOWN_LAYERS = {"chord", "degree", "nashville", "function", "bass", "melodic", "key", "tone"}
_KNOWN_MODES = {
    "major", "minor", "ionian", "dorian", "phrygian",
    "lydian", "mixolydian", "aeolian", "locrian",
}
_ROMAN_TO_NUMBER = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}
_NUMBER_TO_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}

_ROMAN_KEY_RE = re.compile(r"^(III|VII|IV|VI|II|I|iii|vii|iv|vi|ii|i|v|V)$")
_ACC_PREFIX_RE = re.compile(r"^[#b♯♭xn♮𝄪𝄫]+")


# v0.4 short layer tags → canonical internal role names.
_LAYER_ALIASES = {"cs": "chord", "rn": "degree", "ns": "nashville",
                  "fb": "bass", "fn": "function", "tonality": "key"}


def resolve_layer(word: str):
    w = word.lower().rstrip(":")  # a v0.4 tag arrives as e.g. "cs:"
    w = _LAYER_ALIASES.get(w, w)
    return w if w in _KNOWN_LAYERS else None


def _resolve_mode(word: Optional[str]):
    if not word:
        return None
    w = word.lower()
    return w if w in _KNOWN_MODES else None


def _acc_offset_glyphs(glyphs: List[str]) -> int:
    off = 0
    for g in glyphs:
        if g in ("#", "♯"): off += 1
        elif g in ("x", "𝄪"): off += 2
        elif g in ("b", "♭"): off -= 1
        elif g == "𝄫": off -= 2
    return off


def _acc_offset(acc: Optional[Accidental]) -> int:
    return {"sharp": 1, "double-sharp": 2, "flat": -1, "double-flat": -2}.get(acc or "", 0)


def _offset_to_acc(off: int):
    return {1: "sharp", 2: "double-sharp", -1: "flat", -2: "double-flat"}.get(off)


def pitch_to_degree(parent: Key, child_tonic: PitchClass, child_mode: Optional[str] = None) -> str:
    """Inverse of degree_to_pitch: express *child_tonic* as a Roman degree relative to
    *parent* (case = child mode, accidental prefix for chromatic degrees). E.g. G major
    in C major → 'V'; Ab major in C major → 'bVI'; A minor in C major → 'vi'."""
    parent_idx = _LETTER_ORDER.index(parent.tonic.note)
    child_idx = _LETTER_ORDER.index(child_tonic.note)
    n = ((child_idx - parent_idx) % 7) + 1
    steps = _MODE_STEPS.get(parent.mode or "major", _MAJOR_STEPS)
    expected = (_LETTER_SEMITONE[parent.tonic.note] + _acc_offset(parent.tonic.accidental) + steps[n - 1]) % 12
    actual = (_LETTER_SEMITONE[child_tonic.note] + _acc_offset(child_tonic.accidental)) % 12
    off = ((actual - expected + 6) % 12) - 6
    prefix = "#" * off if off > 0 else "b" * (-off)
    roman = _NUMBER_TO_ROMAN[n]
    if (child_mode or "major") not in ("major", "ionian"):
        roman = roman.lower()
    return prefix + roman


def degree_to_pitch(parent: Key, acc_glyphs: List[str], roman: str) -> PitchClass:
    n = _ROMAN_TO_NUMBER.get(roman.lower(), 1)
    steps = _MODE_STEPS.get(parent.mode or "major", _MAJOR_STEPS)
    tonic_letter_idx = _LETTER_ORDER.index(parent.tonic.note)
    parent_semi = (_LETTER_SEMITONE[parent.tonic.note] + _acc_offset(parent.tonic.accidental)) % 12
    target_semi = (parent_semi + steps[n - 1] + _acc_offset_glyphs(acc_glyphs)) % 12
    target_letter = _LETTER_ORDER[(tonic_letter_idx + (n - 1)) % 7]
    natural_semi = _LETTER_SEMITONE[target_letter]
    off = ((target_semi - natural_semi + 6) % 12) - 6
    accidental = _offset_to_acc(off)
    return PitchClass(note=target_letter, accidental=accidental) if accidental else PitchClass(note=target_letter)


def normalize_key_decl(target: dict, mode_word: Optional[str], parent_key: Optional[Key]):
    """Parse a @key: directive. `target` is one of:
       {"type":"pitch","note":str,"acc":Optional[str]}
       {"type":"roman","accs":List[str],"roman":str}
       {"type":"word","text":str}
    Returns (Key, kind, degree_or_None).
    """
    mode = _resolve_mode(mode_word) or "major"

    if target["type"] == "pitch":
        pitch, _ = _normalize_pitch(target["note"], target.get("acc"))
        return Key(tonic=pitch, mode=mode), "key", None

    if target["type"] == "roman":
        return _tonicization_from(target["accs"], target["roman"], mode, parent_key)

    # word: maximal-munch collapsed 'Bb' (a flat key) or 'bVI' (an altered degree).
    word = target["text"]
    m_pitch = re.match(r"^([A-G])([#b♯♭xn♮𝄪𝄫]*)$", word)
    if m_pitch and not _ROMAN_KEY_RE.match(word):
        note = m_pitch.group(1)
        acc_glyph = m_pitch.group(2)[0] if m_pitch.group(2) else None
        pitch, _ = _normalize_pitch(note, acc_glyph)
        return Key(tonic=pitch, mode=mode), "key", None

    acc_prefix = (_ACC_PREFIX_RE.match(word).group(0) if _ACC_PREFIX_RE.match(word) else "")
    roman_part = word[len(acc_prefix):]
    return _tonicization_from(list(acc_prefix), roman_part, mode, parent_key)


def _tonicization_from(acc_glyphs: List[str], roman: str, mode, parent_key: Optional[Key]):
    label = "".join(acc_glyphs) + roman
    tonic = degree_to_pitch(parent_key, acc_glyphs, roman) if parent_key else PitchClass(note="C")
    return Key(tonic=tonic, mode=mode, label=label), "tonicization", label


_NHT_ALIASES = {
    "passing": "passing", "pass": "passing",
    "neighbor": "neighbor", "neighbour": "neighbor", "n": "neighbor",
    "upper": "upper-neighbor", "upper-neighbor": "upper-neighbor", "un": "upper-neighbor",
    "lower": "lower-neighbor", "lower-neighbor": "lower-neighbor", "ln": "lower-neighbor",
    "incomplete": "incomplete-neighbor", "incomplete-neighbor": "incomplete-neighbor",
    "susp": "suspension", "suspension": "suspension", "sus": "suspension",
    "ret": "retardation", "retardation": "retardation",
    "app": "appoggiatura", "appoggiatura": "appoggiatura",
    "esc": "escape", "escape": "escape", "echappee": "escape",
    "ant": "anticipation", "anticipation": "anticipation",
    "ped": "pedal", "pedal": "pedal",
    "cambiata": "cambiata", "fux": "cambiata", "nc": "cambiata",
    "ct": "changing-tone", "changing": "changing-tone", "changing-tone": "changing-tone",
}


def _parse_quarters(text: str) -> Optional[Fraction]:
    """A `[dur:…]` value → an exact :class:`Fraction` of quarter notes.

    Accepts a fraction (``3/4``), an integer (``2``) or a decimal (``1.5``, which the
    grammar admits through its OTHER token). Anything else is ignored rather than
    guessed — an extent we cannot read is not an extent we invent.
    """
    raw = text.strip()
    if not raw:
        return None
    try:
        exact = _PyFraction(raw)
    except (ValueError, ZeroDivisionError):
        return None
    return Fraction(numerator=exact.numerator, denominator=exact.denominator)


def _parse_seconds(text: str) -> Optional[float]:
    """A `[dur:…s]` value → an extent in seconds, or ``None`` if it is not one.

    The suffix is what says which clock the source stated: ``1.85s`` is seconds,
    ``3/4`` is quarter notes. Only a plain decimal takes the suffix — seconds arrive
    from audio annotations, which state them that way. The shape is matched explicitly
    rather than handed to ``float()``, which would also swallow ``1e3s`` and ``nans``:
    the TypeScript side mirrors this exact pattern, and the two must not drift.
    """
    if not re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)[sS]", text.strip()):
        return None
    return float(text.strip()[:-1])


def parse_analysis_attrs(inners: List[str]):
    """Interpret bracketed attributes; returns (HarmonyAttributes|None, tone_dict|None)."""
    attrs: dict = {}
    tone: Optional[dict] = None
    scales: List[ScaleSpec] = []

    for raw in inners:
        inner = raw.strip()
        ci = inner.find(":")
        key = (inner[:ci] if ci >= 0 else inner).lower()
        val = inner[ci + 1:] if ci >= 0 else None

        m_no = re.match(r"^no(\d+)$", inner, re.IGNORECASE)
        if m_no:
            if int(m_no.group(1)) == 1:
                attrs["omittedRoot"] = True
            continue

        if key == "rootless":
            attrs["rootless"] = True
        elif key in ("arp", "arpeggio", "arpeggiated"):
            attrs["arpeggiated"] = True
        elif key in ("ped", "pedal"):
            attrs["pedal"] = True
        elif key == "inv" and val is not None:
            attrs["inversion"] = int(val)
        elif key == "ton" and val is not None:
            attrs["tonicizes"] = val
        elif key == "of" and val is not None:
            attrs["applied"] = AppliedFunction(target=val)
        elif key == "dur" and val:
            # The extent inherits the clock the source stated: a bare value is quarter
            # notes, a trailing `s` is seconds (`[dur:1.85s]`).
            seconds = _parse_seconds(val)
            if seconds is not None:
                attrs["durationSeconds"] = seconds
            else:
                duration = _parse_quarters(val)
                if duration is not None:
                    attrs["duration"] = duration
        elif key == "endref" and val:
            attrs["endRef"] = val.strip()
        elif key == "scale" and val:
            scales.append(ScaleSpec(name=val.strip()))
        elif key == "ht":
            tone = {"category": "harmonic", "type": "chord-tone"}
        elif key == "nht":
            tone = {"category": "nonharmonic",
                    "type": _NHT_ALIASES.get(val.lower()) if val else None}
        # unknown attributes are ignored (surface still round-trips)

    if scales:
        attrs["scales"] = scales
    attributes = HarmonyAttributes(**attrs) if attrs else None
    return attributes, tone
