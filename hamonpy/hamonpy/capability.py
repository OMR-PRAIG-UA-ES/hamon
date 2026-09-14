"""What each encoding can natively say — and where HAMON has to work around it.

The single source of truth for **format capability**, and the reason there is one:
HAMON's exporters are surface-preserving, so they embed the full HAMON surface into
whatever text field the target has. MEI gets ``<harm>Cmaj7[scale:ionian]</harm>`` and
reads it straight back, so a naive round-trip calls MEI *lossless* for a chord-scale
MEI cannot express at all. The format did not carry the meaning; it carried our string.

So every export has two readings, and this module is what tells them apart:

- **native** — only what the target expresses in its own vocabulary. This is the honest
  measure, and the one the loss matrix reports.
- **workaround** — native, plus the HAMON surface parked in an out-of-band slot (a
  comment, an ``<annot>``, a ``sandbox``). Lossless by construction, because it is
  escrow, not translation. Legitimate to *ship*; never a claim about the format.

Text is always a workaround. Where a format could hold the meaning semantically and we
write a string instead, that is a gap to close, not a feature — the standing example is
MEI, where the plan is to propose a semantic HAMON encoding rather than keep leaning on
``<harm>`` text (see ``STATUS.md`` → "New MEI harmony encoding").

The asymmetry is the interlingua argument: Harte ``.lab`` and iReal have **no** slot, so
no workaround can rescue them. :func:`annotation_slot` returns ``None`` for exactly those.

This module holds tables only — no adapter imports — so both :mod:`hamonpy.report`
(the empirical round-trip, and the projection to a format's native vocabulary) and
``site/`` (the declarative aspect count) can depend on it without a cycle. Before it existed the two models lived apart and
could disagree with nobody the wiser.
"""
from __future__ import annotations

import re
from collections import Counter

# ── aspects a harmony label can carry ────────────────────────────────────────
# root/quality/tensions/bass = chord-symbol core · roman = RN degree/function
# applied = secondary/applied (of:, /V) · key = tonal region/key context
# scale = chord-scale (Berklee) · figuredbass · functional (T/S/D) · nashville · tone
ASPECT_LABEL = {
    "root": "root", "quality": "quality", "tensions": "7th/tensions", "bass": "bass/inv.",
    "roman": "roman fn.", "applied": "applied/secondary", "key": "key/region",
    "scale": "chord-scale", "figuredbass": "figured bass", "functional": "T-S-D",
    "nashville": "Nashville", "tone": "non-harm. tone", "nochord": "N.C.", "text": "text",
    # `native_loss` also reports where a label is, which is not a kind of label but is
    # just as lost when the target has nowhere to put it.
    "position": "position",
}

_CS = {"root", "quality", "tensions", "bass"}  # chord-symbol core

# The split is the point. An aspect is **semantic** for a format when the format has its
# own structured vocabulary for it, and merely **text** when the only way to carry it is
# an opaque string in some free field. Text is a workaround: it survives our round-trip
# because we wrote the string and we read it back, which says nothing about the format
# and nothing another tool could use.
#
# MEI is the standing example, and the reason this split exists. `<harm>` accepts
# arbitrary character data, so crediting MEI with Roman numerals, applied chords and key
# context means crediting it for holding *our* text. Semantically MEI encodes figured
# bass (`<fb>`/`<f>`) and chord symbols (`<chordDef>`/`<chordMember>`); it has no
# first-class Roman-numeral or tonal-region vocabulary. Closing that gap by proposing a
# semantic HAMON encoding for MEI — rather than leaning on `<harm>` text forever — is on
# the roadmap (STATUS.md → "New MEI harmony encoding"), and this table is what will
# measure the proposal when it lands.

