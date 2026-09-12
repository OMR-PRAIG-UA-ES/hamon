from __future__ import annotations

import re
import warnings
from typing import List

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from .generated.antlr.hamonLexer import hamonLexer
from .generated.antlr.hamonParser import hamonParser
from .ast import HamonSequence, HarmonyGroup
from .parse_visitor import build_hamon_sequence
from .validate import validate_positions


class HamonWarning(UserWarning):
    """A non-blocking HAMON validation warning (e.g. a ts outside its meter)."""


class _ThrowingErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise SyntaxError(f"Parse error at {line}:{column}: {msg}")


def _normalize_for_lexer(text: str) -> str:
    # Standardize dash/minus-like glyphs to ASCII '-'.
    return re.sub(r"[−‐‒–—]", "-", text)


def parse_hamon_sequence(text: str) -> HamonSequence:
    normalized = _normalize_for_lexer(text)
    stream = InputStream(normalized)

    lexer = hamonLexer(stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(_ThrowingErrorListener())

    tokens = CommonTokenStream(lexer)
    parser = hamonParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(_ThrowingErrorListener())

    tree = parser.start()
    seq = build_hamon_sequence(tree, text)

    # Non-blocking meter/position validation (v0.4.0).
    for message in validate_positions(seq):
        warnings.warn(message, HamonWarning, stacklevel=2)

    return seq


def parse_hamon(text: str) -> List[HarmonyGroup]:
    """Back-compat helper matching parseHamon()."""
    return parse_hamon_sequence(text).groups
