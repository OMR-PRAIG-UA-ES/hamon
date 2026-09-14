# DCML Annotation Format

The DCML (Digital and Cognitive Musicology Lab) annotation format is a TSV-based Roman numeral scheme that Johannes Hentschel and colleagues built at EPFL. It underpins several large, hand-annotated corpora of tonal music — ABC, Beethoven, Brahms, Chopin, Debussy, and more.

## Reference

Hentschel, J., Neuwirth, M., & Rohrmeier, M. (2021). The Annotated Beethoven Corpus (ABC): A dataset of harmonic analyses of all Beethoven string quartets. *Frontiers in Digital Humanities*, 8. https://doi.org/10.3389/fdigh.2021.718509

## TSV Structure

Each file is tab-separated, one row per annotated beat position. The columns that matter for harmony are:

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| `chord` | string | `V7/IV` | Full chord symbol — the surface label (Roman numeral + form + figbass + optional slash secondary) |
| `numeral` | string | `V` | Roman numeral degree (uppercase = major, lowercase = minor context) |
| `form` | string | `M`, `m`, `o`, `+`, `%` | Quality modifier: `M` or empty = major, `m` = minor, `o` = diminished, `+` = augmented, `%` = half-diminished |
| `figbass` | string | `7`, `65`, `43`, `2` | Figured bass inversion/quality: `7`=seventh, `6`=first-inv triad, `65`/`43`/`2`=inverted sevenths |
| `changes` | string | `(b7)`, `(#5)` | Chromatic or added tones in parentheses; may be absent |
| `relativeroot` | string | `IV`, `V` | Secondary target: the denominator after `/`, e.g. `V/IV` → `relativeroot="IV"` |
| `localkey` | string | `I`, `vi`, `IV` | Current local key as a Roman numeral relative to the global key |
| `globalkey` | string | `C`, `a` | Global key; uppercase = major, lowercase = minor |
| `mc` | int | 4 | Measure count (not always present) |
| `onset` | fraction | `0` | Beat onset within the measure |

### Form vocabulary

| `form` value | Meaning |
|---|---|
| (empty) | Major triad (or as otherwise implied by numeral case) |
| `M` | Explicit major (often for major seventh: `VM7`) |
| `m` | Minor |
| `o` | Diminished |
| `+` | Augmented |
| `%` | Half-diminished |

### Figured bass vocabulary

| `figbass` | Inversion / chord type |
|-----------|------------------------|
| (empty) | Root position triad |
| `6` | First inversion triad |
| `64` | Second inversion triad |
| `7` | Root position seventh |
| `65` | First inversion seventh |
| `43` | Second inversion seventh |
| `2` | Third inversion seventh |

## Mapping to HAMON

DCML Roman numerals map cleanly onto HAMON's `RomanSemantic`:

| DCML field | HAMON field | Notes |
|-----------|-------------|-------|
| `numeral` | `degree` | Uppercase/lowercase preserved |
| `form` (`M`/`m`/`o`/`+`/`%`) | part of `tail` | Normalised: `m7`, `°7`, `ø7`, etc. |
| `figbass` | appended to `tail` | `7`→`7`, `65`→`65`, etc. |
| `changes` | appended to `tail` (parenthesised) | Round-trip as a tail suffix |
| `relativeroot` | `secondary` + `HarmonyAttributes.applied` | The denominator after `/`; also drives a tonicization region (below) |
| `globalkey` + `localkey` | `HamonSequence.regions` (`TonalRegion`) | The analytical layer — see below |

### Key columns → tonal regions (v0.2.0)

Since v0.2.0 the importer maps DCML's key columns into the analytical layer
([`analysis.md`](analysis.md)):

- **`globalkey`** is a key name whose case gives the mode (`C` = C major, `a` = A
  minor, `F#`, `eb`). It's the reference point for resolving the Roman key
  columns to real pitches, and it never becomes a region of its own.