# What each format encodes in its OWN structured vocabulary.
SEMANTIC_CAPABILITY = {
    "hamon": set(ASPECT_LABEL),  # the interlingua: everything, natively
    "harte": _CS,                # the shorthand IS Harte's vocabulary
    "ireal": _CS,
    "lilypond": _CS,             # \chordmode is a structured chord vocabulary
    "abc": _CS,                  # quoted chord symbols: a defined convention
    "musescore": _CS,            # <Harmony> has <root>/<extension>
    "musicxml": _CS | {"roman"},                         # <harmony>; MusicXML 4 <numeral>
    "romantext": {"roman", "tensions", "bass", "applied", "key"},
    # DCML expresses inversions via `figbass` *attached to a Roman numeral*, not as a
    # standalone figured bass — so a bare figured-bass line is NOT DCML-native.
    "dcml": {"roman", "tensions", "bass", "applied", "key"},
    # MEI: figured bass and chord symbols are structured; Roman/applied/key are `<harm>`
    # character data, i.e. the workaround — see the note above.
    "mei": _CS | {"figuredbass"},
    # Humdrum: one spine per system (**mxhm/**harm/**fb/**function); `**harm` spells an
    # applied chord (`V7/ii`) and a `*C:` tandem interpretation states the key.
    "humdrum": _CS | {"roman", "figuredbass", "functional", "applied", "key"},
    # Dezrann's label is an opaque `tag` string, so nothing in it is structured.
    "dezrann": set(),
    # JAMS `chord` is a validated namespace of Harte values; `key_mode` likewise.
    "jams": _CS | {"key"},
}

# What a format can additionally hold as an opaque string — the workaround. Union with
# the semantic set gives the old, flattering "capability" the matrix used to report.
TEXT_CAPABILITY = {
    "mei": {"roman", "applied", "key", "functional"},   # <harm> character data
    "dezrann": _CS | {"roman", "applied"},              # the `tag`
    "abc": set(), "lilypond": set(), "musescore": set(),
}

#: The honest capability: what the format says in its own terms. This is what
#: :func:`native_loss` counts against, and what the loss matrix reports.
CAPABILITY = SEMANTIC_CAPABILITY

# `A7[of:ii]` is a chord symbol that also states its function. A Roman vocabulary says
# the function (`V7/ii`) and a chord vocabulary says the chord, but only HAMON says both
# on one label — so an applied attribute on a *chord symbol* is HAMON-only, even for a
# format that carries `applied` on its Roman numerals.
CHORD_APPLIED_NATIVE = {"hamon"}


def holds_as_text(fmt: str) -> set:
    """Aspects ``fmt`` can only carry as an opaque string — its workaround reach."""
    return TEXT_CAPABILITY.get(fmt, set())


# The capability matrix in `documentation/index.md`, rendered from the table above so
# the prose cannot drift from the code (`test_capability.py` checks the file holds it).
_TABLE_COLUMNS = (
    ("Chord sym.", "root"), ("Roman", "roman"), ("Fig. bass", "figuredbass"),
    ("Functional", "functional"), ("Nashville", "nashville"), ("Applied", "applied"),
    ("Key/region", "key"),
)
_TABLE_ROWS = (
    ("**HAMON** (interlingua)", ("hamon",)), ("MEI", ("mei",)), ("Humdrum", ("humdrum",)),
    ("MusicXML", ("musicxml",)), ("Dezrann", ("dezrann",)), ("DCML", ("dcml",)),
    ("RomanText", ("romantext",)), ("Harte · iReal Pro", ("harte", "ireal")),
    ("JAMS", ("jams",)), ("LilyPond · ABC · MuseScore", ("lilypond", "abc", "musescore")),
)


def capability_table_markdown() -> str:
    """The per-format rows of the documentation's capability matrix (Markdown)."""
    lines = ["| Format / library | " + " | ".join(c for c, _ in _TABLE_COLUMNS) + " |",
             "|---|" + ":-:|" * len(_TABLE_COLUMNS)]
    for label, fmts in _TABLE_ROWS:
        caps = [SEMANTIC_CAPABILITY[f] for f in fmts]
        assert all(c == caps[0] for c in caps), f"{label}: formats no longer share a row"
        cells = ["✓" if aspect in caps[0] else "–" for _, aspect in _TABLE_COLUMNS]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


