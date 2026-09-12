# Regex-based extractors

Three notation formats — **LilyPond**, **ABC notation**, and **MuseScore MSCX** — carry harmony as free-form text with no structured harmony model to read from, so hamonpy pulls harmony labels out of them with lightweight regular-expression extractors.

This page walks through the extraction strategy for each one. For the full format specs, follow the individual format pages linked below.

---

## LilyPond (`.ly`)

See [`lilypond.md`](lilypond.md) for the full format spec.

**Extraction strategy (two-pass):**

1. **`% hamon-surface:` comments** — explicit HAMON labels that the author writes as comment annotations in the LilyPond source. Each line matching `% hamon-surface: <label>` yields one label. This is the preferred, lossless path.

2. **`\chordmode { ... }` bodies** — when there are no explicit comments, the extractor parses the chord tokens inside `\chordmode` blocks. Dutch pitch names (`cis`, `es`, `b`) become English accidentals (`C#`, `Eb`, `B`), and LilyPond quality modifiers (`:m`, `:7`, `:maj7`) map to HAMON suffixes.

**Regex (hamonpy `_extract_lilypond`):**
```python
r"^\s*%\s*hamon-surface\s*:\s*(.+)$"    # explicit comment
r"\\chordmode\s*\{([\s\S]*?)\}"          # chordmode body
```

---

## ABC notation (`.abc`)

See [`abc.md`](abc.md) for the full format spec.

**Extraction strategy:** ABC stores chord symbols as inline annotations, wrapped in double quotes right in the melody line:

```abc
"C"C2 "G7"GGG | "Am"A2 "F"F2 |
```

The extractor collects every `"..."` quoted string in the file. It does no structural parsing — anything in quotes is treated as a potential chord label and handed to the HAMON parser.

**Regex (hamonpy `_extract_abc`):**
```python
r'"([^"]+)"'
```

**Note:** ABC files can also carry lyrics in quotes. Those usually fail to parse as chord symbols and end up classified as `TextSemantic`. That's by design: the extractor returns everything and lets the parser decide what is actually a chord.

---

## MuseScore MSCX (`.mscx`)

See [`musescore.md`](musescore.md) for the full format spec.

**Extraction strategy:** MuseScore's uncompressed XML keeps harmony labels inside `<Harmony>` elements. The label text lives in a `<text>` child (MuseScore 3/4) or a `<name>` element (older versions):

```xml
<Harmony>
  <root>14</root>
  <text>Cmaj7</text>
</Harmony>
```

The extractor matches both forms.

**Regex (hamonpy `_extract_musescore`):**
```python
r"<Harmony\b[^>]*>[\s\S]*?<text>\s*([^<]+?)\s*</text>[\s\S]*?</Harmony>"
r"<Harmony\b[^>]*>[\s\S]*?<name>\s*([^<]+?)\s*</name>[\s\S]*?</Harmony>"
```

---

## Comparison

| Format | Extraction basis | Lossless? | Structured? |
|---|---|---|---|
| LilyPond (comment) | `% hamon-surface:` annotations | ✅ yes | ✅ explicit |
| LilyPond (`\chordmode`) | Dutch pitch name parsing | mostly | partial |
| ABC | Quoted strings | ✅ yes | no (text only) |
| MuseScore MSCX | `<Harmony><text>` XML | ✅ yes | partial |

All three extractors hand back a list of surface strings. The HAMON ANTLR parser and normalizer take it from there, so any label that survives extraction ends up fully normalized into a typed `HarmonySemantic`.
