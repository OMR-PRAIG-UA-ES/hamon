# Using HAMON in your editor / environment

HAMON is a normal Python package (`hamonpy`) plus a `hamon` command. Nothing here is
special to one editor — once `hamonpy` is installed in the interpreter you've selected,
everything works. This page shows how to get it there and wire it into the common setups.

## Get HAMON into your environment

The Python package is the `hamonpy/` **subdirectory** of the repo (the repo root is not a
package). Once it's published to PyPI (after ICCCM'26) using it is just
`pip install hamonpy` into your project's environment. **Until then — and always if you
want to edit HAMON — you install from a checkout**, as follows.

First get the code:

```bash
git clone https://github.com/OMR-PRAIG-UA-ES/hamon.git    # or download the ZIP from GitHub
```

Then install `hamonpy` from that checkout **into whichever environment you want** — a
dedicated one, *or your own project's interpreter*. Because you point at the checkout by
path, this works from any project, not just from inside the HAMON repo:

```bash
# in your project's env (conda / venv / poetry — whatever your project uses):
pip install -e /path/to/hamon/hamonpy         # editable install

# optional extras (comma-separated) — install only the ones you need:
#   dev        pytest (run the test suite)
#   demo       streamlit (the interactive demo)
#   music21    music21 (score parsing / analysis / rendering)
#   ms3        ms3 (DCML MuseScore corpora)
#   partitura  partitura (score ingestion)
#   flexohr    FlexOHR (OHR object model)
#   bps        pandas + openpyxl (BPS-FH corpus)
#   notebooks  jupytext + nbconvert + ipykernel (run the tours as notebooks)
# e.g.:
pip install -e "/path/to/hamon/hamonpy[music21,ms3,partitura,notebooks]"
```

That single step gives *your* project both the library (`import hamonpy…`) and the `hamon`
CLI — you do **not** have to open the HAMON repo as your project. (Use `-e` if you might
also edit HAMON; drop it for a plain install.) The
[processing cookbook](processing.md) has the read / export / report / validate recipes;
the rest of this page is only about wiring that install into each tool.

## PyCharm / IntelliJ IDEA

Work in **your own project** — no need to open the HAMON repo:

1. **Select your project's interpreter.** *Settings → Project → Python Interpreter*
   (an existing venv/conda env, or add one). IntelliJ users need the Python plugin first.
2. **Install `hamonpy` into it.** Open the built-in Terminal (it activates the selected
   interpreter) and `pip install -e /path/to/hamon/hamonpy`. Now `import hamonpy` resolves
   in your own code.
3. **Run the CLI** from that Terminal: `hamon convert your-score.mei`, or make a *Run
   Configuration* with module `hamonpy` and parameters
   `export your-score.mei --to harte --report`.
4. **Debug** by setting a breakpoint and running with the same interpreter; with the `-e`
   install you can step straight into `hamonpy`.

> Hacking on HAMON *itself*? Then open the `hamon/` repo as the project instead and mark
> `hamonpy/` as a *Sources Root*; it ships an `.idea/` with run/inspection settings, and
> the CLI examples (`examples/song.mei`) resolve from the repo root.

## Visual Studio Code

Open **your own project folder**:

1. Install the **Python** extension.
2. **Select the interpreter:** Command Palette → *Python: Select Interpreter* → your
   project's env.
3. In the integrated terminal, install HAMON into it once:
   `pip install -e /path/to/hamon/hamonpy`. `hamon` is then on the path and `import
   hamonpy` works: `hamon report your-score.mei --to harte`.
4. For notebooks, also install the **Jupyter** extension; it reuses the same interpreter,
   so `import hamonpy` works in `.ipynb` cells with no extra setup.
5. `launch.json` example to debug the CLI:

   ```json
   { "type": "python", "request": "launch", "module": "hamonpy",
     "args": ["export", "your-score.mei", "--to", "harte", "--report"] }
   ```

## Jupyter notebooks

Install HAMON into the env you run Jupyter from, register it as a kernel once, then select
it in the notebook:

```bash
pip install -e "/path/to/hamon/hamonpy" ipykernel
python -m ipykernel install --user --name hamonpy --display-name "Python (hamonpy)"
```

In a cell:

```python
from hamonpy.cli import convert_file, transcode
from hamonpy.serialize import sequence_to_json

seq = convert_file("your-score.mei")               # a file in your own project
tc  = transcode("your-score.mei", "harte")         # any → any, with the loss report
tc.report                                          # what Harte dropped
```

To pretty-print the canonical JSON inline:

```python
import json
json.loads(sequence_to_json(seq))   # Jupyter renders the dict as a foldable tree
```

The guided tours under [`use-cases/notebooks/`](../use-cases/notebooks/) (in the HAMON
checkout) are [jupytext](https://jupytext.readthedocs.io/) `.py` files — install the extra
(`pip install -e "/path/to/hamon/hamonpy[notebooks]"`) and open them as notebooks
(*right-click → Open as Notebook*, or `jupytext --to notebook <tour>.py`).

## Digital-musicology environments

HAMON is the exchange layer *between* these tools — it reads their harmony and writes it
back out. Install the matching extra (on your checkout path, e.g.
`pip install -e "/path/to/hamon/hamonpy[music21]"`) and use `transcode` / `convert_file`:

| Tool / ecosystem | How HAMON connects | Extra / docs |
|---|---|---|
| **music21** | import a music21-parsed score's harmony, or realise HAMON for display | `[music21]` · [music21.md](music21.md) |
| **DCML / ms3** (MuseScore corpora) | read `harmonies/*.tsv`, round-trip RomanText/DCML | `[ms3]` · [dcml.md](dcml.md), [ms3.md](ms3.md) |
| **partitura** | ingest harmony from partitura-parsed scores | `[partitura]` · [partitura.md](partitura.md) |
| **Humdrum / `**kern`** | read/write `**harm` · `**fb` · `**function` spines | [humdrum.md](humdrum.md) |
| **MuseScore** | read `.mscx`/`.mscz` chord symbols; export MSCX | [musescore.md](musescore.md) |
| **MEI / Verovio** | read `<harm>`/`<fb>`; export HA-MEI for engraving | [mei.md](mei.md), [verovio.md](verovio.md) |
| **Harte / iReal / Dezrann / JAMS** | MIR annotation formats, import and export | [harte.md](harte.md), [ireal.md](ireal.md), [dezrann.md](dezrann.md), [jams.md](jams.md) |

Example — pull harmony out of a DCML corpus and hand it to a Humdrum toolchain:

```bash
hamon export harmonies.tsv --to humdrum -o harmonies.krn --report
```

Everything is one model underneath, so any of these can be converted to any other; the
[processing cookbook](processing.md) covers the full matrix.
