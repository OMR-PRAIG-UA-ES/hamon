# HAMON ↔ Verovio integration

## Overview

Verovio (`/Users/drizo/githubs/verovio/gabc/verovio/`) is a C++ library that renders MEI music scores to SVG. The custom build in `verovio-hamon/compile_verovio.sh` produces a CLI binary from the local Verovio source — currently the `develop-gabc` branch, which adds GABC support.

HAMON and Verovio meet at MEI's `<harm>` element. HAMON labels ride inside `<harm>` elements in MEI files, and Verovio renders those elements above the staff.

## How Verovio currently renders `<harm>`

`src/view_control.cpp : View::DrawHarm()` does the rendering:
- If the `<harm>` has a `<fb>` child, it renders figured bass symbols.
- Otherwise, it renders the text children as-is (the chord symbol surface string).

`src/harm.cpp : Harm::GetRootPitch()` parses that text to pull out a root note for transposition. It understands ASCII `#`/`b` accidentals and the Unicode sharp/flat glyphs that HAMON uses.

**Conclusion**: HAMON surface strings (`CΔ7`, `ii65`, `6-5`, `N.C.`) written as text inside `<harm>` elements render correctly today, with no C++ changes — Verovio simply treats them as styled text.

## MEI customization (`mei-customization/`)

Two ODD files define the schema for MEI files that carry HAMON harmony:

| File | Purpose |
|------|---------|
| `hamon.odd` | Full HAMON MEI customization (all MEI modules including MEI.harmony) |
| `mei-verovio-hamon.xml.odd` | Verovio-specific subset (`mei-verovio` schema) — uses only modules Verovio supports |

The Verovio-specific ODD (`mei-verovio-hamon.xml.odd`) starts from Verovio's own ODD and extends it with `MEI.harmony`. It controls which `<harm>` attributes Verovio accepts without raising validation errors.

Generate the RelaxNG schema from the ODD like this:
```bash
# Requires oXygen XML Editor or TEI Stylesheets
java -jar teigarage.jar --profile=relaxng mei-verovio-hamon.xml.odd
```

## Integration pipeline

```
hamon label (surface string)
  ↓
hamon→MEI serializer (hamonpy MEI adapter, hamon_to_mei)
  produces: <harm tstamp="1" place="above">CΔ7</harm>
  ↓
MEI file (validates against mei-verovio-hamon RelaxNG schema)
  ↓
Verovio CLI: verovio --from mei --to svg input.mei
  produces: SVG with chord symbols rendered above the staff
```

The reverse direction — reading `<harm>` back out of an MEI file — runs entirely
in hamonpy:
```
MEI file with <harm> elements
  ↓
hamonpy MEI adapter: mei_to_hamon / read_harmony_labels("mei", …)
  ↓
surface strings
  ↓
parse_hamon_sequence → HamonSequence AST
```

## Build the custom Verovio binary

```bash
cd verovio-hamon
sh compile_verovio.sh       # builds the CLI tool from the local source
# binary ends up at verovio-hamon/verovio/tools/verovio (or build-cli/verovio)
```

The script builds the standard CMake target. Whatever hamon-specific rendering the GABC branch adds is compiled in here.

## What is missing / roadmap

### 1. HAMON → MEI serializer (highest priority)
hamonpy's MEI adapter (`hamon_to_mei`) already serializes the analytical layer
back to `<harm>` elements. For Verovio rendering it should also:
- Create `<harm>` elements with `@tstamp` or `@startid` anchors
- Write the surface string as text content (works with Verovio today)
- Optionally write `<fb>` children for figured bass labels

### 2. RelaxNG schema generation
Automate the ODD → RelaxNG step in `tools/scripts/`. We need the schema to validate MEI files before handing them to Verovio.

### 3. Optional: rich chord rendering in Verovio
For properly typeset chord symbols (superscript `7`, the `Δ` glyph, italic `m`), Verovio's `DrawHarm` would need to:
- Parse the HAMON surface string (or read structured child elements)
- Apply font, size, and glyph rules per token (root, quality, seventh, bass)

That means C++ changes in `src/view_control.cpp`, and possibly new MEI child elements inside `<harm>`. Define any new attributes in `mei-verovio-hamon.xml.odd`.

### 4. Figured bass column alignment
Verovio's `adjustharmgrpsspacingfunctor.cpp` handles horizontal spacing for stacked `<harm>` groups. HAMON figured bass notation (`6-5`, `4-3`, `7-6`) uses a single `<harm>` with `<fb>` children, and these already render through the existing `DrawFb` path — no changes needed.

### 5. MEI export round-trip test
Once HAMON labels have been parsed from a Humdrum `**harm` spine into a
`HamonSequence`, write them back to MEI with `hamon_to_mei` and check that the
`<harm>` elements land in the right positions (it round-trips with `mei_to_hamon`).

## Relevant Verovio source files

| File | Role |
|------|------|
| `src/harm.cpp` / `include/vrv/harm.h` | `<harm>` element model, `GetRootPitch` for transposition |
| `src/view_control.cpp : DrawHarm()` | SVG rendering of `<harm>` |
| `src/adjustharmgrpsspacingfunctor.cpp` | Horizontal spacing between chord groups |
| `libmei/` | LibMEI schema / attribute accessors |
| `cmake/CMakeLists.txt` | Build options (e.g., `NO_MUSICXML_SUPPORT`) |

## Relevant HAMON source files

| File | Role |
|------|------|
| `mei-customization/mei-verovio-hamon.xml.odd` | Verovio MEI schema with harmony |
| `mei-customization/hamon.odd` | Full HAMON MEI customization |
| `verovio-hamon/compile_verovio.sh` | Build script for custom Verovio |
| `hamonpy/hamonpy/adapters/mei.py` | Reads/writes `<harm>` (`mei_to_hamon` / `hamon_to_mei`) |
| `documentation/mei.md` | Notes on MEI harmony elements used by HAMON |
