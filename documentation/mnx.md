# MNX — Harmony Encoding

## Overview

[MNX](https://w3c.github.io/mnx/) (Music Notation XML) is a W3C Community Group draft aimed at eventually succeeding MusicXML. Despite the name, its primary serialization is JSON, not XML. As of 2025 the spec is still under active development, and no production software implements it in full.

We document MNX here for completeness — it is a format HAMON may need to support down the line. There are no HAMON fixtures or adapters for it yet.

---

## Harmony in MNX

The MNX draft puts a `harmony` object inside measure content. It defines a structured semantic model much like MusicXML's, but it also adds provisions for Roman numeral analysis and figured bass that MusicXML has no native support for.

### Chord symbol (draft schema)

```json
{
  "type": "harmony",
  "value": {
    "root": { "step": "C", "alter": -1 },
    "kind": { "value": "minor-seventh" },
    "display": "Cm7"
  }
}
```

Key fields:
- `root.step` — pitch class (`A`–`G`)
- `root.alter` — semitone alteration (-1 = flat, 1 = sharp)
- `kind.value` — semantic keyword (reuses MusicXML's vocabulary)
- `display` — the string to render (equivalent to MusicXML's `text` attribute)
- `bass` — optional slash bass, same structure as `root`

### Roman numeral analysis (draft)

The MNX draft has a separate `roman-numeral` harmony type:

```json
{
  "type": "harmony",
  "value": {
    "roman-numeral": {
      "degree": "V",
      "alter": 0,
      "mode": "major",
      "quality": "dominant-seventh"
    }
  }
}
```

This is richer than anything in the formats HAMON supports today, and it maps to HAMON's `roman` kind more cleanly than MusicXML does.

---

## Mapping: HAMON grammar → MNX (draft)

| HAMON concept | MNX field |
|---|---|
| Root note | `root.step` |
| Accidental | `root.alter` |
| Quality (semantic) | `kind.value` |
| Display surface | `display` |
| Slash bass | `bass.step` + `bass.alter` |
| Roman numeral | `roman-numeral.degree` + `roman-numeral.quality` |
| Figured bass | not yet defined in draft |
| Nashville | not yet defined in draft |
| Functional | not yet defined in draft |

---

## Status in HAMON

- **No adapter**: `hamonpy/` has no MNX support yet.
- **No fixtures**: there are no `.mnx` snippets in `fixtures/`.

Once the MNX spec stabilizes and software starts producing MNX files, HAMON will add an adapter. The `display` field lines up directly with HAMON's surface-first model, so chord symbols should slot in easily, and the structured `roman-numeral` type will make Roman numeral support straightforward.

---

## References

- MNX specification draft: https://w3c.github.io/mnx/
- MNX discussion and examples: https://github.com/w3c/mnx
