# ICCCM26 — HAMON as a lossless harmony interlingua

> **Paper:** *"Bridging harmonic representations through a multi-modal encoding."* —
> to be presented at **[ICCCM 2026](https://digital.musicology.org/icccm-2026/)** (Würzburg, 21–23 September 2026).
> **Authors:** Patricia Garcia-Iasci (University of Alicante / University of Salamanca),
> Johannes Hentschel (Anton Bruckner University, Linz), Fabian C. Moss
> (Julius-Maximilians-Universität Würzburg), David Rizo (Universidad de Alicante; Instituto Superior de Enseñanzas Artísticas de la Comunidad Valenciana).
>
> Code **Apache-2.0**, prose and data **CC BY 4.0**. See [`../LICENSE`](../LICENSE).

Companion code and poster assets for **ICCCM26**. It takes a handful of
representative harmony examples and asks, of every supported encoding, **what it can and
cannot say about them in its own vocabulary** — aspect by aspect. The result is HAMON's
*explainable encoding* (**xencoding**): loss you can point at and name, rather than a
single fidelity score.

Each encoding turns out to be strong at what it was designed for — DCML and RomanText
lose nothing of a Roman analysis, MEI and Humdrum nothing of a figured bass. Humdrum
comes closest to covering everything, with a spine per system, and still has no way to
say a Nashville number, a chord-scale, a non-harmonic tone, or what chord symbol a
dominant is applied to. HAMON is the only one that says all of it.

Carrying a HAMON label as an opaque string does **not** count as saying it: see
[How the loss is computed](#how-the-loss-is-computed-xencoding).

## Run it

```bash
conda activate hamonpy
python -m pip install -e ../hamonpy        # provides hamonpy
python -m pip install matplotlib           # for the figures
cd ICCCM26
python run.py --snippets                   # summary table + JSON report + figures + code boxes
# or, as a module:  python -m icccm26
```

The same two readings are available from the command line for any file:
`hamon report score.mei --to harte --mode native` counts what Harte's own vocabulary
loses, and `--mode workaround` (the default) lets the HAMON surface ride along in the
target's text slot.

The outputs land in [`outputs/`](outputs/):

| File | What |
|---|---|
| `figure_loss_matrix.(png/svg)` | **hero figure** — heatmap of what each encoding cannot natively express, examples × encodings (the site shows this same file) |
| `figure_hub_flagship_*.(png/svg)` | hub-and-spoke: HAMON centre, one spoke per encoding |
| `xencoding_report.json` | full field-level loss report for every example × format |
| `<example>.hamon.json` | canonical HAMON JSON for each example |

## The examples ([`examples/`](examples/))

Each example is written directly in HAMON surface syntax. Together they exercise **every
representation system** plus the analytical layer — keys and regions, applied dominants and
tonicizations, chord-scales, and non-harmonic tones.

| File | System | Showcases |
|---|---|---|
| `flagship_love_walked_in.hamon` | layered `cs:` + `rn:` | **Two coordinated analyses of the same bars** — the chord symbols *and* the Roman-numeral reading, time-aligned (position-first `m:`/`ts:`). *Love Walked In* (Gershwin), the closing phrase (mm. 25–31), a harmony-only academic excerpt: a backdoor cadence (`Fm7 Bb7` → `C`, read `iv7 bVII7 I`) and an applied dominant (`A7` = `V7/ii`). Shows off HAMON's multi-modal layering: most target formats carry one analysis or the other; only HAMON and Humdrum keep both, and only HAMON keeps the key with them everywhere. |
| `sat_roman_dcml.hamon` | Roman (`@rn`) | Roman/DCML analysis with a secondary dominant (`V7/V`) and a modulation (`@key:V`). |
| `sat_figured_bass.hamon` | figured bass (`@fb`) | Baroque continuo figures (`6-4`, `5-3`, `7`, `6-5`). |
| `sat_mozart_fb.hamon` | figured bass (`@fb`) | **Real music, not a hand-made snippet** — Mozart K282, 22 labels of continuo figures. The longest example, and the one the other encodings lose the most of. |
| `sat_positions.hamon` | chord symbol (`@cs`) | Time-aligned positions: `m:`/`ts:` against `@meter:4/4`, so the figure asks each target whether it can carry *when* a harmony happens, not just which one. |
| `sat_nashville.hamon` | Nashville (`@ns`) | Nashville number chart with qualities (`6m`, `5sus`). |
| `pangram.hamon` | mixed (`@auto`) | **Every system in one sequence** — the harmony analogue of a *pangram* (a phrase that uses every letter). One auto-detected line touches all five systems plus the analytical layer: chord symbol (`+ [scale:]`), Roman secondary (`V7/V`), figured bass (`6-5`), Nashville (`2m`), functional chains (`DD->D->T`, `PD->T`), and a non-harmonic tone (`[NHT:passing]`). |

## How the loss is computed (xencoding)

The figure counts, per example and target, the analytical aspects the format **cannot
express in its own vocabulary** — from the capability table in `hamonpy/capability.py`,
which names for each encoding what it encodes structurally.

**Text does not count as capability.** MEI's `<harm>` accepts any character data, so
parking a HAMON label in it round-trips perfectly and tells you nothing about MEI. That
is escrow, not translation, and the difference is the whole argument: an encoding that
merely *holds our string* has not carried the analysis, and no other tool reading that
file could use it. The same applies to Dezrann's opaque `tag`.

This is why the number is not a round-trip diff. A round-trip measures *our exporters*:
a weak writer makes a format look lossy, and a writer that parks the HAMON surface in a
comment makes it look lossless (LilyPond did exactly that until 2026-09-03).

Two supporting numbers travel with each cell in `xencoding_report.json`:

- `workaround_recovers` — how much of the loss an out-of-band HAMON annotation would
  rescue. Legitimate to ship; never a claim about the format.
- `has_slot` — whether such a slot exists at all. **`false` for Harte `.lab` and iReal**:
  nothing can rescue them. That asymmetry is the interlingua argument.

`roundtrip_loss` is kept alongside as writer health — it is how an exporter bug surfaces,
which is a different question from what a format can say. It is computed in `native`
mode: the sequence is first projected to the target's vocabulary
(`hamonpy.report.project_native`), so no writer can rescue an aspect by embedding a
string, and a score format is handed the positions it can place.

HAMON's own column is `0` everywhere by construction — the fixed reference that makes
the others readable.

## Layout

```
ICCCM26/
├── examples/         # the .hamon source examples
├── icccm26/          # the package (roundtrip, figure, snippets, cli)
├── outputs/          # generated report + figures
└── run.py            # thin launcher (no install needed)
```
