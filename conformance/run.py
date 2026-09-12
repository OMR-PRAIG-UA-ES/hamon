#!/usr/bin/env python3
"""Cross-implementation conformance — Python golden generator.

Reads conformance/corpus.txt, parses each label with hamonpy's
parse_hamon_sequence, and writes the canonical JSON dump to
conformance/py_output.json. That file is the **golden**: the canonical
semantics that any implementation of the standard must reproduce.

Regenerate the golden after any grammar or normalization change here:

    conda activate hamonpy && python conformance/run.py
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

from hamonpy.parse import parse_hamon_sequence

HERE = Path(__file__).resolve().parent


def _to_plain(value):
    """Recursively convert dataclasses to dicts, drop None/empty, sort keys."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        out = {}
        for key in sorted(value.keys()):
            v = _to_plain(value[key])
            if v is None:
                continue
            if isinstance(v, (list, dict)) and len(v) == 0:
                continue
            out[key] = v
        return out
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


def dump_label(label_text: str):
    try:
        seq = parse_hamon_sequence(label_text)
        if not seq.groups or not seq.groups[0].primary:
            return {"error": "no-label"}
        label = seq.groups[0].primary[0]
        # `attributes` is dumped too (since v0.4.1). It was left out, so the bracketed
        # analytical attributes — `[of:V]`, `[scale:…]`, `[inv:…]`, and now the extent
        # `[dur:…]`/`[endref:…]` — were never compared across implementations: a label
        # matched the golden as long as its *chord* did, whatever it made of the
        # brackets. Anything the golden does not dump, no implementation is held to.
        # The group's `position` is dumped too (since v0.5), for the same reason: the
        # position items are the one part of a line that lives on the GROUP, so while
        # they went undumped an implementation could ignore `s:`/`t:`/`m:` entirely and
        # still match. Absent for the corpus lines that state no position.
        return _to_plain(
            {
                "semantic": label.semantic,
                "detectedSystem": label.detected_system,
                "system": label.system,
                "rendering": label.rendering,
                "attributes": label.attributes,
                "position": seq.groups[0].position,
            }
        )
    except Exception as e:  # noqa: BLE001 - we want to record any failure
        return {"error": f"{type(e).__name__}: {e}"}


def load_corpus() -> list[str]:
    text = (HERE / "corpus.txt").read_text(encoding="utf8")
    labels = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            labels.append(s)
    return labels


def main() -> int:
    labels = load_corpus()
    py_out = {label: dump_label(label) for label in labels}
    (HERE / "py_output.json").write_text(
        json.dumps(py_out, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    errors = {k: v for k, v in py_out.items() if isinstance(v, dict) and "error" in v}
    print(f"Corpus: {len(labels)} labels -> wrote conformance/py_output.json")
    if errors:
        print(f"⚠ {len(errors)} label(s) failed to parse:")
        for label, v in errors.items():
            print(f"  {label!r}: {v['error']}")
        return 1
    print("✔ All labels parsed. Golden written to conformance/py_output.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