# Which targets natively carry a harmony's METRIC onset position (measure:beat)? Score
# and time-aligned annotation formats do; a plain label list or an audio-time list does not.
POSITION_NATIVE = {
    "hamon", "mei", "musicxml", "humdrum", "romantext", "dcml",
    "lilypond", "abc", "musescore", "dezrann", "ireal",
}
# dcml is native since its writer emits the expanded table's `mn`/`mn_onset`/`quarterbeats`
# columns — the ones ms3 writes and `dcml_expanded` reads — for every placed group.
# NOT native:  harte  — .lab carries audio seconds, not a metric measure:beat
#              jams   — observations are audio seconds, not a metric measure:beat

# …and the mirror question, since v0.5: which targets natively carry a harmony's
# PHYSICAL onset (`s:`, seconds)? Exactly the audio-time formats — the same two that
# cannot hold a metric onset. The two clocks do not substitute for each other: a
# format that holds one and not the other loses the one it cannot hold.
SECONDS_NATIVE = {"hamon", "harte", "jams"}

_METRIC_KEYS = ("measure", "beat", "time", "ref")


def _position_lost(position: dict, fmt: str) -> bool:
    """Whether this target can carry none of the clocks the position states.

    Counts a position as dropped only when *nothing* of it survives. A position
    stating both clocks that reaches a target holding one of them is a partial loss
    the matrix does not (yet) grade."""
    metric = any(position.get(k) is not None for k in _METRIC_KEYS)
    physical = position.get("seconds") is not None
    if metric and fmt in POSITION_NATIVE:
        return False
    if physical and fmt in SECONDS_NATIVE:
        return False
    return True


def position_loss(seq_dict: dict, fmt: str) -> int:
    """How many of the sequence's group positions this format can't carry natively."""
    return sum(1 for g in (seq_dict.get("groups") or [])
               if g.get("position") and _position_lost(g["position"], fmt))


# out-of-band slot to carry the full HAMON surface (None = the format has no such slot)
def annotation_slot(fmt, surfaces):
    body = " · ".join(surfaces)
    lines = [f"@hamon {s}" for s in surfaces]
    if fmt in ("lilypond",):
        return "\n".join(f"% hamon: {s}" for s in surfaces)
    if fmt in ("abc",):
        return "\n".join(f"%%hamon {s}" for s in surfaces)
    if fmt in ("humdrum",):
        return "\n".join(f"!!hamon: {s}" for s in surfaces)
    if fmt in ("musicxml", "musescore"):
        return f"<!-- hamon: {body} -->"
    if fmt == "mei":
        return f'<annot type="hamon">{body}</annot>'
    if fmt == "romantext":
        return "\n".join(f"Note: hamon {s}" for s in surfaces)
    if fmt == "dcml":
        return "# hamon\t" + body           # sidecar comment / extra column
    if fmt == "dezrann":
        return '{"hamon": ' + repr(surfaces) + "}"
    if fmt == "jams":
        # JAMS has a first-class `sandbox` for arbitrary payloads → a real slot.
        return '"sandbox": {"hamon": ' + repr(surfaces) + "}"
    # harte (.lab) and iReal: no standard comment/annotation slot
    return None


