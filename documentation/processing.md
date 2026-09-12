# Processing harmony, format by format (CLI & Python)

A practical cookbook: for each thing you'd want to do with a harmony file — read it,
re-emit it in another format, measure what a conversion loses, or QA a corpus — here is
the `hamon` command and the equivalent `hamonpy` Python.

Every snippet uses the ready-to-run inputs in [`../examples/`](../examples/). Install
first (`pip install ./hamonpy`, or `-e ./hamonpy[dev]` for development); that puts the
`hamon` command on your path.

The format *semantics* — what each encoding can carry and where it loses information —
live in the per-format pages under [`index.md`](index.md) (MEI, MusicXML, Humdrum,
Harte, DCML, …). This page is only about *running* the conversions.

## What you can read and write

**Read (import).** The format is auto-detected from the file extension, with a content
sniff as a fallback. Override it with `--format` (CLI) or the `fmt` argument (Python).

| Extension | Default format |
|---|---|
| `.hamon` | `hamon` (the surface syntax) |
| `.mei` | `mei` |
| `.xml` / `.mxl` | `musicxml` (or `mei` by content) |
| `.krn` | `humdrum` (`**text`/`KEY=>:` → `key_modulation`) |
| `.tsv` | `dcml` (`quarterbeats` → `dcml_expanded`; note-level pitch arrays → `dilemma`) |
| `.rntxt` | `romantext` |
| `.lab` | `harte` |
| `.abc` | `abc` |
| `.ly` | `lilypond` |
| `.mscx` / `.mscz` | `musescore` |
| `.json` | `treebank`, `kp`, `rock_corpus`, `bps_fh`, `dezrann`, `jams` (by content) |

Full `--format` list: `abc`, `bps_fh`, `choro`, `dcml`, `dcml_expanded`, `dezrann`,
`dilemma`, `hamon`, `harm`, `harte`, `humdrum`, `ireal`, `jams`, `key_modulation`, `kp`,
`lilypond`, `mei`, `musescore`, `musicxml`, `rock_corpus`, `romantext`, `treebank`.

**Write (export).** Any of these `--to` targets: `abc`, `dcml`, `dezrann`, `hamon`,
`harte`, `humdrum`, `ireal`, `jams`, `lilypond`, `mei`, `musescore`, `musicxml`,
`romantext`. (Research corpora — `treebank`, `kp`, `rock_corpus`, `bps_fh`, `dilemma` —
are import-only.)

## 1. Read any format → canonical HAMON JSON

**CLI**

```bash
hamon convert examples/song.mei                 # auto-detect, JSON to stdout
hamon convert examples/changes.tsv -o out.json  # write to a file
hamon convert chart.txt --format ireal          # force the input format
```

**Python**

```python
from pathlib import Path
from hamonpy.cli import convert_file, convert_text
from hamonpy.serialize import sequence_to_json, sequence_to_hamon_text

seq = convert_file(Path("examples/song.mei"))          # auto-detect
seq = convert_file(Path("chart.txt"), "ireal")         # force the format
seq = convert_text("@cs\nCmaj7\nAm7\nDm7\nG7", "hamon")  # from a string (fmt required)

print(sequence_to_json(seq))         # the canonical JSON
print(sequence_to_hamon_text(seq))   # back to the surface (round-trips)
```

`convert_file`/`convert_text` return a `HamonSequence` — the in-memory canonical model
that every other operation below takes as input.

## 2. Export → another format (any → any)

`export` reads **any** supported input and writes **any** target format. There is no
fixed source/target pairing: the input is parsed into the canonical HAMON model and the
target is generated from it, so **X → HAMON → Y** works for every X you can read and
every Y you can write. Harte → LilyPond, DCML → RomanText, MEI → Humdrum — all the same
command.

**CLI**

```bash
hamon export examples/song.mei --to harte         # MEI <harm> → Harte labels
hamon export examples/changes.tsv --to romantext  # DCML TSV → RomanText
hamon export examples/song.mei --to lilypond -o out.ly
```

The HAMON JSON is always the intermediate. To keep it, and to see what the target
couldn't carry, in the same run:

```bash
hamon export examples/song.mei --to harte --save-hamon mid.json --report
```

`--save-hamon` writes the intermediate canonical JSON; `--report` prints the semantic
loss to stderr. If the target can't represent the source's harmony system at all (e.g.
Roman numerals → Harte), the output is empty and a note explains why.

**Python** — `transcode` does the whole X → HAMON → Y in one call, always producing the
intermediate JSON and measuring the loss:

