#!/usr/bin/env python
"""Render the poster's score excerpt: source notation + HAMON's harmony, as SVG/PNG/PDF.

The site does this in the browser, with Verovio compiled to WebAssembly. The poster
needs a file, so this runs the same two steps offline:

  1. `site/build.py:_overlay_score` injects the example's HAMON labels into the source
     MEI as positioned `<harm>`/`<fb>` — the same function the site uses, so the printed
     score and the web one cannot disagree.
  2. Verovio engraves it.

A one-off, like the MEI generation documented in `scores/README.md` — deliberately not
part of `build_all.sh` or CI, because it needs two dependencies nothing else here wants:

    python -m pip install verovio        # engraving
    brew install librsvg                 # rsvg-convert, for the PNG and the PDF

    python publications/ICCCM26/render_score.py            # defaults to sat_mozart_fb

Width is what decides the system breaks: 2400 gives two systems of four bars, which is
the shape a poster column wants. Narrower stacks more systems, wider flattens to one.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ICCCM = ROOT / "publications" / "ICCCM26"
OUTPUTS = ICCCM / "outputs"

PAGE_WIDTH = 2400          # 2 systems x 4 bars for this excerpt
PNG_WIDTH = 2400           # raster width in pixels


def render(example: str = "sat_mozart_fb") -> Path:
    sys.path.insert(0, str(ROOT / "site"))
    import build                                    # imports only; main() is not called
    import verovio

    source = build.SOURCE_SCORES.get(example)
    if not source:
        raise SystemExit(f"{example} has no entry in SOURCE_SCORES — it has no real score")

    mei = build._overlay_score(ICCCM / "scores" / source,
                               (ICCCM / "examples" / f"{example}.hamon").read_text(encoding="utf-8"))
    if not mei:
        raise SystemExit("the overlay failed — is lxml installed?")
    annotated = OUTPUTS / f"score_{example}.annotated.mei"
    annotated.write_text(mei, encoding="utf-8")

    tk = verovio.toolkit()
    tk.setOptions({
        "pageWidth": PAGE_WIDTH, "pageHeight": 4000, "scale": 50,
        "adjustPageHeight": True, "header": "none", "footer": "none",
        "pageMarginTop": 30, "pageMarginBottom": 30,
        "pageMarginLeft": 30, "pageMarginRight": 30,
        "svgViewBox": True, "svgRemoveXlink": True,
    })
    if not tk.loadData(mei):
        raise SystemExit("Verovio could not load the annotated MEI")
    if tk.getPageCount() != 1:
        print(f"  warning: {tk.getPageCount()} pages — only the first is written")

    svg = OUTPUTS / f"score_{example}.svg"
    svg.write_text(tk.renderToSVG(1), encoding="utf-8")
    print(f"  + {svg.relative_to(ROOT)}")

    for args, suffix in ((["-w", str(PNG_WIDTH)], "png"), (["-f", "pdf"], "pdf")):
        target = OUTPUTS / f"score_{example}.{suffix}"
        try:
            subprocess.run(["rsvg-convert", *args, "-o", str(target), str(svg)], check=True)
            print(f"  + {target.relative_to(ROOT)}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"  ! {suffix} skipped — rsvg-convert not available")
    return svg


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "sat_mozart_fb")
