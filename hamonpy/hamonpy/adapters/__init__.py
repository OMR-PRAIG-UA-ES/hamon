"""We collect adapters for MEI, MusicXML, Humdrum/**kern, ABC, LilyPond, MuseScore, and music21."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from ..ast import HarmonyGroup

@dataclass
class Adapter:
    name: str
    from_: Callable[[Any], List[HarmonyGroup]]
    to: Callable[[List[HarmonyGroup]], Any]

registry: Dict[str, Adapter] = {}


def register(adapter: Adapter) -> None:
    registry[adapter.name] = adapter
