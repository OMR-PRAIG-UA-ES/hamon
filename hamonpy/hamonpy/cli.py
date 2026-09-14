"""hamonpy command-line interface — the harmony hub as a tool.

    python -m hamonpy convert <file> [--format F] [-o out.json]
    python -m hamonpy validate <file> [--format F] [--json] [--strict]
    python -m hamonpy datasets list | info <name> | path <name>

`convert` auto-detects the input format and writes the canonical hamon JSON
(grammar/hamon-schema.json). Supported inputs: hamon surface, DCML TSV (plain, the
time-aligned *expanded* tables — Hentschel/DCML, also emitted by ms3, and the
note-level DiLeMMa pitch arrays),
RomanText, Jazz Harmony Treebank JSON, Humdrum (**harm/**function/**fb spines or
the DDMAL key_modulation **text/=> encoding), MEI/HA-MEI, Harte, iReal Pro,
Dezrann (.dez), and the regex-extracted MusicXML / ABC / LilyPond / MuseScore.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .ast import HamonSequence, HarmonyGroup, HarmonyLabel, RenderingHints, TextSemantic
from .parse import parse_hamon_sequence
from .serialize import sequence_to_json
from .adapters.formats import read_harmony_labels

FORMATS = [
    "hamon", "dcml", "dcml_expanded", "romantext", "treebank", "humdrum",
    "key_modulation", "mei", "harte", "ireal", "dezrann", "jams", "musicxml", "abc",
    "lilypond", "musescore", "bps_fh", "harm", "rock_corpus", "kp", "choro", "dilemma",
]

#: Binary input formats that cannot be read as UTF-8 text (need a file path).
BINARY_FORMATS = {"bps_fh"}


def _is_pitch_array(head: str) -> bool:
    """A DiLeMMa pitch array (note-level TSV)? Late import keeps the CLI light."""
    from .adapters.dilemma import looks_like_pitch_array
    return looks_like_pitch_array(head)


def _dcml_flavour(head: str) -> str:
    """Plain or *expanded* DCML: a table whose header places its rows — ``quarterbeats``,
    or a measure column ``mn``/``mc`` — goes to the expanded reader, the one that keeps
    positions. The header row decides, not the body, so a chord called ``mc`` cannot."""
    columns = set(head.splitlines()[0].split("\t")) if head else set()
    return "dcml_expanded" if columns & {"quarterbeats", "mn", "mc"} else "dcml"


def detect_format(path: Optional[Path], text: str) -> str:
    ext = path.suffix.lower() if path else ""
    head = text.lstrip()[:4000]

    if path and path.name.lower().startswith("kp-chord-list"):
        return "kp"
    if ext == ".xlsx":
        return "bps_fh"
    if ext == ".hamon":
        return "hamon"
    if ext == ".tsv":
        if "rn_chord" in head and "filename" in head:   # DCML Choro Songbook merged table
            return "choro"
        if _is_pitch_array(head):     # before the quarterbeats sniff: DLC arrays have
            return "dilemma"          # a quarterbeats_playthrough column
        return _dcml_flavour(head)
    if ext == ".dez":
        return "dezrann"
    if ext == ".jams":
        return "jams"
    if ext == ".rntxt":
        return "romantext"
    if ext == ".hrm":
        return "harm"
    if ext == ".har":
        return "rock_corpus"
    if ext in (".krn", ".kern"):
        if "**text" in text and "=>" in text:
            return "key_modulation"
        return "humdrum"
    if ext == ".json":
        # JAMS is JSON too — distinguish by its top-level shape.
        if '"annotations"' in head and ('"file_metadata"' in head or '"namespace"' in head):
            return "jams"
        return "treebank"
    if ext == ".mei":
        return "mei"
    if ext == ".lab":
        return "harte"
    if ext == ".abc":
        return "abc"
    if ext == ".ly":
        return "lilypond"
    if ext in (".mscx", ".mscz"):
        return "musescore"
    if ext in (".xml", ".musicxml", ".mxl"):
        return "mei" if "<harm" in head and "<harmony" not in head else "musicxml"

    # Extension-less / .txt — sniff the content.
    if head.startswith("@") or re.match(r"^@(version|cs|rn|ns|fb|fun|auto|text|key)", head):
        return "hamon"
    if re.search(r"^S\[", head, re.MULTILINE) or re.search(r"^P\d+:", head, re.MULTILINE):
        return "choro"                    # DCML Choro Songbook form-grammar transcription
    if "<harm" in head:
        return "mei"
    if "<harmony" in head:
        return "musicxml"
    if re.search(r"^m\d", head, re.MULTILINE) or "Time Signature:" in head:
        return "romantext"
    if "\t" in head and _is_pitch_array(head):
        return "dilemma"
    if "\t" in head and "globalkey" in head:
        return _dcml_flavour(head)
    if re.search(r"^\s*[\d.]+\s+[\d.]+\s+-\s+\d+\s+-?\d+\s+\d+", head, re.MULTILINE):
        return "kp"                       # Kostka-Payne chord-list rows
    return "hamon"


def _text_group(label: str) -> HarmonyGroup:
    return HarmonyGroup(primary=[HarmonyLabel(
        surface=label, semantic=TextSemantic(text=label), rendering=RenderingHints(),
        detected_system="text", system="text", sequence_system_hint="auto",
    )])


def _labels_to_seq(labels) -> HamonSequence:
    """Parse a flat list of surface labels into a HamonSequence.

    Fast path: parse them together (one ``@auto`` block). If that raises — e.g. a
    file carries annotations the hamon grammar rejects (DCML cadence/phrase markers
    embedded in MuseScore ``<Harmony>`` text: ``I|PAC``, ``V(64)``, ``C.I[I{`` …) —
    fall back to parsing each label on its own so one bad label can't sink the whole
    import; unparseable labels are preserved as ``text``."""
    if not labels:
        return HamonSequence(groups=[])
    try:
        return parse_hamon_sequence("@auto\n" + "\n".join(labels))
    except Exception:  # noqa: BLE001 - resilience: never let one label crash import
        groups: list = []
        for lab in labels:
            try:
                sub = parse_hamon_sequence("@auto\n" + lab)
                groups.extend(sub.groups or [_text_group(lab)])
            except Exception:  # noqa: BLE001
                groups.append(_text_group(lab))
        return HamonSequence(groups=groups, sequence_system_hint="auto")


def convert_text(text: str, fmt: str) -> HamonSequence:
    if fmt == "hamon":
        return parse_hamon_sequence(text)
    if fmt == "dcml":
        from .adapters.dcml import dcml_tsv_text_to_hamon
        return dcml_tsv_text_to_hamon(text)
    if fmt == "choro":
        from .adapters.choro import read_tsv, tsv_piece_to_hamon, transcription_to_hamon
        first = text.lstrip().splitlines()[0] if text.strip() else ""
        if "\t" in first and "filename" in first:      # the merged choro.tsv (all pieces)
            groups = []
            for rows in read_tsv(text).values():
                groups += tsv_piece_to_hamon(rows).groups
            return HamonSequence(groups=groups, sequence_system_hint="cs")
        return transcription_to_hamon(text)             # a single-piece .txt transcription
    if fmt == "dcml_expanded":
        from .adapters.dcml_expanded import expanded_tsv_text_to_hamon
        return expanded_tsv_text_to_hamon(text)
    if fmt == "dilemma":
        from .adapters.dilemma import pitch_array_text_to_hamon
        return pitch_array_text_to_hamon(text)
    if fmt == "dezrann":
        from .adapters.dezrann import dez_to_hamon
        return dez_to_hamon(text)
    if fmt == "jams":
        from .adapters.jams import jams_to_hamon
        return jams_to_hamon(text)
    if fmt == "romantext":
        from .adapters.romantext import romantext_to_hamon
        return romantext_to_hamon(text)
    if fmt == "treebank":
        from .adapters.treebank import treebank_json_to_hamon
        return treebank_json_to_hamon(text)
    if fmt == "humdrum":
        from .adapters.humdrum import humdrum_to_hamon
        return humdrum_to_hamon(text)
    if fmt == "key_modulation":
        from .adapters.humdrum import key_modulation_to_hamon
        return key_modulation_to_hamon(text)
    if fmt == "harm":
        from .adapters.harm import harm_to_hamon
        return harm_to_hamon(text)
    if fmt == "rock_corpus":
        from .adapters.rock_corpus import rock_corpus_to_hamon
        return rock_corpus_to_hamon(text)
    if fmt == "kp":
        from .adapters.kp import kp_chord_list_to_hamon
        return kp_chord_list_to_hamon(text)
    if fmt == "mei":
        from .adapters.mei import mei_to_hamon
        return mei_to_hamon(text)
    if fmt == "harte":
        from .adapters.harte import harte_text_to_hamon
        return harte_text_to_hamon(text)
    if fmt == "ireal":
        from .adapters.ireal import ireal_chart_text_to_hamon
        return ireal_chart_text_to_hamon(text)
    if fmt == "musicxml":
        # Positioned path: carries HarmonyGroup.position (measure + beat).
        from .adapters.musicxml import musicxml_to_hamon
        return musicxml_to_hamon(text)
    if fmt in ("abc", "lilypond", "musescore"):
        key = {"musescore": "musescorexml"}.get(fmt, fmt)
        return _labels_to_seq(read_harmony_labels(key, text))
    if fmt in BINARY_FORMATS:
        raise ValueError(f"Format {fmt!r} is binary; use convert_file with a path, not text.")
    raise ValueError(f"Unknown format {fmt!r}. Known: {', '.join(FORMATS)}")


def detect_file_format(path: Union[str, Path]) -> str:
    """Detect a file's format without reading binary content as text."""
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        return "bps_fh"
    return detect_format(path, path.read_text(encoding="utf-8"))


def convert_file(path: Union[str, Path], fmt: Optional[str] = None) -> HamonSequence:
    """Read a harmony file into a :class:`HamonSequence`, detecting its format.

    ``path`` may be a string: ``convert_file("changes.lab")`` is the first line of
    almost every example, and making the caller wrap it in ``Path`` buys nothing.
    """
    path = Path(path)
    fmt = fmt or detect_file_format(path)
    if fmt == "bps_fh":
        from .adapters.bps_fh import bps_fh_chords_file_to_hamon
        return bps_fh_chords_file_to_hamon(str(path))
    text = path.read_text(encoding="utf-8")
    return convert_text(text, fmt)


@dataclass
class Transcode:
    """The result of an any-format → any-format conversion, through HAMON.

    Everything a lossy conversion produces is kept: the intermediate canonical model
    (``sequence`` / ``hamon_json``), the ``output`` text in the target format, and the
    ``report`` of what the target could not carry.
    """
    source_format: str
    target_format: str
    sequence: HamonSequence
    hamon_json: str
    output: str
    report: "object"  # hamonpy.report.LossyReport (late import avoids a cycle)


def transcode(input: "str | Path", to: str, *, input_format: Optional[str] = None,
              mode: str = "workaround") -> Transcode:
    """Convert a file from any supported format to any writable format, via HAMON.

    The canonical HAMON JSON is always produced as the intermediate, and the semantic
    loss of the target step is always measured — so a conversion never silently drops
    information. ``input`` is a path; pass ``input_format`` to skip auto-detection.
    ``mode`` is ``"workaround"`` (the full HAMON surface rides along in the target's text
    slot) or ``"native"`` (only what the target says in its own vocabulary) — see
    :data:`hamonpy.report.Mode`.
    """
    from .report import WRITERS, write_to, lossy_report

    if to not in WRITERS:
        raise ValueError(f"target {to!r} is not writable. Choose one of: {', '.join(sorted(WRITERS))}")
    path = Path(input)
    fmt = input_format or detect_file_format(path)
    seq = convert_file(path, fmt)
    return Transcode(
        source_format=fmt,
        target_format=to,
        sequence=seq,
        hamon_json=sequence_to_json(seq),
        output=write_to(seq, to, mode),
        report=lossy_report(seq, to, keep_output=False, mode=mode),
    )


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------

def _cmd_convert(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    fmt = args.format or detect_file_format(path)
    seq = convert_file(path, fmt)
    out = sequence_to_json(seq, indent=args.indent)
    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
        print(f"wrote {args.output} ({len(seq.groups)} groups, format={fmt})", file=sys.stderr)
    else:
        print(out)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    import json as _json
    from .report import lossy_report, WRITERS

    path = Path(args.input)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    if args.to not in WRITERS:
        print(f"error: --to must be one of: {', '.join(WRITERS)}", file=sys.stderr)
        return 2
    fmt = args.format or detect_file_format(path)
    seq = convert_file(path, fmt)
    rep = lossy_report(seq, args.to, keep_output=bool(args.write_output) or args.json,
                       mode=args.mode)

    if args.write_output and rep.output_text is not None:
        Path(args.write_output).write_text(rep.output_text, encoding="utf-8")
        print(f"wrote {args.write_output} ({args.to})", file=sys.stderr)

    if args.json:
        print(_json.dumps(rep.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Source: {path} (format={fmt})")
        print(rep.summary())
    return 0 if rep.error is None else 1


def _cmd_validate(args: argparse.Namespace) -> int:
    import json as _json
    from .validate import validate_positions

    reports = []
    worst = 0
    for raw in args.inputs:
        path = Path(raw)
        if not path.is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
        fmt = args.format or detect_file_format(path)
        try:
            seq = convert_file(path, fmt)
        except Exception as e:  # noqa: BLE001
            print(f"error: could not parse {path} as {fmt}: {e}", file=sys.stderr)
            return 2

        # Count labels by semantic kind; a label whose semantic stayed "text" is opaque —
        # either genuine text or a harmony the parser could not read semantically.
        kinds: dict[str, int] = {}
        opaque: list[tuple[int, str]] = []
        n_labels = 0

        def _tally(labels, gi: int) -> None:
            nonlocal n_labels
            for lab in labels:
                n_labels += 1
                kind = lab.semantic.kind
                kinds[kind] = kinds.get(kind, 0) + 1
                if kind == "text":
                    opaque.append((gi, lab.surface))

        for gi, group in enumerate(seq.groups):
            _tally(group.primary, gi)
            for alt in group.alternatives:
                _tally(alt, gi)
        position_warnings = validate_positions(seq)

        if args.json:
            reports.append({
                "source": str(path),
                "format": fmt,
                "groups": len(seq.groups),
                "labels": n_labels,
                "kinds": dict(sorted(kinds.items())),
                "opaqueLabels": [{"group": gi, "surface": surface} for gi, surface in opaque],
                "positionWarnings": position_warnings,
            })
        else:
            print(f"Source: {path} (format={fmt})")
            print(f"Groups: {len(seq.groups)}, labels: {n_labels}")
            print("Kinds: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"))
            for gi, surface in opaque[:20]:
                print(f"  opaque (text) label at group {gi}: {surface!r}")
            if len(opaque) > 20:
                print(f"  … and {len(opaque) - 20} more opaque labels")
            for warning in position_warnings:
                print(f"  position: {warning}")
            if not opaque and not position_warnings:
                print("OK — every label parsed semantically and every position is in range.")
            else:
                print(f"{len(opaque)} opaque label(s), {len(position_warnings)} position warning(s).")

        if opaque or position_warnings:
            worst = 1

    if args.json:
        # One object for a single input (stable API), a list when validating many.
        print(_json.dumps(reports[0] if len(reports) == 1 else reports, indent=2, ensure_ascii=False))

    return worst if args.strict else 0


def _cmd_export(args: argparse.Namespace) -> int:
    from .report import WRITERS

    path = Path(args.input)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    if args.to not in WRITERS:
        print(f"error: --to must be one of: {', '.join(WRITERS)}", file=sys.stderr)
        return 2

    # any-format → any-format, through the canonical HAMON model
    tc = transcode(path, args.to, input_format=args.format, mode=args.mode)

    if args.save_hamon:
        Path(args.save_hamon).write_text(tc.hamon_json + "\n", encoding="utf-8")
        print(f"wrote {args.save_hamon} (intermediate HAMON JSON)", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(tc.output, encoding="utf-8")
        print(f"wrote {args.output} ({args.to}, from {tc.source_format})", file=sys.stderr)
    else:
        print(tc.output, end="" if tc.output.endswith("\n") else "\n")

    if not tc.output.strip():
        print(f"note: {args.to} carried nothing from this {tc.source_format} input "
              f"(the target can't represent its harmony system); try --report to see why",
              file=sys.stderr)

    if args.report:
        print(f"Source: {path} (format={tc.source_format}) → {args.to}", file=sys.stderr)
        print(tc.report.summary(), file=sys.stderr)
    return 0


def _cmd_datasets(args: argparse.Namespace) -> int:
    from . import datasets
    if args.action == "list":
        for name in datasets.list_datasets():
            print(name)
        return 0
    if args.action == "info":
        d = datasets.get_dataset(args.name)
        for k in ("title", "authors", "homepage", "license", "citation", "format", "hamon_adapter"):
            if k in d:
                print(f"{k}: {d[k]}")
        return 0
    if args.action == "path":
        try:
            print(datasets.resolve_local_path(args.name))
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"error: {e}", file=sys.stderr)
            return 1
    if args.action == "download":
        try:
            dest = datasets.fetch_dataset(args.name, harmony_only=not args.full)
            print(f"fetched {args.name} → {dest}" + ("" if args.full else "  (harmony-only)"))
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"error: {e}", file=sys.stderr)
            return 1
    if args.action == "download-all":
        mode = "full" if args.full else "harmony-only"
        print(f"fetching all datasets ({mode}) …", file=sys.stderr)
        results = datasets.download_all(harmony_only=not args.full)
        ok = sum(1 for v in results.values() if v == "ok")
        for name, status in results.items():
            print(f"  {name}: {status}")
        print(f"{ok}/{len(results)} fetched into {datasets.data_dir()}", file=sys.stderr)
        return 0 if all(not v.startswith("error") for v in results.values()) else 1
    return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hamon", description="hamon — universal harmony hub")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("convert", help="convert a harmony file to canonical hamon JSON")
    c.add_argument("input", help="input file")
    c.add_argument("--format", "-f", choices=FORMATS, help="override format auto-detection")
    c.add_argument("--output", "-o", help="write JSON to this file instead of stdout")
    c.add_argument("--indent", type=int, default=2, help="JSON indent (default 2)")
    c.set_defaults(func=_cmd_convert)

    from .report import WRITERS
    e = sub.add_parser("export", help="convert any format to any target format (through HAMON)")
    e.add_argument("input", help="input file")
    e.add_argument("--to", required=True, choices=WRITERS, help="target export format")
    e.add_argument("--format", "-f", choices=FORMATS, help="override input format auto-detection")
    e.add_argument("--output", "-o", help="write to this file instead of stdout")
    e.add_argument("--mode", choices=["workaround", "native"], default="workaround",
                   help="'native' writes only what the target says in its own vocabulary; "
                        "'workaround' (default) also parks the full HAMON surface in its "
                        "text slot, so nothing is lost but nothing is translated either")
    e.add_argument("--save-hamon", metavar="PATH",
                   help="also write the intermediate canonical HAMON JSON here")
    e.add_argument("--report", action="store_true",
                   help="also print, to stderr, what the target format could not carry")
    e.set_defaults(func=_cmd_export)

    r = sub.add_parser("report", help="round-trip a file to a target format and report semantic loss")
    r.add_argument("input", help="input file")
    r.add_argument("--to", required=True, choices=WRITERS, help="target export format")
    r.add_argument("--format", "-f", choices=FORMATS, help="override input format auto-detection")
    r.add_argument("--mode", choices=["workaround", "native"], default="workaround",
                   help="'native' writes only what the target says in its own vocabulary; "
                        "'workaround' (default) also parks the full HAMON surface in its "
                        "text slot, so nothing is lost but nothing is translated either")
    r.add_argument("--write-output", help="also write the exported text to this file")
    r.add_argument("--json", action="store_true", help="emit the report as JSON")
    r.set_defaults(func=_cmd_report)

    v = sub.add_parser("validate", help="parse file(s) and report opaque labels + position warnings")
    v.add_argument("inputs", nargs="+", metavar="input", help="input file(s)")
    v.add_argument("--format", "-f", choices=FORMATS, help="override format auto-detection")
    v.add_argument("--json", action="store_true", help="emit the report as JSON")
    v.add_argument("--strict", action="store_true",
                   help="exit 1 when any label stayed opaque or any position is out of range")
    v.set_defaults(func=_cmd_validate)

    d = sub.add_parser("datasets", help="inspect the dataset registry")
    dsub = d.add_subparsers(dest="action", required=True)
    dsub.add_parser("list", help="list registered datasets")
    di = dsub.add_parser("info", help="show a dataset's metadata")
    di.add_argument("name")
    dp = dsub.add_parser("path", help="resolve a dataset's local path (via the downloader manifest)")
    dp.add_argument("name")
    dd = dsub.add_parser("download", help="fetch one dataset into datasets/_data/ (git/http)")
    dd.add_argument("name")
    dd.add_argument("--full", action="store_true",
                    help="fetch full corpora (scores + submodules); default is harmony-only")
    da = dsub.add_parser("download-all", help="fetch every git/http dataset into datasets/_data/")
    da.add_argument("--full", action="store_true",
                    help="fetch full corpora (scores + submodules); default is harmony-only")
    d.set_defaults(func=_cmd_datasets)

    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
