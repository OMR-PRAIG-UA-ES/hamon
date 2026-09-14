# Source scores (real notation) for the real-score overlay

These MEI files hold the **notes** of a real piece. Only music that is clearly out of
copyright goes here: the flagship example (Gershwin) is shown as harmony alone, with no
notation, via `HARMONY_ONLY` in `site/build.py`. The site (`site/build.py`,
`_overlay_score`) injects the HAMON harmony of the matching example as positioned
`<harm>`/`<fb>` and Verovio renders the annotated score in the browser. The harmony
stays authored in the `.hamon` example — the overlay is re-derived at build time, so the
two never drift, and the source's own harmony markup is stripped first (HAMON is the sole
source of the displayed labels).

Mapping example → source score lives in `SOURCE_SCORES` in `site/build.py`.

| Source MEI | Example (`publications/ICCCM26/examples/`) | Piece |
|---|---|---|
| `K282-1.mei` | `sat_mozart_fb.hamon` | Mozart, Piano Sonata K. 282/i (Adagio), mm. 1–8 — figured bass |
| `figured-bass-demo.mei` | `sat_figured_bass.hamon` | Synthetic one-bar bass (dominant pedal) for the bare figured-bass example |

Placement follows the label's layer: figured bass → `<fb>` below the bass staff; Roman
(`rn:`/degree) → below; chord symbols and everything else → above.

Secondary dominants (a Roman with a `secondary` target, e.g. `V7/ii`) also get a
**tonicization mark** drawn from the applied dominant to the chord it tonicizes (the next
Roman whose degree matches). It renders in the Roman line as a `<slur curvedir="below">`,
because Verovio only places analytical `<bracketSpan>`s above the staff.

## Rendering one for print

The site engraves these in the browser. For a poster you need a file, and
`publications/ICCCM26/render_score.py` produces one — SVG, PNG and PDF — by calling the
*same* `_overlay_score` the site calls, so the printed score and the web one cannot drift.
It needs `pip install verovio` and `brew install librsvg`, which is why it is a one-off
and not part of `build_all.sh`.

## How `K282-1.mei` was made (regenerate only if the score changes)

Requires MuseScore (3 or 4) and the Verovio CLI — a one-off, not part of `build_all.sh`
or CI (the committed MEI is what the site uses):

```bash
# 1. MuseScore: .mscx → MusicXML   (source: DCML annotated-mozart-sonatas/MS3/K282-1.mscx)
"/Applications/MuseScore 3.app/Contents/MacOS/mscore" -o K282-1.musicxml K282-1.mscx
# 2. Verovio: MusicXML → MEI
verovio K282-1.musicxml -f musicxml -t mei -o K282-1.mei
# 3. Trim to the measures the example covers (mm. 1–8) and drop the score's own <harm>.
```
