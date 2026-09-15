# hamonpy

We implement the **HAMON** standard — **Ha**rmony **Mo**del and **N**otation — in Python.

We design this module to work well in a conda environment.

## We install

```bash
pip install hamonpy
```

This package lives in the `hamonpy/` subdirectory of the
[repository](https://github.com/OMR-PRAIG-UA-ES/hamon) (the repository root is not a
Python package). To run it from a checkout, with the test dependencies, install it
editable from the repository root:

```bash
conda create -n hamonpy python=3.11
conda activate hamonpy
python -m pip install -e "./hamonpy[dev]"
```

Questions and bug reports go to the
[issue tracker](https://github.com/OMR-PRAIG-UA-ES/hamon/issues).

## We run unit tests

```bash
pytest -q
```

## We parse

We ship an **ANTLR4-based parser** generated from the normative grammars (`antlr/hamonLexer.g4` + `antlr/hamonParser.g4`, kept in sync with `grammar/hamon.ebnf`). It parses the full HAMON surface — chord symbols, Roman numerals, Nashville, figured bass, functional labels, positions, alternatives, and rendering dictionaries — into the typed AST in `hamonpy/ast.py`. Labels that can't be parsed with confidence are preserved losslessly as `unparsedHarmony`.
