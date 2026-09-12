"""ANTLR4 parse-tree visitor — bridges generated parser contexts to our AST."""
from __future__ import annotations

import re
from typing import List, Optional

from .generated.antlr.hamonParser import hamonParser
from .ast import (
    ChordSymbolSemantic, DetectedSystem, FiguredBassSemantic, Fraction, FunctionalSemantic,
    HamonSequence, HarmonyAttributes, HarmonyGroup, HarmonyLabel, Key, Meter, NashvilleSemantic,
    Position, RenderingHints, ScaleSpec, SequenceSystem, ToneSemantic, TonalRegion,
)
from .normalize import (
    normalize_chord_symbol_from_ctx,
    normalize_functional_from_chain,
    normalize_key_decl,
    normalize_no_chord,
    normalize_number_harmony_from_parts,
    normalize_roman_from_parts,
    normalize_text_from_surface,
    parse_analysis_attrs,
    resolve_layer,
)

_FUNC_TOKEN_RE = re.compile(r"^(T|S|D|PD|SD|DD)$")


def _resolve_system(hint: Optional[SequenceSystem], detected: DetectedSystem) -> DetectedSystem:
    if hint and hint != "auto":
        return hint  # type: ignore[return-value]
    return detected


def _normalize_atom(atom: hamonParser.HarmonyAtomContext):
    if atom.chordSymbol():
        cs = atom.chordSymbol()
        pitch_ctx = cs.pitch()
        note = pitch_ctx.NOTE().getText()
        acc_glyph = pitch_ctx.accidental().getText() if pitch_ctx.accidental() else None
        parts: List[str] = [p.getText() for p in cs.chordPart()]
        bass_note = bass_acc_glyph = None
        sb = cs.slashBass()
        if sb:
            bp = sb.pitch()
            bass_note = bp.NOTE().getText()
            bass_acc_glyph = bp.accidental().getText() if bp.accidental() else None
        return normalize_chord_symbol_from_ctx(note, acc_glyph, parts, bass_note, bass_acc_glyph)

    if atom.romanNumeral():
        rn = atom.romanNumeral()
        prefix_acc = [a.getText() for a in rn.rnAccidental()]
        tail = "".join(t.getText() for t in rn.rnTail())
        if rn.ROMAN() is not None:
            degree = rn.ROMAN().getText()
        else:
            # ROMAN_DIM lexes 'viio' as one token: split the ASCII diminished mark
            # back into the tail so 'viio7' ≡ 'vii' + tail 'o7'.
            fused = rn.ROMAN_DIM().getText()
            degree = fused[:-1]
            tail = "o" + tail
        secondary = None
        sec_ctx = rn.rnSecondary()
        if sec_ctx is not None:
            if sec_ctx.WORD() is not None:
                # maximal-munch lexed '/bVII' as one WORD (the flat is the letter 'b')
                secondary = sec_ctx.WORD().getText()
            else:
                sec_acc = "".join(a.getText() for a in sec_ctx.rnAccidental())
                sec_roman = sec_ctx.ROMAN() or sec_ctx.ROMAN_DIM()
                secondary = sec_acc + sec_roman.getText()
        return normalize_roman_from_parts(degree, prefix_acc, tail, secondary)

    if atom.numberHarmony():
        nh = atom.numberHarmony()
        prefix_acc = [a.getText() for a in nh.rnAccidental()]
        number = int(nh.INT().getText())
        tail = "".join(t.getText() for t in nh.numberTail())
        sec_ctx = nh.numberSecondary()
        secondary = sec_ctx.getText()[1:] if sec_ctx else None
        return normalize_number_harmony_from_parts(number, prefix_acc, tail, secondary)

    if atom.functionalHarmony():
        fh = atom.functionalHarmony()
        toks = fh.funcToken()
        if toks:  # chain form: funcToken (-> funcToken)+
            chain = [t.getText() for t in toks]
        else:  # single form: a lone functional token
            chain = [fh.funcSingleToken().getText()]
        return normalize_functional_from_chain(chain)

    if atom.noChord():
        return normalize_no_chord()

    tl = atom.textLabel()
    raw = tl.getText()
    quoted = raw.startswith('"') and raw.endswith('"')
    text = raw[1:-1] if quoted else raw
    return normalize_text_from_surface(text, quoted)


