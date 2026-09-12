"""DCML TSV annotation adapter.

Reads DCML-annotated TSV files (Hentschel et al., used in the DCMLab corpora)
and converts them to HamonSequence, and vice versa.

Column reference:
  chord, numeral, form, figbass, changes, relativeroot, localkey, globalkey
"""
from __future__ import annotations

import csv
import io
import re
from typing import Dict, List, Optional, Tuple

from hamonpy.ast import (
    AppliedFunction,
    HamonSequence,
    HarmonyAttributes,
    HarmonyGroup,
    HarmonyLabel,
    Key,
    PitchClass,
    RomanSemantic,
    RenderingHints,
    TonalRegion,
)
from hamonpy.normalize import degree_to_pitch, normalize_roman_from_parts, pitch_to_degree


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

_FORM_TO_TAIL_PREFIX: Dict[str, str] = {
    "M": "",    # explicitly major — no tail prefix needed
    "m": "m",
    "o": "°",
    "+": "+",
    "%": "ø",
}


def _dcml_row_to_surface(row: Dict[str, str]) -> Optional[str]:
    """Reconstruct a hamon surface string from a DCML TSV row.

    Returns None for non-chord rows (e.g. phrase boundaries marked with `@`).
    """
    chord = (row.get("chord") or "").strip()
    if not chord or chord.startswith("@") or chord == ".":
        return None
    return chord


def _dcml_surface_to_roman(surface: str) -> Optional[Tuple[RomanSemantic, RenderingHints]]:
    """Parse a DCML chord surface string into a RomanSemantic.

    DCML surfaces look like: ``V7/IV``, ``ii%43``, ``bII``, ``#+IV65``.
    """
    # Extract secondary (denominator after final '/')
    secondary: Optional[str] = None
    slash_pos = surface.rfind("/")
    if slash_pos > 0:
        secondary = surface[slash_pos + 1:].strip()
        surface = surface[:slash_pos].strip()

    # Extract prefix accidentals (#, b, bb, #b, …)
    prefix_m = re.match(r"^([#b♭♯𝄫𝄪]*)", surface)
    prefix_raw = prefix_m.group(1) if prefix_m else ""
    surface = surface[len(prefix_raw):]
    prefix_accidentals: List[str] = list(prefix_raw)

    # Extract Roman numeral degree
    degree_m = re.match(r"(III|VII|IV|VI|II|I|iii|vii|iv|vi|ii|i|v|V)", surface)
    if not degree_m:
        return None
    degree = degree_m.group(1)
    tail_raw = surface[len(degree):]

    # Map DCML form+figbass tail tokens to hamon tail string
    tail = _normalize_dcml_tail(tail_raw)

    return normalize_roman_from_parts(
        degree=degree,
        prefix_accidentals=prefix_accidentals,
        tail=tail,
        secondary=secondary,
    )


def _normalize_dcml_tail(tail_raw: str) -> str:
    """Convert a raw DCML tail (form + figbass + changes) to a hamon tail.

    Examples: ``m7`` → ``m7``, ``%43`` → ``ø43``, ``M7`` → ``maj7``,
    ``o7`` → ``°7``, ``+`` → ``+``.
    """
    t = tail_raw.strip()
    if not t:
        return ""
    # Explicit major seventh shorthand
    if t in ("M7", "Maj7", "maj7"):
        return "maj7"
    # Replace form sigils
    t = t.replace("%", "ø").replace("o", "°")
    # 'M' alone means major (no change needed in tail)
    t = re.sub(r"^M(?=[^a-z]|$)", "", t)
    return t


# ---------------------------------------------------------------------------
# Public API — parsing
# ---------------------------------------------------------------------------

def dcml_tsv_to_hamon(path: str) -> HamonSequence:
    """Parse a DCML TSV file and return a HamonSequence.

    Each non-empty chord row becomes one HarmonyGroup (one primary label).
    The `@rn` system hint is set automatically.
    """
    with open(path, encoding="utf-8") as fh:
        return _parse_dcml_stream(fh)


def dcml_tsv_text_to_hamon(text: str) -> HamonSequence:
    """Parse DCML TSV text (already loaded) into a HamonSequence."""
    return _parse_dcml_stream(io.StringIO(text))


# ---------------------------------------------------------------------------
# Key / region helpers (localkey / relativeroot → TonalRegion)
# ---------------------------------------------------------------------------

_GLYPH_TO_ACC = {"#": "sharp", "♯": "sharp", "b": "flat", "♭": "flat", "𝄪": "double-sharp", "𝄫": "double-flat"}
_KEY_RE = re.compile(r"^([A-Ga-g])([#b♯♭𝄪𝄫]*)$")
_ROMAN_KEY_RE = re.compile(r"^([#b♯♭𝄪𝄫]*)(III|VII|IV|VI|II|I|iii|vii|iv|vi|ii|i|v|V)")


