# HAMON Grammar

This directory holds the normative HAMON grammar in two equivalent forms:

- `hamon.ebnf` — W3C-style EBNF. This is the source of truth; it drives the railroad diagrams and the papers.
- `../antlr/hamonLexer.g4` + `../antlr/hamonParser.g4` — the ANTLR4 transcription, which we use to generate parsers.

Keep the two in sync. If they ever disagree, the EBNF wins.

---

## Design philosophy

### Surface-first

HAMON captures the **written surface** of a harmony label — the exact glyphs the composer, analyst, or editor wrote — and stores them losslessly. Semantic normalization is a separate pass (`normalize.ts` / `normalize.py`); the grammar itself does none of it.

A few consequences:
- `Cmaj7`, `CM7`, and `CΔ7` are three distinct surfaces that all normalize to the same semantic (`chordSymbol`, `major-seventh`).
- `ii65` is captured as `roman` with tail `65`. The grammar makes no call about whether `65` means a figured-bass position or something else.
- An unrecognized label like `Ger65` is captured losslessly as `textLabel` instead of being rejected.

### System-agnostic parsing

One set of grammar rules handles all five harmony systems. You either declare the system (`cs`, `rn`, `ns`, `fb`, `fun`) with a `@<systemId>` hint, or the normalizer infers it from the shape of the parsed tokens. That means a single sequence can mix Roman numerals, chord symbols, and figured bass.

### Permissive tails

Quality markers, extensions, and alterations inside a chord symbol or Roman numeral are captured as open-ended `chordPart` or `rnTail` sequences. Anything the grammar doesn't recognize becomes a `word` token and is kept in `rendering.rawParts`. As a result, the parser never rejects a real-world label just because it carries an unusual suffix.

---

## Grammar rules — narrative

### `start`

```ebnf
start ::= versionDecl? systemDecl? harmonyGroup ( EOL+ harmonyGroup )* EOL*
```

The top-level sequence. An optional `@version:<semver>` pins the HAMON standard version, and an optional `@<systemId>` hint applies to the whole sequence. Newlines separate groups; within a group, labels are comma-separated, with `|` for alternatives.

**Design decision**: We use the newline as the group separator (rather than a comma or space) because that mirrors how harmony labels appear in real scores — one chord per beat or measure, stacked vertically in an analysis.

---

### `versionDecl`

```ebnf
versionDecl ::= "@version:" VERSION
VERSION     ::= NUMBER ( "." NUMBER )*
```

An optional first line that declares which version of the HAMON standard this sequence targets (e.g. `@version:0.1.0`). When both are present, it must come before `systemDecl`. The lexer matches the whole `@version:M.m.p` string as a single `VERSION_DECL` token, so the colon and digits never collide with other tokens.

Maps to `HamonSequence.version` in the JSON schema.

---

### `systemDecl` and `systemId`

```ebnf
systemDecl ::= "@" systemId
systemId   ::= "auto" | "cs" | "rn" | "ns" | "fb" | "fun" | "text"
```

An optional line (after `versionDecl`, if present) that declares the notation system for the whole sequence. The normalizer uses it to resolve ambiguous tokens — for example, `4` is Nashville under `@ns` but figured bass under `@fb`.

`@auto` is the default when no hint is present; it tells the normalizer to detect the system label by label.

**Why a hint instead of separate grammars**: real scores mix systems — a Roman numeral analysis might carry a figured bass label for a pedal point. One grammar with an optional hint handles that cleanly.

---

### `harmonyGroup` and `harmonyList`

```ebnf
harmonyGroup ::= harmonyList ( "|" harmonyList )* positionTag?
harmonyList  ::= harmony ( "," harmony )*
positionTag  ::= POS                         (* v0.2.1 *)
POS          ::= "@@" ( any char except whitespace, "|" or "," )+
```

A group represents the harmony at one time point. Within a group:
- `,` separates simultaneous alternatives — say, two analysts' readings of the same chord.
- `|` separates mutually exclusive interpretations or layers — say, a chord symbol layer against a Roman numeral layer for the same passage.

**v0.2.1 — time-aligned position.** A group may end with a `@@` tag that gives its
position in the source (→ `HarmonyGroup.position` in the JSON schema):

| Tag | Position |
|---|---|
| `@@1:3` | measure 1, beat 3 |
| `@@4` | measure 4 (no beat) |
| `@@t5/4` | absolute position `5/4` quarter notes |
| `@@#note-9` | anchored to score-object id `note-9` |

For example, `Cmaj7 @@1:1`. The `@@` sigil keeps this distinct from the `@` directives, and
the parser accepts it only at the end of a group. Positions are optional and
backward compatible — most surfaces are line-ordered and carry no `@@` tag.

