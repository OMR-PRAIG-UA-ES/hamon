# HAMON Architecture (Mermaid UML)

Mermaid diagrams of HAMON's architecture, as implemented in **hamonpy** (the Python
reference implementation).

> Conventions
>
> - **Surface-first**: every label keeps the exact substring as written.
> - `sequenceSystemHint` comes from the optional `@cs/@rn/@auto/...` prefix line.
> - `detectedSystem` is what the grammar and heuristics matched.
> - `system` is the final system, once the hint has been applied.

---

## 1) Package / component overview

```mermaid
flowchart LR
  U["Caller / pytest"]
  P["parse_hamon_sequence(text)"]
  L["HamonLexer (ANTLR4)"]
  G["HamonParser (ANTLR4)"]
  T["Parse Tree"]
  V["HamonParseVisitor"]
  N["normalize_*(ctx) functions"]
  A["HamonSequence AST"]

  U -->|"string input"| P
  P --> L --> G --> T
  P --> V
  T --> V
  V -->|"per label context"| N
  N -->|"semantic + rendering + detected"| V
  V --> A

  subgraph Adapters["adapters/"]
    F["formats.py\n(MEI/MusicXML/Humdrum/LilyPond/ABC/MuseScore)"]
    DC["dcml.py"]
    HA["harte.py"]
    IR["ireal.py"]
    M21["music21_adapter.py"]
    ETC["… 23 adapters in all\n(dcml_expanded, dilemma, dezrann,\njams, romantext, treebank, …)"]
  end

  U -->|"file / text"| F
  F -->|"surface strings"| P
```

---

## 2) Core data model (AST) — class diagram

The core data model (`hamonpy/hamonpy/ast.py`).

```mermaid
classDiagram
  class HamonSequence {
    +sequenceSystemHint?: SequenceSystem
    +groups: HarmonyGroup[]
  }

  class HarmonyGroup {
    +primary: HarmonyLabel[]
    +alternatives: HarmonyLabel[][]
    +position?: Position
  }

  class HarmonyLabel {
    +surface: string
    +sequenceSystemHint?: SequenceSystem
    +detectedSystem: DetectedSystem
    +system: DetectedSystem
    +semantic?: HarmonySemantic
    +rendering?: RenderingHints
  }

  class RenderingHints {
    +accidentalGlyphs?: Map~Accidental,string~
    +qualityGlyph?: string
    +seventhGlyph?: string
    +rawParts?: string[]
  }

  class HarmonySemantic {
    <<interface>>
    +kind: string
  }

  class ChordSymbolSemantic {
    +kind: "chordSymbol"
    +root: PitchClass
    +bass?: PitchClass
    +quality: ChordQuality
    +seventh?: SeventhQuality
    +extensions?: number[]
    +alterations?: Alteration[]
    +adds?: number[]
    +omits?: number[]
    +suspensions?: (number | null)[]
  }

  class RomanSemantic {
    +kind: "roman"
    +degree: string
    +prefixAccidentals?: string[]
    +secondary?: string
    +tail?: string
  }

  class NashvilleSemantic {
    +kind: "nashville"
    +number: number
    +prefixAccidentals?: string[]
    +tail?: string
    +secondary?: string
  }

  class FiguredBassSemantic {
    +kind: "figuredBass"
    +number: number
    +tail?: string
  }

  class FunctionalSemantic {
    +kind: "functional"
    +chain: string[]
  }

  class NoChordSemantic {
    +kind: "noChord"
  }

  class TextSemantic {
    +kind: "text"
    +text: string
  }

  class PitchClass {
    +note: A|B|C|D|E|F|G
    +accidental?: Accidental
  }

  class Alteration {
    +accidental: Accidental
    +degree: number
    +glyph: string
  }

  HamonSequence "1" o-- "many" HarmonyGroup
  HarmonyGroup "1" o-- "many" HarmonyLabel : primary
  HarmonyGroup "1" o-- "many" HarmonyLabel : alternatives[]

  HarmonyLabel "0..1" o-- RenderingHints
  HarmonyLabel "0..1" o-- HarmonySemantic

  HarmonySemantic <|.. ChordSymbolSemantic
  HarmonySemantic <|.. RomanSemantic
  HarmonySemantic <|.. NashvilleSemantic
  HarmonySemantic <|.. FiguredBassSemantic
  HarmonySemantic <|.. FunctionalSemantic
  HarmonySemantic <|.. NoChordSemantic
  HarmonySemantic <|.. TextSemantic

  ChordSymbolSemantic "1" o-- "1" PitchClass : root
  ChordSymbolSemantic "0..1" o-- "1" PitchClass : bass
  ChordSymbolSemantic "0..*" o-- Alteration
```

