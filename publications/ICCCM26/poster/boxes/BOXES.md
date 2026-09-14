# Las cuatro cajas de código del póster

Columna derecha del A0. Cada caja lleva las cuatro cosas en este orden: **input · code · console · output**. Las etiquetas van en inglés porque se imprimen. Una caja cuyo resultado *es* la consola no repite un fichero de salida con lo mismo dentro.

Se regenera con `cd publications/ICCCM26/poster/boxes && python build.py`. Nada está tecleado a mano.


---

## 1 · Read any encoding

**input · in/dcml.tsv**

```
mn	mn_onset	quarterbeats	globalkey	localkey	chord	relativeroot
1	0	0	C	I	ii7	
2	0	4	C	I	V7	
3	0	8	C	I	IM7	
3	1/2	10	C	I	V7/ii	ii
```

**input · in/harte.lab**

```
0.000000 2.000000 D:min7
2.000000 4.000000 G:7
4.000000 8.000000 C:maj7
8.000000 10.000000 A:7
```

**input · in/humdrum.krn**

```
**mxhm	**kern
*M4/4	*M4/4
*C:	*C:
=1	=1
Dm7	4d
=2	=2
G7	4g
=3	=3
Cmaj7	4c
=4	=4
A7	4a
*-	*-
```

**code · box1_read.py**

```python
from hamonpy.cli import convert_file
from hamonpy.serialize import sequence_to_dict, sequence_to_hamon_text

for name in ("harte.lab", "humdrum.krn", "dcml.tsv"):
    seq = convert_file(f"in/{name}")
    groups = sequence_to_dict(seq)["groups"]
    for label in (groups[0]["primary"][0], groups[-1]["primary"][0]):    # first and last chord
        typed = {k: v for k, v in label["semantic"].items() if k != "kind"}
        print(f"{name:12} {label['surface']:8} {typed}")
    open(f"out/{name}.hamon", "w").write(sequence_to_hamon_text(seq))
```

**console**

```
harte.lab    D:min7   {'root': {'note': 'D'}, 'quality': 'minor', 'seventh': 'min7'}
harte.lab    A:7      {'root': {'note': 'A'}, 'quality': 'major', 'seventh': 'dom7'}
humdrum.krn  Dm7      {'root': {'note': 'D'}, 'quality': 'minor', 'seventh': 'min7'}
humdrum.krn  A7       {'root': {'note': 'A'}, 'quality': 'major', 'seventh': 'dom7'}
dcml.tsv     ii7      {'degree': 'ii', 'tail': '7'}
dcml.tsv     V7/ii    {'degree': 'V', 'tail': '7', 'secondary': 'ii'}
```

**output · out/dcml.tsv.hamon**

```
@rn
@key:C
m:1,ts:1,t:0/1,ii7
m:2,ts:1,t:4/1,V7
m:3,ts:1,t:8/1,IM7
@key:ii
m:3,ts:3,t:10/1,V7/ii
```

**output · out/harte.lab.hamon**

```
@cs
s:0,D:min7[dur:2s]
s:2,G:7[dur:2s]
s:4,C:maj7[dur:4s]
s:8,A:7[dur:2s]
```

**output · out/humdrum.krn.hamon**

```
@cs
@key:C
m:1,Dm7
m:2,G7
m:3,Cmaj7
m:4,A7
```


---

## 2 · Write any encoding

**input · in/progression.hamon**

```
@version:0.4.0
@meter:4/4
@key:C
m:1,ts:1,cs:Dm7,rn:ii7
m:2,ts:1,cs:G7,rn:V7
m:3,ts:1,cs:Cmaj7,rn:Imaj7
m:3,ts:3,cs:A7[of:ii],rn:V7/ii
m:4,ts:1,cs:Dm7,rn:ii7
```

**code · box2_write.py**

```python
from hamonpy.cli import convert_file
from hamonpy.report import write_to

seq = convert_file("in/progression.hamon")
for fmt, ext in (("humdrum", "krn"), ("mei", "mei"), ("lilypond", "ly"), ("dcml", "tsv")):
    open(f"out/progression.{ext}", "w").write(write_to(seq, fmt, mode="native"))
    print(f"{fmt:10} → out/progression.{ext}")
```

**console**

```
humdrum    → out/progression.krn
mei        → out/progression.mei
lilypond   → out/progression.ly
dcml       → out/progression.tsv
```

