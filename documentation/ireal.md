# iReal Pro Format

iReal Pro is a commercial app that keeps chord charts in a proprietary, URL-encoded format. You share a chart as an `irealb://` URI, and decoding it yields chord symbols in a compact ASCII notation.

## Reference

- iReal Pro app: https://irealpro.com
- Community decoder: https://github.com/pianosnake/ireal-reader
- Format documentation: unofficial, reverse-engineered

## URI Structure

```
irealb://<title>=<composer>=<style>=<key>=<time-sig>=<encoded-chart>=<bpm>
```

Multiple songs are separated by `===`.

The `<encoded-chart>` is first obfuscated with a character-rotation cipher (applied to 50-character substrings), then percent-encoded.

## Chord notation inside a decoded chart

Once decoded, each chord event is a combination of:

- **Root note**: `A`–`G`, optionally followed by `#` or `b`
- **Quality suffix**: standard short notation (see table below)
- **Separator space** between successive chords

### Quality suffixes

| iReal suffix | Meaning | HAMON equivalent |
|---|---|---|
| (none) | Major triad | (no suffix) |
| `-` or `m` | Minor triad | `m` |
| `^7` | Major seventh | `maj7` |
| `7` | Dominant seventh | `7` |
| `-7` or `m7` | Minor seventh | `m7` |
| `^` | Major (alt. glyph) | (no suffix) |
| `dim` or `o` | Diminished | `°` |
| `dim7` or `o7` | Diminished seventh | `°7` |
| `h7` or `ø7` | Half-diminished seventh | `ø7` |
| `aug` or `+` | Augmented | `+` |
| `sus` or `sus4` | Suspended fourth | `sus4` |
| `2` or `sus2` | Suspended second | `sus2` |
| `-^7` or `m^7` | Minor-major seventh | `mmaj7` |
| `add9` | Add ninth | `add9` |
| `6` | Major sixth | `6` |
| `-6` or `m6` | Minor sixth | `m6` |
| `69` | Six-nine | `69` |
| `9` | Dominant ninth | `9` |
| `-9` or `m9` | Minor ninth | `m9` |
| `^9` | Major ninth | `maj9` |
| `13` | Dominant thirteenth | `13` |
| `alt` | Altered dominant | `alt` (tail) |

### Special symbols

| iReal symbol | Meaning |
|---|---|
| `n` or `N` | No chord |
| `W` | Whole rest |
| `p` | Repeat previous bar |
| `x` or `r` | Repeat last two bars |
| `f` | Fermata (ignore) |
| `XyQ` | Start/end repeat markers |

### Slash bass notation

`G/B` means G major over a B bass. The slash and bass note come after the quality suffix.

## Mapping to HAMON

iReal chord symbols map to HAMON `ChordSymbolSemantic`. HAMON pulls out only the harmony content; it does not model repeat signs, fermatas, or bar-structure markers.

| iReal field | HAMON field |
|------------|-------------|
| Root note + accidental | `root` |
| Quality suffix | `quality` + `seventh` + `suspensions` |
| Slash bass | `bass` |
| `n`/`N` | `NoChordSemantic` |

## Known limitations

- The obfuscation cipher runs per 50-character substring; the adapter implements the standard rotation scheme.
- HAMON does not model bar structure (repeat signs, section markers).
- The `alt` (altered dominant) suffix goes into a tail string; HAMON populates no first-class `alteration` fields for it.
- iReal sometimes writes `^7` (the hat glyph) for a major seventh; the adapter normalizes it to `maj7`.
