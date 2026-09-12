"""iReal Pro chord-chart adapter.

Parses iReal Pro `irealb://` URIs or pre-decoded plain-text chord sequences
into HamonSequence. Does NOT export back to iReal format (proprietary).

The iReal encoding applies a character-rotation cipher over 50-char blocks,
then percent-encodes the result. This module implements the standard decoder.

Reference: https://github.com/pianosnake/ireal-reader (community spec)
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import unquote

from hamonpy.ast import (
    HamonSequence,
    HarmonyGroup,
    HarmonyLabel,
    NoChordSemantic,
    RenderingHints,
)
from hamonpy.normalize import normalize_chord_symbol_from_surface


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

def _rotate_block(block: str) -> str:
    """Apply the iReal 50-char rotation cipher to one block."""
    if len(block) < 50:
        return block
    # Swap positions: first 24 chars ↔ last 24 chars around centre char at [24]
    return block[25:49] + block[24] + block[0:24] + block[49:]


def _decode_ireal_chart(encoded: str) -> str:
    """Decode the obfuscated chart string from an iReal URI."""
    s = unquote(encoded)
    blocks = [s[i:i + 50] for i in range(0, len(s), 50)]
    return "".join(_rotate_block(b) for b in blocks)


def _extract_chart_from_uri(uri: str) -> str:
    """Extract and decode the chord-chart portion from an irealb:// URI."""
    # Strip protocol
    body = uri
    if body.startswith("irealb://"):
        body = body[len("irealb://"):]
    # Multiple songs separated by '==='
    songs = body.split("===")
    # Take first song; fields are '=' separated: title=composer=style=key=n=chart=bpm
    parts = songs[0].split("=")
    if len(parts) >= 6:
        chart_encoded = parts[5]
    elif len(parts) >= 1:
        chart_encoded = parts[-1]
    else:
        chart_encoded = body
    return _decode_ireal_chart(chart_encoded)


# ---------------------------------------------------------------------------
# Chord token extraction
# ---------------------------------------------------------------------------

# Quality suffix patterns (longest first for greedy matching)
_QUALITY_PATTERNS = [
    r"^7alt",
    r"^\^7",        # major seventh
    r"^-\^7",       # minor-major seventh
    r"^m\^7",
    r"^-7",         # minor seventh
    r"^m7",
    r"^dim7",
    r"^o7",
    r"^h7",         # half-diminished
    r"^ø7",
    r"^\^9",        # major ninth
    r"^-9",         # minor ninth
    r"^m9",
    r"^add9",
    r"^-6",         # minor sixth
    r"^m6",
    r"^69",
    r"^sus4",
    r"^sus2",
    r"^sus",
    r"^alt",
    r"^aug",
    r"^dim",
    r"^\+",
    r"^-",           # minor
    r"^m",
    r"^o",           # diminished
    r"^\^",          # major (hat only)
    r"^9",
    r"^13",
    r"^6",
    r"^2",
    r"^7",
]

_QUALITY_SUFFIX_TO_HAMON: dict = {
    "^7":   "maj7",
    "-^7":  "mmaj7",
    "m^7":  "mmaj7",
    "-7":   "m7",
    "m7":   "m7",
    "dim7": "°7",
    "o7":   "°7",
    "h7":   "ø7",
    "ø7":   "ø7",
    "^9":   "maj9",
    "-9":   "m9",
    "m9":   "m9",
    "add9": "add9",
    "-6":   "m6",
    "m6":   "m6",
    "69":   "69",
    "sus4": "sus4",
    "sus2": "sus2",
    "sus":  "sus4",
    "alt":  "alt",
    "7alt": "7alt",
    "aug":  "+",
    "dim":  "°",
    "o":    "°",
    "+":    "+",
    "-":    "m",
    "m":    "m",
    "^":    "",
    "9":    "9",
    "13":   "13",
    "6":    "6",
    "2":    "sus2",
    "7":    "7",
}

