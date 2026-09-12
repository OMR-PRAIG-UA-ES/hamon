"""Tests for the dataset hub (hamonpy.datasets).

No network: the download path is exercised against a local file:// URL.
"""

from pathlib import Path

import pytest

from hamonpy import datasets

REQUIRED_KEYS = {"name", "title", "description", "authors", "homepage", "license", "citation", "download"}


def test_manifest_loads_and_lists_datasets():
    names = datasets.list_datasets()
    assert "dcml-corpora" in names
    assert "isophonics" in names
    assert "music21-corpus" in names
    assert len(names) == len(set(names))  # unique


def test_every_entry_is_well_formed():
    for name in datasets.list_datasets():
        entry = datasets.get_dataset(name)
        assert REQUIRED_KEYS <= set(entry), f"{name} missing keys"
        assert isinstance(entry["authors"], list) and entry["authors"]
        assert entry["download"]["method"] in {"http", "git", "huggingface", "builtin", "manual"}


def test_paper_datasets_present():
    names = set(datasets.list_datasets())
    assert {"when-in-rome", "distant-listening-corpus", "jazz-harmony-treebank",
            "key-modulation", "interactive-melodic-analysis"} <= names


def test_get_dataset_unknown_raises():
    with pytest.raises(KeyError):
        datasets.get_dataset("does-not-exist")


def test_non_downloadable_sources_raise_with_guidance():
    # music21-corpus is 'builtin', isophonics is 'manual' — both must refuse and point home.
    for name in ("music21-corpus", "isophonics"):
        with pytest.raises(ValueError) as exc:
            datasets.download_dataset(name)
        assert datasets.get_dataset(name)["homepage"] in str(exc.value)


def test_download_via_file_url(tmp_path: Path):
    # A local source file stands in for a remote dataset archive (no network).
    src = tmp_path / "corpus.tsv"
    src.write_text("chord\tnumeral\nI\tI\n", encoding="utf-8")
    file_url = src.as_uri()  # file:///...

    dest = tmp_path / "out"
    got = datasets.download_dataset("dcml-corpora", dest_dir=dest, url=file_url)

    assert got.exists()
    assert got.parent == dest
    assert got.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_default_cache_dir_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HAMON_CACHE_DIR", str(tmp_path / "cache"))
    assert datasets.default_cache_dir() == tmp_path / "cache"


# ---------------------------------------------------------------------------
# Integration with the companion downloader (resolve_local_path)
# ---------------------------------------------------------------------------

def _write_downloader_manifest(tmp_path: Path) -> Path:
    import json
    data = {
        "datasets": [
            {"id": "when_in_rome", "status": "exists", "path": str(tmp_path / "wir")},
            {"id": "jazzmus_hf", "status": "skipped_gated", "path": str(tmp_path / "jz")},
        ],
        "integration_contract": {"status_ok_values": ["cloned", "updated", "exists", "downloaded"]},
    }
    p = tmp_path / "music_datasets_manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_resolve_local_path_ok(tmp_path: Path):
    m = _write_downloader_manifest(tmp_path)
    assert datasets.resolve_local_path("when-in-rome", manifest_path=m) == tmp_path / "wir"


def test_resolve_local_path_gated_raises(tmp_path: Path):
    m = _write_downloader_manifest(tmp_path)
    with pytest.raises(ValueError):
        datasets.resolve_local_path("jazzmus", manifest_path=m)


def test_resolve_local_path_missing_manifest(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("MUSIC_DATASETS_MANIFEST", raising=False)
    monkeypatch.delenv("MUSIC_DATASETS_ROOT", raising=False)
    with pytest.raises(FileNotFoundError):
        datasets.resolve_local_path("when-in-rome")


def test_resolve_local_path_env(monkeypatch, tmp_path: Path):
    m = _write_downloader_manifest(tmp_path)
    monkeypatch.setenv("MUSIC_DATASETS_MANIFEST", str(m))
    assert datasets.resolve_local_path("when-in-rome") == tmp_path / "wir"


def test_to_https_normalises_urls():
    assert datasets._to_https("git@github.com:DCMLab/ABC.git") == "https://github.com/DCMLab/ABC"
    assert datasets._to_https("https://github.com/DCMLab/corelli") == "https://github.com/DCMLab/corelli"


def test_read_gitmodules(tmp_path: Path):
    (tmp_path / ".gitmodules").write_text(
        '[submodule "ABC"]\n\tpath = ABC\n\turl = git@github.com:DCMLab/ABC.git\n'
        '[submodule "corelli"]\n\tpath = sub/corelli\n\turl = https://github.com/DCMLab/corelli.git\n',
        encoding="utf-8")
    subs = list(datasets._read_gitmodules(tmp_path))
    assert subs == [("ABC", "https://github.com/DCMLab/ABC"),
                    ("sub/corelli", "https://github.com/DCMLab/corelli")]


def test_dcml_meta_datasets_declare_harmonies_glob():
    # the harmony-only fetch keys off this glob
    for name in ("dcml-corpora", "distant-listening-corpus"):
        assert datasets.get_dataset(name).get("harmony_glob") == "**/harmonies/*.tsv"
    for name in ("corelli", "annotated-beethoven-corpus", "annotated-mozart-sonatas"):
        assert datasets.get_dataset(name).get("harmony_glob") == "harmonies/*.tsv"
