"""Tests for the hamonpy CLI (hamonpy.cli)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hamonpy import cli

USE_CASES = Path(__file__).resolve().parents[2] / "use-cases"


@pytest.mark.parametrize("name,ext,fmt", [
    ("a", ".hamon", "hamon"),
    ("a", ".tsv", "dcml"),
    ("a", ".rntxt", "romantext"),
    ("a", ".json", "treebank"),
    ("a", ".mei", "mei"),
    ("a", ".lab", "harte"),
    ("a", ".abc", "abc"),
])
def test_detect_format_by_extension(name, ext, fmt):
    assert cli.detect_format(Path(name + ext), "") == fmt


def test_detect_key_modulation_vs_humdrum():
    assert cli.detect_format(Path("x.krn"), "**kern\t**text\n4c\tC=>:I\n") == "key_modulation"
    assert cli.detect_format(Path("x.krn"), "**kern\t**harm\n4c\tI\n") == "humdrum"


def test_detect_content_sniff():
    assert cli.detect_format(None, "@rn\nI\nV7") == "hamon"
    assert cli.detect_format(None, "m1 C: I b2 V") == "romantext"


def test_convert_text_dcml_has_regions():
    seq = cli.convert_text(
        "chord\tnumeral\tform\tfigbass\tchanges\trelativeroot\tlocalkey\tglobalkey\n"
        "I\tI\t\t\t\t\tI\tC\n", "dcml")
    assert seq.regions and seq.regions[0].key.tonic.note == "C"


def test_convert_file_autodetect(tmp_path: Path):
    p = tmp_path / "x.hamon"
    p.write_text("@cs\nCΔ7\nAm7")
    seq = cli.convert_file(p)
    assert len(seq.groups) == 2


def test_transcode_any_to_any(tmp_path: Path):
    p = tmp_path / "x.hamon"
    p.write_text("@cs\nCmaj7\nAm7")
    tc = cli.transcode(p, "harte")
    assert tc.source_format == "hamon" and tc.target_format == "harte"
    assert tc.output.strip().splitlines() == ["C:maj7", "A:min7"]
    assert json.loads(tc.hamon_json)["groups"]          # intermediate JSON is always produced
    assert tc.report.target == "harte"                  # loss is always measured


def test_transcode_rejects_unwritable_target(tmp_path: Path):
    p = tmp_path / "x.hamon"
    p.write_text("@cs\nCmaj7")
    with pytest.raises(ValueError):
        cli.transcode(p, "treebank")                    # import-only, not a writer


def test_main_export_saves_hamon_and_reports(tmp_path: Path, capsys):
    src = tmp_path / "x.hamon"
    src.write_text("@cs\nCmaj7\nAm7")
    mid = tmp_path / "mid.json"
    rc = cli.main(["export", str(src), "--to", "harte", "--save-hamon", str(mid), "--report"])
    assert rc == 0
    cap = capsys.readouterr()
    assert "C:maj7" in cap.out                           # target text on stdout
    assert json.loads(mid.read_text())["groups"]         # intermediate JSON written
    assert "loss" in cap.err.lower() or "No semantic loss" in cap.err  # report on stderr


def test_main_convert_outputs_json(capsys):
    rc = cli.main(["convert", str(USE_CASES / "when-in-rome" / "analysis.txt")])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert [r["kind"] for r in data["regions"]] == ["key", "modulation"]


def test_main_convert_to_file(tmp_path: Path, capsys):
    out = tmp_path / "o.json"
    rc = cli.main(["convert", str(USE_CASES / "key-modulation" / "snippet.krn"), "-o", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["groups"][0]["primary"][0]["semantic"]["degree"] == "I"


def test_main_datasets_list(capsys):
    assert cli.main(["datasets", "list"]) == 0
    assert "when-in-rome" in capsys.readouterr().out


def test_main_datasets_info(capsys):
    assert cli.main(["datasets", "info", "when-in-rome"]) == 0
    assert "homepage:" in capsys.readouterr().out


# ── validate ─────────────────────────────────────────────────────────────────

def test_main_validate_clean_file(tmp_path: Path, capsys):
    p = tmp_path / "x.hamon"
    p.write_text("@cs\nCΔ7\nAm7\nDm7\nG7")
    assert cli.main(["validate", str(p)]) == 0
    out = capsys.readouterr().out
    assert "Groups: 4" in out
    assert "chordSymbol 4" in out
    assert "OK" in out


def test_main_validate_reports_opaque_and_meter(tmp_path: Path, capsys):
    # ts:9 is outside 4/4, and "??" stays an opaque text label.
    p = tmp_path / "x.hamon"
    p.write_text("@meter:4/4\nm:1,ts:9,cs:C\n??")
    assert cli.main(["validate", str(p)]) == 0          # tolerant by default
    out = capsys.readouterr().out
    assert "position:" in out
    assert "opaque" in out
    assert cli.main(["validate", "--strict", str(p)]) == 1


def test_main_validate_json(tmp_path: Path, capsys):
    p = tmp_path / "x.hamon"
    p.write_text("@meter:4/4\nm:1,ts:9,cs:C")
    assert cli.main(["validate", "--json", str(p)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["groups"] == 1
    assert data["kinds"] == {"chordSymbol": 1}
    assert len(data["positionWarnings"]) == 1


def test_main_validate_missing_file(capsys):
    assert cli.main(["validate", "no-such-file.hamon"]) == 2


def test_main_validate_many_files(tmp_path: Path, capsys):
    ok = tmp_path / "ok.hamon"
    ok.write_text("@cs\nCmaj7")
    bad = tmp_path / "bad.hamon"
    bad.write_text("@meter:4/4\nm:1,ts:9,cs:C")
    assert cli.main(["validate", str(ok), str(bad)]) == 0
    out = capsys.readouterr().out
    assert out.count("Source:") == 2
    assert cli.main(["validate", "--strict", str(ok), str(bad)]) == 1
    assert cli.main(["validate", "--strict", str(ok)]) == 0


def test_main_validate_many_files_json(tmp_path: Path, capsys):
    a = tmp_path / "a.hamon"; a.write_text("@cs\nC")
    b = tmp_path / "b.hamon"; b.write_text("@cs\nDm7")
    assert cli.main(["validate", "--json", str(a), str(b)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) == 2
    assert data[1]["kinds"] == {"chordSymbol": 1}
