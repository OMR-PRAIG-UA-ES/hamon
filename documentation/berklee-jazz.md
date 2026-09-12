# Berklee-style jazz analysis & the MuRET-hamon pipeline

This page covers two things: how HAMON encodes a **Berklee-method jazz harmonic
analysis**, and how it serves as the **interchange layer** in the *MuRET-hamon*
workflow (produce → store → render visually) without tying itself to any one
renderer.

## Berklee constructs in HAMON

A Berklee reading is a *functional* analysis of chord changes. HAMON represents it
as a chord-symbol (`@cs`) sequence inside a key region, carrying applied functions
and tensions:

| Berklee concept | HAMON surface | Captured as |
|-----------------|---------------|-------------|
| Key / tonal center | `@key:C` | `TonalRegion` (home key) |
| Diatonic seventh chords | `Cmaj7`, `Dm7`, `Em7`, `Fmaj7`, `G7`, `Am7`, `Bø7` | `ChordSymbolSemantic` |
| Tensions | `Cmaj7#11`, `Dm9`, `G13`, `G7b9b13` | `extensions` / `alterations` |
| Secondary dominant (V7/x) | `A7[of:ii]`, `D7[of:V]` | `HarmonyAttributes.applied.target` |
| Related ii of a V7/x | `Eø7[of:ii]` | `applied.target` |
| **Tritone substitution (subV7/x)** | `Db7[of:I]`, `Ab7[of:V]` | flat-root dominant + `applied.target` |
| Chord-scale (per chord) | `G7[scale:altered]`, `Dm7[scale:dorian]` | `HarmonyAttributes.scales` |
| Chord-scales (per region) | `@scale:dorian,mixolydian` | `TonalRegion.scales` |
| Time position (for sync/render) | `t:12/1` | `HarmonyGroup.position.time` (quarters) |

> A grammar fix on 2026-06-15 enabled the flat-root / quality-letter `[of:…]` cases
> (`Db7[of:I]`, `Dm7[of:V]`, `Em7b5[of:ii]`) and parenthesised tension lists
> (`A7(b9,b13)`) — see [`analysis.md`](analysis.md) (§4) and the CHANGELOG. Since
> v0.3.0 the parenthesised tensions are also **lifted into the semantic**
> (`alterations` / `extensions`), so `G7(b9,b13)` and the stacked `G7b9b13` normalize
> to the same thing. **Chord-scales** (per chord and per region) arrived in v0.3.0 —
> see [`analysis.md` §11](analysis.md). **Still missing:** a first-class `subV`
> marker; for now subV is just the flat-root dominant plus `[of:target]`.

## The MuRET-hamon pipeline — HAMON as the communication medium

```
JAZZMUS lead sheet (MusicXML / Humdrum **kern + recognised chords)
   │  hamonpy.adapters.humdrum (the **jazz chord spine)  ·  or hamonpy.adapters.formats extractors
   ▼
HAMON  — raw changes (typed chord symbols)
   │  analyst adds the Berklee layer (@key, [of:…], subV, t: anchors)
   ▼
HAMON  — the canonical, exchangeable analysis (.hamon / .hamon.json)
   ├──►  MuRET-engraving        — renders the analysed score (the visual layer)
   ├──►  Dezrann (.dez)         — time-aligned labels on the score/audio timeline
   └──►  ms3 / DCML ecosystem   — exchange with Roman-numeral corpora & tooling
```

- **MuRET-hamon** (app, `OMR-PRAIG-UA-ES/MuRET-hamon`) drives the pipeline: it runs
  the Berklee analysis on the HAMON model, renders with
  **MuRET-engraving**, and saves `.hamon.json`. HAMON stays *render-agnostic* — the
  analysis artifact is the contract, and MuRET-engraving and Dezrann are
  interchangeable visual consumers of it.
- The two runnable recipes in this repo are the reference point:
  [`use-cases/berklee-jazz/`](../use-cases/berklee-jazz/) (the encoding/concept demo,
  with a "what HAMON captures vs. needs" table) and
  [`use-cases/jazzmus-berklee-dezrann/`](../use-cases/jazzmus-berklee-dezrann/) (the
  full JAZZMUS → HAMON → Dezrann pipeline).
- Related interchange targets: [`dezrann.md`](dezrann.md), [`ms3.md`](ms3.md),
  [`humdrum.md`](humdrum.md), [`music21.md`](music21.md).

## Where things live

| Artifact | Path |
|----------|------|
| Concept use case (encoding + gap table) | `use-cases/berklee-jazz/` |
| Pipeline use case (JAZZMUS→HAMON→Dezrann) | `use-cases/jazzmus-berklee-dezrann/` |
| Applied-function / `[of:…]` spec + the fix note | `documentation/analysis.md` |
| Dezrann `.dez` adapter | `hamonpy/hamonpy/adapters/dezrann.py` · `documentation/dezrann.md` |
| Grammar (source of truth) | `grammar/hamon.ebnf` · `antlr/hamonParser.g4` |
| Conformance corpus (Python golden) | `conformance/` |
