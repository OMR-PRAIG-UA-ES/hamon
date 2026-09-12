"""Lossy-conversion report — what a HamonSequence keeps vs. loses on export.

HAMON is the hub format: any source maps into a :class:`~hamonpy.ast.HamonSequence`,
and from there back out to a target format. Exporting is **lossy** whenever the target
format cannot represent something HAMON's AST holds (e.g. chord-scales, alternatives,
time positions, secondary-function detail). This module measures that loss by a
**round-trip**: ``HAMON → target text → HAMON'`` and a structural diff of the canonical
dicts of the two sequences. Anything present in the source but missing or changed in the
re-parsed copy is a *finding* -- and so is anything present in the copy that the source
never said, which the diff walks the output for as well.

Four kinds, and one of them is not a loss:

- ``dropped`` / ``changed`` / ``reordered`` -- what the target could not carry.
  :attr:`LossyReport.lost`.
- ``added`` -- what the target INVENTED: a default the writer supplied, a version the
  reader stamps, a group the format pads out. :attr:`LossyReport.invented`. Nothing went
  missing, so a conversion with only these is still :attr:`~LossyReport.lossless`; it is
  not :attr:`~LossyReport.faithful`, which is the stricter question of whether the copy
  says what the source said *and only that*.

Lists are compared **aligned**, not position by position: anchored on the items that came
back untouched, then on kind. One item a target drops in the MIDDLE otherwise shifts every
item after it, and a single lost chord reads as "D became G, G became A, A became F" plus a
dropped last chord that is still there. A loss at the tail reports fine either way, which is
why the corpus never showed this.

This is the skeleton the demo (CLI / Streamlit) sits on, and the empirical input to the
planned provenance layer (an open design decision: "what's lost" is exactly what
provenance must record).

    from hamonpy.report import lossy_report, WRITERS
    rep = lossy_report(seq, "harte")
    print(rep.summary())
"""
from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .ast import HamonSequence
import dataclasses
import re

from .capability import CAPABILITY, clean_native, label_aspects
from .serialize import sequence_to_dict

# ---------------------------------------------------------------------------
# Target-format registry: each entry can WRITE a HamonSequence to text and READ
# that text back into a HamonSequence (so we can diff the round-trip).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormatIO:
    name: str
    write: Callable[[HamonSequence], str]
    read: Callable[[str], HamonSequence]
    note: str = ""


def _registry() -> Dict[str, FormatIO]:
    # Imported lazily so optional adapters never block this module from loading.
    from .parse import parse_hamon_sequence
    from .serialize import sequence_to_hamon_text
    from .cli import convert_text
    from .adapters.dcml import hamon_to_dcml_tsv, dcml_tsv_text_to_hamon
    from .adapters.dezrann import hamon_to_dez, dez_to_hamon
    from .adapters.mei import hamon_to_mei, mei_to_hamon
    from .adapters.harte import hamon_to_harte_text, harte_text_to_hamon
    from .adapters.jams import hamon_to_jams, jams_to_hamon
    from . import export as ex

    def reader(fmt: str):
        return lambda text: convert_text(text, fmt)

    return {
        # canonical
        "hamon": FormatIO("hamon", sequence_to_hamon_text, parse_hamon_sequence,
                          "canonical surface — the lossless reference round-trip"),
        # structured writers (rich adapters)
        "dcml": FormatIO("dcml", hamon_to_dcml_tsv, dcml_tsv_text_to_hamon, "DCML plain TSV"),
        "dezrann": FormatIO("dezrann", hamon_to_dez, dez_to_hamon, "Dezrann .dez label JSON"),
        "mei": FormatIO("mei", lambda s: hamon_to_mei(s, wrap=True), mei_to_hamon,
                        "MEI <harm> elements"),
        "harte": FormatIO("harte", hamon_to_harte_text, harte_text_to_hamon, "Harte chord-label syntax"),
        "jams": FormatIO("jams", hamon_to_jams, jams_to_hamon, "JAMS chord/key_mode annotation JSON"),
        # surface-preserving writers (export.py)
        "musicxml": FormatIO("musicxml", ex.hamon_to_musicxml, reader("musicxml"),
                             "MusicXML <harmony> elements"),
        "lilypond": FormatIO("lilypond", ex.hamon_to_lilypond, reader("lilypond"), "LilyPond \\chordmode"),
        "abc": FormatIO("abc", ex.hamon_to_abc, reader("abc"), "ABC quoted chord symbols"),
        "musescore": FormatIO("musescore", ex.hamon_to_musescore, reader("musescore"),
                              "MuseScore <Harmony> blocks"),
        "romantext": FormatIO("romantext", ex.hamon_to_romantext, reader("romantext"),
                              "RomanText (.rntxt)"),
        "humdrum": FormatIO("humdrum", ex.hamon_to_humdrum, reader("humdrum"),
                            "Humdrum **harm/**mxhm spine"),
        "ireal": FormatIO("ireal", ex.hamon_to_ireal, reader("ireal"), "iReal Pro plain chart"),
    }


