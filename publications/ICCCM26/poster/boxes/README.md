# Las cuatro cajas de código del póster

La columna derecha del A0. Cuatro cajas, una por cosa que hace HAMON, en el orden en que
se entiende: **leer → escribir → medir → comprobar**.

Cada caja enseña, en este orden: el **fichero de entrada** entero, el **código** sin
recortar, la **salida de consola** y el **fichero de salida** que genera. Las cajas 3 y 4
no tienen fichero de salida a propósito: su resultado *es* la consola, y repetirlo en un
fichero solo gastaría columna.

Las etiquetas y los comentarios del código van **en inglés**, porque se imprimen. Este
README y los mensajes de commit son internos y van en español.

Todo está en [`BOXES.md`](BOXES.md), listo para pegar. **Nada está tecleado a mano**: lo
regenera `build.py` corriendo los cuatro scripts de verdad, y un test
(`test_poster_boxes_are_current`) falla si el documento se desfasa del código.

```bash
cd publications/ICCCM26/poster/boxes
python build.py           # regenera BOXES.md y out/
python build.py --check   # falla si está desfasado
```

## Las cajas

| | Script | Qué enseña |
|---|---|---|
| **1 · Read any encoding** | `box1_read.py` | La misma armonía en tres codificaciones que no se parecen en nada — Harte (de audio, en segundos), Humdrum (de partitura, en compases) y una tabla DCML (análisis en números romanos, con `quarterbeats`) — cae en el mismo modelo tipado. Los glifos se guardan tal cual (`D:min7` frente a `Dm7`); el significado sale idéntico en las dos primeras, y en DCML sale tipado como romano: el último acorde es `A:7`/`A7` en las de acordes y `V7/ii` en DCML, que es la única que dice *de qué* es dominante. La consola enseña el primer y el último acorde de cada fichero. |
| **2 · Write any encoding** | `box2_write.py` | Ese modelo sale a Humdrum, MEI, LilyPond y DCML. Cada escritor coge la capa que sabe decir: Humdrum las dos (`**mxhm` y `**harm`), MEI y LilyPond los acordes, DCML los romanos, con compás, `mn_onset`, `timesig`, `relativeroot` y tonalidades. Los cuatro ficheros están abajo. |
| **3 · What each encoding cannot say** | `box3_loss.py` | Qué no sabe decir cada formato **en su propio vocabulario**. Los formatos de acordes pierden la capa romana entera; DCML y RomanText, la de acordes; todos, que el `A7` es la dominante *de* `ii`; casi todos, la tonalidad; Harte y JAMS, dónde está cada acorde. Humdrum solo pierde el `[of:ii]` del cifrado. |
| **4 · What the round-trip lost** | `box4_roundtrip.py` | Escribe a MEI, lo vuelve a leer y compara. Encuentra exactamente lo que la caja 3 había predicho: los cinco romanos, la dominante secundaria y la tonalidad. La caja 3 declara, la 4 mide. |

La caja 3 y la caja 4 juntas son el argumento: la pérdida no se estima, se nombra. La 4
vuelve a leer el MEI que escribió la 2, así que las dos se leen encadenadas.

## El ejemplo

Una vuelta de `ii–V–I` en Do con una dominante secundaria — `Dm7 G7 Cmaj7 A7 Dm7` —
escrita tres veces, en [`in/`](in/):

| Fichero | Formato | Reloj |
|---|---|---|
| `harte.lab` | Harte | segundos (lo que publica el reconocimiento de acordes sobre audio) |
| `humdrum.krn` | Humdrum `**mxhm` | compases |
| `dcml.tsv` | DCML (tabla *expanded*, como la escribe ms3) | compases + `quarterbeats`, con `globalkey`/`localkey` y `relativeroot` |
| `progression.hamon` | HAMON, **por capas** (`cs:Dm7,rn:ii7`) | compás y tiempo, más `@key:C` y `[of:ii]` |

Todo es sintético y nuestro: ningún corpus de terceros, ninguna licencia que arrastre. La
tabla DCML está para Fabian, que presenta el póster: usa las columnas de su estándar
(`mn`, `mn_onset`, `quarterbeats`, `globalkey`, `localkey`, `chord`, `relativeroot`) y
nada más.

## DCML en la caja 3

La fila `dcml` de la caja 3 decía que DCML pierde la *posición* de los cinco acordes. Era
culpa del escritor de hamonpy, que sacaba la tabla plana sin `mn`/`quarterbeats`, no del
formato, que siempre las ha tenido. El 09-14 el escritor pasó a escribir esas columnas y
`dcml` entró en `POSITION_NATIVE`; lo que la fila dice ahora — raíz y calidad de los
acordes cifrados, y la dominante aplicada — es lo que DCML de verdad no sabe decir en su
vocabulario.
