"""Physical time (v0.5): `s:<seconds>`, the clock HAMON was missing.

HAMON had metric (`m:`/`ts:`), musical absolute (`t:`) and structural (`ref:`) positions
and nothing in seconds, so Harte and JAMS — whose only positional data is audio time —
were imported with no position at all. `s:` is a fourth clock, not a replacement: the
clocks COEXIST and none is derived from another, because deriving one from another
launders an estimate into a fact. See `documentation/positions.md`.
"""
from __future__ import annotations

from hamonpy.adapters.harte import hamon_to_harte_text, harte_text_to_hamon
from hamonpy.adapters.jams import hamon_to_jams_dict, jams_to_hamon
from hamonpy.parse import parse_hamon_sequence
from hamonpy.serialize import sequence_to_dict, sequence_to_hamon_text


# ---------------------------------------------------------------------------
# Surface → AST
# ---------------------------------------------------------------------------

def test_seconds_are_read_as_a_position():
    pos = parse_hamon_sequence("@cs\ns:12.34,C").groups[0].position
    assert pos.seconds == 12.34


def test_whole_seconds_need_no_decimal_part():
    assert parse_hamon_sequence("@cs\ns:7,C").groups[0].position.seconds == 7.0


def test_every_clock_a_source_states_is_held_at_once():
    """The point of the feature. A multimodal source (audio plus a transcription) states
    the seconds AND the bar; before this, one of the two had to be thrown away."""
    pos = parse_hamon_sequence("@cs\nm:25,ts:1,t:96/1,s:48.5,ref:note-9,C").groups[0].position
    assert (pos.measure, pos.beat, pos.seconds, pos.ref) == (25, 1.0, 48.5, "note-9")
    assert (pos.time.numerator, pos.time.denominator) == (96, 1)


def test_seconds_are_not_confused_with_the_musical_clock():
    """`t:` is quarter notes and `s:` is seconds — adjacent syntax, different clocks.
    Neither is filled in from the other."""
    musical = parse_hamon_sequence("@cs\nt:5/4,C").groups[0].position
    physical = parse_hamon_sequence("@cs\ns:5,C").groups[0].position
    assert musical.seconds is None
    assert (musical.time.numerator, musical.time.denominator) == (5, 4)
    assert physical.time is None and physical.seconds == 5.0


# ---------------------------------------------------------------------------
# AST → surface, AST → JSON
# ---------------------------------------------------------------------------

def test_text_round_trip_is_stable():
    text = "@cs\ns:0,C\ns:2.5,F\ns:4.25,G7\n"
    assert sequence_to_hamon_text(parse_hamon_sequence(text)) == text


def test_the_items_are_written_in_grammar_order():
    text = "@cs\nm:2,ts:1.5,t:5/4,s:3.75,ref:n1,C\n"
    assert sequence_to_hamon_text(parse_hamon_sequence(text)) == text


def test_json_carries_the_seconds():
    """`report.py` diffs the canonical dicts, so a clock the JSON does not hold can never
    be reported as dropped."""
    position = sequence_to_dict(parse_hamon_sequence("@cs\ns:12.34,C"))["groups"][0]["position"]
    assert position == {"seconds": 12.34}


# ---------------------------------------------------------------------------
# The formats that only have this clock
# ---------------------------------------------------------------------------

def test_harte_lab_timestamps_survive_the_import():
    seq = harte_text_to_hamon("0.000000 1.500000 C:maj\n1.500000 3.000000 G:7\n")
    assert [g.position.seconds for g in seq.groups] == [0.0, 1.5]


def test_a_harte_line_without_columns_has_no_position():
    """Absent means unknown: a bare label list states no time, and none is invented."""
    seq = harte_text_to_hamon("C:maj\nG:7\n")
    assert all(g.position is None for g in seq.groups)


def test_jams_observation_times_survive_the_import():
    doc = {"annotations": [{"namespace": "chord", "data": [
        {"time": 0.0, "duration": 1.5, "value": "C:maj"},
        {"time": 1.5, "duration": 1.5, "value": "G:7"},
    ]}]}
    assert [g.position.seconds for g in jams_to_hamon(doc).groups] == [0.0, 1.5]


def test_jams_writes_back_the_stated_seconds_not_a_placeholder():
    seq = parse_hamon_sequence("@cs\ns:10.5,C\ns:14,G7")
    data = hamon_to_jams_dict(seq)["annotations"][0]["data"]
    assert [obs["time"] for obs in data] == [10.5, 14.0]


def test_jams_round_trips_the_audio_clock():
    doc = {"annotations": [{"namespace": "chord", "data": [
        {"time": 2.25, "duration": 1.75, "value": "D:min7"},
    ]}]}
    back = hamon_to_jams_dict(jams_to_hamon(doc))["annotations"][0]["data"]
    assert (back[0]["time"], back[0]["duration"]) == (2.25, 1.75)