- **`localkey`** is a Roman numeral *relative to the global key* (case = mode).
  HAMON computes its absolute tonic in the global key's scale — mode-aware, so
  minor and modal globals spell correctly. The first `localkey` becomes a
  `TonalRegion` of kind `key`; each change after that becomes a `modulation`.
- **`relativeroot`** is a Roman numeral *relative to the local key*. A run of
  rows that share a non-empty `relativeroot` becomes a **nested** `TonalRegion`
  of kind `tonicization` (`degree` = the relativeroot, `parent` = the local-key
  region), and every chord in that run also carries
  `HarmonyAttributes.applied.target`.

For example, global `C`, local `I`, chord `V7/V` with `relativeroot=V` gives you
a C-major key region plus a nested G-major tonicization region (`degree:"V"`),
and the chord keeps both `secondary:"V"` and `applied.target:"V"`.

### Reconstruction of surface string

`chord = numeral + form + figbass [+ changes] [+ "/" + relativeroot]`

Example: `numeral=V`, `form=""`, `figbass=7`, `relativeroot=IV` → `chord=V7/IV`.

## Known limitations

- `changes` (chromatic alterations) round-trip as a raw tail suffix; HAMON doesn't model individual altered tones as first-class fields.
- Region **import and export** both work. On export, `hamon_to_dcml_tsv` adds `localkey`/`globalkey` columns whenever the sequence has `regions`: it uses the **home (first) key region as the `globalkey`** and expresses every region's `localkey` relative to it (tonicizations become `relativeroot`). That keeps the absolute keys intact on a DCML→HAMON→DCML round-trip; the `globalkey` string matches the original only when the piece's home key is `I`.
- The *plain* `dcml.py` reader ignores `mc` / `onset` (the time positions); any table whose header has a position column (`quarterbeats`, `mn` or `mc`) is routed to the **expanded** adapter below, which fills `HarmonyGroup.position` from them. The writer goes the other way: a placed sequence gets `mn` / `mn_onset` / `quarterbeats` / `duration_qb` (+ `timesig`) columns in front of the chord columns, so a DCML→HAMON→DCML round-trip keeps the positions and a HAMON analysis lands in DCML already aligned.

## Expanded (time-aligned) tables — the Hentschel annotation standard & ms3

