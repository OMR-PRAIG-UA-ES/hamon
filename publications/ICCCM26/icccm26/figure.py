"""Poster figures built from the xencoding results.

Two figures:
  * ``build_matrix_figure`` — heatmap of what each encoding cannot natively say, for
    every (example × target-format) pair. HAMON's own column is 0 everywhere: the
    lossless interlingua. This is the poster's main figure, and the site
    (``site/build.py``) reuses the same files rather than drawing its own.
  * ``build_hub_figure`` — hub-and-spoke view of a single example: HAMON in the
    centre, one spoke per encoding, edge colour/width ∝ loss.

Both are written as PNG (300 dpi) and SVG into ``outputs/``.
"""
from __future__ import annotations

import math
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import FancyArrowPatch, Circle
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "This module needs matplotlib. Install it with:\n"
        "    pip install matplotlib\n"
        f"(import failed: {exc})"
    )

from .roundtrip import ExampleResult, OUTPUTS_DIR

# Nice display names for the encodings.
FORMAT_LABELS = {
    "hamon": "HAMON",
    "dcml": "DCML",
    "dezrann": "Dezrann",
    "mei": "MEI",
    "harte": "Harte",
    "musicxml": "MusicXML",
    "lilypond": "LilyPond",
    "abc": "ABC",
    "musescore": "MuseScore",
    "romantext": "RomanText",
    "humdrum": "Humdrum",
    "ireal": "iReal Pro",
    "jams": "JAMS",
}

# Brand-ish palette.
LOSSLESS = "#1b9e77"   # green
LOSS_HI = "#d62728"    # red
INK = "#222222"
_LOSS_CMAP = LinearSegmentedColormap.from_list(
    "hamon_loss", ["#f7fbf9", "#fdd9b5", "#f16913", "#a63603"]
)


def _short(label: str) -> str:
    return label.replace("\n", " ")


def build_matrix_figure(results: list[ExampleResult], out_stem: Path | None = None) -> Path:
    """Semantic-loss heatmap: rows = examples, cols = encodings."""
    targets = [t.target for t in results[0].targets]
    n_rows, n_cols = len(results), len(targets)
    data = [[r.target(t).semantic_loss for t in targets] for r in results]
    vmax = max((max(row) for row in data), default=1) or 1

    fig, ax = plt.subplots(figsize=(1.05 * n_cols + 2.4, 0.9 * n_rows + 2.2))
    im = ax.imshow(data, cmap=_LOSS_CMAP, vmin=0, vmax=vmax, aspect="auto")

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels([FORMAT_LABELS.get(t, t) for t in targets],
                       rotation=40, ha="right", fontsize=11)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([r.label for r in results], fontsize=10.5)

    # annotate each cell
    for i in range(n_rows):
        for j in range(n_cols):
            v = data[i][j]
            lossless = v == 0
            ax.text(j, i, "✓" if lossless else str(v),
                    ha="center", va="center",
                    color=(LOSSLESS if lossless else (INK if v < 0.6 * vmax else "white")),
                    fontsize=12 if lossless else 11,
                    fontweight="bold")

    # highlight the HAMON column as the lossless hub
    if "hamon" in targets:
        hj = targets.index("hamon")
        ax.add_patch(plt.Rectangle((hj - 0.5, -0.5), 1, n_rows,
                                   fill=False, edgecolor=LOSSLESS, lw=3, zorder=5))
        ax.get_xticklabels()[hj].set_color(LOSSLESS)
        ax.get_xticklabels()[hj].set_fontweight("bold")

    ax.set_title("What each encoding cannot say about a HAMON analysis\n"
                 "counted against each format's own vocabulary  ·  0 = says it all "
                 "(only HAMON does)",
                 fontsize=13, fontweight="bold", pad=14)
    # The distinction the whole figure rests on: an aspect a format can only hold as an
    # opaque string is NOT counted as carried. Parking a HAMON label in MEI's <harm>
    # character data round-trips perfectly and tells you nothing about MEI.
    ax.set_xlabel("target encoding  ·  text-only carriage counts as loss, not capability",
                  fontsize=11)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("# analytical aspects the format cannot express", fontsize=10)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, n_cols)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, n_rows)], minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)

    fig.tight_layout()
    return _save(fig, out_stem or (OUTPUTS_DIR / "figure_loss_matrix"))


