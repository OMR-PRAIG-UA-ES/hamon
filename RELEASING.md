# Releasing `hamonpy`

Two separate channels, neither of which fires by accident.

## Internal builds (private, for us)

Push a tag matching the version in `hamonpy/pyproject.toml`:

```bash
git tag hamonpy-v0.2.0 && git push origin hamonpy-v0.2.0
```

`.github/workflows/release-hamonpy.yml` builds the wheel and the sdist, smoke-installs
the wheel in a clean virtualenv, and attaches both to a GitHub Release on this private
repo. Collaborators install from that tag. Nothing leaves the organisation.

## PyPI (public)

Run the **Publish hamonpy to PyPI** workflow by hand, from the Actions tab. It asks for
the tag and the index, and it is the *only* path to PyPI — no push and no tag can publish
on its own.

1. Run it with index `testpypi`. Then install from there in a clean environment and try
   the four commands:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ hamonpy
   hamon convert changes.tsv
   ```
   The extra index matters: TestPyPI does not carry the ANTLR runtime.
2. When that is clean, run it again with index `pypi`.

Before either run, bump `version` in `hamonpy/pyproject.toml`. **A version number can only
be uploaded once**, on either index, and deleting a release does not free it. A botched
upload costs you a version number, not a day.

### One-time setup

Repository secrets: `TEST_PYPI_API_TOKEN` and `PYPI_API_TOKEN`, from the token pages of
each index. Until the project exists the token has to be account-scoped; narrow it to the
`hamonpy` project right after the first successful upload.

### What the workflow checks for you

`twine check` on the rendered metadata, a smoke install of the wheel in a clean
virtualenv with `hamon --help` and a parse, and that the wheel actually carries the
`LICENSE` — Apache-2.0 requires shipping it, and a wheel without it is the kind of thing
nobody notices for three releases.

## What is in the package, and what is not

The wheel carries the `hamonpy` sources and the generated ANTLR parser. It does **not**
carry the grammar, the fixtures, the conformance corpus, the documentation or the test
suite: those are data-driven against files that live in the repository, so shipping the
suite would hand users tests that cannot pass.

Datasets are never redistributed. `datasets/manifest.json` is a registry that points at
each source and states its licence; the user downloads and complies. Several of the
registered corpora are CC BY-NC-SA, so vendoring even one of them would contaminate the
licence of everything around it.
