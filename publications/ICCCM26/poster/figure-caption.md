# The score, and the paragraph that ties it to the figure

The eight bars printed beside the hub figure are the theme of Mozart's *Andante with
variations* for piano four hands, **K. 501** (1786), in G major.

The Roman and functional readings are **TAVERN**'s (Devaney, Arthur, Condit-Schultz &
Nisula, *TAVERN: A dataset for Theme And Variation Encodings with Roman Numerals*,
ISMIR 2015): two annotators marked the piece independently and reconciled the result.
The chord symbols follow from those numerals in G major. **No analysis on the poster is
ours** — which matters, because the poster's claim is about carrying somebody else's
analysis without degrading it.

Mozart is public domain, TAVERN is CC BY-SA 4.0, and we do not redistribute their file:
the excerpt is written out as `ICCCM26/examples/k501_mozart_duet.hamon` and they are cited.

Figure: `ICCCM26/outputs/figure_hub_k501_mozart_duet.svg`

## The analysis, bar by bar

| bar | chords | Roman | function |
|---|---|---|---|
| 1 | G · D7 | I · V7 | T |
| 2 | G | I | T |
| 3 | D/A · A7 | I64/V · **V7/V** | D |
| 4 | D | V | D |
| 5 | G7 | **V7/IV** | PD |
| 6 | C · G/B | IV · I6 | PD |
| 7 | Am/E · D | ii64 · V | PD · D |
| 8 | D7 | V7 | D |

Two applied dominants and a cadential six-four over the dominant, which is why the figure
measures the analytical vocabulary and not just the chords.

## The paragraph (poster prose, ~95 words)

> Eight bars of Mozart, and three ways of saying the same thing about them: the chord
> symbols a player reads, the Roman numerals an analyst writes, and the
> tonic-predominant-dominant function underneath. The analysis is not ours — it is
> TAVERN's, marked by two annotators and reconciled. Every spoke in the figure is one
> encoding, and its thickness is what that encoding **cannot** say in its own vocabulary.
> Humdrum loses nothing, because it gives each reading its own spine. MusicXML keeps the
> chords and cannot say that the A7 in bar 3 is the dominant *of* the dominant. DCML and
> RomanText keep the analysis and cannot hold the chords at all.

## Short version (~45 words)

> Three readings of eight bars of Mozart, analysed not by us but by TAVERN. Each spoke is
> an encoding; its thickness is what that encoding cannot say. Humdrum loses nothing.
> MusicXML loses the function and the applied dominants. DCML loses the chords.

## The numbers, so the caption can be checked

| Encoding | Cannot express | What is missing |
|---|---:|---|
| HAMON · Humdrum | 0 | — |
| MusicXML | 16 | the function, the applied dominants, the key |
| MEI · LilyPond · ABC · MuseScore · iReal | 28 | the Roman reading, the function, the applied dominants, the key |
| RomanText | 36 | the chord symbols |
| JAMS | 39 | the Roman reading, the function, the positions |
| Harte | 40 | the Roman reading, the function, the key, the positions |
| DCML | 48 | the chord symbols and the positions |
| Dezrann | 66 | almost everything but the bass |

Regenerate both with `cd publications/ICCCM26 && python run.py`.
