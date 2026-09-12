"""HAMON → external-format exporters (surface-preserving).

Complements the per-format readers (``adapters/`` + ``adapters/formats.py``) so HAMON
can **export to every format it can import**. These are harmony-only renderers: they
embed each group's HAMON *surface* label into the target format's container so the
matching reader recovers it. Whatever a format cannot represent is reported by
:func:`hamonpy.report.lossy_report` rather than silently dropped.

Writers here (text out):
  ``musicxml`` · ``lilypond`` · ``abc`` · ``musescore`` · ``romantext`` · ``humdrum`` · ``ireal``

The richer structured writers live in their adapters (``dcml``, ``dezrann``, ``mei``,
``harte``) and the canonical surface/JSON in ``serialize``.
"""
from __future__ import annotations

from typing import List, Tuple, Optional

from .ast import ChordSymbolSemantic, HamonSequence
from .serialize import sequence_to_hamon_text  # noqa: F401  (re-export convenience)

_ACC_GLYPH = {"flat": "b", "sharp": "#", "double-flat": "bb", "double-sharp": "##",
              "natural": ""}
_ALTER = {"flat": -1, "sharp": 1, "double-flat": -2, "double-sharp": 2, "natural": 0}


def _surfaces(seq: HamonSequence) -> List[str]:
    """One surface string per primary label, in order (layered labels included)."""
    return [l.surface for g in seq.groups for l in g.primary if l.surface]


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _export_system(seq: HamonSequence) -> str:
    """Best system tag for the sequence (cs/rn/ns/fb/fun), from the hint or first label."""
    if seq.sequence_system_hint and seq.sequence_system_hint != "auto":
        return seq.sequence_system_hint
    for g in seq.groups:
        for l in g.primary:
            if l.system and l.system != "unknown":
                return l.system
    return "cs"


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------

def hamon_to_abc(seq: HamonSequence) -> str:
    """ABC tune with quoted chord symbols (``"Cmaj7"``) over rests."""
    chords = _surfaces(seq)
    head = "X:1\nT:HAMON export\nM:4/4\nL:1/4\nK:C\n"
    body = " ".join(f'"{c}" z' for c in chords) if chords else "z"
    return head + body + " |\n"


# ---------------------------------------------------------------------------
# LilyPond
# ---------------------------------------------------------------------------

# LilyPond chord modifiers we are confident of, keyed by (quality, seventh). Anything
# outside this map is written as a skip rather than guessed at: emitting `:m7` for a
# minor-major seventh would be the writer saying something false, which is the habit
# this codebase is getting rid of.
_LILY_MODIFIER = {
    ("major", None): "", ("minor", None): "m",
    ("diminished", None): "dim", ("augmented", None): "aug",
    ("major", "dom7"): "7", ("major", "maj7"): "maj7",
    ("minor", "min7"): "m7", ("diminished", "dim7"): "dim7",
    ("half-diminished", "hdim7"): "m7.5-",
}

_LILY_ACC = {"sharp": "is", "flat": "es", "double-sharp": "isis", "double-flat": "eses"}


def _lily_chord(label) -> Optional[str]:
    """One LilyPond chordmode token for a label, or None if we cannot say it exactly."""
    sem = getattr(label, "semantic", None)
    if not isinstance(sem, ChordSymbolSemantic):
        return None
    # An alteration, an added or an omitted tone we cannot spell would come out as a
    # *different* chord (F#m7b5 written `fis:m7` is a plain minor seventh), so we decline
    # instead. Degrading in silence is the failure mode this whole pass is about.
    if sem.alterations or sem.adds or sem.omits:
        return None
    root = sem.root.note.lower() + _LILY_ACC.get(sem.root.accidental or "", "")
    if sem.suspensions:
        n = sem.suspensions[0] or 4
        modifier = f"sus{n}"
    else:
        key = (sem.quality or "major", sem.seventh)
        if key not in _LILY_MODIFIER:
            return None
        modifier = _LILY_MODIFIER[key]
        # A stated tension replaces the plain seventh: c:9, c:maj9, c:m11 …
        for degree in (13, 11, 9, 6):
            if degree in (sem.extensions or []):
                base = {"7": "", "maj7": "maj", "m7": "m"}.get(modifier)
                if base is None:
                    return None
                modifier = f"{base}{degree}"
                break
    if sem.bass:
        modifier += "/" + sem.bass.note.lower() + _LILY_ACC.get(sem.bass.accidental or "", "")
    return f"{root}:{modifier}" if modifier else root