def _accs_to_accidental(accs: str):
    if accs in ("##", "𝄪"):
        return "double-sharp"
    if accs in ("bb", "𝄫"):
        return "double-flat"
    if accs[:1] in ("#", "♯"):
        return "sharp"
    if accs[:1] in ("b", "♭"):
        return "flat"
    return None


def _parse_dcml_global_key(s: str) -> Optional[Key]:
    """DCML globalkey is a key name (case = mode): 'C'=C major, 'a'=A minor, 'F#', 'eb'."""
    m = _KEY_RE.match(s.strip())
    if not m:
        return None
    letter, accs = m.group(1), m.group(2)
    mode = "major" if letter.isupper() else "minor"
    acc = _accs_to_accidental(accs) if accs else None
    return Key(tonic=PitchClass(note=letter.upper(), accidental=acc), mode=mode)


def _split_dcml_roman(s: str):
    """A DCML degree (localkey/relativeroot): optional accidentals + Roman; case = mode.
    Returns (acc_glyphs, roman, mode) or None."""
    m = _ROMAN_KEY_RE.match(s.strip())
    if not m:
        return None
    accs = list(m.group(1))
    roman = m.group(2)
    mode = "major" if roman[0].isupper() else "minor"
    return accs, roman, mode


def _key_from_degree(parent: Optional[Key], degree_str: str, label: str) -> Optional[Key]:
    """Resolve a DCML Roman degree (relative to *parent*) to an absolute Key."""
    parsed = _split_dcml_roman(degree_str)
    if not parsed or parent is None:
        return None
    accs, roman, mode = parsed
    tonic = degree_to_pitch(parent, accs, roman)
    return Key(tonic=tonic, mode=mode, label=label)


def _parse_dcml_stream(stream) -> HamonSequence:
    reader = csv.DictReader(stream, delimiter="\t")

    groups: List[HarmonyGroup] = []
    regions: List[TonalRegion] = []
    global_key: Optional[Key] = None
    open_local_idx: Optional[int] = None
    open_ton_idx: Optional[int] = None
    cur_localkey: Optional[str] = None
    cur_relroot: Optional[str] = None

    for row in reader:
        surface = _dcml_row_to_surface(row)
        if surface is None:
            continue
        result = _dcml_surface_to_roman(surface)
        if result is None:
            continue
        semantic, rendering, _detected = result

        gi = len(groups)
        if global_key is None and (row.get("globalkey") or "").strip():
            global_key = _parse_dcml_global_key(row["globalkey"])

        # localkey → tonal region (first = home key, later changes = modulations)
        lk = (row.get("localkey") or "").strip()
        if lk and lk != cur_localkey:
            if open_ton_idx is not None and gi > 0:
                regions[open_ton_idx].to_group = gi - 1
                open_ton_idx = None
            if open_local_idx is not None and gi > 0:
                regions[open_local_idx].to_group = gi - 1
            local_key = _key_from_degree(global_key, lk, lk) or (global_key or Key(tonic=PitchClass(note="C")))
            regions.append(TonalRegion(
                key=local_key, kind=("key" if open_local_idx is None else "modulation"), from_group=gi,
            ))
            open_local_idx = len(regions) - 1
            cur_localkey = lk
            cur_relroot = None

        label = HarmonyLabel(
            surface=surface, semantic=semantic, rendering=rendering,
            detected_system="rn", system="rn", sequence_system_hint="rn",
        )

        # relativeroot → tonicization region (nested) + applied function on the chord
        rr = (row.get("relativeroot") or "").strip()
        if rr:
            if rr != cur_relroot:
                if open_ton_idx is not None and gi > 0:
                    regions[open_ton_idx].to_group = gi - 1
                parent_key = regions[open_local_idx].key if open_local_idx is not None else global_key
                ton_key = _key_from_degree(parent_key, rr, rr)
                if ton_key is not None:
                    regions.append(TonalRegion(
                        key=ton_key, kind="tonicization", from_group=gi,
                        degree=rr, parent=open_local_idx,
                    ))
                    open_ton_idx = len(regions) - 1
                cur_relroot = rr
            label.attributes = HarmonyAttributes(applied=AppliedFunction(target=rr), tonicizes=rr)
        else:
            if open_ton_idx is not None and gi > 0:
                regions[open_ton_idx].to_group = gi - 1
                open_ton_idx = None
            cur_relroot = None

        groups.append(HarmonyGroup(primary=[label]))

    return HamonSequence(groups=groups, sequence_system_hint="rn", regions=regions or None)


# ---------------------------------------------------------------------------
# Public API — exporting
# ---------------------------------------------------------------------------

