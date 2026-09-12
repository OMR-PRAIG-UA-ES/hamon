# HAMON standalone XML encoding

Version: 0.1.0

A lightweight XML encoding for HAMON sequences, and a direct counterpart to `hamon-schema.json` — every field maps one-to-one. Reach for it when you need an XML serialization outside of MEI: standalone analysis files, database exports, or tool pipelines that prefer XML to JSON.

For harmony embedded in MEI, use `<harm>` instead, as defined in `documentation/mei.md` and the HAMON ODD (`mei-customization/`). This encoding is for standalone use only.

---

## Root element

```xml
<?xml version="1.0" encoding="UTF-8"?>
<hamonSequence xmlns="https://hamon.music/xml/0.1"
               version="0.1.0"
               systemHint="cs">
  <!-- HarmonyGroup elements -->
</hamonSequence>
```

| Attribute | JSON field | Required | Description |
|---|---|---|---|
| `version` | — | yes | Schema version of this file (`0.1.0`) |
| `systemHint` | `sequenceSystemHint` | no | System hint for the whole sequence (`auto`, `cs`, `rn`, `ns`, `fb`, `fun`, `text`) |

---

## `<group>` — HarmonyGroup

Each `<group>` corresponds to one time point — one `HarmonyGroup` in the JSON.

```xml
<group>
  <primary>
    <!-- one or more <label> elements -->
  </primary>
  <alternative>
    <!-- one or more <label> elements — repeat <alternative> for multiple alternatives -->
  </alternative>
</group>
```

- `<primary>` holds the main label(s) and is always present.
- `<alternative>` may repeat; each occurrence is one alternative layer (`HarmonyGroup.alternatives[i]`).

---

## `<label>` — HarmonyLabel

```xml
<label surface="CΔ7"
       detectedSystem="cs"
       system="cs"
       systemHint="cs">
  <semantic>
    <!-- one semantic child element -->
  </semantic>
  <rendering qualityGlyph="m" seventhGlyph="Δ">
    <accidentalGlyph type="sharp">#</accidentalGlyph>
    <rawPart>sus4</rawPart>
  </rendering>
</label>
```

| Attribute | JSON field | Required | Description |
|---|---|---|---|
| `surface` | `surface` | yes | Exact original string |
| `detectedSystem` | `detectedSystem` | yes | System detected by grammar |
| `system` | `system` | yes | Resolved system (after hint) |
| `systemHint` | `sequenceSystemHint` | no | Propagated sequence hint |

---

## Semantic elements

Each `<semantic>` element holds exactly one child, chosen by the label kind.

### `<chordSymbol>`

```xml
<semantic>
  <chordSymbol quality="major" seventh="maj7">
    <root note="C" accidental="sharp"/>
    <bass note="G"/>
    <extension>9</extension>
    <alteration accidental="sharp" degree="11" glyph="#"/>
    <add>9</add>
    <omit>5</omit>
    <suspension>4</suspension>
  </chordSymbol>
</semantic>
```

| Element / attribute | JSON field | Required |
|---|---|---|
| `@quality` | `quality` | yes |
| `@seventh` | `seventh` | no |
| `<root>` | `root` | yes |
| `<bass>` | `bass` | no |
| `<extension>` | `extensions[]` | no, repeatable |
| `<alteration>` | `alterations[]` | no, repeatable |
| `<add>` | `adds[]` | no, repeatable |
| `<omit>` | `omits[]` | no, repeatable |
| `<suspension>` | `suspensions[]` | no, repeatable; empty element = `sus` (null) |

`<root>` and `<bass>` attributes:

| Attribute | JSON field | Required |
|---|---|---|
| `note` | `note` | yes |
| `accidental` | `accidental` | no |

### `<roman>`

```xml
<semantic>
  <roman degree="V" tail="65" secondary="V">
    <prefix>b</prefix>
  </roman>
</semantic>
```

| Element / attribute | JSON field | Required |
|---|---|---|
| `@degree` | `degree` | yes |
| `@tail` | `tail` | no |
| `@secondary` | `secondary` | no |
| `<prefix>` | `prefixAccidentals[]` | no, repeatable |

