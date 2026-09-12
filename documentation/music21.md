# music21 Integration

hamonpy integrates with [music21](https://web.mit.edu/music21/), MIT's Python toolkit for computer-aided musicology. The integration has two layers:

1. **Adapter functions** (`music21_adapter.py`) — convert directly between a `HamonSequence` and a music21 `Stream` of native `ChordSymbol` / `RomanNumeral` / `NoChord` objects.
2. **Native I/O format** (`music21_converter.py`) — register `.hamon` as a music21 format, so `converter.parse(..., format="hamon")` and `stream.write("hamon")` behave like any built-in format.

## Installation

music21 is an optional dependency:

```bash
pip install hamonpy[music21]
```

Or install manually:

```bash
pip install "music21>=9"
```

## Quick start

### music21 → HAMON

```python
import music21.corpus
from hamonpy.adapters.music21_adapter import music21_stream_to_hamon

# Load a score from the music21 corpus
score = music21.corpus.parse("bach/bwv66.6")

# Extract harmony labels
seq = music21_stream_to_hamon(score)
for group in seq.groups:
    label = group.primary[0]
    print(label.surface, "→", label.semantic)
```

### HAMON → music21

```python
from hamonpy.parse import parse_hamon_sequence
from hamonpy.adapters.music21_adapter import hamon_to_music21_stream

seq = parse_hamon_sequence("@cs\nC\nAm\nF\nG7")
part = hamon_to_music21_stream(seq)
part.show()  # or part.write("musicxml", fp="output.xml")
```

### `.hamon` as a native music21 format

Register it once, then use music21's own `converter`:

```python
from hamonpy.adapters.music21_converter import register_hamon_format
register_hamon_format()  # idempotent

from music21 import converter
s = converter.parse("@cs\nC\nF\nG7", format="hamon")   # text → Stream
s = converter.parse("song.hamon")                        # by file extension
s.write("hamon", fp="out.hamon")                         # Stream → .hamon
```

Parsing goes through `hamon_to_music21_stream` (Roman numerals resolve against the sequence's `@key:` regions); writing goes through `music21_stream_to_hamon` + `sequence_to_hamon_text`. To override the emitted `@<system>` hint, pass `sequenceSystemHint="rn"` (or similar) as a keyword to `write`.

### Key context for roman numerals

Roman numerals resolve to concrete pitches against the prevailing key, which HAMON derives from the sequence's analytical `@key:` regions (or a label's `local_key`):

```python
seq = parse_hamon_sequence("@rn\n@key:G\nV7/V\nV")
part = hamon_to_music21_stream(seq)
# V7/V in G → A7 (A C# E G); V → D major (D F# A)
```

Tonicizations live in the roman `secondary` (e.g. `V/V`), not in the prevailing key, so they map onto music21's `secondaryRomanNumeral` figure form.

## API

### `music21_stream_to_hamon(stream, sequence_system_hint="cs") → HamonSequence`

Converts a `music21.stream.Stream` to a `HamonSequence`.

It walks `stream.flatten().getElementsByClass(['ChordSymbol', 'RomanNumeral', 'NoChord'])` and converts each element:

| music21 class | HAMON semantic |
|---|---|
| `harmony.ChordSymbol` | `ChordSymbolSemantic` |
| `roman.RomanNumeral` | `RomanSemantic` |
| `harmony.NoChord` | `NoChordSemantic` |

**Parameters:**
- `stream`: Any `music21.stream.Stream` (Score, Part, flat stream, etc.)
- `sequence_system_hint`: Override the HAMON system hint (`"cs"`, `"rn"`, etc.)

**Returns:** `HamonSequence` with one `HarmonyGroup` per harmony event.

### `hamon_to_music21_stream(seq) → music21.stream.Part`

Converts a `HamonSequence` to a `music21.stream.Part`.

| HAMON semantic | music21 class |
|---|---|
| `ChordSymbolSemantic` | `harmony.ChordSymbol` |
| `RomanSemantic` | `roman.RomanNumeral` |
| `NoChordSemantic` | `harmony.NoChord` |
| `NashvilleSemantic`, `FiguredBassSemantic`, etc. | skipped |

**Time placement.** When the groups carry `HarmonyGroup.position` (schema 0.2.1):

- if every group has a `measure`, elements are inserted into `music21.stream.Measure`
  objects at offset `beat - 1`, so `measureNumber` and `beat` round-trip;
- else if every group has an absolute `time`, elements are inserted at `time × 4`
  quarter-note offsets;
- otherwise elements fall back to sequential offsets (1 quarter note apart).

Going the other way, `music21_stream_to_hamon` reads each element's measure context
back into `position` — `measure` from `measureNumber`, `beat` from the meter or the
measure-relative offset. So a MusicXML → HAMON → music21 → HAMON trip preserves
measure+beat.

Chord symbols export through a music21 **chord figure** built from the semantic fields, which preserves natively: slash bass (`G7/B`), suspensions (`Csus4`), added tones (`Cadd9`), and alterations (`Dm7b5` → lowered fifth, `C7b9`). Roman numerals keep the secondary target (`V/IV`), front alterations (`bVI`), and inversion figures from `tail` (`V65`, `ii43`), and they resolve against the region/`local_key` key when one is available.

### Native I/O format API (`music21_converter.py`)

| Symbol | Description |
|---|---|
| `register_hamon_format()` | Registers the `HamonConverter` SubConverter with music21's global `converter` (idempotent). Returns the converter class. |
| `HamonConverter` | `music21` `SubConverter` subclass: `registerFormats = ("hamon",)`, input/output extension `.hamon`. `parseData` → Stream; `write` → `.hamon` text. |

## Mapping table

### ChordSymbol quality mapping

| HAMON quality + seventh | music21 `chordKind` |
|---|---|
| `major` (no seventh) | `"major"` |
| `minor` (no seventh) | `"minor"` |
| `augmented` | `"augmented"` |
| `diminished` | `"diminished"` |
| `major` + `maj7` | `"major-seventh"` |
| `minor` + `min7` | `"minor-seventh"` |
| `major` + `dom7` | `"dominant"` |
| `diminished` + `dim7` | `"diminished-seventh"` |
| `half-diminished` + `hdim7` | `"half-diminished"` |
| `minor` + `maj7` | `"minor-major-seventh"` |

### Accidental mapping

| HAMON accidental | music21 pitch modifier |
|---|---|
| `flat` | `-` |
| `sharp` | `#` |
| `doubleFlat` | `--` |
| `doubleSharp` | `##` |

## Known limitations

- **Time positions**: now carried via `HarmonyGroup.position` (schema 0.2.1) — see *Time placement* above. Groups without a position fall back to sequential offsets. The measure→beat mapping assumes 1 quarter = 1 beat (it infers no time signature), so compound and irregular meters may not land precisely.
- **`omits`**: the exported chord figure does not yet reflect the `ChordSymbolSemantic.omits` field (it does carry `extensions`, `alterations`, `adds`, `bass`, and `suspensions`).
- **Nashville / functional**: these HAMON semantics have no direct music21 counterpart, so export skips them.
- **Figured bass**: music21 has its own figured-bass notation, but this adapter does not bridge to it, so `FiguredBassSemantic` labels are skipped on export.