def hamon_to_lilypond(seq: HamonSequence) -> str:
    """A real LilyPond ``\\chordmode`` block.

    This used to emit a single placeholder ``c1`` with every harmony parked in
    ``% hamon-surface:`` comments — so the export carried no LilyPond harmony at all,
    and its round-trip measured our own comments coming back. A label LilyPond cannot
    state exactly becomes a skip (``s``), which holds the slot without asserting a
    chord; the loss is then real and gets reported as such.

    The duration sits on the first token only, and the rest inherit it: writing ``1`` on
    every chord would assert a rhythm the label stream does not know."""
    tokens, first = [], True
    for group in seq.groups:
        chord = next((c for c in (_lily_chord(l) for l in group.primary) if c), None)
        token = chord if chord else "s"
        if first:
            root, _, modifier = token.partition(":")
            token = f"{root}1:{modifier}" if modifier else f"{root}1"
            first = False
        tokens.append(token)
    body = " ".join(tokens) if tokens else "s1"
    return '\\version "2.24.0"\n\\chordmode {\n  ' + body + "\n}\n"


# ---------------------------------------------------------------------------
# MuseScore (uncompressed .mscx)
# ---------------------------------------------------------------------------

def hamon_to_musescore(seq: HamonSequence) -> str:
    """Minimal MSCX with one ``<Harmony><text>…</text></Harmony>`` per label."""
    blocks = "\n".join(
        f"      <Harmony>\n        <text>{_xml_escape(c)}</text>\n      </Harmony>"
        for c in _surfaces(seq)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<museScore version="4.20">\n  <Score>\n    <Staff id="1">\n'
        f"{blocks}\n"
        "    </Staff>\n  </Score>\n</museScore>\n"
    )


# ---------------------------------------------------------------------------
# MusicXML
# ---------------------------------------------------------------------------

def _root_and_suffix(label) -> Tuple[str, int, str]:
    """For a chordSymbol, return (root-step, root-alter, surface-suffix-after-root)."""
    sem = label.semantic
    assert isinstance(sem, ChordSymbolSemantic)
    note = sem.root.note
    alter = _ALTER.get(sem.root.accidental or "", 0)
    root_glyph = note + _ACC_GLYPH.get(sem.root.accidental or "", "")
    suffix = label.surface[len(root_glyph):] if label.surface.startswith(root_glyph) else ""
    return note, alter, suffix


def hamon_to_musicxml(seq: HamonSequence) -> str:
    """MusicXML ``<harmony>`` elements. Chord symbols round-trip via the ``@text``
    on ``<kind>`` (the reader reconstructs root + text). Non-chord-symbol systems
    cannot be carried by ``<harmony>`` and are omitted (reported as loss)."""
    parts: List[str] = []
    for g in seq.groups:
        for label in g.primary:
            sem = label.semantic
            if not isinstance(sem, ChordSymbolSemantic):
                continue  # noChord/roman/nashville/fb/functional: not representable here
            note, alter, suffix = _root_and_suffix(label)
            alter_el = f"<root-alter>{alter}</root-alter>" if alter else ""
            kind = f'<kind text="{_xml_escape(suffix)}">other</kind>' if suffix else "<kind></kind>"
            parts.append(f"  <harmony><root><root-step>{note}</root-step>{alter_el}</root>{kind}</harmony>")
    body = "\n".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<score-partwise version="4.0">\n  <part id="P1">\n    <measure number="1">\n'
        f"{body}\n"
        "    </measure>\n  </part>\n</score-partwise>\n"
    )


# ---------------------------------------------------------------------------
# RomanText
# ---------------------------------------------------------------------------

