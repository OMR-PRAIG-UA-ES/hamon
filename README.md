# HAMON

**HAMON** — **Ha**rmony **Mo**del and **N**otation — is a universal, lossless harmony-label
standard: one typed model for chord
symbols, Roman numerals, Nashville numbers, figured bass and functional analysis, that
round-trips across MEI · MusicXML · Humdrum · LilyPond · ABC · MuseScore · Harte ·
iReal Pro · DCML · RomanText · Dezrann.

> **Paper:** *"Bridging harmonic representations through a multi-modal encoding."* —
> presented at **[ICCCM 2026](https://digital.musicology.org/icccm-2026/)** (Würzburg,
> 21–23 September 2026).
> Patricia Garcia-Iasci (Universidad de Alicante / Universidad de Salamanca),
> Johannes Hentschel (Anton Bruckner University, Linz),
> Fabian C. Moss (Julius-Maximilians-Universität Würzburg),
> David Rizo (Universidad de Alicante; Instituto Superior de Enseñanzas Artísticas de la
> Comunidad Valenciana).

**[Browse the site](https://omr-praig-ua-es.github.io/hamon/)** — the examples exported to
every encoding, an interactive loss viewer, and the fixture corpus.

## Install

```bash
pip install hamonpy
```

```python
from hamonpy.cli import convert_text
from hamonpy.serialize import sequence_to_json
from hamonpy.report import lossy_report, WRITERS

seq = convert_text("@cs\nDm7\nG7\nCmaj7\nA7[of:ii]", "hamon")  # one label per line
print(sequence_to_json(seq))                      # canonical HAMON JSON
for fmt in WRITERS:                               # export to every encoding + measure loss
    rep = lossy_report(seq, fmt)
    print(fmt, rep.semantic, rep.notational, rep.lossless)
```

Getting started, with the command line too:
<https://omr-praig-ua-es.github.io/hamon/use.html>

## What is here

| | |
|---|---|
| `grammar/` | the normative EBNF, and the JSON schema for the canonical form |
| `antlr/` | the ANTLR grammars the parsers are generated from |
| `conformance/` | the cross-implementation corpus and its golden output |
| `fixtures/` | the conformance suite, one directory per case |
| `hamonpy/` | the Python reference implementation |
| `documentation/` | one document per format, plus the tutorial and the CLI reference |
| `mei-customization/` | the ODD for carrying HAMON labels in MEI |
| `datasets/` | a registry of corpora HAMON reads — pointers and licences, never the data |

## Issues

This repository is a **published mirror**: it is regenerated from a working repository,
so pull requests here would be overwritten. **Issues are the way in** — bug reports,
questions about the standard, and formats you would like covered are all welcome, and
they are read. This is research software, offered as is, with no support commitment.

## Citing

See [`CITATION.cff`](CITATION.cff), or the paper above. Both licences ask for attribution.

## License

Copyright © 2026 **Universidad de Alicante**. The code is **Apache-2.0**; the standard and
its data (grammar, schema, conformance corpus, fixtures, documentation) are **CC BY 4.0**.
See [`LICENSE`](LICENSE). Corpora that HAMON reads keep their own terms.
