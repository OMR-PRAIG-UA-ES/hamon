"""Pure-Python harmony extractors for MEI, MusicXML, Humdrum, LilyPond, ABC, MuseScore."""
from __future__ import annotations

import re
from typing import List, Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_harmony_labels(format_key: str, text: str) -> List[str]:
    """Return a deduplicated list of surface harmony strings from *text*.

    *format_key* is the lowercase fixture source key, e.g. ``"musicxml"``,
    ``"mei"``, ``"kern_mxhm"``, ``"lilypond"``, ``"abc"``, ``"musescorexml"``,
    ``"kern_function"``, ``"kern_harm"``, ``"kern_fb"``, ``"dcml"``,
    ``"harte"``, ``"ireal"``.
    """
    f = format_key.lower()
    if "musicxml" in f:
        labels = _extract_musicxml(text)
    elif "mei" in f:
        labels = _extract_mei(text)
    elif "kern" in f or "humdrum" in f:
        labels = _extract_kern(text)
    elif "lily" in f or f == "ly":
        labels = _extract_lilypond(text)
    elif "abc" in f:
        labels = _extract_abc(text)
    elif "musescore" in f or "mscx" in f:
        labels = _extract_musescore(text)
    elif "dcml" in f:
        labels = _extract_dcml(text)
    elif "harte" in f:
        labels = _extract_harte(text)
    elif "jams" in f:
        labels = _extract_jams(text)
    elif "ireal" in f:
        labels = _extract_ireal(text)
    else:
        labels = []
    return list(dict.fromkeys(s for s in labels if s))  # dedup, preserve order


def read_harmony_labels_from_file(format_key: str, file_path: str) -> List[str]:
    with open(file_path, encoding="utf-8") as fh:
        return read_harmony_labels(format_key, fh.read())


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------

def _accidental_from_alter(n: float) -> str:
    if n == 0 or (n != n):  # NaN check
        return ""
    if n == 1:   return "#"
    if n == 2:   return "x"
    if n == -1:  return "b"
    if n == -2:  return "bb"
    return "#" * int(n) if n > 0 else "b" * int(-n)


_MUSICXML_KIND_MAP: dict = {
    "major": "",
    "minor": "m",
    "augmented": "+",
    "diminished": "°",
    "half-diminished": "ø",
    "dominant": "7",
    "major-seventh": "maj7",
    "minor-seventh": "m7",
    "dominant-seventh": "7",
    "diminished-seventh": "°7",
    "half-diminished-seventh": "ø7",
    "suspended-fourth": "sus4",
    "suspended-second": "sus2",
}


def _normalize_musicxml_kind(kind: str) -> str:
    k = kind.strip()
    return _MUSICXML_KIND_MAP.get(k, k)


def _extract_musicxml(text: str) -> List[str]:
    out: List[str] = []
    for block_m in re.finditer(r"<harmony\b[^>]*>[\s\S]*?</harmony>", text, re.IGNORECASE):
        block = block_m.group(0)
        step_m = re.search(r"<root-step>\s*([A-G])\s*</root-step>", block, re.IGNORECASE)
        if not step_m:
            continue
        step = step_m.group(1)
        alter_m = re.search(r"<root-alter>\s*(-?\d+(?:\.\d+)?)\s*</root-alter>", block, re.IGNORECASE)
        alter = float(alter_m.group(1)) if alter_m else 0.0
        kind_text_m = re.search(r'<kind\b[^>]*\btext="([^"]+)"', block, re.IGNORECASE)
        kind_inner_m = re.search(r"<kind\b[^>]*>\s*([^<\s]+)\s*</kind>", block, re.IGNORECASE)
        kind = _normalize_musicxml_kind((kind_text_m or kind_inner_m or re.match("", "")).group(1) if (kind_text_m or kind_inner_m) else "")
        bass_m = re.search(r"<bass-step>\s*([A-G])\s*</bass-step>", block, re.IGNORECASE)
        bass_alter_m = re.search(r"<bass-alter>\s*(-?\d+(?:\.\d+)?)\s*</bass-alter>", block, re.IGNORECASE)
        bass = ""
        if bass_m:
            b_alter = float(bass_alter_m.group(1)) if bass_alter_m else 0.0
            bass = f"/{bass_m.group(1)}{_accidental_from_alter(b_alter)}"
        label = f"{step}{_accidental_from_alter(alter)}{kind}{bass}"
        if label.strip():
            out.append(label)
    return out


def _extract_mei(text: str) -> List[str]:
    out: List[str] = []
    for m in re.finditer(r'<harm\b[^>]*\blabel="([^"]+)"', text, re.IGNORECASE):
        out.append(m.group(1))
    for m in re.finditer(r"<harm\b[^>]*>\s*([^<\s][^<]*?)\s*</harm>", text, re.IGNORECASE):
        out.append(m.group(1).strip())
    return out