```python
from hamonpy.cli import transcode

tc = transcode("examples/song.mei", "harte")   # any input path → any WRITERS target
print(tc.output)          # the target-format text
print(tc.hamon_json)      # the intermediate canonical HAMON JSON (always produced)
tc.source_format          # 'mei' (what was detected)
semantic = [f for f in tc.report.findings if not f.notational]   # what Harte dropped
```

Or compose the primitives yourself — `write_to(convert_file(path), target)`:

```python
from pathlib import Path
from hamonpy.cli import convert_file
from hamonpy.report import write_to, WRITERS

text = write_to(convert_file(Path("examples/song.mei")), "harte")  # target ∈ WRITERS
Path("out.ly").write_text(write_to(convert_file(Path("examples/changes.tsv")), "lilypond"),
                          encoding="utf-8")
```

Because no two formats carry the same information, a conversion can drop what the target
can't represent — `transcode`/`--report` (and `report`, next) show exactly what.

## 3. Report the loss of a conversion

Runs the export and diffs the result back against the source, splitting **semantic
loss** (dropped/changed meaning) from **notational re-spelling** (glyphs that differ
but mean the same).

**CLI**

```bash
hamon report examples/song.mei --to harte                 # human-readable summary
hamon report examples/song.mei --to harte --json          # structured
hamon report examples/song.mei --to mei --write-output out.mei
```

**Python**

```python
from hamonpy.report import lossy_report

rep = lossy_report(seq, "harte")
semantic   = [f for f in rep.findings if not f.notational]  # real loss
respelling = [f for f in rep.findings if f.notational]      # same meaning, other glyphs
lossless   = not semantic

print(f"{rep.target}: {len(semantic)} lost, {len(respelling)} respelled")
print(rep.output_text)                     # the exported text
for f in semantic:
    print(f"  [{f.kind}] {f.path}: {f.summary}")   # kind ∈ {dropped, changed, added}
```

For `examples/song.mei --to harte` this reports 7 semantic losses (the beat positions,
and the `b5` of `Am7b5` that Harte flattens to `A:min7`) and 16 re-spellings.

## 4. Validate a corpus

Flags **opaque labels** (a surface the parser couldn't read as harmony, so its kind
stayed `text`) and **position warnings** (a `ts:` beat outside the `@meter`). With
`--strict` it exits non-zero when anything is flagged — a CI gate over a corpus.

**CLI**

```bash
hamon validate examples/corpus.hamon --strict
hamon validate corpus/*.hamon --json        # many files at once
```

**Python**

```python
from hamonpy.cli import convert_file
from hamonpy.validate import validate_positions

seq = convert_file(Path("examples/corpus.hamon"))
position_warnings = validate_positions(seq)
opaque = [lab.surface
          for g in seq.groups for lab in g.primary
          if lab.semantic.kind == "text"]
```

## Format-specific behaviour

The command is the same for every format; what changes is *what survives the trip*.
Each per-format page documents its mapping, its native capability, and its losses:

[MEI](mei.md) · [MusicXML](musicxml.md) · [Humdrum](humdrum.md) ·
[LilyPond](lilypond.md) · [ABC](abc.md) · [MuseScore](musescore.md) ·
[Harte](harte.md) · [DCML](dcml.md) · [RomanText](romantext.md) ·
[Dezrann](dezrann.md) · [iReal Pro](ireal.md) · [JAMS](jams.md)

## Python API, at a glance

| Function | Import from | Does |
|---|---|---|
| `convert_file(path, fmt=None)` | `hamonpy.cli` | file → `HamonSequence` (auto-detect unless `fmt`) |
| `convert_text(text, fmt)` | `hamonpy.cli` | string → `HamonSequence` (`fmt` required) |
| `transcode(path, to, input_format=None)` | `hamonpy.cli` | any → any → `Transcode` (`.output`, `.hamon_json`, `.report`) |
| `detect_file_format(path)` | `hamonpy.cli` | the format that auto-detection would pick |
| `sequence_to_json(seq)` | `hamonpy.serialize` | `HamonSequence` → canonical JSON |
| `sequence_to_hamon_text(seq)` | `hamonpy.serialize` | `HamonSequence` → surface string |
| `write_to(seq, target)` | `hamonpy.report` | `HamonSequence` → text in a `WRITERS` format |
| `lossy_report(seq, target)` | `hamonpy.report` | export + diff → `LossyReport` |
| `validate_positions(seq)` | `hamonpy.validate` | list of out-of-meter position warnings |

See [`cli.md`](cli.md) for the full command reference.