#: Target formats this report can round-trip (those with a HAMON→text writer).
WRITERS: Tuple[str, ...] = tuple(_registry().keys())


#: How an export is allowed to say things the target has no vocabulary for.
#:
#: ``"native"``    — only what the format expresses in its own terms. The projection
#:                   strips everything else *before* the writer runs, so no writer can
#:                   quietly rescue it by embedding a HAMON string. The honest measure.
#: ``"workaround"`` — the writers as they are: surface-preserving, so the full HAMON
#:                   surface rides along inside whatever text field the target has.
#:                   Lossless by construction, because it is escrow, not translation.
#:
#: Text is a workaround, never a capability. See :mod:`hamonpy.capability`.
Mode = str


# A label's *kind* decides whether the format can hold the label at all …
_KIND_ASPECT = {
    "chordSymbol": "root", "roman": "roman", "nashville": "nashville",
    "figuredBass": "figuredbass", "functional": "functional", "tone": "tone",
}
# … and its bracketed attributes are stripped one by one. An extent (`[dur:…]`,
# `[endref:…]`) always stays: the writers that carry it do, the rest ignore it. An
# inversion stays where the format has a bass vocabulary. Everything else (`[of:…]`,
# `[scale:…]`, `[HT]`/`[NHT:…]`, …) is HAMON-only.
_ATTR_ITEM_RE = re.compile(r"\[([^\]:]+)(?::[^\]]*)?\]")
_EXTENT_ATTRS = {"dur", "endref"}
_ATTR_ASPECT = {"inv": "bass"}


def _native_label_surface(label, semantic: dict, cap: set) -> str:
    def keep(m):
        key = m.group(1).strip().lower()
        return m.group(0) if key in _EXTENT_ATTRS or _ATTR_ASPECT.get(key) in cap else ""
    surface = _ATTR_ITEM_RE.sub(keep, label.surface)
    # A Roman numeral spells its applied target inline (`V7/ii`); a Roman vocabulary
    # without applied chords keeps the numeral and loses the target.
    if semantic.get("kind") == "roman" and semantic.get("secondary") and "applied" not in cap:
        surface = re.sub(r"/[^\[\]]*", "", surface, count=1)
    return surface


def project_native(seq: HamonSequence, target: str) -> HamonSequence:
    """``seq`` reduced to what ``target`` natively expresses.

    Labels of a kind the format has no vocabulary for are dropped (a Roman numeral
    headed for Harte, a chord symbol headed for RomanText); the ones kept lose the
    attributes the format cannot state. Positions, layers, regions and meters are left
    for the writer to carry or not — that is the writer's honesty, measured by the
    round-trip, and a score format that can place a harmony must be handed the position.
    The result is re-parsed from its own surface so the semantics match the text.
    HAMON itself is the interlingua and is never projected."""
    if target == "hamon":
        return seq
    from .parse import parse_hamon_sequence
    from .serialize import sequence_to_hamon_text

    cap = CAPABILITY.get(target, set())
    groups, index_map = [], {}
    for gi, (group, gd) in enumerate(zip(seq.groups, sequence_to_dict(seq).get("groups") or [])):
        kept = []
        for label, ld in zip(group.primary, gd.get("primary") or []):
            semantic = ld.get("semantic") or {}
            aspect = _KIND_ASPECT.get(semantic.get("kind"))
            if aspect is not None and aspect not in cap:
                continue          # noChord / text are plain strings any writer can hold
            kept.append(dataclasses.replace(
                label, surface=_native_label_surface(label, semantic, cap)))
        if kept:
            index_map[gi] = len(groups)
            groups.append(dataclasses.replace(group, primary=kept, alternatives=[]))
    if not groups:
        return HamonSequence(groups=[])

    def remap(i):
        # the first kept group at or after the original index
        later = [new for old, new in index_map.items() if old >= i]
        return min(later) if later else None

    regions = [dataclasses.replace(r, from_group=remap(r.from_group),
                                   to_group=None if r.to_group is None else remap(r.to_group))
               for r in (seq.regions or []) if remap(r.from_group) is not None]
    meters = [dataclasses.replace(m, from_group=remap(m.from_group))
              for m in (seq.meters or []) if remap(m.from_group) is not None]
    if "key" not in cap:
        regions = []          # a key the format cannot state must not ride along as text
    projected = dataclasses.replace(seq, groups=groups, regions=regions or None,
                                    meters=meters or None, alternative_analyses=None)
    return parse_hamon_sequence(sequence_to_hamon_text(projected))