def _normalize_kern_token(token: str) -> str:
    t = token.strip()
    harte = re.match(r"^([A-G])([#b]?)(?::maj7)$", t, re.IGNORECASE)
    if harte:
        return f"{harte.group(1).upper()}{harte.group(2) or ''}maj7"
    return t


def _extract_kern(text: str) -> List[str]:
    lines = text.splitlines()
    out: List[str] = []
    header_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"\*\*(kern|harm|mxhm|jazz|irb|harte|fb|function)", line, re.IGNORECASE):
            header_idx = i
            break
    if header_idx >= 0:
        header_cols = lines[header_idx].split("\t")
        harm_cols = [
            i for i, tok in enumerate(header_cols)
            if re.match(r"^\*\*(harm|mxhm|jazz|irb|harte|fb|function)", tok.strip(), re.IGNORECASE)
        ]
        for line in lines[header_idx + 1:]:
            if not line:
                continue
            if re.match(r"^\*-(\t\*-)*$", line):
                break
            if line.startswith("!") or line.startswith("*") or line.startswith("="):
                continue
            cols = line.split("\t")
            for ci in harm_cols:
                tok = cols[ci].strip() if ci < len(cols) else ""
                if tok and tok != ".":
                    out.append(tok)
        return [_normalize_kern_token(t) for t in dict.fromkeys(out)]
    # fallback: grab anything that looks like a chord token
    for line in lines:
        if not line or line.startswith("!") or line.startswith("*"):
            continue
        for tok in line.split():
            if re.match(r"^[A-G](?:[#b]|bb|##)?", tok):
                out.append(tok)
    return list(dict.fromkeys(out))


def _extract_lilypond(text: str) -> List[str]:
    # Prefer explicit hamon-surface comments.
    surface_labels = [
        m.group(1).strip()
        for m in re.finditer(r"^\s*%\s*hamon-surface\s*:\s*(.+)$", text, re.MULTILINE)
    ]
    if surface_labels:
        return list(dict.fromkeys(filter(None, surface_labels)))
    # Fall back to parsing \chordmode bodies.
    out: List[str] = []
    for body_m in re.finditer(r"\\chordmode\s*\{([\s\S]*?)\}", text):
        for raw in body_m.group(1).split():
            tok = raw.strip("{}").strip()
            if not tok or tok.startswith("\\"):
                continue
            label = _lily_token_to_hamon(tok)
            if label:
                out.append(label)
    return list(dict.fromkeys(out))


def _lily_accidental(acc: str) -> str:
    return {"is": "#", "s": "#", "es": "b", "ef": "b", "f": "b", "ees": "bb"}.get(acc, "")


def _lily_token_to_hamon(token: str) -> Optional[str]:
    # `\chordmode` puts a duration on the token (`d1:m7`, `c2`), and it is mandatory on
    # the first chord of a block — so a reader that rejects digits cannot read real
    # LilyPond, only our old comment-based export.
    m = re.match(r"^([a-g])(is|ees|es|ef|s|f)?(\d+\.*)?(?::([^\s]+))?$", token, re.IGNORECASE)
    if not m:
        return None
    note = m.group(1).upper()
    acc = _lily_accidental(m.group(2) or "")
    mod = m.group(4) or ""
    if not mod:
        return f"{note}{acc}"
    if re.match(r"^maj7?$", mod):
        return f"{note}{acc}maj7"
    if mod == "7+":
        return f"{note}{acc}maj7"
    if mod == "m7":
        return f"{note}{acc}m7"
    if mod == "m":
        return f"{note}{acc}m"
    if mod == "7":
        return f"{note}{acc}7"
    return f"{note}{acc}{mod}"


def _extract_abc(text: str) -> List[str]:
    out = [m.group(1).strip() for m in re.finditer(r'"([^"]+)"', text)]
    return list(dict.fromkeys(filter(None, out)))


def _extract_musescore(text: str) -> List[str]:
    out: List[str] = []
    for m in re.finditer(
        r"<Harmony\b[^>]*>[\s\S]*?<text>\s*([^<]+?)\s*</text>[\s\S]*?</Harmony>",
        text, re.IGNORECASE
    ):
        out.append(m.group(1).strip())
    for m in re.finditer(
        r"<Harmony\b[^>]*>[\s\S]*?<name>\s*([^<]+?)\s*</name>[\s\S]*?</Harmony>",
        text, re.IGNORECASE
    ):
        out.append(m.group(1).strip())
    return list(dict.fromkeys(filter(None, out)))


