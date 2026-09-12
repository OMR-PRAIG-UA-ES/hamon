"""Measure, for every example and every encoding, what the encoding cannot say.

For each ``*.hamon`` example we:
  1. parse it into a HAMON sequence (the canonical typed AST),
  2. serialize the sequence to HAMON JSON,
  3. count the aspects each target format cannot express in its own vocabulary
     (``hamonpy.capability.native_loss``) — the *explainable-encoding* (xencoding)
     number the figure shows,
  4. round-trip it through the writer as well (``hamonpy.report.lossy_report``), which
     is kept as writer health: it measures our exporters, not the format.

``HAMON → HAMON`` is lossless by construction and is the fixed reference point.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from hamonpy.cli import convert_file
from hamonpy.capability import ASPECT_LABEL, annotation_slot, holds_as_text, native_loss
from hamonpy.report import lossy_report, WRITERS
from hamonpy.serialize import sequence_to_json, sequence_to_dict

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / "examples"
OUTPUTS_DIR = ROOT / "outputs"

# Curated order: flagship first, then the satellites, then the synthetic pangram.
EXAMPLE_ORDER = [
    "flagship_love_walked_in",
    "sat_roman_dcml",
    "sat_figured_bass",
    "sat_mozart_fb",
    "sat_nashville",
    "sat_positions",
    "pangram",
]

# Short human labels for the poster / figures.
EXAMPLE_LABELS = {
    "flagship_love_walked_in": "Chord + Roman\n(Love Walked In)",
    "sat_roman_dcml": "Roman / DCML\nanalysis",
    "sat_figured_bass": "Figured bass",
    "sat_mozart_fb": "Figured bass\n(Mozart K282, real)",
    "sat_nashville": "Nashville numbers",
    "sat_positions": "Time-aligned\n(measure : beat)",
    "pangram": "Pangram\n(all systems)",
}


@dataclass
class TargetResult:
    """Result of round-tripping one example through one target format."""

    target: str
    #: **The headline.** Aspects this format cannot express in its own vocabulary,
    #: counted from the capability table — not from a round-trip. A round-trip measures
    #: our writers: a weak one makes a format look lossy, and one that parks the HAMON
    #: surface in a comment makes it look lossless (LilyPond did, until 2026-09-03).
    semantic_loss: int
    #: Round-trip findings that are re-spellings (`Cmaj7` ↔ `C:maj7`), not loss.
    notational_diff: int
    lossless: bool
    error: Optional[str]
    output_text: str
    semantic_findings: list  # list of {path, kind, source, output, summary}
    #: Aspects reachable only by parking a HAMON string in a free text field. The gap
    #: between this and `semantic_loss` is how much of the format's apparent fidelity is
    #: really our escrow — for MEI it was all of the Roman-numeral analysis.
    workaround_recovers: int = 0
    #: Whether an out-of-band slot exists at all. False for Harte `.lab` and iReal:
    #: nothing can rescue them, which is the interlingua argument.
    has_slot: bool = False
    #: The empirical round-trip, kept for writer health — not for the figure.
    roundtrip_loss: int = 0
    #: The headline, itemised: `{aspect, label, count}`, largest first.
    lost_aspects: list = field(default_factory=list)


@dataclass
class ExampleResult:
    name: str
    label: str
    path: str
    system_hint: Optional[str]
    n_labels: int
    hamon_text: str
    hamon_json: str
    targets: list  # list[TargetResult]

    def target(self, name: str) -> Optional[TargetResult]:
        for t in self.targets:
            if t.target == name:
                return t
        return None


def _finding_dict(f) -> dict:
    """Normalize a report Finding to a plain dict (it has no ``to_dict``)."""
    if hasattr(f, "to_dict"):
        return f.to_dict()
    keys = ("path", "kind", "notational", "source", "output", "summary")
    return {k: getattr(f, k, None) for k in keys}


def _n_labels(seq) -> int:
    d = sequence_to_dict(seq)
    return sum(len(g.get("primary", []) or []) for g in d.get("groups", []) or [])


def analyze_example(path: Path) -> ExampleResult:
    """Parse one ``.hamon`` file and round-trip it through every writer."""
    seq = convert_file(Path(path), "hamon")
    hamon_text = Path(path).read_text(encoding="utf-8")
    hamon_json = sequence_to_json(seq)

    targets: list[TargetResult] = []
    seq_dict = sequence_to_dict(seq)
    for t in WRITERS:
        lost = native_loss(seq_dict, hamon_text, t)
        # The empirical round-trip still runs: it is how a writer bug surfaces. It just
        # does not get to be the headline, because it answers a different question.
        rep = lossy_report(seq, t, mode="workaround")
        recovered = len(holds_as_text(t) & set(lost))
        targets.append(
            TargetResult(
                target=t,
                semantic_loss=sum(lost.values()),
                notational_diff=len(rep.notational),
                lossless=not lost,
                error=rep.error,
                output_text=rep.output_text or "",
                semantic_findings=[_finding_dict(f) for f in rep.semantic],
                workaround_recovers=recovered,
                has_slot=annotation_slot(t, ["x"]) is not None and t != "hamon",
                roundtrip_loss=len(rep.semantic),
                lost_aspects=[{"aspect": a, "label": ASPECT_LABEL.get(a, a), "count": c}
                              for a, c in sorted(lost.items(), key=lambda kv: (-kv[1], kv[0]))],
            )
        )

    name = Path(path).stem
    return ExampleResult(
        name=name,
        label=EXAMPLE_LABELS.get(name, name),
        path=str(path),
        system_hint=getattr(seq, "sequence_system_hint", None),
        n_labels=_n_labels(seq),
        hamon_text=hamon_text,
        hamon_json=hamon_json,
        targets=targets,
    )


def analyze_all(examples_dir: Path = EXAMPLES_DIR) -> list[ExampleResult]:
    """Analyze every example, in curated order (flagship → satellites → pangram)."""
    examples_dir = Path(examples_dir)
    found = {p.stem: p for p in examples_dir.glob("*.hamon")}
    ordered = [found[n] for n in EXAMPLE_ORDER if n in found]
    ordered += [p for stem, p in sorted(found.items()) if stem not in EXAMPLE_ORDER]
    return [analyze_example(p) for p in ordered]


def to_report_dict(results: list[ExampleResult]) -> dict:
    """A JSON-serializable summary of the whole run (the xencoding artifact)."""
    return {
        "writers": list(WRITERS),
        "examples": [
            {
                "name": r.name,
                "label": r.label.replace("\n", " "),
                "system_hint": r.system_hint,
                "n_labels": r.n_labels,
                "targets": [asdict(t) for t in r.targets],
            }
            for r in results
        ],
    }


def write_report(results: list[ExampleResult], outputs_dir: Path = OUTPUTS_DIR) -> Path:
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    out = outputs_dir / "xencoding_report.json"
    out.write_text(json.dumps(to_report_dict(results), indent=2, ensure_ascii=False), encoding="utf-8")
    # also drop each example's canonical HAMON JSON next to it
    for r in results:
        (outputs_dir / f"{r.name}.hamon.json").write_text(r.hamon_json, encoding="utf-8")
    return out