def write_to(seq: HamonSequence, target: str, mode: Mode = "workaround") -> str:
    """Serialize ``seq`` to ``target`` format text (one of :data:`WRITERS`).

    ``mode`` picks between the two honest readings of an export — see :data:`Mode`.
    The default stays ``"workaround"``, which is what these writers have always done;
    it is named now so that calling it lossless is no longer possible by accident."""
    reg = _registry()
    if target not in reg:
        raise ValueError(f"Unknown target {target!r}. Known: {', '.join(reg)}")
    if mode == "native":
        text = reg[target].write(project_native(seq, target))
        return clean_native(text, target)
    return reg[target].write(seq)

# Leaf fields that are *notation*, not *meaning*: differences here are expected
# across formats (re-spelled glyphs) and are reported separately from semantic loss.
NOTATIONAL_LEAVES = frozenset({
    "surface", "rendering", "qualityGlyph", "seventhGlyph", "accidentalGlyphs",
    "rawParts", "detectedSystem", "system", "sequenceSystemHint",
})


# ---------------------------------------------------------------------------
# Structural diff over canonical dicts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    path: str
    kind: str          # "dropped" | "changed" | "added" | "reordered"
    notational: bool
    source: Any = None
    output: Any = None
    summary: str = ""  # compact one-line display (group surface, glyph, scalar value…)


def _clip(value: Any, limit: int = 120) -> str:
    s = value if isinstance(value, str) else repr(value)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _leaf(path: str) -> str:
    seg = path.rsplit(".", 1)[-1]
    return seg.split("[", 1)[0]


_PITCH = {"flat": "b", "sharp": "#", "double-flat": "bb", "double-sharp": "##", "natural": "♮"}


def _summarize(value: Any) -> str:
    """A compact human label for a dropped composite (so we never dump raw dicts)."""
    if isinstance(value, dict):
        if "primary" in value:                       # a HarmonyGroup
            labels = " , ".join(_summarize(l) for l in value.get("primary", []))
            alts = value.get("alternatives") or []
            return f"{labels} (+{len(alts)} alt)" if alts else labels
        if "surface" in value:                        # a HarmonyLabel
            return str(value["surface"])
        if "accidental" in value and "degree" in value:  # an alteration
            return f"{_PITCH.get(value.get('accidental', ''), '')}{value['degree']}"
        if "target" in value:                          # an applied function
            chain = "/".join(value.get("chain", [])) if value.get("chain") else ""
            return f"applied→{value['target']}" + (f" ({chain})" if chain else "")
        if "tonic" in value:                           # a key / region
            k = value["tonic"]
            tonic = f"{k.get('note', '?')}{_PITCH.get(k.get('accidental', ''), '')}"
            return f"{tonic} {value.get('mode', '')}".strip()
        if len(value) == 1:                            # single-key wrapper (e.g. attributes)
            return _summarize(next(iter(value.values())))
        items = ", ".join(f"{k}={_summarize(v)}" for k, v in value.items())
        return _clip(f"{{{items}}}")
    if isinstance(value, list):
        return ", ".join(_summarize(v) for v in value)
    return _clip(value)


def _drop(value: Any, path: str, notational: bool, findings: List[Finding]) -> None:
    """Record a dropped value. Lists expand one finding per element; a non-group
    dict collapses to a single compact-summary finding; scalars report their value."""
    if isinstance(value, list):
        for i, item in enumerate(value):
            _drop(item, f"{path}[{i}]", notational, findings)
        return
    findings.append(Finding(path, "dropped", notational, value, None, _summarize(value)))