---

### `harmony`

```ebnf
harmony ::= noChord
          | functionalHarmony
          | chordSymbol
          | romanNumeral
          | numberHarmony
          | textLabel
```

This is an ordered choice, and the order matters for disambiguation:

1. `noChord` — tried first, so `N` isn't swallowed as a note name.
2. `functionalHarmony` — before `romanNumeral`, because `T`, `S`, and `D` also serve as Roman numeral prefixes in some systems.
3. `chordSymbol` — before `romanNumeral`, since both start with a letter. Chord symbols require a `NOTE` token (A–G), which is a strict subset of `ROMAN`.
4. `romanNumeral` — before `numberHarmony`.
5. `numberHarmony` — covers both Nashville and figured bass; the normalizer tells them apart.
6. `textLabel` — the catch-all.

---

### `noChord`

```ebnf
noChord ::= "NC" | "N.C." | "n.c." | "NoChord"
```

Every common written form of "no chord". All of them normalize to the canonical `noChord` kind.

---

### `functionalHarmony`

```ebnf
functionalHarmony ::= funcToken ( "->" funcToken )*
funcToken         ::= "T" | "S" | "D" | "PD" | "SD" | "DD"
```

Riemannian functional labels. The `->` operator encodes a functional progression inside a single label — `D->T`, for instance, is a dominant resolving to a tonic.

**Current limitation**: only the basic tokens are listed. Regional variants (`Tp`, `Sp`, `DP`, `tP`, and the German `Tg`/`Sg`/`Dg`) aren't in the grammar yet, so they fall through to `textLabel`.

---

### `chordSymbol`

```ebnf
chordSymbol ::= pitch chordPart* slashBass?
pitch       ::= NOTE accidentalGlyph?
NOTE        ::= "A" | "B" | "C" | "D" | "E" | "F" | "G"
```

The chord symbol rule is permissive on purpose. `chordPart` accepts any recognized quality marker, seventh mark, extension, alteration, suspended/add/omit modifier, parenthesized group, or unrecognized word. That's why `C7(#11b9)`, `Csus4add9`, and `C(maj7)` all parse without error.

#### `seventhMark` vs `qualityMark` ordering

```ebnf
chordPart ::= seventhMark | qualityMark | extension | alteration | addOmitSus | parenGroup | word
seventhMark ::= "Δ" NUMBER? | ("maj" | "M") NUMBER
qualityMark ::= "maj" | "M" | "min" | "m" | "-" | "dim" | "o" | "°" | "aug" | "+" | "ø"
```

`seventhMark` is tried before `qualityMark` so that `maj7` parses as a single seventh token, not as `qualityMark(maj)` + `extension(7)`. This is the key disambiguation: it separates `Cmaj7` (major seventh) from a hypothetical `Cmaj` (major) + `7` (extension).

#### Accidentals in `pitch`

Both ASCII (`#`, `b`) and Unicode (`♯`, `♭`, `♮`, `𝄪`, `𝄫`) glyphs are accepted. True to the surface-first principle, whatever the source file contains is preserved.

#### `slashBass`

```ebnf
slashBass ::= "/" pitch
```

A slash bass note — `C/E`, for example, is C major over an E bass. The bass pitch reuses the same `pitch` rule as the root.

---

### `romanNumeral`

```ebnf
romanNumeral ::= rnAccidental* rnDegree rnTail* rnSecondary?
rnDegree     ::= ROMAN
ROMAN        ::= "I" | "II" | "III" | "IV" | "V" | "VI" | "VII"
               | "i" | "ii" | "iii" | "iv" | "v" | "vi" | "vii"
rnSecondary  ::= "/" rnAccidental* ROMAN
```

Case encodes mode: uppercase is major, lowercase is minor — the standard Schenkerian/tonal-analysis convention.

Prefix accidentals (`b`, `#`, `♭`, `♯`) modify the scale degree. Tails (`rnTail`) capture figures (`65`, `43`), quality suffixes (`°`, `ø`), and other modifiers. Secondary function goes after a `/`.

**Ambiguity with figured bass positions**: `ii65` is captured as `roman` (degree `ii`, tail `65`). Whether `65` means "first-inversion seventh chord in figured-bass style" or something else is a decision for the normalizer or the annotation, not for the grammar.

---

### `numberHarmony`

```ebnf
numberHarmony    ::= rnAccidental* NUMBER numberTail* numberSecondary?
numberTail       ::= ( "-" NUMBER ) | qualityMark | extension | alteration | parenGroup | word
numberSecondary  ::= "/" ( NUMBER | pitch )
```

