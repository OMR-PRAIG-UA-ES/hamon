# Use case — Roman-numeral analysis with tonal regions

**Scenario.** You have a Roman-numeral analysis of a phrase in C major that
briefly tonicizes the dominant, and you want it as structured data: a list of
degrees *plus* the tonal regions in force, with the tonicization's local key
resolved to an actual pitch.

**Input.** [`progression.hamon`](progression.hamon):

```
@version:0.2.0
@rn
@key:C
I
IV
@key:V
V7/V
V
@key:C
I
```

## Run it

Python:

```python
from hamonpy.parse import parse_hamon_sequence

seq = parse_hamon_sequence(open("progression.hamon").read())

for r in seq.regions:
    print(r.kind, r.from_group, r.to_group, r.key.tonic.note, r.key.mode, r.degree)
# key          0 2    C major None
# tonicization 2 3    G major V        (parent=0)
# key          4 None C major None

print([g.primary[0].semantic.degree for g in seq.groups])
# ['I', 'IV', 'V', 'V', 'I']   (group 2 = V7/V, secondary='V')
```

## What you get

- Four labels become a `HamonSequence` of Roman-numeral `groups`.
- The two `@key:` directives become `TonalRegion`s. `@key:V` is a **tonicization**:
  its local tonic is computed from the parent key (V of C major → **G major**), and
  it carries `degree: "V"` and `parent: 0`.
- The secondary dominant `V7/V` keeps `secondary: "V"` on its `RomanSemantic`.

This is exactly the analytical structure described in
[`documentation/analysis.md`](../../documentation/analysis.md).