def _visit_harmony(ctx: hamonParser.HarmonyContext, hint: Optional[SequenceSystem],
                   original_input: str) -> HarmonyLabel:
    surface = ctx.getText()

    # Optional analytical layer tag (cs:, rn:, ns:, fb:, fn:, …). Keep the label's
    # `surface` bare (the tag lives in `layer`) so exporters see the chord glyphs.
    layer = None
    if ctx.layerTag():
        tag = ctx.layerTag().LAYERTAG().getText()  # e.g. "cs:"
        layer = resolve_layer(tag)
        if surface.startswith(tag):
            surface = surface[len(tag):]

    # Optional bracketed analytical attributes.
    attr_inners = [
        "".join(i.getText() for i in a.attrItem())
        for a in ctx.analysisAttr()
    ]
    attributes, tone = parse_analysis_attrs(attr_inners)

    atom = ctx.harmonyAtom()
    semantic, rendering, detected = _normalize_atom(atom)

    # On a `function:` layer a bare functional token is intended, but "D" is
    # shadowed by the NOTE lexer rule, so reinterpret it as a functional label.
    if layer == "function" and isinstance(semantic, ChordSymbolSemantic) and _FUNC_TOKEN_RE.match(atom.getText()):
        semantic = FunctionalSemantic(chain=[atom.getText()])
        detected = "fun"

    # On a `bass:` layer a number is a figured-bass figure, not a Nashville degree.
    if layer == "bass" and isinstance(semantic, NashvilleSemantic):
        semantic = FiguredBassSemantic(
            number=semantic.number,
            prefixAccidentals=semantic.prefixAccidentals,
            tail=semantic.tail,
        )
        detected = "fb"

    # A harmonic/non-harmonic tone annotation turns a bare pitch into a ToneSemantic.
    if tone is not None:
        pitch = semantic.root if isinstance(semantic, ChordSymbolSemantic) else None
        semantic = ToneSemantic(
            category=tone["category"],
            pitch=pitch,
            type=tone.get("type"),
        )

    system = _resolve_system(hint, detected)

    return HarmonyLabel(
        surface=surface,
        semantic=semantic,
        rendering=rendering if rendering is not None else RenderingHints(),
        detected_system=detected,
        system=system,
        sequence_system_hint=hint,
        layer=layer,
        attributes=attributes,
    )


def _visit_harmony_list(ctx: hamonParser.HarmonyListContext, hint: Optional[SequenceSystem],
                         original_input: str) -> List[HarmonyLabel]:
    return [_visit_harmony(h, hint, original_input) for h in ctx.harmony()]


def _position_from_items(items) -> Optional[Position]:
    """Build a Position from the leading position items: ``m:<measure>``,
    ``ts:<beat>`` (1-based decimal), ``t:<frac>`` (absolute, in quarter notes),
    ``s:<seconds>`` (physical time, v0.5), ``ref:<id>``."""
    measure = beat = time = seconds = ref = None
    for it in items or []:
        t = it.getText()
        if t.startswith("m:"):
            measure = int(t[2:])
        elif t.startswith("ts:"):
            beat = float(t[3:])
        elif t.startswith("s:"):
            seconds = float(t[2:])
        elif t.startswith("t:"):
            frac = t[2:]
            num, den = (frac.split("/", 1) + ["1"])[:2] if "/" in frac else (frac, "1")
            try:
                time = Fraction(int(num), int(den))
            except ValueError:
                pass
        elif t.startswith("ref:"):
            ref = t[4:] or None
    if measure is None and beat is None and time is None and seconds is None and ref is None:
        return None
    return Position(measure=measure, beat=beat, time=time, seconds=seconds, ref=ref)


