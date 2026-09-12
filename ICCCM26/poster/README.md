# Poster code boxes — the runnable version

Four scripts, one per code box on the ICCCM'26 poster. Each one runs on its own,
reads a real file from [`../examples/`](../examples/), and prints something small
enough to sit in a box. Nothing here is pseudo-code and no output is typed by hand:
what the poster shows is what these print.

```bash
pip install hamonpy
python ICCCM26/poster/example1.py     # …and 2, 3, 4
```

| Script | Box | What it shows |
|---|---|---|
| `example1.py` | Parse any encoding into HAMON | The same typed model out of two notations that look nothing alike: a HAMON lead sheet carrying chord symbols **and** their Roman reading, and a Harte annotation that has chord labels and nothing else. |
| `example2.py` | One typed AST | One bar where `A7` and `V7/ii` describe the same sound. Both are kept, each with its normalized meaning, with the key held as a region rather than as a label. |
| `example3.py` | What each encoding cannot say | The capability question, counted per format. Humdrum loses nothing. MusicXML keeps the chord symbols and has nowhere to put the function or the key. DCML and RomanText are the mirror image. |
| `example4.py` | Export, and what the round-trip lost | The measured question: write the file, read it back, diff it. Includes the Humdrum export itself, two spines side by side. |

## The example used

All four read `../examples/flagship_love_walked_in.hamon` — *Love Walked In*
(Gershwin), the closing phrase, with the chord symbols and a Roman analysis of the
same bars, time-aligned. That pairing is what makes the loss story legible: a format
that carries only one of the two readings is visibly missing the other, and Humdrum
is lossless precisely because it has a spine for each.

`example1.py` also reads `../examples/changes.lab`, a Harte annotation, to make the
"any encoding in" claim with a second, unrelated notation.

## Relationship with `icccm26/snippets.py`

`snippets.py` holds the **trimmed** text of the same four boxes, sized for the poster
and with its expected output as comments. These scripts are the long form: same API,
same files, plus the docstring explaining what the box is arguing. Change one and
check the other.
