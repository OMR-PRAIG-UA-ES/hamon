# Use case — JAZZMUS → HAMON (Berklee analysis) → Dezrann

**Scenario.** HAMON as the **interchange / communication medium** for a visual
jazz-harmony workflow (the MuRET-hamon thread). Take a real lead sheet from
**JAZZMUS**, normalise its changes into HAMON, add a **Berklee-style functional
analysis** (secondary dominants, a **tritone substitution**), and ship it to
**Dezrann** as time-aligned labels. The same analysis can then be rendered on
Dezrann's timeline *or* by MuRET-engraving, and exchanged with other tools.

```
JAZZMUS lead sheet (MusicXML / Humdrum **kern + recognised chords)
   │  hamonpy.adapters.humdrum  (the **jazz chord spine)
   ▼
HAMON  — raw changes as typed chord symbols
   │  analyst adds the Berklee layer: @key region, [of:…] applied functions,
   │  subV (tritone sub), and t: time anchors
   ▼
HAMON  — analysis.hamon  (the canonical, exchangeable artifact)
   │  hamonpy.adapters.dezrann.hamon_to_dez
   ▼
Dezrann .dez  — time-aligned labels on the score/audio timeline
                (and/or MuRET-engraving for the rendered analysis)
```

## 1. Ingest the JAZZMUS chart → HAMON

[`chart.krn`](chart.krn) is a tiny **synthetic** Humdrum stand-in for a JAZZMUS
chart. We never bundle the dataset — JAZZMUS is gated, so fetch it via the
[dataset hub](../../datasets/README.md):

```python
from hamonpy.adapters.humdrum import humdrum_file_to_hamon
raw = humdrum_file_to_hamon("chart.krn")
print([g.primary[0].surface for g in raw.groups])
# ['Cmaj7', 'A7', 'Dm7', 'Db7', 'Cmaj7']   ← the **jazz spine, as typed chord symbols
```

## 2. The Berklee analysis, stored in HAMON

[`analysis.hamon`](analysis.hamon) adds the functional reading and time anchors:

```
@version:0.4.0
@key:C
t:0/1,Cmaj7
t:4/1,A7b9[of:ii]
t:8/1,Dm7
t:12/1,Db7[of:I]
t:16/1,Cmaj7
```

- `@key:C` → the home `TonalRegion`.
- `A7b9[of:ii]` → the **V7♭9/ii** secondary dominant (`applied.target = ii`).
- `Db7[of:I]` → **subV7/I**, the **tritone substitution** of G7. The flat-rooted
  dominant now keeps its applied function — see the note below.
- `t:N/1` → an absolute time position (`HarmonyGroup.position.time`); here the
  values are quarter notes from the start, which is the anchor Dezrann needs.

```python
from hamonpy.parse import parse_hamon_sequence
seq = parse_hamon_sequence(open("analysis.hamon").read())
sub = seq.groups[3].primary[0]
print(sub.surface, sub.attributes.applied.target)   # Db7[of:I] I  (tritone sub)
```

## 3. Export to Dezrann

```python
from hamonpy.adapters.dezrann import hamon_to_dez
open("chart.dez", "w").write(hamon_to_dez(seq))
# labels: start=0 "Cmaj7", 4 "A7b9[of:ii]", 8 "Dm7", 12 "Db7[of:I]", 16 "Cmaj7"
```

`dez_to_hamon` reads it back — the `[of:…]` survives in the tag — so the round-trip
HAMON ↔ Dezrann is lossless for the harmony surface.

## Why this matters

This is the concrete demonstration of HAMON as a **neutral hub**: JAZZMUS provides
the real material, HAMON stores the *analysis* (typed, validated against the grammar,
format-agnostic), and Dezrann / MuRET-engraving provide the *visual* layer — none of
them needs to know about the others. The same `analysis.hamon` is what you'd exchange
with collaborators working in the DCML/ms3 ecosystem (see
[`documentation/ms3.md`](../../documentation/ms3.md) and [`dezrann.md`](../../documentation/dezrann.md)).

> **Grammar note (fixed 2026-06-15).** Flat-rooted and quality-letter chords
> (`Db7`, `Bb7`, `Em7b5`, `Dm7`, `Cmaj7`) used to be lexed as a single WORD and
> routed through the text path, which **swallowed a trailing `[of:…]`** — so
> tritone subs and most real jazz chords lost their applied function. The grammar
> now stops a raw run at `[`, and parenthesised tension lists (`A7(b9,b13)`) no
> longer split on the comma. This use case relies on that fix.
