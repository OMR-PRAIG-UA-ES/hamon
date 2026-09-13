#!/usr/bin/env python
"""Thin launcher so the demo runs without installing the package.

    cd publications/ICCCM26 && python run.py [--snippets] [--no-figures]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icccm26.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
