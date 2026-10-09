"""scripts/generate_dataset_matrix.py: data-root creation, request-sized disk check, exit codes.

Hermetic: a temporary data root, no Spark (the per-table writer is replaced by a
fake that writes a manifest the real validity check accepts), and a stubbed
disk-usage reading.
"""
from __future__ import annotations

import importlib.util
import json
from collections import namedtuple
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_dataset_matrix.py"
GIB = 1024 ** 3
Usage = namedtuple("Usage", "total used free")
ONE_SMALL = ["--scale", "small", "--seed", "0", "--skew", "1.0"]


@pytest.fixture
def gen(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("generate_dataset_matrix_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    root = tmp_path / "not" / "created" / "yet"
    for name, path in (("DATA_ROOT", root), ("GENERATED_DIR", root / "generated"),
                       ("DATASETS_DIR", root / "generated" / "datasets"),
                       ("INDEX_PATH", root / "generated" / "index.json"),
                       ("SUMMARY_PATH", root / "generated" / "summary.json")):
        monkeypatch.setattr(mod, name, path)
    monkeypatch.setattr(mod, "_spark_session", lambda: object())
    monkeypatch.setattr(mod, "stop_session", lambda spark: None)
    monkeypatch.setattr(mod.shutil, "disk_usage", lambda p: Usage(500 * GIB, 0, 100 * GIB))
    calls: list[tuple] = []

    def fake_generate_table(spark, table, scale, seed, skew, pdir, chunk_rows):
        calls.append((table, scale, seed, skew))
        tspec = mod.expected_spec(table, scale, seed, skew, chunk_rows)
        tdir = pdir / table
        (tdir / "data").mkdir(parents=True, exist_ok=True)
        (tdir / "data" / "part-0.parquet").write_bytes(b"x")
        manifest = mod.build_manifest(dataset_id=f"{table}-{mod.phys_id(skew, scale, seed)}",
                                      spec=tspec, checksum="0" * 64, file_count=1,
                                      total_bytes=1, code_version="test")
        (tdir / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
        return True

    monkeypatch.setattr(mod, "_generate_table", fake_generate_table)
    mod.calls = calls
    return mod


def test_missing_data_root_is_created_and_one_dataset_exits_zero(gen):
    assert not gen.DATA_ROOT.exists()
    assert gen.main(ONE_SMALL) == 0
    assert gen.INDEX_PATH.exists()
    summary = json.loads(gen.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert (summary["valid_physical"], summary["missing_physical"]) == (1, 29)


def test_repeated_generation_skips_valid_tables(gen):
    assert gen.main(ONE_SMALL) == 0
    first = len(gen.calls)
    assert first == 2                                   # orders + lineitem
    assert gen.main(ONE_SMALL) == 0
    assert len(gen.calls) == first                      # nothing regenerated


def test_failed_requested_dataset_exits_one(gen, monkeypatch):
    monkeypatch.setattr(gen, "_generate_table", lambda *a, **k: False)
    assert gen.main(ONE_SMALL) == 1


def test_full_matrix_needs_every_dataset(gen, monkeypatch):
    assert gen.main([]) == 0                            # all 30 valid
    assert len(gen.calls) == 60
    (gen.phys_dir(1.0, "large", 4) / "lineitem" / "manifest.json").unlink()
    monkeypatch.setattr(gen, "_generate_table", lambda *a, **k: False)
    assert gen.main([]) == 1                            # one of 30 cannot be repaired


def test_insufficient_disk_stops_before_generating(gen, monkeypatch):
    monkeypatch.setattr(gen.shutil, "disk_usage", lambda p: Usage(500 * GIB, 0, GIB // 2))
    with pytest.raises(SystemExit) as stop:
        gen.main(ONE_SMALL)
    assert stop.value.code == 2
    assert gen.calls == []


def test_disk_requirement_scales_with_the_request(gen):
    one = gen.disk_requirement_bytes([(1.0, "small", 0)])
    assert GIB < one < 2 * GIB                          # ~1.2 GiB, not ~40 GiB
    full = gen.disk_requirement_bytes(gen.ordered_matrix())
    line_rows = sum(gen.SCALE_LINE_ROWS.values()) * len(gen.SKEWS) * len(gen.SEEDS)
    rows = line_rows + line_rows // gen.LINEITEM_TO_ORDERS
    assert full == rows * 60 + 10 * GIB                 # the original full-matrix check