---

## 3) Parsing pipeline — sequence diagram

Entry point: `parse_hamon_sequence(text)` → `HamonSequence`.

```mermaid
sequenceDiagram
  autonumber
  participant U as Caller
  participant P as parse_hamon_sequence
  participant L as hamonLexer
  participant G as hamonParser
  participant V as HamonParseVisitor
  participant N as normalize_*(ctx)

  U->>P: text: str
  P->>L: InputStream(text)
  L-->>P: tokens
  P->>G: hamonParser(CommonTokenStream(lexer))
  P->>G: start()
  G-->>P: parse tree
  P->>V: build_hamon_sequence(tree, text)

  loop for each HarmonyContext
    V->>N: normalize_x(ctx)
    N-->>V: (semantic, rendering, detected)
  end

  V-->>P: HamonSequence
  P-->>U: HamonSequence
```

---

## 4) Visitor decision logic (label family dispatch)

The **parser** first recognizes one of these label families:
`noChord | functionalHarmony | chordSymbol | romanNumeral | numberHarmony | textLabel`.

The **visitor** mirrors that dispatch and calls the matching normalizer.

```mermaid
flowchart TD
  H["HarmonyContext"]
  H -->|noChord| NC["normalizeNoChord"]
  H -->|functionalHarmony| FH["normalizeFunctional"]
  H -->|chordSymbol| CS["normalizeChordSymbol"]
  H -->|romanNumeral| RN["normalizeRoman"]
  H -->|numberHarmony| NH["normalizeNumberHarmony"]
  H -->|else| TL["normalizeText"]

  NC --> L["HarmonyLabel"]
  FH --> L
  CS --> L
  RN --> L
  NH --> L
  TL --> L
```

---

## 5) Chord symbol normalization — activity diagram

The chord symbol normalizer is deliberately permissive. It parses the pieces it recognizes and stashes whatever's left in `rendering.rawParts`.

```mermaid
flowchart TD
  A["ChordSymbolContext\n(pitch chordPart* slashBass?)"]
  A --> B["normalizePitch(root)"]
  A --> C{slash bass?}
  C -->|yes| D["normalizePitch(bass)"]
  C -->|no| E["no bass"]

  B --> F["for each chordPart"]
  D --> F
  E --> F

  F --> Q{qualityMark?}
  Q -->|yes| Q1["set quality\n+ rendering.qualityGlyph"]
  Q -->|no| S{seventhMark?}

  S -->|yes| S1["set seventh/extensions\n+ rendering.seventhGlyph"]
  S -->|no| ALT{alteration?}

  ALT -->|yes| ALT1["push alteration\n+ accidental glyph hints"]
  ALT -->|no| AOS{add/omit/sus?}

  AOS -->|yes| AOS1["push adds/omits/suspensions\nstore leftovers in rawParts"]
  AOS -->|no| EXT{numeric extension?}

  EXT -->|yes| EXT1["push extension"]
  EXT -->|no| RAW["push into rendering.rawParts"]

  Q1 --> F
  S1 --> F
  ALT1 --> F
  AOS1 --> F
  EXT1 --> F
  RAW --> F

  F --> Z["post-pass fixes\n- default quality=major\n- if ext has 9/11/13 and no 7 => implied dom7\n- coerce dom7->maj7 when explicit major marker"]
  Z --> OUT["ChordSymbolSemantic + RenderingHints"]
```

---

## 6) Fixture test pipeline

```mermaid
sequenceDiagram
  autonumber
  participant T as pytest
  participant FX as test_fixtures.py
  participant AD as adapters/formats.py
  participant P as parse_hamon_sequence

  T->>FX: parametrized(fixture_id, format, source_text)
  FX->>AD: extract_harmony_labels(format, source_text)
  AD-->>FX: surface_strings[]
  loop for each surface
    FX->>P: parse_hamon_sequence(surface)
    P-->>FX: HamonSequence
    FX->>FX: assert matches expected
  end
```

---

## 7) Extension notes

### Roman / number harmony normalization
- `normalizeRoman()` currently keeps `tail` as a surface string. Split it into inversion/figures/secondary relationships when you're ready.
- `normalizeNumberHarmony()` uses a **hyphen-digit** heuristic (`6-5`) to decide figured bass. Swap in a richer rule set when you need one.

### Round-trip rendering
- `RenderingHints` records the explicit "how it was printed" choices (`b` vs. `♭`, `maj` vs. `Δ`).
- `surface` is always preserved as-is. Semantics and rendering stay in separate layers.
