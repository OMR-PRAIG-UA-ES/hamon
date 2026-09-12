#!/usr/bin/env bash
# Regenerate hamonpy/generated/antlr/ from the shared ANTLR4 grammars.
# Run from the hamonpy/ directory: ./antlr.sh
set -e

if ! command -v antlr4 >/dev/null 2>&1; then
  echo "antlr4 not found on PATH. Skipping regeneration (using checked-in generated parser)."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/hamonpy/hamonpy/generated/antlr"

echo "Removing old generated files..."
rm -f "$OUT"/hamon*.py "$OUT"/hamon*.interp "$OUT"/hamon*.tokens
# Some antlr4 versions append the grammar's parent dir to -o, leaving a stale
# nested copy in $OUT/antlr/ — clean it up so only $OUT holds the parser.
rm -rf "$OUT/antlr"

echo "Generating Python parser..."
# Run from the grammar directory so antlr4 never appends "antlr/" to -o.
# -lib on the parser step makes it read the freshly generated hamonLexer.tokens
# from $OUT (never a stale copy lying next to the grammars).
(cd "$ROOT/antlr" && antlr4 -Dlanguage=Python3 -o "$OUT" -visitor hamonLexer.g4)
(cd "$ROOT/antlr" && antlr4 -Dlanguage=Python3 -o "$OUT" -lib "$OUT" -visitor hamonParser.g4)

echo "Done. Generated files in $OUT/"