### `<nashville>`

```xml
<semantic>
  <nashville number="4" tail="m" secondary="5">
    <prefix>b</prefix>
  </nashville>
</semantic>
```

| Element / attribute | JSON field | Required |
|---|---|---|
| `@number` | `number` | yes |
| `@tail` | `tail` | no |
| `@secondary` | `secondary` | no |
| `<prefix>` | `prefixAccidentals[]` | no, repeatable |

### `<figuredBass>`

```xml
<semantic>
  <figuredBass number="6" tail="-5"/>
</semantic>
```

| Element / attribute | JSON field | Required |
|---|---|---|
| `@number` | `number` | yes |
| `@tail` | `tail` | no |
| `<prefix>` | `prefixAccidentals[]` | no, repeatable |

### `<functional>`

```xml
<semantic>
  <functional>
    <token>D</token>
    <token>T</token>
  </functional>
</semantic>
```

Each `<token>` is one element of `FunctionalSemantic.chain`. A single element is a plain label; several elements form a progression chain (`D->T`).

### `<noChord>`

```xml
<semantic>
  <noChord/>
</semantic>
```

### `<text>`

```xml
<semantic>
  <text>Ger65</text>
</semantic>
```

---

## `<rendering>` — RenderingHints

```xml
<rendering qualityGlyph="m" seventhGlyph="Δ">
  <accidentalGlyph type="flat">b</accidentalGlyph>
  <rawPart>(#11)</rawPart>
</rendering>
```

| Element / attribute | JSON field | Notes |
|---|---|---|
| `@qualityGlyph` | `qualityGlyph` | e.g., `m`, `−`, `°`, `ø`, `+` |
| `@seventhGlyph` | `seventhGlyph` | e.g., `Δ`, `M`, `maj`, `7` |
| `<accidentalGlyph type="…">` | `accidentalGlyphs[type]` | `type` = `sharp`, `flat`, `double-sharp`, `double-flat`, `natural` |
| `<rawPart>` | `rawParts[]` | repeatable; uninterpreted surface fragments |

---

## Namespace and versioning

XML namespace: `https://hamon.music/xml/0.1`

The minor version is baked into the namespace URI. A breaking (major) bump produces a new namespace; a minor or patch bump keeps the same one and stays backwards-compatible.

---

## Complete example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<hamonSequence xmlns="https://hamon.music/xml/0.1" version="0.1.0" systemHint="cs">

  <group>
    <primary>
      <label surface="CΔ7" detectedSystem="cs" system="cs">
        <semantic>
          <chordSymbol quality="major" seventh="maj7">
            <root note="C"/>
          </chordSymbol>
        </semantic>
        <rendering seventhGlyph="Δ"/>
      </label>
    </primary>
  </group>

  <group>
    <primary>
      <label surface="Am7" detectedSystem="cs" system="cs">
        <semantic>
          <chordSymbol quality="minor" seventh="min7">
            <root note="A"/>
          </chordSymbol>
        </semantic>
        <rendering qualityGlyph="m" seventhGlyph="7"/>
      </label>
    </primary>
  </group>

  <group>
    <primary>
      <label surface="G7" detectedSystem="cs" system="cs">
        <semantic>
          <chordSymbol quality="major" seventh="dom7">
            <root note="G"/>
          </chordSymbol>
        </semantic>
        <rendering seventhGlyph="7"/>
      </label>
    </primary>
  </group>

  <group>
    <primary>
      <label surface="C" detectedSystem="cs" system="cs">
        <semantic>
          <chordSymbol quality="major">
            <root note="C"/>
          </chordSymbol>
        </semantic>
      </label>
    </primary>
  </group>

</hamonSequence>
```

---

## Relationship to other formats

| Format | Role |
|---|---|
| `hamon-schema.json` | Canonical JSON schema; this XML encoding is its XML counterpart |
| `hamon.ebnf` | Text surface syntax; parses to/from the same semantic model |
| MEI `<harm>` | Embedded in MEI scores; uses HAMON surfaces as text content |
| MusicXML `<harmony>` | Source/target for chord symbol mapping |
