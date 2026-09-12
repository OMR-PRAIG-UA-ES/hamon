# fixtures

We store our cross-format example corpus here.

We use this corpus to:

- compare how different ecosystems encode the same harmony concepts
- build adapters (MEI, MusicXML, Humdrum/**kern, LilyPond, ABC, MuseScore, music21)
- run unit tests that ensure we do not regress the standard or the reference implementations

As we expand the repository, we typically add:

- source files in their native formats (`.musicxml`, `.mei`, `.krn`, `.abc`, `.ly`, etc.)
- expected HAMON exchange strings (`.hamon`) where we want golden tests
- optional expected AST snapshots (`.json`) for deeper invariants
- optional Markdown previews (`.md`) with the surface chord symbol and a simple note spelling line

We also support snippet-only fixture sources (for example just a `<harmony>` block or a `\chordmode` fragment).
The fixture `.json` + per-format snippets are the source of truth, consumed by
`hamonpy/tests/test_fixtures.py`.