_CHORD_RE = re.compile(
    r"([A-G][#b]?)"       # root
    r"([^\s/A-G]*)"        # quality
    r"(?:/([A-G][#b]?))?"  # optional slash bass
)


def _extract_chords_from_chart(chart: str) -> List[str]:
    """Extract chord symbols from a decoded iReal chart string."""
    out: List[str] = []
    # Strip structural markers: bar lines, section markers, repeat signs, spaces
    # Keep only chord tokens
    cleaned = re.sub(r"[|\[\]{}XYZQnNWpxrflstu*<>T1234567890,]", " ", chart)
    for m in _CHORD_RE.finditer(cleaned):
        root = m.group(1)
        quality_raw = (m.group(2) or "").strip()
        bass_raw = m.group(3)

        # Map quality suffix to hamon
        hamon_suffix = _quality_suffix_to_hamon(quality_raw)
        bass_str = f"/{bass_raw}" if bass_raw else ""
        out.append(f"{root}{hamon_suffix}{bass_str}")

    return list(dict.fromkeys(filter(None, out)))


def _quality_suffix_to_hamon(raw: str) -> str:
    """Map an iReal quality suffix to a hamon-compatible tail string."""
    for pattern in _QUALITY_PATTERNS:
        m = re.match(pattern, raw, re.IGNORECASE)
        if m:
            matched = m.group(0)
            # normalize matched key
            key = matched.replace("^", "^").replace("−", "-")
            return _QUALITY_SUFFIX_TO_HAMON.get(key, key)
    return ""


# ---------------------------------------------------------------------------
# Public API — parsing
# ---------------------------------------------------------------------------

def ireal_uri_to_hamon(uri: str) -> HamonSequence:
    """Parse an iReal Pro `irealb://` URI and return a HamonSequence."""
    chart = _extract_chart_from_uri(uri)
    return _chart_to_hamon(chart)


def ireal_chart_text_to_hamon(chart: str) -> HamonSequence:
    """Parse a pre-decoded iReal chart string into a HamonSequence.

    Accepts both raw encoded charts and plain-text sequences of chord tokens.
    If the input looks like a plain chord list (one per line), parse it directly.
    """
    if "\n" in chart.strip() or not re.search(r"[|{}\[\]XY]", chart):
        return _plain_chord_list_to_hamon(chart)
    return _chart_to_hamon(chart)


def _plain_chord_list_to_hamon(text: str) -> HamonSequence:
    groups: List[HarmonyGroup] = []
    for line in text.splitlines():
        tok = line.strip()
        if not tok or tok.startswith("#"):
            continue
        if tok.upper() in ("N", "N.C.", "NC"):
            label = HarmonyLabel(
                surface=tok, semantic=NoChordSemantic(), rendering=RenderingHints(),
                detected_system="cs", system="cs", sequence_system_hint="cs",
            )
            groups.append(HarmonyGroup(primary=[label]))
            continue
        result = normalize_chord_symbol_from_surface(tok)
        if result is None:
            continue
        semantic, rendering, _detected = result
        label = HarmonyLabel(
            surface=tok, semantic=semantic, rendering=rendering,
            detected_system="cs", system="cs", sequence_system_hint="cs",
        )
        groups.append(HarmonyGroup(primary=[label]))
    return HamonSequence(groups=groups, sequence_system_hint="cs")


def _chart_to_hamon(chart: str) -> HamonSequence:
    groups: List[HarmonyGroup] = []
    chord_surfaces = _extract_chords_from_chart(chart)
    for surface in chord_surfaces:
        result = normalize_chord_symbol_from_surface(surface)
        if result is None:
            continue
        semantic, rendering, _detected = result
        label = HarmonyLabel(
            surface=surface, semantic=semantic, rendering=rendering,
            detected_system="cs", system="cs", sequence_system_hint="cs",
        )
        groups.append(HarmonyGroup(primary=[label]))
    return HamonSequence(groups=groups, sequence_system_hint="cs")
