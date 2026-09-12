"""Dataset hub — discover and fetch third-party harmony corpora.

HAMON does **not** redistribute any dataset. This module reads
`datasets/manifest.json` (a registry of original sources: authors, license,
citation, download URL) and offers a tiny stdlib-only helper to download a
dataset into a local cache so users can convert it with the format adapters
(`hamonpy.adapters.*`). Users must comply with each dataset's own license.

    from hamonpy import datasets
    datasets.list_datasets()                 # -> ['dcml-corpora', 'isophonics', ...]
    info = datasets.get_dataset('dcml-corpora')
    path = datasets.download_dataset('dcml-corpora')   # only for http/file sources
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "manifest_path",
    "load_manifest",
    "list_datasets",
    "get_dataset",
    "default_cache_dir",
    "data_dir",
    "download_dataset",
    "fetch_dataset",
    "download_all",
    "resolve_local_path",
]


def manifest_path() -> Path:
    """Locate datasets/manifest.json (env override: HAMON_DATASETS_MANIFEST)."""
    env = os.environ.get("HAMON_DATASETS_MANIFEST")
    if env:
        return Path(env)
    # hamonpy/hamonpy/datasets.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2] / "datasets" / "manifest.json"


def load_manifest() -> Dict:
    path = manifest_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset manifest not found at {path}. Set HAMON_DATASETS_MANIFEST to its location."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def list_datasets() -> List[str]:
    """Return the registered dataset names."""
    return [d["name"] for d in load_manifest().get("datasets", [])]


def get_dataset(name: str) -> Dict:
    """Return the manifest entry for *name* (raises KeyError if unknown)."""
    for d in load_manifest().get("datasets", []):
        if d["name"] == name:
            return d
    raise KeyError(f"Unknown dataset {name!r}. Known: {', '.join(list_datasets())}")


def default_cache_dir() -> Path:
    """User cache directory for downloaded datasets (override: HAMON_CACHE_DIR)."""
    env = os.environ.get("HAMON_CACHE_DIR")
    base = Path(env) if env else Path.home() / ".cache" / "hamon" / "datasets"
    return base


def data_dir() -> Path:
    """In-repo download location used by the demo: ``datasets/_data/`` (git-ignored).

    Override with HAMON_DATASETS_DIR. This is where ``fetch_dataset`` / ``download_all``
    place corpora so the Streamlit demo can find them without polluting the repo.
    """
    env = os.environ.get("HAMON_DATASETS_DIR")
    return Path(env) if env else manifest_path().parent / "_data"


def download_dataset(name: str, dest_dir: Optional[Path] = None, url: Optional[str] = None) -> Path:
    """Download a dataset to the local cache and return the downloaded file path.

    Only `http(s)://` and `file://` sources are fetched automatically. Datasets
    whose method is `git`, `builtin` or `manual` raise a helpful error pointing
    at the homepage (we never bundle or scrape them). `url` overrides the
    manifest URL (used in tests and for mirror/local copies).
    """
    entry = get_dataset(name)
    download = entry.get("download", {})
    method = download.get("method")
    src = url or download.get("url")

    if src is None or method in {"git", "builtin", "manual"} and url is None:
        raise ValueError(
            f"Dataset {name!r} is not directly downloadable (method={method!r}). "
            f"See {entry.get('homepage')} and honour its license: {entry.get('license')}."
        )

    dest_dir = Path(dest_dir) if dest_dir else default_cache_dir() / name
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = src.rstrip("/").split("/")[-1] or f"{name}.download"
    target = dest_dir / filename

    urllib.request.urlretrieve(src, target)  # noqa: S310 - http/file only, user-initiated
    return target


# ---------------------------------------------------------------------------
# Unattended fetching into the in-repo demo location (datasets/_data/)
# ---------------------------------------------------------------------------

def _git_clone(url: str, dest: Path, *, recurse_submodules: bool = False) -> None:
    import subprocess
    sub = ["--recurse-submodules", "--shallow-submodules"] if recurse_submodules else []
    if (dest / ".git").is_dir():
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only", "--depth", "1"],
                       check=True, capture_output=True, text=True)
        if recurse_submodules:
            subprocess.run(["git", "-C", str(dest), "submodule", "update", "--init",
                            "--depth", "1"], check=True, capture_output=True, text=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", *sub, _to_https(url), str(dest)],
                   check=True, capture_output=True, text=True)


#: harmony_glob values whose harmony lives in ``harmonies/`` dirs (DCML layout) — these
#: support the lightweight "harmony-only" fetch (sparse clone of just those TSVs).
_DCML_HARMONY_GLOBS = {"harmonies/*.tsv", "**/harmonies/*.tsv"}


def _to_https(url: str) -> str:
    return url.replace("git@github.com:", "https://github.com/").removesuffix(".git")


def _git_sparse_harmonies(url: str, dest: Path, sparse_dir: str = "harmonies") -> None:
    """Blobless + sparse (cone) clone of a single repo fetching only ``sparse_dir``;
    on re-run, fast-forward pull to pick up upstream updates."""
    import subprocess
    if (dest / ".git").is_dir():
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"],
                       check=True, capture_output=True, text=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                    _to_https(url), str(dest)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", sparse_dir],
                   check=True, capture_output=True, text=True)


def _read_gitmodules(meta_dir: Path):
    """Yield ``(submodule_path, https_url)`` from a meta-repo's ``.gitmodules``."""
    gm = meta_dir / ".gitmodules"
    if not gm.is_file():
        return
    path = None
    for raw in gm.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("path ="):
            path = line.split("=", 1)[1].strip()
        elif line.startswith("url =") and path:
            yield path, _to_https(line.split("=", 1)[1].strip())
            path = None