def _add(value: Any, path: str, notational: bool, findings: List[Finding]) -> None:
    """Record a value the round-trip *gained*: absent from the source, present in the
    re-read copy. The mirror of :func:`_drop`, with source and output swapped."""
    if isinstance(value, list):
        for i, item in enumerate(value):
            _add(item, f"{path}[{i}]", notational, findings)
        return
    findings.append(Finding(path, "added", notational, None, value, _summarize(value)))


#: Above this many items a list is compared position by position instead of aligned. The
#: alignment is quadratic, and a sequence that long makes a cascade obvious anyway.
_ALIGNMENT_LIMIT = 800


def _canonical_key(value: Any) -> str:
    """JSON with dict keys sorted, so two equal values always give the same string. Both
    sides come from :func:`sequence_to_dict`, so this is enough to say "the same item"."""
    return _json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _item_kind(value: Any) -> str:
    """What kind of thing an item is, for the second alignment pass. Two labels of the same
    kind are each other's counterpart even when their content differs; a chord symbol and a
    figured bass are not comparable at all."""
    if isinstance(value, dict):
        semantic = value.get("semantic")
        if isinstance(semantic, dict) and isinstance(semantic.get("kind"), str):
            return semantic["kind"]
        primary = value.get("primary")          # a HarmonyGroup takes the kind of its first label
        if isinstance(primary, list) and primary:
            return _item_kind(primary[0])
        if isinstance(value.get("kind"), str):
            return value["kind"]
    return type(value).__name__


def _is_permutation(src_keys: List[str], out_keys: List[str]) -> bool:
    """Whether two lists hold exactly the same items in a different order."""
    if len(src_keys) != len(out_keys) or len(src_keys) < 2:
        return False
    if src_keys == out_keys:                    # same order: not a reordering
        return False
    return sorted(src_keys) == sorted(out_keys)


def _common_anchors(src_keys: List[str], out_keys: List[str]) -> List[Tuple[int, int]]:
    """The index pairs of the items that appear, in the same relative order, in both lists --
    the anchors an aligned diff hangs off. A plain longest common subsequence."""
    n, m = len(src_keys), len(out_keys)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = table[i], table[i + 1]
        for j in range(m - 1, -1, -1):
            row[j] = nxt[j + 1] + 1 if src_keys[i] == out_keys[j] else max(nxt[j], row[j + 1])
    anchors: List[Tuple[int, int]] = []
    i = j = 0
    while i < n and j < m:
        if src_keys[i] == out_keys[j]:
            anchors.append((i, j))
            i += 1
            j += 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return anchors


#: How many moved items a reordering names before it stops listing them.
_MOVES_LISTED = 4


def _describe_moves(src: List[Any], src_keys: List[str], out_keys: List[str]) -> str:
    """Name the items that actually moved -- everything outside the longest run both lists
    agree on. Dumping the two full lists instead would bury the one label that travelled."""
    anchors = _common_anchors(src_keys, out_keys)
    anchored_src = {i for i, _ in anchors}
    anchored_out = {j for _, j in anchors}
    destinations: Dict[str, List[int]] = {}
    for j, key in enumerate(out_keys):
        if j not in anchored_out:               # an anchored position is where it always was
            destinations.setdefault(key, []).append(j)

    moves: List[str] = []
    for i, key in enumerate(src_keys):
        if i in anchored_src or len(moves) >= _MOVES_LISTED:
            continue
        where = destinations.get(key) or []
        to = where.pop(0) if where else "?"
        moves.append(f"{_summarize(src[i])} [{i}] → [{to}]")
    hidden = len(src_keys) - len(anchored_src) - len(moves)
    return "; ".join(moves) + (f" (and {hidden} more)" if hidden > 0 else "")