def build_hub_figure(result: ExampleResult, out_stem: Path | None = None) -> Path:
    """Hub-and-spoke: HAMON in the centre, one spoke per encoding."""
    spokes = [t for t in result.targets if t.target != "hamon"]
    vmax = max((t.semantic_loss for t in spokes), default=1) or 1
    n = len(spokes)

    fig, ax = plt.subplots(figsize=(8.6, 8.6))
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")

    # spokes
    for k, t in enumerate(spokes):
        ang = math.pi / 2 - 2 * math.pi * k / n
        x, y = math.cos(ang), math.sin(ang)
        frac = t.semantic_loss / vmax
        color = _LOSS_CMAP(0.15 + 0.85 * frac) if t.semantic_loss else LOSSLESS
        lw = 1.6 + 4.2 * frac
        ax.add_patch(FancyArrowPatch((0, 0), (0.72 * x, 0.72 * y),
                                     arrowstyle="-", lw=lw, color=color, alpha=0.9, zorder=1))
        # node
        ax.add_patch(Circle((x, y), 0.145, facecolor="white", edgecolor=color, lw=2.2, zorder=3))
        ax.text(x, y + 0.02, FORMAT_LABELS.get(t.target, t.target),
                ha="center", va="center", fontsize=9.5, fontweight="bold", color=INK, zorder=4)
        badge = "lossless" if t.lossless else f"−{t.semantic_loss}"
        ax.text(x, y - 0.058, badge, ha="center", va="center", fontsize=8,
                color=(LOSSLESS if t.lossless else LOSS_HI), zorder=4)
        # loss label near the edge midpoint
        if t.semantic_loss:
            ax.text(0.42 * x, 0.42 * y, str(t.semantic_loss), ha="center", va="center",
                    fontsize=9, color=color, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.16", fc="white", ec=color, lw=1), zorder=2)

    # centre hub
    ax.add_patch(Circle((0, 0), 0.26, facecolor=LOSSLESS, edgecolor="white", lw=3, zorder=5))
    ax.text(0, 0.03, "HAMON", ha="center", va="center", color="white",
            fontsize=14, fontweight="bold", zorder=6)
    ax.text(0, -0.075, "JSON · lossless", ha="center", va="center", color="white",
            fontsize=8.5, zorder=6)

    ax.set_title(f"{_short(result.label)} — one analysis, every encoding\n"
                 "edge = aspects the encoding cannot say in its own vocabulary",
                 fontsize=13, fontweight="bold", pad=8)
    fig.tight_layout()
    return _save(fig, out_stem or (OUTPUTS_DIR / f"figure_hub_{result.name}"))


def _save(fig, stem: Path) -> Path:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    png = stem.with_suffix(".png")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png


def build_figures(results: list[ExampleResult]) -> list[Path]:
    """Build the loss matrix, and a hub figure for the first example in EXAMPLE_ORDER.

    Only the first example gets a hub, so changing which example leads leaves the old
    one's figure sitting in `outputs/`. Two hub figures in a directory is exactly the
    kind of thing that ends up on a poster by mistake, so the stale ones are swept.
    """
    paths = [build_matrix_figure(results)]
    if not results:
        return paths

    hub = build_hub_figure(results[0])
    paths.append(hub)
    for stale in OUTPUTS_DIR.glob("figure_hub_*"):
        if stale.stem != hub.stem:
            stale.unlink()
            print(f"  removed stale hub figure: {stale.name}")
    return paths