_HAMON_ACC_TO_DCML: Dict[str, str] = {
    "#": "#", "b": "b", "bb": "bb", "♭": "b", "♯": "#", "𝄫": "bb", "𝄪": "##"
}


_ACC_GLYPH_TO_NAME = {"sharp": "#", "flat": "b", "double-sharp": "##", "double-flat": "bb"}


def _key_to_global_name(key: Key) -> str:
    """A Key → a DCML globalkey name (case = mode): C major→'C', A minor→'a', Ab major→'Ab'."""
    letter = key.tonic.note
    name = letter.upper() if (key.mode or "major") in ("major", "ionian") else letter.lower()
    return name + _ACC_GLYPH_TO_NAME.get(key.tonic.accidental or "", "")


def _region_for_group(regions, gi: int, kinds) -> Optional[TonalRegion]:
    """Innermost region of one of *kinds* whose span covers group index *gi*."""
    found = None
    for r in regions:
        if r.kind in kinds and r.from_group <= gi and (r.to_group is None or gi <= r.to_group):
            found = r  # later (more nested) regions win
    return found


def hamon_to_dcml_tsv(seq: HamonSequence) -> str:
    """Serialize a HamonSequence (Roman-numeral system) to DCML TSV text.

    Only RomanSemantic labels are exported; others are skipped. Columns:
    chord, numeral, form, figbass, changes, relativeroot — plus localkey and
    globalkey when the sequence carries tonal regions (the analytical layer).
    """
    regions = seq.regions or []
    home = _region_for_group(regions, 0, ("key", "region", "modulation"))
    global_key = home.key if home is not None else None

    rows: List[Dict[str, str]] = []
    for gi, group in enumerate(seq.groups):
        for label in group.primary:
            if not isinstance(label.semantic, RomanSemantic):
                continue
            row = _roman_to_dcml_row(label)

            if global_key is not None:
                local_region = _region_for_group(regions, gi, ("key", "region", "modulation"))
                local_key = local_region.key if local_region is not None else global_key
                row["localkey"] = pitch_to_degree(global_key, local_key.tonic, local_key.mode)
                row["globalkey"] = _key_to_global_name(global_key)

                ton_region = _region_for_group(regions, gi, ("tonicization",))
                if ton_region is not None and not row.get("relativeroot"):
                    row["relativeroot"] = ton_region.degree or pitch_to_degree(
                        local_key, ton_region.key.tonic, ton_region.key.mode
                    )

            rows.append(row)

    if not rows:
        return ""

    fieldnames = ["chord", "numeral", "form", "figbass", "changes", "relativeroot"]
    if global_key is not None:
        fieldnames += ["localkey", "globalkey"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, delimiter="\t",
                            lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _roman_to_dcml_row(label: HarmonyLabel) -> Dict[str, str]:
    sem: RomanSemantic = label.semantic  # type: ignore[assignment]
    degree = sem.degree
    prefix = "".join(_HAMON_ACC_TO_DCML.get(a, a) for a in (sem.prefixAccidentals or []))
    tail = sem.tail or ""
    secondary = sem.secondary or ""

    # Split tail into form, figbass, changes
    form, figbass, changes = _split_tail(tail)

    chord = f"{prefix}{degree}{form}{figbass}"
    if changes:
        chord += f"({changes})"
    if secondary:
        chord += f"/{secondary}"

    return {
        "chord": chord,
        # DCML's `numeral` includes the accidental (`bVII`, `#vii`); writing the bare
        # degree turned `bVII7` into a `VII` in the column a consumer reads.
        "numeral": f"{prefix}{degree}",
        "form": form,
        "figbass": figbass,
        "changes": changes,
        "relativeroot": secondary,
    }


def _split_tail(tail: str) -> Tuple[str, str, str]:
    """Split a hamon tail into DCML (form, figbass, changes) triple."""
    changes_m = re.search(r"\(([^)]+)\)", tail)
    changes = changes_m.group(1) if changes_m else ""
    tail_no_changes = re.sub(r"\([^)]*\)", "", tail).strip()

    # Detect form prefix
    form = ""
    fb = tail_no_changes
    if tail_no_changes.startswith("maj7") or tail_no_changes.startswith("Maj7"):
        form = "M"
        fb = "7"
    elif tail_no_changes.startswith("ø"):
        form = "%"
        fb = tail_no_changes[1:]
    elif tail_no_changes.startswith("°"):
        form = "o"
        fb = tail_no_changes[1:]
    elif tail_no_changes.startswith("+"):
        form = "+"
        fb = tail_no_changes[1:]
    elif tail_no_changes.startswith("m"):
        form = "m"
        fb = tail_no_changes[1:]

    return form, fb, changes
