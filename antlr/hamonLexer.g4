lexer grammar hamonLexer;

/* --- separators --- */
COMMA : ',' ;
PIPE  : '|' ;
EOL    : '\r'? '\n' ;
WS    : [ \t]+ -> skip ;

/* --- directives --- */
VERSION_DECL : '@version:' [0-9]+ ('.' [0-9]+)* ;  // e.g. @version:0.1.0 — precedes AT by longest-match
METER_DECL : '@meter:' ;                            // v0.4.0 time-signature directive — precedes AT by longest-match
KEY_DECL : '@key:' ;                               // v0.2.0 tonal-region directive — precedes AT by longest-match
SCALE_DECL : '@scale:' ;                            // chord-scale(s) for the current region — precedes AT by longest-match
AT    : '@' ;

/* --- v0.4 time-aligned group position (leading, comma-separated) --- */
MEAS : 'm:' [0-9]+ ;                                // measure number, e.g. m:25
TS   : 'ts:' [0-9]+ ('.' [0-9]+)? ;                // timestamp/beat — MEI data.BEAT, 1-based decimal, e.g. ts:2.5
TABS : 't:' [0-9]+ ('/' [0-9]+)? ;                 // absolute position in QUARTER notes, e.g. t:5/4
SECS : 's:' [0-9]+ ('.' [0-9]+)? ;                 // v0.5: physical time in SECONDS, e.g. s:12.34
REF  : 'ref:' ~[ \t\r\n|,]+ ;                       // score-object id, e.g. ref:note-9

/* --- punctuation used inside labels --- */
LPAREN: '(' ;
RPAREN: ')' ;
LBRACK: '[' ;              // v0.2.0 analytical attributes
RBRACK: ']' ;
COLON : ':' ;             // v0.2.0 layer tag / mode suffix / attribute argument
SLASH : '/' ;
DASH  : '-' ;               // hyphen-minus (used structurally and as minor marker)
ARROW : '->' ;

/* --- quoted text --- */
QUOTED_TEXT : '"' (~["\r\n])* '"' ;

/* --- no-chord --- */
NOCHORD
  : ('N' '.'? 'C' '.'?) | ('n' '.'? 'c' '.'?) | 'NoChord'
  ;

/* --- system ids for @prefix --- */
SYSTEM_ID : 'auto' | 'cs' | 'rn' | 'ns' | 'fb' | 'fun' | 'text' ;

/* --- pitch core --- */
NOTE : [A-G] ;

/* Unicode + ASCII accidentals (we keep token text for lossless rendering) */
SHARP      : '#' | '♯' ;
FLAT       : 'b' | '♭' ;
DBLSHARP   : 'x' | '𝄪' ;
DBLFLAT    : '𝄫' ;
NATURAL    : '♮' | 'n' ;

/* chord-quality & symbols (surface variants) */
DELTA   : 'Δ' ;
DEGREE  : '°' ;
HALF_DIM: 'ø' ;
PLUS    : '+' ;

/* analytical-layer keywords (v0.2.0). These multi-letter literals win by
   maximal-munch over the single-letter quality tokens (m, b, o) and ROMAN
   (i, v), so 'bass', 'melodic', 'minor', 'ionian', … tokenize atomically. */
/* v0.4 analytical layer tags carry the colon so they win by maximal-munch and never
   clash with a bare system id (`@cs` = AT SYSTEM_ID; `cs:C` = LAYERTAG). */
LAYERTAG : 'cs:' | 'rn:' | 'ns:' | 'fb:' | 'fn:' | 'melodic:' | 'tone:' | 'key:' ;
MODE  : 'ionian' | 'dorian' | 'phrygian' | 'lydian' | 'mixolydian' | 'aeolian' | 'locrian' | 'major' | 'minor' ;

/* common words (must come before WORD) */
MAJ : 'maj' | 'Maj' | 'MAJ' | 'M' ;
MIN : 'min' | 'Min' | 'MIN' | 'm' ;
DIM : 'dim' | 'Dim' | 'DIM' | 'o' ;
AUG : 'aug' | 'Aug' | 'AUG' ;
ADD : 'add' | 'Add' | 'ADD' ;
OMIT: 'omit' | 'Omit' | 'OMIT' ;
NO  : 'no' | 'No' | 'NO' ;
SUS : 'sus' | 'Sus' | 'SUS' ;

/* functional tokens */
T  : 'T' ;
S  : 'S' ;
D  : 'D' ;
PD : 'PD' ;
SD : 'SD' ;
DD : 'DD' ;

/* roman numeral token */
ROMAN
  : 'I''I''I'?
  | 'I''V'
  | 'V''I''I'?
  | 'V'
  | 'I'
  | 'i''i''i'?
  | 'i''v'
  | 'v''i''i'?
  | 'v'
  | 'i'
  ;

/* roman numeral fused with the ASCII diminished mark ('viio7', 'iio'). Needed because
   WORD's maximal munch would otherwise swallow 'viio' whole and knock the label out of
   romanNumeral — the normative EBNF (rnDegree + qualityMark 'o') allows this surface. */
ROMAN_DIM
  : ('III' | 'II' | 'IV' | 'VII' | 'VI' | 'V' | 'I'
    | 'iii' | 'ii' | 'iv' | 'vii' | 'vi' | 'v' | 'i') 'o'
  ;

/* number token */
INT : [0-9]+ ;

/* fallback word */
WORD : [A-Za-z]+ ;

/* ultimate fallback: we keep anything else losslessly (1 char) */
OTHER : . ;
