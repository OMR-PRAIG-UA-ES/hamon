# Dezrann (`.dez`) Integration

[Dezrann](https://www.dezrann.net) (Algomus; Foscarin, Giraud, Rigaux et al.) is
an open web platform for browsing annotated music corpora on a single timeline —
it lines up scores, audio, and analytical labels so you can move through them
together. For the details, see the TISMIR paper: *Dezrann: A Web Platform for
Unified Access to Annotated Music Corpora*
(<https://doi.org/10.5334/tismir.212>).

Dezrann is **not** a harmony standard. By design it stays *agnostic* about the
analytical ontology: a label is just a position and a free `tag`. HAMON adds the
normalisation Dezrann leaves out — it parses the harmony tags into the typed AST
and keeps Dezrann's quarter-note anchor as a `HarmonyGroup.position`.

## The `.dez` format

A `.dez` file is JSON: a required `labels` array plus an optional `meta` block.
Every label is anchored on **musical time, measured in quarter notes from the
start of the piece**:

| Field | Required | Description |
|-------|----------|-------------|
| `start` | ✅ | Onset in quarter notes (the only mandatory field) |
| `duration` | | Inter-onset interval, in quarters |
| `type` | | Annotation family (`Harmony`, `Chord`, `Cadence`, `Tonality`, …) |
| `tag` | | Free detail — for harmony labels, the chord/Roman surface |
| `staff`, `comment`, `layers` | | Staff, free commentary, annotation sources |

```json
{
  "labels": [
    { "type": "Harmony", "start": 0, "duration": 4, "tag": "Cmaj7" },
    { "type": "Harmony", "start": 4, "tag": "G7" },
    { "type": "Cadence", "start": 12, "tag": "C:PAC" }
  ],
  "meta": { "producer": "hamonpy" }
}
```

## Mapping to HAMON

| Dezrann | HAMON |
|---------|-------|
| label `tag` (for harmony `type`s) | parsed `HarmonyLabel` (chord symbol, roman, …) |
| label `start` (quarters) | `HarmonyGroup.position.time` (absolute fraction) |
| `type` ∈ {`Harmony`, `Chord`, `Chords`} | included by default (configurable) |
| non-harmony `type`s (`Cadence`, …) | skipped on import |
| unparseable `tag` | `TextSemantic` fallback (lossless) |

## API (`hamonpy.adapters.dezrann`)

```python
from hamonpy.adapters.dezrann import dez_to_hamon, hamon_to_dez

# Dezrann → hamon (system="auto" detects cs/rn/…; pass "rn"/"cs" to force one)
seq = dez_to_hamon(open("piece.dez").read(), system="auto")

# hamon → Dezrann
dez_json = hamon_to_dez(seq, label_type="Harmony")
```

`dez_to_hamon` takes a parsed dict, JSON text, or a `.dez` file path
(`dez_file_to_hamon`). It emits labels in `start` order. On export, `duration`
is the gap to the next group's start, whenever both positions are known.

## CLI

`hamon convert piece.dez` recognises the `.dez` extension and writes canonical
HAMON JSON. See [cli.md](cli.md).

## Limitations

- Only harmony-bearing label types come across; cadence, phrase, and structure
  labels are out of scope, since HAMON has no AST node for them yet.
- HAMON does not redistribute Dezrann corpora. Get them from the platform or
  their authors (see [datasets.md](datasets.md)).
