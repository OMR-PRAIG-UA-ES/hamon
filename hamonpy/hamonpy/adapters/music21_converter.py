"""Register ``.hamon`` as a native music21 I/O format.

After calling :func:`register_hamon_format`, a hamon surface can be loaded and
written with music21's own ``converter`` machinery — treating ``.hamon`` like
any other format (MusicXML, ABC, MIDI, …):

    from hamonpy.adapters.music21_converter import register_hamon_format
    register_hamon_format()

    from music21 import converter
    s = converter.parse("@cs\\nC\\nF\\nG7", format="hamon")   # → Stream
    s = converter.parse("song.hamon")                          # by extension
    s.write("hamon", fp="out.hamon")                           # Stream → .hamon

Parsing routes through :func:`hamon_to_music21_stream` (so roman numerals resolve
against the sequence's analytical key regions); writing routes through
:func:`music21_stream_to_hamon` + :func:`sequence_to_hamon_text`.

Requires: music21 >= 9 (``pip install hamonpy[music21]``).
"""
from __future__ import annotations

from typing import Optional

from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_hamon_text
from .music21_adapter import hamon_to_music21_stream, music21_stream_to_hamon


def _subconverter_base():
    """Return the music21 ``SubConverter`` base class (raises if music21 absent)."""
    try:
        from music21.converter.subConverters import SubConverter
    except ImportError as e:  # pragma: no cover - exercised only without music21
        raise ImportError(
            "music21 is required: pip install hamonpy[music21]"
        ) from e
    return SubConverter


def _build_converter_class():
    SubConverter = _subconverter_base()

    class HamonConverter(SubConverter):
        """music21 SubConverter for the hamon surface format (``.hamon``)."""

        registerFormats = ("hamon",)
        registerInputExtensions = ("hamon",)
        registerOutputExtensions = ("hamon",)

        def parseData(self, dataString, number: Optional[int] = None):
            """Parse hamon surface text into a music21 ``Stream``."""
            seq = parse_hamon_sequence(dataString)
            self.stream = hamon_to_music21_stream(seq)
            return self.stream

        def write(self, obj, fmt, fp=None, subformats=(), **keywords):
            """Serialize a music21 ``Stream`` to ``.hamon`` surface text."""
            hint = keywords.get("sequenceSystemHint", "cs")
            seq = music21_stream_to_hamon(obj, sequence_system_hint=hint)
            data = sequence_to_hamon_text(seq)
            return self.writeDataStream(fp, data)

    return HamonConverter


# The class is built lazily so that importing this module never hard-requires
# music21; only ``register_hamon_format()`` (or accessing the class) needs it.
HamonConverter = None  # type: ignore[assignment]


def register_hamon_format():
    """Register the hamon SubConverter with music21's global ``converter``.

    Idempotent: returns the ``HamonConverter`` class. After this call,
    ``converter.parse(..., format="hamon")``, parsing ``*.hamon`` files by
    extension, and ``stream.write("hamon", fp=...)`` all work.
    """
    global HamonConverter
    from music21 import converter

    if HamonConverter is None:
        HamonConverter = _build_converter_class()

    if HamonConverter not in converter.Converter.subConvertersList():
        converter.registerSubConverter(HamonConverter)
    return HamonConverter