Covers both the Nashville number system and standalone figured bass figures. The grammar can't tell them apart structurally, so the normalizer falls back on heuristics:

- A token containing `DASH INT` (e.g., `6-5`) is figured bass.
- A plain integer, optionally followed by a quality marker (e.g., `4m`, `b7`), is Nashville.
- A `@<systemId>` hint overrides both.

**Design decision**: folding Nashville and figured bass into one rule avoids an ambiguous lookahead — both start with a digit, optionally preceded by an accidental. The `DASH INT` signal is strong enough that the normalizer can split them reliably.

---

### `textLabel`

```ebnf
textLabel   ::= QUOTED_TEXT | RAW_TEXT
QUOTED_TEXT ::= '"' TEXTCHAR* '"'
RAW_TEXT    ::= RAW_CHAR+
RAW_CHAR    ::= (* any character except whitespace, ",", "|", EOL *)
```

The lossless catch-all. Any label that matches none of the rules above is captured as `textLabel`, so the parser never drops content: an unrecognized token is preserved verbatim, ready to inspect or re-parse later.

Quoted strings (`"…"`) let a label contain commas or pipe characters that would otherwise read as group separators.

---

## Cross-format mapping

Each row names a HAMON grammar concept; each column shows how that format encodes it.

### Chord symbols

| HAMON concept | MusicXML | MEI | Humdrum | LilyPond | ABC | MuseScore |
|---|---|---|---|---|---|---|
| Root note | `<root-step>C</root-step>` | `<harm type="chordSymbol">C…` | `**mxhm` / `**jazz` / `**irb` token prefix | lowercase pitch (`c`, `bes`) | first char(s) of quoted string | `<Harmony><text>C…` |
| Sharp | `<root-alter>1</root-alter>` | `#` in text | `#` in token | `is` suffix (`cis`) | `#` in string | `#` in text |
| Flat | `<root-alter>-1</root-alter>` | `b` in text | `b` in token | `es`/`ees` suffix (`bes`) | `b` in string | `b` in text |
| Major triad | `<kind>major</kind>` | `<harm type="chordSymbol">C</harm>` | `C` | `c` (no modifier) | `"C"` | `<text>C</text>` |
| Minor triad | `<kind text="m">minor</kind>` | `<harm type="chordSymbol">Cm</harm>` | `Cm` | `c:m` | `"Cm"` | `<text>Cm</text>` |
| Augmented | `<kind>augmented</kind>` | `<harm type="chordSymbol">C+</harm>` | `C+` | `c:aug` | `"C+"` | `<text>C+</text>` |
| Diminished | `<kind>diminished</kind>` | `<harm type="chordSymbol">C°</harm>` | `C°` or `Cdim` | `c:dim` | `"Cdim"` | `<text>C°</text>` |
| Dominant 7th | `<kind text="7">dominant</kind>` | `<harm type="chordSymbol">G7</harm>` | `G7` | `g:7` | `"G7"` | `<text>G7</text>` |
| Major 7th | `<kind text="Δ7">major-seventh</kind>` | `<harm type="chordSymbol">CΔ7</harm>` | `CΔ7` | `c:7+` + `majorSevenSymbol` | `"CΔ7"` | `<text>CΔ7</text>` |
| Minor 7th | `<kind text="m7">minor-seventh</kind>` | `<harm type="chordSymbol">Am7</harm>` | `Am7` | `a:m7` | `"Am7"` | `<text>Am7</text>` |
| Dim 7th | `<kind>diminished-seventh</kind>` | `<harm type="chordSymbol">B°7</harm>` | `B°7` | `b:dim7` | `"B°7"` | `<text>B°7</text>` |
| Half-dim 7th | `<kind>half-diminished-seventh</kind>` | `<harm type="chordSymbol">Bø7</harm>` | `Bø7` | `b:m7.5-` | `"Bø7"` | `<text>Bø7</text>` |
| Suspended 2nd | `<kind text="sus2">suspended-second</kind>` | `<harm type="chordSymbol">Csus2</harm>` | `Csus2` | `c:sus2` | `"Csus2"` | `<text>Csus2</text>` |
| Suspended 4th | `<kind text="sus4">suspended-fourth</kind>` | `<harm type="chordSymbol">Csus4</harm>` | `Csus4` | `c:sus4` | `"Csus4"` | `<text>Csus4</text>` |
| Slash bass | `<bass><bass-step>E</bass-step></bass>` | `C/E` in text | `C/E` in token | `c/e` | `"C/E"` | `<text>C/E</text>` |
| Extension (`#11`) | `<degree>` children | in `<harm>` text | in token | `:modifier` | in string | in `<text>` |

### Roman numerals