def _visit_harmony_group(ctx: hamonParser.HarmonyGroupContext, hint: Optional[SequenceSystem],
                          original_input: str) -> HarmonyGroup:
    lists = ctx.harmonyList()
    primary = _visit_harmony_list(lists[0], hint, original_input)
    alternatives = [_visit_harmony_list(lst, hint, original_input) for lst in lists[1:]]
    position = _position_from_items(ctx.positionItem())
    return HarmonyGroup(primary=primary, alternatives=alternatives, position=position)


def _key_target_dict(kd: hamonParser.KeyDeclContext) -> dict:
    kt = kd.keyTarget()
    if kt.pitch():
        p = kt.pitch()
        return {
            "type": "pitch",
            "note": p.NOTE().getText(),
            "acc": p.accidental().getText() if p.accidental() else None,
        }
    if kt.ROMAN():
        return {
            "type": "roman",
            "accs": [a.getText() for a in kt.rnAccidental()],
            "roman": kt.ROMAN().getText(),
        }
    word_tok = kt.WORD() or kt.ROMAN_DIM()
    return {"type": "word", "text": word_tok.getText()}


def build_hamon_sequence(tree: hamonParser.StartContext, original_input: str) -> HamonSequence:
    version: Optional[str] = None
    vdecl = tree.versionDecl()
    if vdecl:
        version = vdecl.VERSION_DECL().getText()[len("@version:"):]  # type: ignore[union-attr]

    hint: Optional[SequenceSystem] = None
    decl = tree.systemDecl()
    if decl:
        hint = decl.SYSTEM_ID().getText()  # type: ignore[assignment]

    groups: List[HarmonyGroup] = []
    meters: List[Meter] = []
    regions: List[TonalRegion] = []
    open_key_index: Optional[int] = None
    open_ton_index: Optional[int] = None

    for line in tree.line():
        md = line.meterDecl()
        if md is not None:
            num, den = (int(n.getText()) for n in md.INT())
            meters.append(Meter(numerator=num, denominator=den, from_group=len(groups)))
            continue

        kd = line.keyDecl()
        if kd is not None:
            start_group = len(groups)
            parent_key = regions[open_key_index].key if open_key_index is not None else None
            mode_word = kd.modeSuffix().MODE().getText() if kd.modeSuffix() else None
            key, kind, degree = normalize_key_decl(_key_target_dict(kd), mode_word, parent_key)

            if kind == "key":
                if open_ton_index is not None and start_group > 0:
                    regions[open_ton_index].to_group = start_group - 1
                    open_ton_index = None
                if open_key_index is not None and start_group > 0:
                    regions[open_key_index].to_group = start_group - 1
                regions.append(TonalRegion(key=key, kind="key", from_group=start_group))
                open_key_index = len(regions) - 1
            else:
                if open_ton_index is not None and start_group > 0:
                    regions[open_ton_index].to_group = start_group - 1
                regions.append(TonalRegion(
                    key=key, kind="tonicization", from_group=start_group,
                    degree=degree, parent=open_key_index,
                ))
                open_ton_index = len(regions) - 1
            continue

        sd = line.scaleDecl()
        if sd is not None:
            scales = [ScaleSpec(name=sn.getText()) for sn in sd.scaleName()]
            target = open_ton_index if open_ton_index is not None else open_key_index
            if target is not None and scales:
                regions[target].scales = scales
            continue

        hg = line.harmonyGroup()
        if hg is not None:
            groups.append(_visit_harmony_group(hg, hint, original_input))

    return HamonSequence(
        groups=groups,
        sequence_system_hint=hint,
        version=version,
        meters=meters or None,
        regions=regions or None,
    )
