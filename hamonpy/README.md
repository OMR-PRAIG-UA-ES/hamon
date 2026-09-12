# hamonpy

We implement the **HAMON** standard — **Ha**rmony **Mo**del and **N**otation — in Python.

We design this module to work well in a conda environment.

## We install

This package lives in the `hamonpy/` subdirectory of the repo (the repo root is not a
Python package).

**Using it** — once published to PyPI (after ICCCM'26):

```bash
pip install hamonpy
```

**Contributing** (and the only way until the PyPI release) — clone the full repo and
install editable with the dev extra, from the repository root:

```bash
conda create -n hamonpy python=3.11
conda activate hamonpy
python -m pip install -e "./hamonpy[dev]"
```

Changes land through **pull requests** (branch, push, open a PR — no direct commits to
`main`); see [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full workflow.

## We run unit tests

```bash
pytest -q
```

## We parse

We ship an **ANTLR4-based parser** generated from the normative grammars (`antlr/hamonLexer.g4` + `antlr/hamonParser.g4`, kept in sync with `grammar/hamon.ebnf`). It parses the full HAMON surface — chord symbols, Roman numerals, Nashville, figured bass, functional labels, positions, alternatives, and rendering dictionaries — into the typed AST in `hamonpy/ast.py`. Labels that can't be parsed with confidence are preserved losslessly as `unparsedHarmony`.
