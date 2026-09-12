parser grammar hamonParser;

options { tokenVocab=hamonLexer; }

start
  : versionDecl? (EOL)* systemDecl? (EOL)* line ( (EOL)+ line )* (EOL)* EOF
  ;

/* v0.2.0: a line is an analytical directive (key/region) or a harmony group;
   v0.3.0 adds the chord-scale directive for the current region. */
line
  : meterDecl
  | keyDecl
  | scaleDecl
  | harmonyGroup
  ;

versionDecl
  : VERSION_DECL
  ;

systemDecl
  : AT SYSTEM_ID
  ;

/* group / list / alternative; v0.4: the time-aligned position is written FIRST,
   comma-separated with the labels, e.g. `m:25,ts:1,cs:C,rn:I`. */
harmonyGroup
  : (positionItem COMMA)* harmonyList (PIPE harmonyList)*
  ;

/* Position items: m:<measure>, ts:<beat> (MEI data.BEAT, 1-based decimal),
   t:<quarter-note fraction> (absolute musical time), s:<seconds> (v0.5, physical
   time — audio or a performance), ref:<score-object id>. They coexist: a position
   carries whichever clocks the source stated, and none is derived from another. */
positionItem
  : MEAS | TS | TABS | SECS | REF
  ;

harmonyList
  : harmony (COMMA harmony)*
  ;

/* v0.2.0: optional analytical layer tag prefix and bracketed attribute suffixes. */
harmony
  : layerTag? harmonyAtom analysisAttr*
  ;

harmonyAtom
  : noChord
  | functionalHarmony
  | chordSymbol
  | romanNumeral
  | numberHarmony
  | textLabel
  ;

/* v0.4 analytical layer tag: cs: rn: ns: fb: fn: (+ melodic:/tone:/key:). */
layerTag
  : LAYERTAG
  ;

/* bracketed analytical attributes; content kept permissive and preserved. */
analysisAttr
  : LBRACK attrItem+ RBRACK
  ;

attrItem
  : WORD | INT | ROMAN | ROMAN_DIM | NOTE | NO | SUS | MAJ | MIN | DIM | AUG | ADD | OMIT
  | MODE | COLON | SLASH | DASH
  | SHARP | FLAT | NATURAL | DBLSHARP | DBLFLAT | DELTA | DEGREE | HALF_DIM | PLUS
  | OTHER
  ;

/* ---------------- no chord ---------------- */
noChord
  : NOCHORD
  ;

/* ---------------- functional ----------------
   The dominant token 'D' collides with the NOTE lexer rule ([A-G]), which is
   declared first and so wins for a lone 'D'. Two forms disambiguate it:
     - chain form: an ARROW is present, and chord symbols never contain '->',
       so a NOTE here is unambiguously the functional 'D' (validated as such);
     - single form: a lone functional token, deliberately WITHOUT NOTE, so a
       bare 'D' stays a chord symbol (write a chain or `function:D` for a lone
       dominant). */
functionalHarmony
  : funcToken (ARROW funcToken)+
  | funcSingleToken
  ;

funcToken
  : T | S | D | PD | SD | DD | NOTE
  ;

funcSingleToken
  : T | S | PD | SD | DD
  ;

/* ---------------- meter / time signature (v0.4.0) ----------------
   "@meter:4/4", "@meter:2/2", "@meter:6/8". Declared at the start and at every
   metric change; fixes the valid range of ts (MEI data.BEAT): ts spans [1, N+1). */
meterDecl
  : METER_DECL INT SLASH INT
  ;

/* ---------------- key / tonal region (v0.2.0) ----------------
   "@key:C", "@key:A:minor", "@key:D:dorian", "@key:V" (tonicize a degree).
   The region applies to the following groups until the next keyDecl. */
keyDecl
  : KEY_DECL keyTarget modeSuffix?
  ;

keyTarget
  : pitch
  | rnAccidental* ROMAN
  | WORD            // maximal-munch lexes 'Bb', 'bVI', … as one WORD; split in the normalizer
  | ROMAN_DIM       // '@key:viio' — kept as an opaque word, like the WORD fallback
  ;

modeSuffix
  : COLON MODE
  ;