def _fetch_meta_harmonies(url: str, dest: Path, sparse_dir: str = "harmonies") -> None:
    """For a DCML meta-repo: shallow-clone the top level (for its ``.gitmodules``), then
    sparse-fetch only ``harmonies/`` of every submodule. Updates on re-run."""
    import subprocess
    if (dest / ".git").is_dir():
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only", "--depth", "1"],
                       check=True, capture_output=True, text=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", _to_https(url), str(dest)],
                       check=True, capture_output=True, text=True)
    for sub_path, sub_url in _read_gitmodules(dest):
        _git_sparse_harmonies(sub_url, dest / sub_path, sparse_dir)


def _http_archive(url: str, dest: Path) -> None:
    import tarfile
    import tempfile
    import zipfile
    dest.mkdir(parents=True, exist_ok=True)
    name = url.split("?", 1)[0].rstrip("/").split("/")[-1] or "download"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / name
        urllib.request.urlretrieve(url, archive)  # noqa: S310 - http only, user-initiated
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(dest)
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive) as tf:
                tf.extractall(dest)  # noqa: S202 - trusted research corpora
        else:
            (dest / name).write_bytes(archive.read_bytes())  # plain file


def fetch_dataset(name: str, root: Optional[Path] = None, *, harmony_only: bool = True) -> Path:
    """Fetch a dataset into ``root`` (default :func:`data_dir`) and return its path.

    ``harmony_only`` (default) keeps it light: DCML datasets (harmony in ``harmonies/``
    TSVs) are sparse-cloned to *only* those tables — for the meta-repos that means each
    submodule's ``harmonies/`` — skipping the large MuseScore scores. With
    ``harmony_only=False`` ("full"), git datasets are shallow-cloned whole and meta-repos
    pull their submodules (large; for a WiFi run). Either way a re-fetch fast-forwards to
    upstream updates. ``builtin``/``manual``/gated datasets raise with guidance.
    """
    entry = get_dataset(name)
    download = entry.get("download", {})
    method = download.get("method")
    url = download.get("url")
    hglob = entry.get("harmony_glob")
    dest = (Path(root) if root else data_dir()) / name

    if download.get("gated"):
        raise ValueError(f"Dataset {name!r} is gated — accept its terms and fetch manually: "
                         f"{entry.get('homepage')}")
    if method == "http":
        _http_archive(url, dest)
        return dest
    if method != "git":
        raise ValueError(f"Dataset {name!r} has no unattended download (method={method!r}); "
                         f"see {entry.get('homepage')}.")

    is_meta = hglob == "**/harmonies/*.tsv"
    if harmony_only and hglob in _DCML_HARMONY_GLOBS:
        if is_meta:
            _fetch_meta_harmonies(url, dest)           # submodule harmonies/ only
        else:
            _git_sparse_harmonies(url, dest)           # this repo's harmonies/ only
    elif is_meta:
        _git_clone(url, dest, recurse_submodules=True)  # full meta-repo (large)
    else:
        _git_clone(url, dest)                           # full shallow clone
    return dest


