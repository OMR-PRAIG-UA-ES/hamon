"""Jazz Harmony Treebank adapter — DCMLab JazzHarmonyTreebank `treebank.json`.

The treebank is a JSON list of tunes; each has a `chords` list in Leadsheet/iRealPro
syntax (`D7`, `G^7`, `F#m7`, `Em7`, `Bm`, `Am7`, …). This adapter maps one tune's
chord list to a HamonSequence of chord symbols by translating the Leadsheet quality
sigils to hamon's and reusing the chord-symbol parser.

    ^  major (maj7)     -  minor      o  diminished
    h  half-diminished  +  augmented  (else: leave as written)

Used by the jazz-harmony-treebank use-case; see `datasets/manifest.json`.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from hamonpy.ast import HamonSequence, HarmonyGroup
from hamonpy.parse import parse_hamon_sequence

_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)$")


def leadsheet_chord_to_hamon_surface(chord: str) -> str:
    """Translate a treebank/Leadsheet chord token to a hamon chord-symbol surface."""
    m = _ROOT_RE.match(chord.strip())
    if not m:
        return chord.strip()
    root, qual = m.group(1), m.group(2)
    # Quality sigils → hamon equivalents (order matters: 'h' before generic).
    qual = qual.replace("^", "maj").replace("h", "ø").replace("o", "°")
    # Leadsheet '-' = minor; hamon also accepts '-', keep it.
    return root + qual


def treebank_tune_to_hamon(tune: Dict) -> HamonSequence:
    """Convert one treebank tune (dict with a `chords` list) to a HamonSequence."""
    groups: List[HarmonyGroup] = []
    for chord in tune.get("chords", []):
        surface = leadsheet_chord_to_hamon_surface(chord)
        sub = parse_hamon_sequence("@cs\n" + surface)
        if sub.groups and sub.groups[0].primary:
            groups.append(HarmonyGroup(primary=[sub.groups[0].primary[0]]))
    return HamonSequence(groups=groups, sequence_system_hint="cs")


def treebank_json_to_hamon(data, title: Optional[str] = None) -> HamonSequence:
    """Convert a treebank (path, JSON text, parsed list, or single tune dict).

    With `title`, return that tune; otherwise the first tune. Use
    `treebank_tunes()` to iterate the whole corpus.
    """
    tunes = _load_tunes(data)
    if not tunes:
        return HamonSequence(groups=[])
    if title is not None:
        tune = next((t for t in tunes if t.get("title") == title), tunes[0])
    else:
        tune = tunes[0]
    return treebank_tune_to_hamon(tune)


def treebank_tunes(data) -> List[Dict]:
    """Return the raw list of tune dicts (each has title/chords/key/…)."""
    return _load_tunes(data)


def _load_tunes(data) -> List[Dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    text = data
    if isinstance(data, str) and ("\n" not in data and data.strip().endswith(".json")):
        with open(data, encoding="utf-8") as fh:
            text = fh.read()
    obj = json.loads(text)
    return obj if isinstance(obj, list) else [obj]
