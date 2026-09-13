"""Entry point: run the whole ICCCM26 pipeline and emit the poster assets.

    python -m icccm26            # analyze, write JSON report + figures, print summary
    python -m icccm26 --snippets # also print the poster code boxes
    python -m icccm26 --no-figures
"""
from __future__ import annotations

import argparse

from .roundtrip import analyze_all, write_report, OUTPUTS_DIR
from .snippets import print_snippets


def _summary_table(results) -> str:
    targets = [t.target for t in results[0].targets]
    head = f"{'example':30s}{'sys':5s}{'lbls':5s}" + "".join(f"{t[:5]:>7s}" for t in targets)
    lines = [head, "-" * len(head)]
    for r in results:
        row = "".join(f"{t.semantic_loss:>7d}" for t in r.targets)
        lines.append(f"{r.name:30s}{str(r.system_hint or '-'):5s}{r.n_labels:<5d}{row}")
    lines.append("")
    lines.append("cells = # analytical aspects the format cannot express in its OWN "
                 "vocabulary (0 = says it all).")
    lines.append("Carrying a HAMON label as an opaque string counts as loss, not "
                 "capability: MEI's <harm> takes any")
    lines.append("text, so a round-trip through it is our escrow coming back, not MEI "
                 "encoding an analysis.")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icccm26", description=__doc__)
    ap.add_argument("--snippets", action="store_true", help="print the poster code boxes")
    ap.add_argument("--no-figures", action="store_true", help="skip matplotlib figures")
    args = ap.parse_args(argv)

    results = analyze_all()
    report_path = write_report(results)

    print(_summary_table(results))
    print(f"\nxencoding report → {report_path}")
    for r in results:
        print(f"canonical JSON    → {OUTPUTS_DIR / (r.name + '.hamon.json')}")

    if not args.no_figures:
        from .figure import build_figures
        for p in build_figures(results):
            print(f"figure            → {p}  (+ .svg)")

    if args.snippets:
        print_snippets()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