def download_all(root: Optional[Path] = None, *, harmony_only: bool = True) -> Dict[str, str]:
    """Fetch every git/http dataset into ``root`` (default :func:`data_dir`).

    ``harmony_only`` (default) fetches only the harmony tables for DCML datasets (light);
    pass ``harmony_only=False`` for the full corpora (scores + submodules; large).
    Returns a ``{name: status}`` map; ``builtin``/``manual``/gated are skipped, not failed.
    """
    results: Dict[str, str] = {}
    for name in list_datasets():
        entry = get_dataset(name)
        download = entry.get("download", {})
        method = download.get("method")
        if download.get("gated"):
            results[name] = "skipped: gated"
            continue
        if method not in {"git", "http"}:
            results[name] = f"skipped: method={method}"
            continue
        try:
            fetch_dataset(name, root=root, harmony_only=harmony_only)
            results[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - report, don't abort the batch
            results[name] = f"error: {type(exc).__name__}: {exc}"
    return results


# ---------------------------------------------------------------------------
# Integration with the companion downloader (download_music_datasets.py)
# ---------------------------------------------------------------------------

def _downloader_manifest_path() -> Optional[Path]:
    env = os.environ.get("MUSIC_DATASETS_MANIFEST")
    if env:
        return Path(env)
    root = os.environ.get("MUSIC_DATASETS_ROOT")
    if root:
        return Path(root) / "music_datasets_manifest.json"
    return None


def resolve_local_path(name: str, manifest_path: Optional[Path] = None) -> Path:
    """Return the on-disk path of a dataset already fetched by the companion
    downloader (download_music_datasets.py).

    Reads that tool's manifest — located via `manifest_path`, else the
    `MUSIC_DATASETS_MANIFEST` env var, else `$MUSIC_DATASETS_ROOT/music_datasets_manifest.json`
    — maps the HAMON dataset `name` to the downloader's `id` (via this registry's
    `downloader_id`), and returns its `path` when its status is one of the
    contract's ok-values. Raises with guidance otherwise.
    """
    entry = get_dataset(name)
    downloader_id = entry.get("downloader_id", name)

    path = Path(manifest_path) if manifest_path else _downloader_manifest_path()
    if path is None or not path.is_file():
        raise FileNotFoundError(
            "No downloader manifest found. Run download_music_datasets.py and set "
            "MUSIC_DATASETS_MANIFEST (or MUSIC_DATASETS_ROOT) to its output."
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    contract = data.get("integration_contract", {})
    ok = set(contract.get("status_ok_values", ["cloned", "updated", "exists", "downloaded"]))

    for d in data.get("datasets", []):
        if d.get("id") == downloader_id:
            if d.get("status") not in ok:
                raise ValueError(
                    f"Dataset {name!r} (id {downloader_id!r}) is present in the downloader "
                    f"manifest but its status is {d.get('status')!r}; see {entry.get('homepage')}."
                )
            return Path(d["path"])

    raise KeyError(f"Dataset id {downloader_id!r} not found in {path}.")
