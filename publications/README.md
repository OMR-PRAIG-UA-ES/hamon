# Publications

One folder per published piece of work: the paper or poster it belongs to, the examples
it uses, the companion code that produces its numbers, and the generated artefacts the
site and the printed version both draw from.

| Folder | Venue | What is in it |
|---|---|---|
| [`ICCCM26/`](ICCCM26/) | ICCCM 2026, Würzburg, 21-23 September 2026 | *Bridging harmonic representations through a multi-modal encoding*. Eight worked examples, the cross-encoding loss report, the hub and matrix figures, and the poster's four runnable code boxes. |

## Why the numbers here are reproducible

Each folder regenerates everything it publishes from the examples it ships, and the test
suite holds the result to it. For ICCCM'26 that is `cd publications/ICCCM26 && python
run.py`, checked by `hamonpy/tests/test_icccm26.py`: if the library's behaviour drifts
from the figures on the poster, the suite says so rather than the reader discovering it.

## What ships and what does not

The whole of `publications/` is copied into the public mirror, so a new folder here is
public the moment it is published. Working material — drafts, proposals, notes towards a
poster — is excluded by name in `site/make_dist.py`, and by path in `.git/info/exclude`
when it should not be committed at all. Check both before adding a folder.