The DCML harmony annotation standard (Hentschel, Neuwirth & Rohrmeier) ships its
corpora as *expanded* harmony tables — see [*The Annotated Mozart Sonatas: Score,
Harmony, and Cadence*](https://doi.org/10.5334/tismir.63) and the *Annotated
Corpus of Tonal Piano Music from the Long 19th Century* — and the `ms3` MuseScore
parser ([ms3.md](ms3.md)) emits the same shape. These tables carry extra columns
that the plain adapter ignores:

| Column | Example | Maps to |
|--------|---------|---------|
| `quarterbeats` | `129/2` | `HarmonyGroup.position.time` (absolute quarter offset, as a fraction) |
| `mc` / `mn` + `mn_onset` | `12` + `1/2` | `position.measure` + `position.beat` (fallback when `quarterbeats` is absent) |
| `cadence` | `PAC`, `HC`, `IAC`, `DC`, `EC` | `extract_cadences()` (side-channel — no AST node yet) |
| `phraseend` | `{`, `}`, `}{` | `extract_phrase_ends()` (side-channel) |

`hamonpy.adapters.dcml_expanded`:

```python
from hamonpy.adapters.dcml_expanded import (
    expanded_tsv_to_hamon, expanded_tsv_text_to_hamon,
    extract_cadences, extract_phrase_ends,
)

seq = expanded_tsv_to_hamon("sonata.harmonies.tsv")  # chords + regions + positions
for g in seq.groups:
    print(g.primary[0].surface, g.position.time)      # time-aligned

cadences = extract_cadences(open("sonata.harmonies.tsv").read())   # [Cadence(type="PAC", position=...), ...]
phrases  = extract_phrase_ends(open("sonata.harmonies.tsv").read())
```

The chord-surface logic and the `localkey`/`relativeroot` → region logic are
**shared** with the plain `dcml.py` adapter; all the expanded adapter adds on top
is positions and the cadence/phrase side-channels. HAMON's AST has no cadence or
phrase node yet, so those come back alongside the sequence instead of being folded
into groups — future work.

The CLI auto-detects expanded tables — a `.tsv` with a `quarterbeats` column — as
`dcml_expanded`; to force it, run `hamon convert file.tsv -f dcml_expanded`.

## Pitch arrays — the DiLeMMa training tables

[`dilemmadata`](https://github.com/johentsch/dilemmadata) (Hentschel) is the data
infrastructure behind the AnalysisGNN multitask analysis models. It ships **pitch
arrays**: TSV tables where *one row is one note* and the annotations are repeated on
every note they cover. Harmony is not a list of labels here — it is a column, and its
rhythm is a flag on the note grid.

Two dialects live in `pitch_arrays/`, and `hamonpy.adapters.dilemma` reads both:

| Dialect | Files | Grouping column | Chord column | Keys |
|---|---|---|---|---|
| **DLC** (Distant Listening Corpus) | `pitch_arrays/DLC/<subcorpus>/*.tsv` | `unfolded_harmony_index` | `chord` (plain DCML) | `localkey` / `globalkey`, as DCML degrees |
| **AN** (AugmentedNet) | `pitch_arrays/AN/{training,validation,test}/*_joint.tsv` | `a_annotationNumber` | `a_romanNumeral` | `a_localKey` / `a_tonicizedKey`, **absolute** and music21-spelled (`B-` = B flat) |

The adapter **collapses** the note grid back to one row per harmony and hands the
result to `dcml_expanded`, so chord surfaces, tonal regions and positions come out of
exactly the same code as for the corpora these arrays were derived from. For the AN
dialect the absolute keys are converted to DCML degrees first (the first `a_localKey`
is taken as the piece's `globalkey`), and AugmentedNet's `Cad` — the cadential
six-four — is written as DCML's `V(64)`, which HAMON parses.

```python
from hamonpy.adapters.dilemma import pitch_array_to_hamon, extract_spans

seq = pitch_array_to_hamon("pitch_arrays/DLC/chopin_mazurkas/BI115-1op33-1.tsv")
len(seq.groups)                      # 90 harmonies, not 509 notes
spans = extract_spans(open(path).read())   # index-aligned with seq.groups
```

What the pitch arrays add over the expanded tables is **harmonic rhythm**: AN states
each harmony's duration outright (`a_duration`), and in DLC it follows from consecutive
onsets. HAMON's `Position` is onset-only, so `extract_spans()` returns them on the
side — a `HarmonySpan(position, duration, source)` per group, where `source` is
`"explicit"` (the corpus said so) or `"derived"` (computed from the next onset), and
`duration` is `None` for the last DLC harmony, whose end the array never states. Same
treatment as cadences and phrase ends: reported honestly, not folded into the AST.

The CLI auto-detects pitch arrays — a `.tsv` with an `unfolded_harmony_index` or
`a_annotationNumber` column — as `dilemma`, ahead of the `quarterbeats` sniff (DLC
arrays have a `quarterbeats_playthrough` column). The `corpora/` directory of that repo
holds git submodules with SSH URLs; the pitch arrays do not need them. The companion
`*_slices.tsv` files carry no harmony.

## Corpus availability

The public DCML-annotated corpora live on GitHub under the `DCMLab` organisation:
- [DCMLab/ABC](https://github.com/DCMLab/ABC) — Annotated Beethoven Corpus
- [DCMLab/mozart_piano_sonatas](https://github.com/DCMLab/mozart_piano_sonatas)
- [DCMLab/chopin_mazurkas](https://github.com/DCMLab/chopin_mazurkas)