# ── aspect extraction ───────────────────────────────────────────────────────
def label_aspects(lab: dict) -> set:
    sem = lab.get("semantic") or {}
    attrs = lab.get("attributes") or {}
    kind = sem.get("kind")
    a = set()
    if kind == "chordSymbol":
        a.add("root")
        if sem.get("quality"):
            a.add("quality")
        if sem.get("seventh") or sem.get("extensions") or sem.get("alterations") \
                or sem.get("addedTones") or sem.get("suspensions"):
            a.add("tensions")
        if sem.get("bass"):
            a.add("bass")
    elif kind == "roman":
        a.add("roman")
        if sem.get("tail"):
            a.add("tensions")
        if sem.get("secondary"):
            a.add("applied")
    elif kind == "nashville":
        a.add("nashville")
    elif kind == "figuredBass":
        a.add("figuredbass")
    elif kind == "functional":
        a.add("functional")
    elif kind == "tone":
        a.add("tone")
    elif kind == "noChord":
        a.add("nochord")
    elif kind == "text":
        a.add("text")
    if attrs.get("applied"):
        a.add("applied")
    if attrs.get("scales"):
        a.add("scale")
    if attrs.get("inversion"):
        a.add("bass")
    return a


_ATTR_RE = re.compile(r"\[[^\]]*\]")
# The out-of-band slot lines (`% hamon:`, `!!hamon:`, `Note: hamon`, `# hamon`) that a
# workaround export or the site's annotated view append; strip them so the *native* view
# is genuinely native.
_EMBED_RE = re.compile(r"^\s*(%+\s*hamon|!!?hamon|Note:\s*hamon|#\s*hamon)", re.IGNORECASE)


def clean_native(text: str, fmt: str) -> str:
    lines = [ln for ln in text.splitlines() if not _EMBED_RE.match(ln)]
    text = "\n".join(lines)
    # a figured-bass figure kept its `bass:` tag for re-parse; drop it from a NATIVE
    # export (Humdrum **fb etc.), but keep it in HAMON's own canonical text.
    if fmt != "hamon":
        text = re.sub(r"\b(?:fb|bass):(?=[\d#b])", "", text)
        # …and so does the extent. `project_native` leaves `[dur:…]`/`[endref:…]` on the
        # surface for the writers that carry it, but none of them carries it *as those
        # glyphs*: the ones that can (Dezrann, JAMS) have a field of their own and read
        # the extent from the label's attributes. `m1 Eb: I[dur:2]` is not RomanText.
        text = re.sub(r"\[(?:dur|endref):[^\]]*\]", "", text)
    return text


# ── the declarative loss: what the format cannot say, regardless of our code ──

def native_loss(seq_dict: dict, hamon_text: str, fmt: str) -> "Counter":
    """Aspects of ``seq_dict`` that ``fmt`` cannot natively express, counted.

    Declarative on purpose. The alternative — running our exporter and diffing the
    round-trip — measures *our writers*: a weak writer makes a format look lossy, and a
    writer that parks the HAMON surface in a comment makes it look lossless (LilyPond did
    exactly that until 2026-09-03). This counts what the capability table says, so it
    holds regardless of writer quality, and it is the number the loss matrix reports.

    The empirical round-trip stays worth running — it is how writer bugs surface — but
    it answers "do our writers work", not "can this format carry this meaning"."""
    cap = CAPABILITY.get(fmt, set())
    groups = seq_dict.get("groups") or []
    labels = [l for g in groups for l in (g.get("primary") or [])]

    lost: "Counter" = Counter()
    for label in labels:
        needed = label_aspects(label)
        missing = needed - cap
        if ("applied" in needed and fmt not in CHORD_APPLIED_NATIVE
                and (label.get("semantic") or {}).get("kind") == "chordSymbol"):
            missing.add("applied")
        for aspect in sorted(missing):
            lost[aspect] += 1
    if (seq_dict.get("regions") or "@key:" in hamon_text) and "key" not in cap:
        lost["key"] += 1
    positions = position_loss(seq_dict, fmt)
    if positions:
        lost["position"] = positions
    # `missing` is a set, so without a fixed order the *same* input prints its aspects
    # differently from one run to the next. Callers show this straight to a reader, and
    # one of them is a poster, so the order is part of the answer: heaviest loss first,
    # ties broken by name.
    return Counter(dict(sorted(lost.items(), key=lambda kv: (-kv[1], kv[0]))))
