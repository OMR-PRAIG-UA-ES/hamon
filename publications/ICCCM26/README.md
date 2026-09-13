# ICCCM26 — HAMON as a lossless harmony interlingua

> **Paper:** *"Bridging harmonic representations through a multi-modal encoding."* —
> to be presented at **[ICCCM 2026](https://digital.musicology.org/icccm-2026/)** (Würzburg, 21–23 September 2026).
> **Authors:** Patricia Garcia-Iasci (University of Alicante / University of Salamanca),
> Johannes Hentschel (Anton Bruckner University, Linz), Fabian C. Moss
> (Julius-Maximilians-Universität Würzburg), David Rizo (Universidad de Alicante; Instituto Superior de Enseñanzas Artísticas de la Comunidad Valenciana).
>
> **Contributions:** HAMON was designed and implemented by Patricia Garcia-Iasci and David
> Rizo. Johannes Hentschel and Fabian C. Moss took part as **expert advisers**, on the design
> of the standard and on the role it should play in the computational musicology community.
>
> Code **Apache-2.0**, prose and data **CC BY 4.0**. Copyright Universidad de Alicante.
> See [`../LICENSE`](../LICENSE).

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

From a clone of the repository, because the pipeline reads the examples in
[`examples/`](examples/):

```bash
conda create -n hamon-icccm26 python=3.11 -y   # or: python3.11 -m venv .venv
conda activate hamon-icccm26

python -m pip install "hamonpy==0.4.0"     # the version these numbers came from
python -m pip install matplotlib           # the figures need it

cd publications/ICCCM26
python run.py --snippets                   # table + JSON report + figures + code boxes
# or, as a module:  python -m icccm26
```

**0.4.0 is the version this material was produced with**, and pinning it is the point:
`pip install hamonpy` would give you whatever is on PyPI today, which will move.
`outputs/xencoding_report.json` records the version that produced it, so if you ever see
a different number there than the one you installed, the report and the library have
drifted and the numbers are not comparable.

The other half of what fixes these results is this repository — the examples, the
capability table and the pipeline all live here — so the pinned package reproduces the
library, and the commit you have checked out reproduces the rest.

If you are changing HAMON rather than reproducing the paper, install the checkout instead
(`python -m pip install -e ./hamonpy` from the repository root) and regenerate. If you
only want the library, see [Use HAMON](https://omr-praig-ua-es.github.io/hamon/use.html).

Run the `pip` lines from the repository root.

The environment is deliberately **not** called `hamonpy`. That name is the one a HAMON
developer already has, holding an editable install of the checkout; pinning 0.4.0 into it
would replace their working copy with a released one and leave them debugging a library
they did not change. A separate environment costs nothing and cannot do that.

Two habits from that page apply here too. Give `conda create` an explicit `python=3.11`,
because without it conda makes an environment with no interpreter and the commands after
it fall through to whatever Python your shell already had. And write `python -m pip`
rather than `pip`, so you install into the interpreter you are about to run.

The same two readings are available from the command line for any file:
`hamon report score.mei --to harte --mode native` counts what Harte's own vocabulary
loses, and `--mode workaround` (the default) lets the HAMON surface ride along in the
target's text slot.

The outputs land in [`outputs/`](outputs/):

| File | What |
|---|---|
| `figure_loss_matrix.(png/svg)` | **the main figure** — heatmap of what each encoding cannot natively express, examples × encodings (the site shows this same file) |
| `figure_hub_flagship_*.(png/svg)` | hub-and-spoke: HAMON centre, one spoke per encoding |
| `xencoding_report.json` | full field-level loss report for every example × format |
| `<example>.hamon.json` | canonical HAMON JSON for each example |

## The examples ([`examples/`](examples/))

Each example is written directly in HAMON surface syntax. Together they exercise **every
representation system** plus the analytical layer — keys and regions, applied dominants and
tonicizations, chord-scales, and non-harmonic tones.

They are listed in the order `EXAMPLE_ORDER` runs them, which matters for the first one:
the hub figure is drawn for whichever example comes first.

One file in there is not HAMON: `changes.lab` is a **Harte** annotation, the format audio
chord estimation publishes in. It is what the poster's `convert_file()` line reads, so that
the code on the poster runs against a real file rather than an imaginary one.

| File | System | Showcases |
|---|---|---|
| `k501_mozart_duet.hamon` | layered `cs:` + `rn:` + `fn:` | **The hub figure's example, and the only one whose analysis is not ours.** Mozart, *Andante with variations* for piano four hands, K. 501 (1786), mm. 1–8 in G major, carrying three coordinated readings of the same bars: the chord symbols, the Roman numerals, and the T–PD–D function underneath. Two applied dominants (`V7/V`, `V7/IV`) and a cadential six-four over the dominant (`I64/V`), so the figure measures the analytical vocabulary and not just the chords. The Roman and functional readings come from **TAVERN** (Devaney, Arthur, Condit-Schultz & Nisula, ISMIR 2015), where two annotators marked the piece independently and reconciled the result; the chord symbols follow from those numerals in G major. TAVERN is CC BY-SA 4.0 and Mozart is public domain; we cite them rather than redistributing their file. |
| `flagship_love_walked_in.hamon` | layered `cs:` + `rn:` | **Two coordinated analyses of the same bars** — the chord symbols *and* the Roman-numeral reading, time-aligned (position-first `m:`/`ts:`). *Love Walked In* (Gershwin), the closing phrase (mm. 25–31), a harmony-only academic excerpt: a backdoor cadence (`Fm7 Bb7` → `C`, read `iv7 bVII7 I`) and an applied dominant (`A7` = `V7/ii`). Shows off HAMON's multi-modal layering: most target formats carry one analysis or the other; only HAMON and Humdrum keep both, and only HAMON keeps the key with them everywhere. |
| `sat_roman_dcml.hamon` | Roman (`@rn`) | Roman/DCML analysis with a secondary dominant (`V7/V`) and a modulation (`@key:V`). |
| `sat_figured_bass.hamon` | figured bass (`@fb`) | Baroque continuo figures (`6-4`, `5-3`, `7`, `6-5`). |
| `sat_mozart_fb.hamon` | figured bass (`@fb`) | **Real music, not a hand-made snippet** — Mozart K282, 22 labels of continuo figures. The longest example, and the one the other encodings lose the most of. |
| `sat_nashville.hamon` | Nashville (`@ns`) | Nashville number chart with qualities (`6m`, `5sus`). |
| `sat_positions.hamon` | chord symbol (`@cs`) | Time-aligned positions: `m:`/`ts:` against `@meter:4/4`, so the figure asks each target whether it can carry *when* a harmony happens, not just which one. |
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
├── examples/         # the .hamon source examples (+ changes.lab, a Harte file)
├── icccm26/          # the package (roundtrip, figure, snippets, cli)
├── outputs/          # generated report + figures
└── run.py            # thin launcher (no install needed)
```