| HAMON concept | MusicXML | MEI | Humdrum | LilyPond | ABC | MuseScore |
|---|---|---|---|---|---|---|
| Degree (`I`–`VII`) | `<kind text="I">` (non-standard) | `<harm>I</harm>` text | `**harm` token | `% hamon-surface:` | `"I"C` | `<text>I</text>` |
| Lowercase minor (`ii`) | text only | `<harm>ii</harm>` text | `**harm` token | `% hamon-surface:` | `"ii"C` | `<text>ii</text>` |
| Prefix accidental (`bVII`) | not standard | in text | in token | `% hamon-surface:` | in string | in text |
| Figured suffix (`V65`) | not standard | in text | in token | `% hamon-surface:` | in string | in text |
| Secondary (`V/V`) | not standard | in text | in token | `% hamon-surface:` | in string | in text |

### Figured bass

| HAMON concept | MusicXML | MEI | Humdrum | LilyPond | ABC | MuseScore |
|---|---|---|---|---|---|---|
| Figure numeral | not standard | `<fb><f>6</f><f>5</f></fb>` | `**fb` or `**harm` token | `% hamon-surface:` | `"6-5"C` | `<text>6-5</text>` |
| Multiple figures | `<degree>` hacks | `<fb>` children | `-`-separated in token | `% hamon-surface:` | in string | in text |
| Alterations (`#6`) | not standard | `<f accid="s">6</f>` | in token | `% hamon-surface:` | in string | in text |

### Nashville numbers

| HAMON concept | MusicXML | MEI | Humdrum | LilyPond | ABC | MuseScore |
|---|---|---|---|---|---|---|
| Scale degree number | not standard | `<harm>4</harm>` text | `**harm` token | `% hamon-surface:` | `"4"C` | `<text>4</text>` |
| Quality suffix (`4m`) | not standard | in text | in token | `% hamon-surface:` | in string | in text |
| Prefix accidental (`b7`) | not standard | in text | in token | `% hamon-surface:` | in string | in text |

### Functional harmony

| HAMON concept | MusicXML | MEI | Humdrum | LilyPond | ABC | MuseScore |
|---|---|---|---|---|---|---|
| Tonic (`T`) | not standard | `<harm>T</harm>` text | `**function` token | `% hamon-surface:` | `"T"C` | `<text>T</text>` |
| Subdominant (`S`) | not standard | in text | `**function` token | `% hamon-surface:` | in string | in text |
| Dominant (`D`) | not standard | in text | `**function` token | `% hamon-surface:` | in string | in text |
| Progression (`D->T`) | not standard | in text | in token | `% hamon-surface:` | in string | in text |

### Structural

| HAMON concept | MusicXML | MEI | Humdrum | LilyPond | ABC | MuseScore |
|---|---|---|---|---|---|---|
| No chord | `<kind text="N.C.">none</kind>` | `<harm>N.C.</harm>` text | `.` (null token) | — | `"N.C."C` | `<text>N.C.</text>` |
| System hint | — | — | spine type (`**harm`, `**mxhm`, …) | file extension / comment | — | — |
| Time position | `<harmony>` offset in measure | `@tstamp` attribute | spine row order | note attachment | note attachment | element order in voice |
| Display surface | `<kind text="…">` attribute | `<harm>` text content | token as-is | `majorSevenSymbol` + token | quoted string | `<text>` content |

---

## Format support summary

| Format | Chord symbols | Roman numerals | Figured bass | Nashville | Functional | Structured or plain text |
|---|---|---|---|---|---|---|
| MusicXML | ✅ structured | text only | text only | text only | ❌ | structured |
| MEI | ✅ structured (`<harm type>`) | plain text | `<fb><f>` children | plain text | plain text | both |
| Humdrum | ✅ `**mxhm`/`**jazz`/`**irb` | `**harm` token | `**fb` / `**harm` token | `**harm` token | `**function` token | plain text in spine |
| LilyPond | ✅ `\chordmode` | comment only | comment only | comment only | comment only | comment (`% hamon-surface:`) |
| ABC | ✅ quoted string | quoted string | quoted string | quoted string | quoted string | plain text |
| MuseScore | ✅ `<Harmony><text>` | `<text>` as-is | `<text>` as-is | `<text>` as-is | `<text>` as-is | plain text |
| MNX (draft) | ✅ structured | structured | TBD | TBD | TBD | `display` field |

**Key insight**: MusicXML is the only format with a fully structured chord symbol model, with separate root, quality, and extensions. MEI structures figured bass (`<fb>`) but stores everything else as text. Humdrum has the richest spine-type vocabulary for telling notation systems apart. LilyPond structures chord symbols but leans on the `% hamon-surface:` convention for everything else.