def hamon_to_romantext(seq: HamonSequence) -> str:
    """RomanText (``m1 C: I`` …) — one measure per group; the home key (from the
    first region, else ``C``) is emitted on the first measure. Best for the rn system."""
    key = "C"
    if seq.regions:
        k = seq.regions[0].key
        tonic = k.tonic.note + _ACC_GLYPH.get(k.tonic.accidental or "", "")
        key = tonic.lower() if (k.mode or "major") == "minor" else tonic
    lines = ["Time Signature: 4/4"]
    n = 0
    for g in seq.groups:
        for label in g.primary:
            if not label.surface:
                continue
            n += 1
            prefix = f"{key}: " if n == 1 else ""
            lines.append(f"m{n} {prefix}{label.surface}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Humdrum (**harm / **mxhm / **fb / **function spine)
# ---------------------------------------------------------------------------

_SYSTEM_SPINE = {"cs": "**mxhm", "rn": "**harm", "ns": "**harm", "fb": "**fb", "fun": "**function"}
# An analytical layer maps to the Humdrum spine that means the same thing (the reader
# in ``adapters/humdrum.py`` does the reverse). Layers Humdrum has no spine for
# (``melodic``, ``key``, ``tone``) are not written: there is nothing true to write them
# as, and ``report.py`` reports the loss.
_LAYER_SPINE = {"chord": "**mxhm", "degree": "**harm", "bass": "**fb", "function": "**function"}


def _humdrum_key(key) -> Optional[str]:
    """The ``*C:`` / ``*b-:`` tandem interpretation for a key (None for a mode Humdrum
    cannot spell — it knows major, upper case, and minor, lower case)."""
    mode = key.mode or "major"
    if mode not in ("major", "minor"):
        return None
    acc = {"sharp": "#", "flat": "-", "double-sharp": "##", "double-flat": "--"}.get(
        key.tonic.accidental or "", "")
    letter = key.tonic.note if mode == "major" else key.tonic.note.lower()
    return f"*{letter}{acc}:"


def hamon_to_humdrum(seq: HamonSequence) -> str:
    """Humdrum harmony spines: one per analytical layer, one data line per group.

    A layered sequence (``m:25,ts:1,cs:C,rn:I``) becomes parallel spines
    (``**mxhm\t**harm``) with ``.`` where a layer is silent; an unlayered one is a single
    spine chosen by its system. Tonal regions become ``*C:`` tandem interpretations at
    the group that opens them, and measures become ``=N`` barlines — so key context and
    the bar survive, which is what the capability table credits Humdrum with. The beat
    does not: a harmony-only file has no ``**recip`` to place it on."""
    layers: List[Optional[str]] = []
    for group in seq.groups:
        for label in group.primary:
            if label.layer not in layers:
                layers.append(label.layer)
    layers = [l for l in layers if l is None or l in _LAYER_SPINE] or [None]
    default_spine = _SYSTEM_SPINE.get(_export_system(seq), "**mxhm")
    spines = [_LAYER_SPINE.get(l, default_spine) if l else default_spine for l in layers]
    width = len(spines)

    keys_at = {}
    for region in (seq.regions or []):
        if region.degree or region.kind not in ("key", "region", "modulation"):
            continue                    # a tonicization has no Humdrum tandem
        tandem = _humdrum_key(region.key)
        if tandem:
            keys_at[region.from_group] = tandem

    lines = ["\t".join(spines)]
    measure = None
    for gi, group in enumerate(seq.groups):
        if gi in keys_at:
            lines.append("\t".join([keys_at[gi]] * width))
        pos = group.position
        if pos is not None and pos.measure is not None and pos.measure != measure:
            measure = pos.measure
            lines.append("\t".join([f"={measure}"] * width))
        cells = ["."] * width
        for label in group.primary:
            if label.layer in layers and label.surface:
                col = layers.index(label.layer)
                if cells[col] == ".":
                    cells[col] = label.surface
        if any(c != "." for c in cells):
            lines.append("\t".join(cells))
    lines.append("\t".join(["*-"] * width))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# iReal Pro (plain chart text — one chord per line)
# ---------------------------------------------------------------------------

def hamon_to_ireal(seq: HamonSequence) -> str:
    """iReal Pro plain-text chart (one chord per line; the reader's plain-text path)."""
    return "\n".join(_surfaces(seq)) + "\n"