**output · out/progression.krn**

```
**mxhm	**harm
*C:	*C:
=1	=1
Dm7	ii7
=2	=2
G7	V7
=3	=3
Cmaj7	Imaj7
A7	V7/ii
=4	=4
Dm7	ii7
*-	*-
```

**output · out/progression.ly**

```
\version "2.24.0"
\chordmode {
  d1:m7 g:7 c:maj7 a:7 d:m7
}
```

**output · out/progression.mei**

```
<measure n="1">
<harm type="chord" tstamp="1">Dm7</harm>
</measure>
<measure n="2">
<harm type="chord" tstamp="1">G7</harm>
</measure>
<measure n="3">
<harm type="chord" tstamp="1">Cmaj7</harm>
<harm type="chord" tstamp="3">A7</harm>
</measure>
<measure n="4">
<harm type="chord" tstamp="1">Dm7</harm>
</measure>
```

**output · out/progression.tsv**

```
mn	mn_onset	timesig	chord	numeral	form	figbass	changes	relativeroot	localkey	globalkey
1	0	4/4	ii7	ii		7			I	C
2	0	4/4	V7	V		7			I	C
3	0	4/4	IM7	I	M	7			I	C
3	1/2	4/4	V7/ii	V		7		ii	I	C
4	0	4/4	ii7	ii		7			I	C
```


---

## 3 · What each encoding cannot say

**input · in/progression.hamon**

```
@version:0.4.0
@meter:4/4
@key:C
m:1,ts:1,cs:Dm7,rn:ii7
m:2,ts:1,cs:G7,rn:V7
m:3,ts:1,cs:Cmaj7,rn:Imaj7
m:3,ts:3,cs:A7[of:ii],rn:V7/ii
m:4,ts:1,cs:Dm7,rn:ii7
```

**code · box3_loss.py**

```python
from hamonpy.capability import native_loss
from hamonpy.cli import convert_text
from hamonpy.report import WRITERS
from hamonpy.serialize import sequence_to_dict

text = open("in/progression.hamon").read()
seq = sequence_to_dict(convert_text(text, "hamon"))

for f in WRITERS:
    print(f"{f:10}", dict(native_loss(seq, text, f)) or "says it all")
```

**console**

```
hamon      says it all
dcml       {'quality': 5, 'root': 5, 'applied': 1}
dezrann    {'tensions': 10, 'quality': 5, 'roman': 5, 'root': 5, 'applied': 2, 'key': 1}
mei        {'roman': 5, 'applied': 2, 'key': 1}
harte      {'position': 5, 'roman': 5, 'applied': 2, 'key': 1}
jams       {'position': 5, 'roman': 5, 'applied': 2}
musicxml   {'applied': 2, 'key': 1}
lilypond   {'roman': 5, 'applied': 2, 'key': 1}
abc        {'roman': 5, 'applied': 2, 'key': 1}
musescore  {'roman': 5, 'applied': 2, 'key': 1}
romantext  {'quality': 5, 'root': 5, 'applied': 1}
humdrum    {'applied': 1}
ireal      {'roman': 5, 'applied': 2, 'key': 1}
```


---

## 4 · What the round-trip lost

**input · in/progression.hamon**

```
@version:0.4.0
@meter:4/4
@key:C
m:1,ts:1,cs:Dm7,rn:ii7
m:2,ts:1,cs:G7,rn:V7
m:3,ts:1,cs:Cmaj7,rn:Imaj7
m:3,ts:3,cs:A7[of:ii],rn:V7/ii
m:4,ts:1,cs:Dm7,rn:ii7
```

**code · box4_roundtrip.py**

```python
from hamonpy.cli import convert_file
from hamonpy.report import lossy_report

rep = lossy_report(convert_file("in/progression.hamon"), "mei", mode="native")

for f in rep.semantic:
    if f.path.startswith(("groups", "regions")):      # the music, not the bookkeeping
        print(f"{f.kind:8} {f.path:30} {f.summary}")
```

**console**

```
dropped  groups[0].primary[1]           ii7
dropped  groups[1].primary[1]           V7
dropped  groups[2].primary[1]           Imaj7
dropped  groups[3].primary[0].attributes applied→ii
dropped  groups[3].primary[1]           V7/ii
dropped  groups[4].primary[1]           ii7
dropped  regions[0]                     {key=C major, kind=key, fromGroup=0}
```
