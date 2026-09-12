# major seventh variants

This directory now contains surface variants for the same major-seventh harmony:

- `C_maj7/` → `Cmaj7`
- `C_delta7/` → `CΔ7`
- `C_M7/` → `CM7`

Each fixture folder contains snippet-only encodings for multiple ecosystems plus:

- a `.hamon` golden file using the HAMON grammar
- a small `.svg` preview image

(The `.json` + snippets are the source of truth.)

Notes:

- `kern_mxhm` is the most defensible companion-spine choice for chord symbols in the Humdrum/**kern ecosystem.
- `kern_jazz` and `kern_irb` are included as practical/custom companion-spine examples for comparison, not as claims of a formally standardized Humdrum representation.
- MuseScore `.mscx` is treated here as a best-effort internal XML snippet representation; MusicXML remains the safer interchange format.
