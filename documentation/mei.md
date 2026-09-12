# MEI — Harmony Encoding

## Overview

[MEI (Music Encoding Initiative)](https://music-encoding.org/) is the XML format the scholarly music-encoding world reaches for. It's an established fixture in digital musicology, and it's the format HAMON's MEI customization and Verovio integration target first.

MEI puts harmony in the `MEI.harmony` module, which gives you:

- `<harm>` — the main element for any written harmony label (chord symbols, Roman numerals, figured bass, Nashville, functional)
- `<fb>` + `<f>` — structured figured bass notation
- `<chordDef>` / `<chordTable>` — chord definition library (less commonly used for exchange)

---

## What MEI carries natively, and what it only holds as text

`<harm>` accepts arbitrary character data. That makes it a convenient home for a HAMON
label — and it is why, until 2026-09-03, the loss matrix reported MEI as **lossless for
chord-scales MEI cannot express**: the exporter wrote `<harm>Cmaj7[scale:ionian]</harm>`
and the importer read it straight back. The round-trip was measuring our own string.

HAMON now counts that as a **workaround**, not a capability:

| Aspect | In MEI | Counted as |
|---|---|---|
| chord symbols | `<harm>` + `<chordDef>`/`<chordMember>` | **native** |
| figured bass | `<harm>` + `<fb>`/`<f>` | **native** |
| Roman numerals | `<harm>` character data | text — *loss* |
| applied / secondary | `<harm>` character data | text — *loss* |
| key / tonal region | `<harm>` character data | text — *loss* |

The distinction is not pedantry: an analysis parked in `<harm>` text is unreadable to any
MEI tool that is not HAMON, which is precisely what an interchange standard must not
depend on. Shipping such a file is fine — carrying the surface out of band is a real,
useful thing to do — but it is not MEI encoding the analysis.

**This is the gap the planned MEI proposal closes** (see `STATUS.md` → "New MEI harmony
encoding"): give MEI a semantic vocabulary for Roman numerals, applied chords and tonal
regions, rather than leaning on `<harm>` text forever. `hamonpy/capability.py` is what
will score the proposal — each aspect that becomes structural moves from
`TEXT_CAPABILITY` to `SEMANTIC_CAPABILITY`, and MEI's column in the loss matrix drops.


## The `<harm>` element

`<harm>` is where harmony information lives. It sits inside `<measure>` (or `<section>`) as a sibling of the `<staff>` elements, anchored either to a time position or to a specific note.

### Minimal form

At its simplest, a `<harm>` just holds a text label:

```xml
<harm>CΔ7</harm>
<harm>V7</harm>
<harm>6-5</harm>
```

This is the form the HAMON fixture snippets use, and HAMON's grammar parses the text content directly.

### Time anchoring

You can anchor a `<harm>` two ways.

**By timestamp** (`@tstamp`) — beats counted from the start of the measure, 1-based:

```xml
<harm tstamp="1" place="above">CΔ7</harm>
<harm tstamp="3" place="above">G7</harm>
```

**By note reference** (`@startid`) — pointing at a note's `@xml:id`:

```xml
<note xml:id="n1" pname="c" oct="4" dur="4"/>
<harm startid="#n1" place="above">CΔ7</harm>
```

Reach for `@startid` when you want analytical precision; `@tstamp` travels better when note IDs aren't stable.

### The `type` attribute (HAMON convention)

In the HAMON fixture corpus, chord symbols carry `type="chordSymbol"` so the notation system is stated outright:

```xml
<harm type="chordSymbol">CΔ7</harm>
<harm type="chordSymbol">Am7</harm>
```

Other labels — Roman numerals, Nashville, figured bass in text form — leave `type` off, and HAMON infers the system from the grammar.

---

## The HAMON MEI customization

The HAMON ODD (`mei-customization/hamon.odd`) adds structured semantic attributes to the standard `<harm>` element — the same information MusicXML puts in `<root>`, `<kind>`, and `<bass>`:

```xml
<harm startid="#n1"
      root.pname="c"
      root.accid="s"
      bass.pname="g"
      chord.kind="major-seventh">
  C♯maj7/G
</harm>
```

| Attribute | Description | Values |
|---|---|---|
| `root.pname` | Root pitch class | `a`–`g` |
| `root.accid` | Root accidental | MEI accidental tokens: `s`=sharp, `f`=flat, `n`=natural, `ss`=double-sharp, `ff`=double-flat |
| `bass.pname` | Slash-bass pitch class | `a`–`g` |
| `bass.accid` | Slash-bass accidental | same as `root.accid` |
| `chord.kind` | Semantic chord quality | MusicXML kind vocabulary: `major`, `minor`, `major-seventh`, `dominant`, etc. |

The text content always sits alongside the structured attributes and keeps the display surface intact, so the file works both for a human reader and for a parser that only reads text content.

There are two ODD variants:

| File | Purpose |
|---|---|
| `mei-customization/hamon.odd` | Full HAMON MEI customization (all MEI modules) |
| `mei-customization/mei-verovio-hamon.xml.odd` | Verovio-compatible subset — uses only modules Verovio supports |

For validation, there's a compiled RelaxNG schema at `mei-customization/examples/hamon.odd.rng`.

---

## Analytical layer (HA-MEI, v0.2.0)

MEI has no native element for tonal regions or non-harmonic tones, so HAMON
carries the analytical layer on `<harm>` through the `@type` token instead (a
`hamon:` prefix is allowed and ignored). The adapter
`hamonpy.adapters.mei.mei_to_hamon(text)` reads these in document order and
builds a `HamonSequence` with `regions`, `HarmonyLabel.layer`, and
`ToneSemantic`.

> **`@type` is a token set (MEI NMTOKENS).** Alongside the analytical/region
> tokens below, a `<harm>` may also carry a **harmony-layer provenance token** —
> `omr` (OMR-detected) or `score` (written). The two coexist happily (e.g.
> `type="omr function"`): a reader takes the tokens it understands and ignores the
> rest. hamonpy keeps the analytical/region token and ignores `omr`/`score`.

| `<harm type="…">` | Maps to |
|---|---|
| `key` / `region` / `modulation` | a `TonalRegion` (content = a key: `C`, `A:minor`, `D:dorian`; bare lowercase `a` ⇒ A minor). The first key region is `key`, later ones `modulation`. |
| `tonicization` | a nested `TonalRegion` (content = a degree like `V`, `bVI`; local tonic computed from the current key, `parent` set). |
| `function` / `degree` / `bass` / `chord` | a label on that analytical `layer`. |
| `tone` / `melodic` | a `ToneSemantic` on the `melodic` layer (content = a pitch + class, e.g. `F[NHT:passing]`, `C[HT]`). |
| *(absent / other)* | a plain harmony label (chord symbol, Roman numeral, …). |

### Time-aligned positions (schema 0.2.1)

`mei_to_hamon` also folds each `<harm>`'s time anchoring into the group's optional
`position` (`grammar/hamon-schema.json` ≥ 0.2.1):

- `@startid` ⇒ `position = { ref }`.
- `@tstamp` ⇒ `position = { measure, beat }`, where `measure` is the enclosing
  `<measure @n>` (tracked in document order) and `beat` is the timestamp.

Region directives (`type="key"`/`tonicization`/…) produce a `TonalRegion` rather
than a group, so they never consume a position — the next harmony keeps its own
anchor.

```xml
<harm type="hamon:key"          tstamp="1">C</harm>
<harm type="degree"             tstamp="1">I</harm>
<harm type="hamon:tonicization" tstamp="2">V</harm>     <!-- → G-major region -->
<harm type="degree"             tstamp="2">V7/V</harm>
<harm type="function"           tstamp="2">D</harm>      <!-- dominant, not a D chord -->
<harm type="tone"               tstamp="2.5">F[NHT:passing]</harm>
<harm type="hamon:key"          tstamp="3">A:minor</harm> <!-- modulation -->
```

This reuses the very same surface grammar and region/tone semantics as
[`analysis.md`](analysis.md); the only difference is that MEI is the carrier.

The inverse, `hamon_to_mei(seq, wrap=False)`, serializes a `HamonSequence` back
into these `<harm>` elements — regions become `hamon:key`/`hamon:modulation`/
`hamon:tonicization`, labels carry their `@type` layer and their beat as `@tstamp`,
and tones come out as `[HT]`/`[NHT:…]` — and it round-trips with `mei_to_hamon`.
With `wrap=True` the elements are nested in one `<measure n="…">` per measure the
positions name (a single anonymous `<measure>` when nothing is positioned), and two
`<harm>`s on the same `@tstamp` read back as one layered group. Full Verovio rendering
is still to come, in Phase 8.1b–8.6.

---

## Figured bass: `<fb>` and `<f>`

MEI has dedicated structured encoding for figured bass: `<fb>` (a child of `<harm>`) wraps individual figure elements, each an `<f>`:

```xml
<harm tstamp="1">
  <fb>
    <f>6</f>
    <f>5</f>
  </fb>
</harm>
```

An `<f>` can also carry an accidental attribute:

```xml
<harm tstamp="1">
  <fb>
    <f accid="s">6</f>   <!-- #6 -->
    <f>5</f>
  </fb>
</harm>
```

The HAMON fixture corpus keeps figured bass as plain text in `<harm>` (e.g. `<harm>6-5</harm>`), which is simpler and more portable. Save the structured `<fb>` form for when you need full MEI encoding — for instance, to render figured bass symbols in Verovio.

---

## Complete MEI example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei" meiversion="5.1">
  <meiHead>
    <fileDesc>
      <titleStmt><title>Example</title></titleStmt>
      <pubStmt/>
    </fileDesc>
  </meiHead>
  <music>
    <body>
      <mdiv>
        <score>
          <scoreDef>
            <staffGrp>
              <staffDef n="1" lines="5" clef.shape="G" clef.line="2"
                        meter.count="4" meter.unit="4"/>
            </staffGrp>
          </scoreDef>
          <section>
            <measure n="1">
              <staff n="1">
                <layer n="1">
                  <note xml:id="n1" pname="c" oct="4" dur="4"/>
                  <note xml:id="n2" pname="g" oct="3" dur="4"/>
                </layer>
              </staff>
              <!-- Chord symbol with hamon structured attributes -->
              <harm startid="#n1" type="chordSymbol"
                    root.pname="c" chord.kind="major-seventh">CΔ7</harm>
              <!-- Dominant seventh -->
              <harm startid="#n2" type="chordSymbol"
                    root.pname="g" chord.kind="dominant">G7</harm>
            </measure>
            <measure n="2">
              <staff n="1">
                <layer n="1">
                  <note xml:id="n3" pname="c" oct="4" dur="1"/>
                </layer>
              </staff>
              <!-- Figured bass, structured form -->
              <harm startid="#n3">
                <fb><f>6</f><f>4</f></fb>
              </harm>
            </measure>
          </section>
        </score>
      </mdiv>
    </body>
  </music>
</mei>
```

---

## Mapping: JSON fields → MEI

All mappings are relative to the canonical JSON schema (`grammar/hamon-schema.json`). MEI encodes harmony at two depths: **text form** (the surface string in `<harm>` text content) and **structured form** (the HAMON ODD attributes on `<harm>`). Keep both present at once.

### Chord symbols (`kind: "chordSymbol"`)

| JSON field | HAMON → MEI | MEI → HAMON | Loss / note |
|---|---|---|---|
| `surface` | text content of `<harm>` | text content → parsed surface | always present |
| `root.note` | `root.pname="c"` (structured) | `root.pname` → uppercase note | lowercase in MEI (`c`–`g`) |
| `root.accidental: "sharp"` | `root.accid="s"` (structured) | `"s"` → `sharp` | MEI accid token differs from HAMON |
| `root.accidental: "flat"` | `root.accid="f"` | `"f"` → `flat` | none |
| `root.accidental: "double-sharp"` | `root.accid="ss"` or `"x"` | → `double-sharp` | two MEI tokens map to same HAMON value |
| `root.accidental: "double-flat"` | `root.accid="ff"` | → `double-flat` | none |
| `quality` + `seventh` | `chord.kind="major-seventh"` (structured) | MusicXML kind vocabulary | same vocabulary as MusicXML |
| `bass.note` | `bass.pname="e"` (structured) | `bass.pname` → uppercase note | none |
| `bass.accidental` | `bass.accid="f"` | same as root accid | none |
| `rendering.seventhGlyph` | surface text only | from surface | not in structured attrs |

### Figured bass (`kind: "figuredBass"`)

| JSON field | HAMON → MEI | MEI → HAMON | Loss / note |
|---|---|---|---|
| `surface` | `<harm>6-5</harm>` text | text → parsed surface | text form preferred for portability |
| `number` + `tail` | `<fb><f>6</f><f>5</f></fb>` | `<f>` children → number + tail | structured form for rendering |
| `alterations[]` | `<f accid="s">6</f>` | `@accid` → `Alteration` | none |

### Other notation systems

| JSON `kind` | HAMON → MEI | MEI → HAMON | Loss / note |
|---|---|---|---|
| `roman` | `<harm>V7</harm>` text | text → parsed as surface | no structured MEI form |
| `nashville` | `<harm>4m</harm>` text | text → parsed | no structured MEI form |
| `functional` | `<harm>T</harm>` text | text → parsed | no structured MEI form |
| `noChord` | `<harm>N.C.</harm>` text | text → `noChord` | none |
| `text` | `<harm>…</harm>` text | text → `TextSemantic` | none |

### Structure and anchoring

| JSON field | HAMON → MEI | MEI → HAMON |
|---|---|---|
| `HarmonyGroup` time position | `@tstamp` (beat) or `@startid` (note `xml:id`) | `@tstamp` / `@startid` → time position |
| Display placement | `@place="above"` / `"below"` | — |
| Notation system | `type="chordSymbol"` (HAMON convention) | `@type` value → `detectedSystem` |

---

## Losses and ambiguities

- **Notation system ambiguity in plain text**: `<harm>V7</harm>`, `<harm>5</harm>`, and `<harm>6-5</harm>` say nothing about which system they use. HAMON infers `roman`, `nashville`, and `figuredBass` respectively from the grammar; a `@type` attribute would spell it out. So far the HAMON ODD defines no controlled vocabulary for `@type` beyond `chordSymbol`.
- **Structured vs. text form**: A `<harm>` can hold both `root.pname`/`chord.kind` attributes and text content. Given only structured attributes, HAMON reconstructs a surface from them; given only text, the structured fields are simply missing. This is why the HAMON ODD encourages keeping both.
- **`<fb>` vs. text figures**: Figured bass shows up either as `<fb><f>6</f><f>5</f></fb>` (structured) or as `<harm>6-5</harm>` (text). HAMON's MEI extractor reads both.
- **No native Roman numeral structure**: MEI has `@deg` (scale degree) in `MEI.analytical`, but nothing dedicated for Roman numerals in `MEI.harmony`, so Roman numerals go in `<harm>` as plain text.
- **MEI version**: The HAMON ODD targets MEI 5.x. MEI 4.x files use a slightly different attribute vocabulary for some elements.

---

## How HAMON reads MEI

hamonpy reads MEI `<harm>` elements directly in Python — there's no external
importer. Two entry points cover the two use cases:

- **Analytical adapter** (`hamonpy/hamonpy/adapters/mei.py`) — `mei_to_hamon(text)`
  scans `<measure>` and `<harm>` elements in document order, maps each `<harm>`'s
  `@type` token and text content to a hamon surface line (regions, layers, tones),
  and parses the result into a `HamonSequence` (the analytical layer above).
- **Surface extractor** (`hamonpy/hamonpy/adapters/formats.py`) —
  `read_harmony_labels("mei", text)` pulls just the surface strings, scanning for:
  - `<harm label="…">` — reads the `label` attribute.
  - `<harm …>text</harm>` — reads the text content directly.

Either way the surface string is handed to HAMON's grammar
(`parse_hamon_sequence`), which parses it into the typed AST.

---

## Relationship to Verovio

Verovio draws `<harm>` elements above the staff:

- **Text content** renders as styled text — this works today, with no C++ changes.
- **`<fb>` children** render as stacked figured bass symbols via `DrawFb()`.
- **Rich chord symbol rendering** (superscript 7, the Δ glyph, italic m) is planned, but it needs C++ changes in `src/view_control.cpp : DrawHarm()`.

See `verovio.md` for the full integration architecture and roadmap.

---

## Examples from the HAMON fixture corpus

| Fixture | MEI snippet | HAMON surface | HAMON `kind` |
|---|---|---|---|
| `C_major` | `<harm type="chordSymbol">C</harm>` | `C` | `chordSymbol` |
| `CΔ7` | `<harm type="chordSymbol">CΔ7</harm>` | `CΔ7` | `chordSymbol` |
| `B_hdim7` | `<harm type="chordSymbol">Bø7</harm>` | `Bø7` | `chordSymbol` |
| `rn_V7` | `<harm>V7</harm>` | `V7` | `roman` |
| `rn_ii` | `<harm>ii</harm>` | `ii` | `roman` |
| `fb_6_5` | `<harm>6-5</harm>` | `6-5` | `figuredBass` |
| `ns_2m` | `<harm>2m</harm>` | `2m` | `nashville` |

Full fixture files: `fixtures/chords/`, `fixtures/roman/`, `fixtures/figuredbass/`, `fixtures/nashville/`.
Schema and examples: `mei-customization/`.
