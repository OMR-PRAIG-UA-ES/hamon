# Command-line interface (`hamon` / `python -m hamonpy`)

The hub, as a command-line tool: convert any supported harmony file into the
canonical HAMON JSON (`grammar/hamon-schema.json`), and inspect the dataset registry.

Once you've run `pip install -e ./hamonpy`, the `hamon` command is on your path;
`python -m hamonpy` does the same thing.

## `convert`

```bash
hamon convert <file> [--format F] [-o out.json] [--indent N]
```

This auto-detects the input format and writes the canonical JSON to stdout (or to `-o`):

```bash
hamon convert harmonies.tsv                 # DCML TSV → JSON with tonal regions
hamon convert analysis.txt                  # RomanText (When in Rome)
hamon convert snippet.krn                   # Humdrum (incl. key_modulation **text/=>)
hamon convert treebank.json                 # Jazz Harmony Treebank
hamon convert analysis.mei                  # MEI / HA-MEI (regions + tones)
hamon convert chart.txt --format ireal      # force a format
```

Detection goes by extension (`.hamon`, `.tsv`, `.rntxt`, `.krn`, `.json`, `.mei`,
`.xml`, `.lab`, `.abc`, `.ly`, `.mscx`, `.dez`, `.jams`, `.hrm`, `.har`, `.xlsx`),
falling back to a content sniff. To override it, pass `--format` — the 22 input formats
are `hamon`, `dcml`, `dcml_expanded`, `dilemma`, `romantext`, `treebank`, `humdrum`,
`key_modulation`, `mei`, `harte`, `ireal`, `dezrann`, `jams`, `musicxml`, `abc`,
`lilypond`, `musescore`, `bps_fh`, `harm`, `rock_corpus`, `kp`, `choro`.

Two extensions carry more than one format, so the sniff decides: for `.krn`, the DDMAL
`**text`/`KEY=>:` encoding is `key_modulation` and standard `**harm`/`**function`/`**fb`
spines are `humdrum`; for `.tsv`, a `quarterbeats` column means `dcml_expanded`, a
note-level pitch array means `dilemma`, and anything else `dcml`.

`hamonpy.serialize.sequence_to_json` produces the JSON. It has the same
canonical, camelCase shape as `grammar/hamon-schema.json` (and the TS AST).

> Ready-to-run inputs for every command below live in
> [`examples/`](../examples/) (`examples/README.md` walks through each one).

## `export` — any format → any format

```bash
hamon export <file> --to TARGET [--format F] [-o out] [--save-hamon PATH] [--report]
```

Reads harmony from **any** supported input (same auto-detection as `convert`) and
writes **any** target format. There is no fixed pairing: the input is parsed into the
canonical HAMON model and the target is generated from it, so **X → HAMON → Y** works
for every readable X and writable Y. Writes to stdout, or to `-o`.

```bash
hamon export song.mei --to harte          # MEI <harm> → Harte chord labels
hamon export changes.tsv --to romantext   # DCML TSV → RomanText
hamon export chart.txt --format ireal --to mei   # iReal → MEI (force the input format)
```

`--to` accepts: `abc`, `dcml`, `dezrann`, `hamon`, `harte`, `humdrum`, `ireal`,
`jams`, `lilypond`, `mei`, `musescore`, `musicxml`, `romantext`.

The HAMON JSON is always the intermediate. Two options capture it and the loss in the
same run — because no two formats carry the same information, a conversion can drop what
the target can't represent:

- `--save-hamon PATH` — also write the intermediate canonical HAMON JSON.
- `--report` — also print, to stderr, **what the target could not carry** (the same
  semantic-loss summary as the `report` command below).

```bash
hamon export song.mei --to harte --save-hamon mid.json --report
```

If the target can't represent the source's harmony system at all (e.g. Roman numerals
→ Harte), the output is empty and a note on stderr explains why.

## `report`

```bash
hamon report <file> --to TARGET [--format F] [--write-output out] [--json]
```

Runs the same export, then **diffs the result back against the source** and reports
every semantic difference — what was dropped, what changed, and the merely notational
re-spellings (glyphs that differ across formats but mean the same thing). It writes a
human-readable summary by default; `--json` emits the structured report, and
`--write-output` also saves the exported text.

```bash
hamon report song.mei --to harte
```

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

Harte can't carry beat positions and flattens `Am7b5` to `A:min7`, so the report flags
the dropped positions and the lost `b5`.

A round-trip can also **gain** something the source never said — a default the writer
supplies, a version the reader stamps (`mei` does), a group the format pads out. Those are
reported apart, under `+ invented by the target`, because nothing was lost:

```
Target format: mei
  source groups: 3
  ✓ no semantic loss on round-trip
  + invented by the target: 1 field(s) (in the output, never said by the source)
      [added] version: 0.2.0
```

So `lossless` still means **nothing was lost** and is unaffected by an addition; `faithful`
is the stricter question — lossless *and* nothing invented. The `--json` form has both
booleans, `semanticLoss[]` and `invented[]` (each entry with `path` / `kind` / `summary` /
`source` / `output`), plus `target`, `sourceGroups`, and `error`.

## `validate`

```bash
hamon validate <file>... [--format F] [--strict] [--json]
```

Parses one or more files and reports two classes of corpus problem: **opaque labels**
(a surface the parser couldn't read as harmony, so its semantic kind stayed `text` —
e.g. a `?…` fallback) and **position warnings** (a group's `ts:` beat that falls
outside the meter declared with `@meter`). It never blocks parsing on its own; with
`--strict` it **exits 1** when anything is flagged, so it works as a CI gate over a
harmony corpus.

```bash
hamon validate corpus.hamon --strict
```

```
Source: corpus.hamon (format=hamon)
Groups: 6, labels: 6
Kinds: chordSymbol 5, text 1
  opaque (text) label at group 5: '?tacet'
  position: group 4 (m:3,ts:5.0) is outside meter 4/4 — ts must be in [1, 5)
1 opaque label(s), 1 position warning(s).
```

Pass several files at once (`hamon validate corpus/*.hamon --strict`) to QA a whole
corpus. `--json` emits one report per file with `groups`, `labels`, `kinds`,
`opaqueLabels[]`, and `positionWarnings[]`.

## `datasets`

```bash
hamon datasets list                 # registered dataset names
hamon datasets info when-in-rome    # authors / homepage / license / citation / adapter
hamon datasets path when-in-rome    # local path of an already-downloaded dataset
```

`datasets path` reads the companion downloader's manifest through
`MUSIC_DATASETS_MANIFEST` / `MUSIC_DATASETS_ROOT` (see
[`datasets.md`](datasets.md)) and prints the on-disk path. For example:

```bash
export MUSIC_DATASETS_MANIFEST=/data/music-corpora/music_datasets_manifest.json
hamon convert "$(hamon datasets path when-in-rome)/Corpus/.../analysis.txt"
```

## Library equivalent

```python
from hamonpy.cli import convert_file
from hamonpy.serialize import sequence_to_json

seq = convert_file("harmonies.tsv")     # auto-detect
print(sequence_to_json(seq))
```