# ---------------------------------------------------------------------------
# The extent inherits the clock: `[dur:1.85s]`
# ---------------------------------------------------------------------------

def test_a_suffixed_extent_is_seconds_and_a_bare_one_is_quarters():
    """One key, an optional suffix. The suffix is the whole difference between the two
    clocks, so a bare value must not silently become seconds or the reverse."""
    physical = parse_hamon_sequence("@cs\nC[dur:1.85s]").groups[0].primary[0].attributes
    musical = parse_hamon_sequence("@cs\nC[dur:3/4]").groups[0].primary[0].attributes
    assert (physical.durationSeconds, physical.duration) == (1.85, None)
    assert musical.durationSeconds is None
    assert (musical.duration.numerator, musical.duration.denominator) == (3, 4)


def test_an_unreadable_seconds_extent_is_ignored_not_guessed():
    """The shape is matched explicitly, so the exotic spellings `float()` would accept
    (`1e3s`, `nans`) are not extents. The TypeScript side mirrors the same pattern —
    a value one implementation reads and the other does not is a silent divergence."""
    for surface in ("C[dur:1e3s]", "C[dur:nans]", "C[dur:s]"):
        attrs = parse_hamon_sequence(f"@cs\n{surface}").groups[0].primary[0].attributes
        assert attrs is None or attrs.durationSeconds is None, surface


def test_a_seconds_extent_round_trips_through_the_text():
    text = "@cs\ns:0,C[dur:2.5s]\ns:2.5,G7[dur:1.75s]\n"
    assert sequence_to_hamon_text(parse_hamon_sequence(text)) == text


def test_json_carries_the_seconds_extent():
    attrs = sequence_to_dict(parse_hamon_sequence("@cs\nC[dur:1.85s]"))["groups"][0]["primary"][0]["attributes"]
    assert attrs == {"durationSeconds": 1.85}


def test_harte_states_the_end_so_the_extent_is_read_too():
    """`Harte → HAMON → Harte` used to lose 100% of the file's positional content; the
    start is the onset and `end - start` is the extent, both in the source's own clock."""
    label = harte_text_to_hamon("0.500000 2.000000 C:maj\n").groups[0].primary[0]
    assert label.attributes.durationSeconds == 1.5


def test_jams_duration_is_read_as_a_seconds_extent():
    doc = {"annotations": [{"namespace": "chord", "data": [
        {"time": 0.0, "duration": 1.5, "value": "C:maj"},
    ]}]}
    label = jams_to_hamon(doc).groups[0].primary[0]
    assert label.attributes.durationSeconds == 1.5


# ---------------------------------------------------------------------------
# Writing a `.lab` back: the columns are all-or-nothing
# ---------------------------------------------------------------------------

def test_a_lab_round_trips_through_hamon_unchanged():
    """What the clock work was for. This used to come back as a bare token list, losing
    100% of the file's positional content."""
    text = "0.000000\t1.500000\tC:maj\n1.500000\t3.500000\tG:7\n"
    assert hamon_to_harte_text(harte_text_to_hamon(text)) == text


def test_the_writer_states_the_end_it_was_given_not_the_next_onset():
    """The gap to the next group is a computation. Here it happens to differ from the
    stated extent — a rest between the two chords — and the file must say what the
    source said."""
    seq = parse_hamon_sequence("@cs\ns:0,C[dur:1s]\ns:2,G7[dur:1s]")
    assert hamon_to_harte_text(seq) == "0.000000\t1.000000\tC:maj\n2.000000\t3.000000\tG:7\n"


def test_one_untimed_harmony_drops_the_whole_file_to_bare_tokens():
    """A `.lab` is a positional-column format, so a half-timed file is not one. The
    seconds the other groups had are lost — honestly, and `report.py` says so."""
    seq = parse_hamon_sequence("@cs\ns:0,C[dur:1.5s]\nG7")
    assert hamon_to_harte_text(seq) == "C:maj\nG:7\n"


def test_an_onset_without_an_extent_is_not_enough():
    """The end is the one thing this writer will not invent."""
    seq = parse_hamon_sequence("@cs\ns:0,C\ns:1.5,G7")
    assert hamon_to_harte_text(seq) == "C:maj\nG:7\n"


def test_a_sequence_with_no_clock_at_all_is_unchanged():
    assert hamon_to_harte_text(parse_hamon_sequence("@cs\nC\nG7")) == "C:maj\nG:7\n"


def test_a_seconds_extent_is_never_read_as_quarter_notes():
    """The reason the two are separate fields: crossing the clocks needs a tempo map,
    so a target that speaks quarters must see the seconds extent as absent, not as a
    number it can use."""
    label = harte_text_to_hamon("0.000000 1.500000 C:maj\n").groups[0].primary[0]
    assert label.attributes.duration is None
