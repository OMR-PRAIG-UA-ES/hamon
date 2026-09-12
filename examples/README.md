# Examples — try the `hamon` CLI

Four tiny, self-contained files so you can run every `hamon` command without hunting
for input. Install `hamonpy` first (`pip install ./hamonpy` from the repo root), then
run the commands below from **this directory**.

| File | Format | Used by |
|------|--------|---------|
| [`changes.tsv`](changes.tsv)   | DCML harmony TSV (a ii–V–I with a tonicized V) | `convert` |
| [`song.mei`](song.mei)         | MEI with `<harm>` chord symbols + beat positions | `export`, `report` |
| [`corpus.hamon`](corpus.hamon) | HAMON surface — **with two deliberate flaws** | `validate` |

## `convert` — any format → canonical HAMON JSON

```bash
hamon convert changes.tsv
```

Auto-detects DCML from the `.tsv` header and prints the canonical JSON. Each chord
becomes a Roman-numeral group; `V7/V` keeps its secondary-dominant structure.

## `export` — HAMON → another format

```bash
hamon export song.mei --to harte
```

Reads the `<harm>` labels out of the MEI and re-emits them as Harte chord labels:

```
C:min7
F:7
Bb:maj7
Eb:maj7
A:min7
```

(`--to` accepts `harte`, `dcml`, `romantext`, `humdrum`, `lilypond`, `abc`,
`musescore`, `musicxml`, `mei`, `dezrann`, `jams`, `ireal`, `hamon`.)

## `report` — export **and** report what was lost

```bash
hamon report song.mei --to harte
```

Harte can't carry beat positions, and it flattens `Am7b5` to `A:min7` — so the report
flags the dropped `position`s and the dropped `b5` alteration:

```
Source: song.mei (format=mei)
Target format: harte
  source groups: 5
  ⚠ semantic loss: 7 field(s)
      [dropped] groups[0].position: {measure=1, beat=1.0}
      ...
      [dropped] groups[4].primary[0].semantic.alterations[0]: b5
  · notational re-spelling: 16 field(s) (expected — glyphs/surface differ across formats)
```

## `validate` — corpus QA

```bash
hamon validate corpus.hamon --strict
```

`corpus.hamon` hides two mistakes on purpose so you can see the checks fire:

- `m:3,ts:5` — beat 5 doesn't exist in `4/4` (a **position** warning)
- `?tacet` — an **opaque** label the parser couldn't read as harmony

```
  opaque (text) label at group 5: '?tacet'
  position: group 4 (m:3,ts:5.0) is outside meter 4/4 — ts must be in [1, 5)
1 opaque label(s), 1 position warning(s).
```

`--strict` exits non-zero when anything is flagged, so it works as a CI gate over a
harmony corpus. Fix the two lines and it exits clean.