/* ---------------- chord-scale region directive (v0.3.0) ----------------
   "@scale:dorian", "@scale:lydian-dominant", "@scale:dorian,mixolydian".
   The scale(s) attach to the region opened by the preceding keyDecl. */
scaleDecl
  : SCALE_DECL scaleName (COMMA scaleName)*
  ;

scaleName
  : (MODE | WORD) ( DASH (MODE | WORD | INT) )*
  ;

/* ---------------- chord symbols ----------------
   We accept: CΔ7, Cmaj7, CM7, Cm7, C-7, C7(#11)/G, etc.
*/
chordSymbol
  : pitch chordPart* slashBass?
  ;

pitch
  : NOTE accidental?
  ;

accidental
  : SHARP | FLAT | DBLSHARP | DBLFLAT | NATURAL
  ;

slashBass
  : SLASH pitch
  ;

/* chordPart is permissive:
   we parse what we recognize and keep the rest (WORD/OTHER) to preserve surface.
*/
chordPart
  : seventhMark
  | qualityMark
  | extension
  | alteration
  | addOmitSus
  | parenGroup
  | WORD
  | OTHER
  ;

qualityMark
  : MAJ | MIN | DIM | AUG | DEGREE | HALF_DIM | PLUS | DASH
  ;

seventhMark
  : DELTA INT?
  | MAJ INT
  ;

extension
  : INT
  ;

alteration
  : (SHARP | FLAT | NATURAL | DBLSHARP | DBLFLAT) INT
  ;

addOmitSus
  : (ADD | OMIT | NO | SUS) INT?
  ;

parenGroup
  : LPAREN parenItem* RPAREN
  ;

parenItem
  : alteration
  | seventhMark
  | addOmitSus     // '(add9)', '(no3)', '(omit5)', '(sus4)' — keywords lex as their
                   // own tokens (ADD/OMIT/NO/SUS), never as WORD, so list them here
  | INT
  | WORD
  | qualityMark
  | SLASH
  | DASH
  | COMMA          // tension lists, e.g. (b9,b13,#11)
  | OTHER
  ;

/* ---------------- roman numerals ---------------- */
romanNumeral
  : rnAccidental* (ROMAN | ROMAN_DIM) rnTail* rnSecondary?
  ;

/* we reuse accidental tokens */
rnAccidental
  : SHARP | FLAT | DBLSHARP | DBLFLAT | NATURAL
  ;

rnTail
  : INT
  | qualityMark
  | WORD
  | OTHER
  ;

rnSecondary
  : SLASH rnAccidental* (ROMAN | ROMAN_DIM)
  | SLASH WORD       // maximal-munch lexes '/bVII', '/bII' tail as WORD; split in the normalizer
  ;

/* ---------------- number-based (ns or fb) ----------------
   We parse structure but we decide system later.
*/
numberHarmony
  : rnAccidental* INT numberTail* numberSecondary?
  ;

numberTail
  : (DASH INT)          // strong figured-bass signal: 6-5 etc
  | qualityMark
  | extension
  | alteration
  | addOmitSus
  | parenGroup
  | WORD
  | OTHER
  ;

numberSecondary
  : SLASH (INT | pitch)
  ;

/* ---------------- text (lossless) ---------------- */
textLabel
  : QUOTED_TEXT
  | rawRun
  ;

/* We consume any non-separator tokens into a raw label. A balanced parenGroup is
   matched as a unit so its inner COMMA (a tension list like WORD-led `Cm7(9,11)`)
   groups rather than separating the harmonyList — mirrors the NOTE-led chordSymbol
   path, where parenGroup already shields the comma. A stray '(' with no ')' falls
   back to the LPAREN rawAtom, so surface stays lossless. */
rawRun
  : (parenGroup | rawAtom)+
  ;

rawAtom
  : NOTE | ROMAN | ROMAN_DIM | INT | WORD | MODE
  | SHARP | FLAT | DBLSHARP | DBLFLAT | NATURAL
  | DELTA | DEGREE | HALF_DIM | PLUS | DASH
  | LPAREN | RPAREN | SLASH | COLON
  | OTHER
  ;
// NB: LBRACK/RBRACK are intentionally NOT raw atoms, so a trailing bracketed
// analytical attribute (e.g. Bb7[of:I], Em7b5[of:ii]) is parsed as analysisAttr
// at the `harmony` level rather than swallowed into a WORD-led text run.