def _extract_dcml(text: str) -> List[str]:
    """Extract normalized hamon surface strings from a DCML TSV file.

    Parses each chord via the DCML semantic parser and reconstructs a
    canonical hamon surface, so lexer maximal-munch issues (e.g. iim7 →
    WORD token) are avoided when the result is re-parsed by hamon.
    """
    import csv, io as _io
    from hamonpy.adapters.dcml import _dcml_surface_to_roman  # type: ignore[import]
    out: List[str] = []
    reader = csv.DictReader(_io.StringIO(text), delimiter="\t")
    for row in reader:
        chord = row.get("chord", "").strip()
        if not chord or chord.startswith("@") or chord == ".":
            continue
        result = _dcml_surface_to_roman(chord)
        if result is None:
            out.append(chord)
            continue
        sem, _r, _d = result
        # Reconstruct a clean hamon surface from the parsed semantic
        surface = _roman_sem_to_surface(sem)
        out.append(surface)
    return list(dict.fromkeys(filter(None, out)))


def _harte_label_to_hamon_surface(label) -> str:
    """Reconstruct a hamon-parseable surface string from a Harte-parsed label."""
    from hamonpy.ast import ChordSymbolSemantic, NoChordSemantic  # type: ignore[import]
    sem = label.semantic
    if isinstance(sem, NoChordSemantic):
        return "N.C."
    if not isinstance(sem, ChordSymbolSemantic):
        return label.surface
    acc_map = {"flat": "b", "sharp": "#", "doubleFlat": "bb", "doubleSharp": "##"}
    note = sem.root.note
    acc = acc_map.get(sem.root.accidental or "", sem.root.accidental or "")
    quality = sem.quality or "major"
    seventh = sem.seventh
    suspensions = sem.suspensions
    # Build suffix
    if suspensions:
        n = suspensions[0]
        return f"{note}{acc}sus{n}"
    suffix_map = {
        ("major", "maj7"): "maj7",
        ("major", "dom7"): "7",
        ("minor", "min7"): "m7",
        ("minor", "maj7"): "mmaj7",
        ("diminished", "dim7"): "°7",
        ("half-diminished", "hdim7"): "ø7",
        ("major", None): "",
        ("minor", None): "m",
        ("diminished", None): "°",
        ("augmented", None): "+",
        ("half-diminished", None): "ø",
    }
    suffix = suffix_map.get((quality, seventh), "")
    return f"{note}{acc}{suffix}"


def _roman_sem_to_surface(sem) -> str:
    """Reconstruct a minimal hamon-compatible surface from a RomanSemantic."""
    prefix = "".join(sem.prefixAccidentals or [])
    tail = sem.tail or ""
    secondary = f"/{sem.secondary}" if sem.secondary else ""
    return f"{prefix}{sem.degree}{tail}{secondary}"


def _extract_harte(text: str) -> List[str]:
    """Extract normalized hamon surface strings from a Harte-notation file.

    Parses each token via the Harte adapter and reconstructs a canonical
    hamon surface so the Harte colon-notation (C:maj7) doesn't break the
    hamon parser.
    """
    import re as _re
    from hamonpy.adapters.harte import harte_token_to_hamon_label  # type: ignore[import]
    out: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = _re.split(r"\s+", line)
        token = parts[-1] if parts else line
        label = harte_token_to_hamon_label(token)
        if label is None:
            continue
        out.append(label.surface if ":" not in label.surface else _harte_label_to_hamon_surface(label))
    return list(dict.fromkeys(filter(None, out)))


def _extract_jams(text: str) -> List[str]:
    """Extract hamon surface strings from a JAMS document.

    Reads the first ``chord``/``chord_harte`` annotation and converts each Harte
    ``value`` to a canonical hamon surface (same path as the Harte extractor).
    """
    import json as _json
    from hamonpy.adapters.harte import harte_token_to_hamon_label  # type: ignore[import]
    try:
        doc = _json.loads(text)
    except Exception:
        return []
    anns = doc.get("annotations") if isinstance(doc, dict) else None
    data = []
    for ann in (anns or []):
        if ann.get("namespace") in ("chord", "chord_harte"):
            data = sorted(ann.get("data", []), key=lambda o: o.get("time") or 0)
            break
    out: List[str] = []
    for obs in data:
        label = harte_token_to_hamon_label(str(obs.get("value", "")))
        if label is None:
            continue
        out.append(label.surface if ":" not in label.surface else _harte_label_to_hamon_surface(label))
    return list(dict.fromkeys(filter(None, out)))


def _extract_ireal(text: str) -> List[str]:
    """Extract normalized hamon surface strings from an iReal Pro plain-text file.

    Handles plain-text chord sequences (one chord per line) and iReal chart
    strings. Uses the iReal adapter to extract and normalize chord labels.
    """
    from hamonpy.adapters.ireal import ireal_chart_text_to_hamon  # type: ignore[import]
    seq = ireal_chart_text_to_hamon(text)
    return list(dict.fromkeys(label.surface for g in seq.groups for label in g.primary if label.surface))
