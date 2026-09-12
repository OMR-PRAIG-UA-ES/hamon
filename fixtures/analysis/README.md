# Analytical-layer fixtures (v0.2.0)

Example instances for the optional **analytical layer** described in
[`documentation/analysis.md`](../../documentation/analysis.md). Each fixture has
three files:

| File | Role | Validated by |
|---|---|---|
| `<id>.json` | **model fixture** — a hand-authored `HamonSequence` under a `sequence` key (with `id` + `description`), demonstrating the *full* canonical model (`grammar/hamon-schema.json`), including JSON-only fields the surface can't express (e.g. `alternativeAnalyses`, tone `metric`/`approach`, `impliedRoot`, `prolongation`). | `hamonpy/tests/test_analysis.py` |
| `<id>.hamon` | **surface counterpart** — the `.hamon` text that encodes the surface-expressible part of the analysis. | — |
| `<id>.expected.json` | **golden** — the canonical AST produced by parsing `<id>.hamon`, in schema-shaped (camelCase) JSON. | `hamonpy/tests/test_analysis_roundtrip.py` |

The round-trip suite (`hamonpy/tests/test_analysis_roundtrip.py`) parses each `.hamon`
and asserts it equals the matching `.expected.json` — the canonical parser output. When
you make an intentional change, regenerate the affected golden from the new parser output.

The `.hamon` surfaces cover the surface-expressible subset; richer JSON-only
features remain demonstrated by the `<id>.json` model fixtures.

| File | Feature |
|---|---|
| `tonal_regions.json` | tonal regions + modulation |
| `tonicization.json` | nested tonicization (passing tonal region) + applied function |
| `secondary_dominant_DD.json` | secondary dominant / dominant-of-the-dominant (Roman + functional `DD`) |
| `functional_layers.json` | layered functional analysis (key / function / degree / bass) |
| `nonharmonic_tones.json` | melodic HT/NHT analysis (passing, appoggiatura, *nota cambiata*) |
| `modal.json` | modal harmony (D dorian) |
| `omitted_fundamental.json` | omitted fundamental / implied root |
| `arpeggiation.json` | chord arpeggiation/unfolding + prolongation |
| `alternative_progression.json` | point alternative + whole-progression alternative |

Targeted end-to-end surface→AST coverage also lives in
the shared corpus and `hamonpy/tests/test_analysis_parse.py`.
