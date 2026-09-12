# Systems, the `@` hint, and the analytical layer

Here's a question that comes up a lot: *if a label carries `[of:II]` (a Roman-numeral degree)
and `[scale:lydian-dominant]`, does it still make sense to declare `@cs` (chord symbol)?*
It does — because three things are **orthogonal**:

1. **Base harmony system** — how the *label itself* is spelled: chord symbol (`cs`),
   Roman numeral (`rn`), Nashville number (`ns`), figured bass (`fb`), functional (`fun`).
2. **Analytical layer** — optional attributes you can layer onto **any** label: `[of:…]`
   (applied/secondary target), `[scale:…]` (chord-scale), `[NHT:…]` (non-harmonic tone),
   `[inv:…]`, `@key:…` regions, and so on. See [analysis.md](analysis.md).
3. **Per-label `detected_system`** — what each label actually is, computed independently
   of the sequence hint.

`D7[of:II][scale:lydian-dominant]` is a **chord symbol** (`D7`) with two analytical
attributes. The `II` inside `[of:…]` is Roman-numeral *notation for the applied target*
degree, and `[scale:…]` is a Berklee chord-scale. **Neither one touches the base system**, so
`@cs` is exactly right for a jazz lead sheet where every label is a chord symbol.

## The `@<system>` sequence hint

The first non-version directive can declare the sequence's system:

| Hint | Effect |
|---|---|
| `@cs` `@rn` `@ns` `@fb` `@fun` | declares the **default/expected base system** for the sequence |
| `@auto` (or none) | each label's system is **detected independently** |

The hint does two jobs. It sets the sequence-level `system`, and it **disambiguates**
tokens that could parse under more than one system — a bare `6` as figured bass vs.
Nashville, or `bVI` as a Roman numeral vs. a flat chord root.

### `@cs` vs `@auto` — when to use which

The hint sets the label's `system` field, while `detected_system` always reports what the label really is:

| Input | `detected_system` | `system` (with `@cs`) | `system` (with `@auto`) |
|---|---|---|---|
| `D7[of:II][scale:…]` | `cs` | `cs` | `cs` |
| `V7/V` | `rn` | **`cs`** ← forced | `rn` |
| `6-5` | `fb` | **`cs`** ← forced | `fb` |

- **Homogeneous** sequence (a chord-symbol lead sheet with analysis, like the ICCCM'26
  flagship) → **declare the system** (`@cs`). It's honest, and it disambiguates.
- **Genuinely mixed** systems in one sequence (some chord symbols, some Roman, some
  figured bass) → **`@auto`**, so each label keeps its own `system` and a `V7/V` isn't
  stamped `system=cs`. This is why the ICCCM'26 *pangram* uses `@auto`.

Either way, the parsed `kind` and `detected_system` come out identical — only the
sequence-level `system` label differs. Both are valid encodings of the same content.

See also: [analysis.md](analysis.md) (the analytical layer in full),
[positions.md](positions.md) (time-aligned positions).