def _diff_list(src: List[Any], out: List[Any], path: str, findings: List[Finding]) -> None:
    """Diff two lists by aligning them on the items that survived untouched, and comparing
    what lies between consecutive anchors.

    Comparing position by position is not good enough: one item a target drops shifts every
    item after it, so a single lost chord gets reported as "D became G, G became A, A became
    F" plus a dropped last chord that is in fact still there -- four statements, all of them
    false. That only shows when the loss is in the MIDDLE; a loss at the tail reports fine
    either way, which is why the corpus did not catch this. Anchoring on what did survive
    keeps a cascade down to the one finding it is.
    """
    notational = _leaf(path) in NOTATIONAL_LEAVES
    src_keys = [_canonical_key(v) for v in src]
    out_keys = [_canonical_key(v) for v in out]

    if _is_permutation(src_keys, out_keys):
        findings.append(Finding(path, "reordered", notational, src, out,
                                _describe_moves(src, src_keys, out_keys)))
        return

    def compare_gap(frm: int, to: int, out_frm: int, out_to: int) -> None:
        """A stretch no identity anchor falls in. These items are not equal, but a chord
        symbol and a roman numeral are not each other's counterpart either, so they are
        aligned a second time by kind and only same-kind items are compared field by field."""
        src_kinds = [_item_kind(v) for v in src[frm:to]]
        out_kinds = [_item_kind(v) for v in out[out_frm:out_to]]
        i, j = frm, out_frm
        for anchor_i, anchor_j in _common_anchors(src_kinds, out_kinds):
            while i < frm + anchor_i:
                _drop(src[i], f"{path}[{i}]", notational, findings)
                i += 1
            while j < out_frm + anchor_j:
                _add(out[j], f"{path}[{j}]", notational, findings)
                j += 1
            _diff(src[i], out[j], f"{path}[{i}]", findings)   # same kind, different content
            i += 1
            j += 1
        while i < to:
            _drop(src[i], f"{path}[{i}]", notational, findings)
            i += 1
        while j < out_to:
            _add(out[j], f"{path}[{j}]", notational, findings)
            j += 1

    if len(src) > _ALIGNMENT_LIMIT or len(out) > _ALIGNMENT_LIMIT:
        compare_gap(0, len(src), 0, len(out))
        return

    i = j = 0
    for anchor_i, anchor_j in _common_anchors(src_keys, out_keys):
        compare_gap(i, anchor_i, j, anchor_j)   # the gap before this anchor
        i = anchor_i + 1                        # the anchor itself is identical: nothing to report
        j = anchor_j + 1
    compare_gap(i, len(src), j, len(out))


def _diff(src: Any, out: Any, path: str, findings: List[Finding]) -> None:
    if isinstance(src, dict):
        if not isinstance(out, dict):
            findings.append(Finding(path, "changed", _leaf(path) in NOTATIONAL_LEAVES,
                                    src, out, f"{_summarize(src)} → {_summarize(out)}"))
            return
        for key, val in src.items():
            sub = f"{path}.{key}" if path else key
            if key not in out:
                _drop(val, sub, key in NOTATIONAL_LEAVES, findings)
            else:
                _diff(val, out[key], sub, findings)
        # The reverse pass: what the target format INVENTED. Walking the source keys alone
        # cannot see it, and a value nobody wrote is as much a departure from the source as
        # one that went missing -- a default the writer supplied, a system the reader
        # inferred. It is what provenance has to record as "not from the source".
        for key, val in out.items():
            if key not in src:
                _add(val, f"{path}.{key}" if path else key, key in NOTATIONAL_LEAVES, findings)
        return
    if isinstance(src, list):
        if not isinstance(out, list):
            findings.append(Finding(path, "changed", _leaf(path) in NOTATIONAL_LEAVES,
                                    src, out, f"{_summarize(src)} → {_summarize(out)}"))
            return
        _diff_list(src, out, path, findings)
        return
    if src != out:
        findings.append(Finding(path, "changed", _leaf(path) in NOTATIONAL_LEAVES,
                                src, out, f"{_clip(src)} → {_clip(out)}"))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass
class LossyReport:
    target: str
    findings: List[Finding] = field(default_factory=list)
    output_text: Optional[str] = None
    error: Optional[str] = None
    source_groups: int = 0

    @property
    def semantic(self) -> List[Finding]:
        """Every finding that touches meaning rather than spelling: lost *and* invented."""
        return [f for f in self.findings if not f.notational]

    @property
    def notational(self) -> List[Finding]:
        return [f for f in self.findings if f.notational]

    @property
    def lost(self) -> List[Finding]:
        """What the target could not carry: present in the source, gone or altered after it."""
        return [f for f in self.semantic if f.kind != "added"]

    @property
    def invented(self) -> List[Finding]:
        """What the round-trip GAINED: values in the re-read copy that the source never said.

        A default the writer supplied, a version the reader stamps, a group the format pads
        out. Not a loss -- nothing went missing -- but just as much a departure from the
        source, and the thing provenance has to be able to mark as "not from the source".
        """
        return [f for f in self.semantic if f.kind == "added"]

    @property
    def lossless(self) -> bool:
        """No error and nothing LOST. Unchanged in meaning: an invented value does not make
        a conversion lossy, because nothing was lost -- see :attr:`faithful` for the
        stricter question."""
        return self.error is None and not self.lost

    @property
    def faithful(self) -> bool:
        """Lossless AND nothing invented: the re-read copy says what the source said, and
        only that."""
        return self.lossless and not self.invented

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "sourceGroups": self.source_groups,
            "error": self.error,
            "lossless": self.lossless,
            "faithful": self.faithful,
            "semanticLoss": [
                {"path": f.path, "kind": f.kind, "summary": f.summary,
                 "source": f.source, "output": f.output}
                for f in self.lost
            ],
            "invented": [
                {"path": f.path, "kind": f.kind, "summary": f.summary,
                 "source": f.source, "output": f.output}
                for f in self.invented
            ],
            "notationalDiff": [
                {"path": f.path, "kind": f.kind, "summary": f.summary,
                 "source": f.source, "output": f.output}
                for f in self.notational
            ],
        }

    def summary(self) -> str:
        lines = [f"Target format: {self.target}"]
        if self.error:
            lines.append(f"  ✗ writer error: {self.error}")
            return "\n".join(lines)
        lines.append(f"  source groups: {self.source_groups}")
        if self.lossless:
            lines.append("  ✓ no semantic loss on round-trip")
        else:
            lines.append(f"  ⚠ semantic loss: {len(self.lost)} field(s)")
            for f in self.lost:
                lines.append(f"      [{f.kind}] {f.path}: {f.summary}")
        if self.invented:
            lines.append(f"  + invented by the target: {len(self.invented)} field(s) "
                         "(in the output, never said by the source)")
            for f in self.invented:
                lines.append(f"      [{f.kind}] {f.path}: {f.summary}")
        if self.notational:
            lines.append(f"  · notational re-spelling: {len(self.notational)} field(s) "
                         "(expected — glyphs/surface differ across formats)")
        return "\n".join(lines)


def lossy_report(seq: HamonSequence, target: str, *, keep_output: bool = True,
                 mode: Mode = "workaround") -> LossyReport:
    """Round-trip ``seq`` through ``target`` and report what changed/was lost.

    ``target`` must be one of :data:`WRITERS`. The diff compares the canonical dict
    of ``seq`` against the canonical dict of the sequence re-parsed from the written
    text; semantic loss is separated from purely notational re-spelling.

    ``mode`` decides *which* question is being asked (see :data:`Mode`). In
    ``"native"`` the sequence is projected to the target's own vocabulary before the
    writer runs, so what comes back measures the **format**; in ``"workaround"`` the
    writer may park the HAMON surface in a text field, so what comes back measures our
    **escrow**. The second is why MEI once reported lossless for a chord-scale MEI
    cannot express — the comparison is against the original either way, so the native
    run counts what the projection stripped as the loss it is.
    """
    reg = _registry()
    if target not in reg:
        raise ValueError(f"Unknown target {target!r}. Known: {', '.join(reg)}")
    io = reg[target]
    rep = LossyReport(target=target, source_groups=len(seq.groups))
    if not seq.groups:
        # Nothing to lose; also avoids re-parsing an empty surface (which the grammar
        # rejects). Keep the writer's output for display.
        if keep_output:
            try:
                rep.output_text = write_to(seq, target, mode)
            except Exception:  # noqa: BLE001
                rep.output_text = ""
        return rep
    try:
        text = write_to(seq, target, mode)
    except Exception as exc:  # noqa: BLE001 — surface the writer failure as a finding
        rep.error = f"{type(exc).__name__}: {exc}"
        return rep
    if keep_output:
        rep.output_text = text
    try:
        roundtripped = io.read(text)
    except Exception as exc:  # noqa: BLE001
        rep.error = f"re-read failed: {type(exc).__name__}: {exc}"
        return rep
    _diff(sequence_to_dict(seq), sequence_to_dict(roundtripped), "", rep.findings)
    return rep
