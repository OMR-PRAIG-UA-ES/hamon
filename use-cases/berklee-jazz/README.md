# Use case — Berklee-style jazz harmonic analysis

**Scenario.** A jazz progression in C major, analysed the Berklee way: chord
symbols with **tensions**, a **related ii–V** borrowed-dominant region, and
**altered dominants**. It stays typed chord data with the functional (applied)
reading made explicit, so the same `.hamon` both renders visually (e.g. via
MuRET-engraving in the MuRET-hamon project) and exchanges with other analysis
tools.

**Input.** [`changes.hamon`](changes.hamon):

```
@version:0.2.0
@key:C
Cmaj7
Eø7[of:ii]
A7b9[of:ii]
Dm7
G7b9b13
Cmaj7
```

Berklee reading, bar by bar:

| Surface | Berklee function | HAMON encoding |
|---------|------------------|----------------|
| `Cmaj7` | I maj7 (tonic) | chord symbol, inside the `@key:C` region |
| `Eø7[of:ii]` | ii⌀7 of ii — the related ii of the secondary dominant | `[of:ii]` → `applied.target = ii` |
| `A7b9[of:ii]` | V7♭9/ii (secondary dominant of ii) | `applied.target = ii` + `alterations=[♭9]` |
| `Dm7` | ii‑7 (target of the V/ii) | chord symbol |
| `G7b9b13` | V7♭9♭13 (altered primary dominant) | `alterations=[♭9, ♭13]` |
| `Cmaj7` | I maj7 (resolution) | chord symbol |

## Run it

```python
from hamonpy.parse import parse_hamon_sequence

seq = parse_hamon_sequence(open("changes.hamon").read())
print("home key:", seq.regions[0].key.tonic.note, seq.regions[0].key.mode)  # C major

for g in seq.groups:
    lbl = g.primary[0]; s = lbl.semantic
    applied = getattr(lbl.attributes, "applied", None) if lbl.attributes else None
    print(lbl.surface, s.seventh, s.alterations, applied and applied.target)
# Cmaj7       maj7  None              None
# Eø7[of:ii]  hdim7 None              ii
# A7b9[of:ii] dom7  [{...,'degree':9}] ii
# Dm7         min7  None              None
# G7b9b13     dom7  [{...9},{...13}]  None
# Cmaj7       maj7  None              None
```

## What you get

- Every change is a `ChordSymbolSemantic` (root, quality, seventh, and
  **alterations** for the upper-structure tensions).
- `@key:C` opens a `TonalRegion` (the home key), so the analysis is *functional*
  rather than just a chord list.
- `[of:ii]` attaches a `HarmonyAttributes.applied` reading to the secondary
  dominant **and its related ii**, marking the borrowed V7/ii region without
  touching the chords themselves. It's the same mechanism as the
  [`jazz-leadsheet`](../jazz-leadsheet/) use case, extended to a full ii–V cell.

## What HAMON captures today vs. what Berklee needs next

Building this showed us where the grammar already speaks "Berklee" and where it
doesn't (findings from `hamonpy` 0.1.0 — roadmap items, **not** used in
`changes.hamon`):

| Berklee construct | Status | Note |
|-------------------|--------|------|
| Tensions stacked (`G7b9b13`, `Cmaj7#11`, `Dm9`, `C13`) | ✅ captured | lifted into `alterations`/`extensions` |
| Tensions in parentheses (`G7(b9,b13)`) | ⚠️ parses | **fixed 2026-06-15**: the comma no longer splits the token and `[of:…]` survives; the paren tensions are preserved in the surface but not yet lifted into `alterations` (use the stacked form for that) |
| Half-diminished as `ø7` + `[of:…]` (`Eø7[of:ii]`) | ✅ | applied function attaches |
| Half-diminished as `m7b5` + `[of:…]` (`Em7b5[of:ii]`) | ✅ | **fixed 2026-06-15** (was dropping `[of:…]`) |
| Secondary dominant `[of:X]` on a natural root | ✅ | `A7[of:ii]`, `G7[of:I]`, `C7[of:IV]` |
| `[of:X]` on a **flat-rooted** / quality-letter chord (`Db7[of:I]`, `Bb7[of:V]`, `Dm7[of:V]`) | ✅ | **fixed 2026-06-15** — see the [jazzmus-berklee-dezrann](../jazzmus-berklee-dezrann/) tritone-sub demo |
| Altered dominant marker (`G7alt`) | ⚠️ partial | accepted, but individual tensions are not enumerated |
| Chord–scale relationships (G7 → altered / Lydian♭7) | ❌ none | no native concept; needs a grammar extension |
| Tritone substitution as a first-class relation (subV7) | ⚠️ workable | now expressed cleanly as the flat-root dominant + `[of:target]` (e.g. `Db7[of:I]`); a dedicated `subV` marker is still future work |

> Remaining backlog for the **MuRET-hamon / Berklee** thread: lift parenthesised
> tensions into `alterations`, enumerate `alt`, and add native **chord-scales** plus
> a first-class **`subV`** relation (grammar/AST additions — the source of truth is
> here → `conformance/run.py`). The flat-root / `m7b5` /
> comma-tension parser bugs were **fixed on 2026-06-15**.

To convert real charts at scale, export iReal Pro playlists and read them with
`hamonpy.adapters.ireal`, or ingest the Jazz Harmony Treebank /
[JAZZMUS](../../datasets/README.md) and Dezrann `.dez` labels — see the note in
[`use-cases/README.md`](../README.md).
