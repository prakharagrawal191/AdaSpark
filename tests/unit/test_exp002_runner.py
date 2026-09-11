"""Unit tests for the EXP-002 runner's pure logic: status mapping, applied-config
verification, record I/O and atomic writes.

No Spark session is ever created here: ``execute_run`` / ``run_experiment`` are not
called. RunMetrics objects are built directly and RunSpec objects come from a real
ExperimentSpec.plan() entry, so the record shapes are the production ones.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkrl.experiments.runner import (COMPLETED, FAILED, INCOMPLETE,
                                        RECORD_SCHEMA_VERSION, _atomic_write_json,
                                        build_record, is_completed, load_records,
                                        read_record, record_status,
                                        verify_applied,)
from sparkrl.experiments.spec import EXPERIMENT_ID, ExperimentSpec
from sparkrl.monitoring import RunMetrics

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_YAML = REPO_ROOT / "experiments" / "exp002.yaml"

SPEC = ExperimentSpec.from_yaml(SPEC_YAML)
PLAN = SPEC.plan()
VARIED_RUN = next(r for r in PLAN if not r.config.is_reference)
B0_RUN = next(r for r in PLAN if r.config.is_reference)


def _metrics(**over) -> RunMetrics:
    """A usable (valid) RunMetrics, mutated by keyword for the invalid cases."""
    base = dict(run_id=VARIED_RUN.run_id, workload_id="F1_agg_v1",
                family=VARIED_RUN.family, scale=VARIED_RUN.scale, seed=0,
                dataset_id="skew1_small_s0",
                config_fingerprint=VARIED_RUN.config.fingerprint(),
                aqe_enabled=False, result_signature="8d7c822ef7e22db0",
                execution_time_s=12.5, execution_time_source="runner",
                success=True, usable=True, timeout=False, error=None,
                event_log_status="COMPLETE", timestamp="2026-01-01T00:00:00+00:00",
                code_version="abc1234")
    base.update(over)
    return RunMetrics(**base)


def _applied(**over) -> dict:
    point = VARIED_RUN.config
    base = {
        "spark.master": point.master,
        "spark.sql.shuffle.partitions": str(point.shuffle_partitions),
        "spark.default.parallelism": str(point.default_parallelism),
        "spark.sql.adaptive.enabled": "false",
        "spark.driver.memory": point.driver_memory,
        "sc.defaultParallelism": point.default_parallelism,
    }
    base.update(over)
    return base


def _record(metrics: RunMetrics, attempt: int = 1) -> dict:
    return build_record(SPEC, VARIED_RUN, metrics, {"code_version": "abc1234"},
                        attempt)


# --- status mapping ------------------------------------------------------

def test_usable_metrics_map_to_completed():
    record = _record(_metrics())
    assert record["status"] == COMPLETED
    assert record["schema_version"] == RECORD_SCHEMA_VERSION == "exp002-run/v1"
    assert record["experiment_id"] == EXPERIMENT_ID
    assert record["attempt"] == 1
    assert record["spec_fingerprint"] == SPEC.fingerprint()
    assert record["run_spec"]["run_id"] == VARIED_RUN.run_id
    assert record["metrics"]["execution_time_s"] == 12.5


def test_unusable_metrics_with_an_error_map_to_failed():
    record = _record(_metrics(usable=False, success=False,
                              error="Py4JJavaError: boom", execution_time_s=None))
    assert record["status"] == FAILED


def test_timed_out_metrics_map_to_failed():
    record = _record(_metrics(usable=False, success=False, timeout=True,
                              error=None, execution_time_s=None))
    assert record["status"] == FAILED


def test_unusable_metrics_that_succeeded_without_an_error_map_to_incomplete():
    record = _record(_metrics(usable=False, success=True, error=None,
                              timeout=False, event_log_status="INCOMPLETE"))
    assert record["status"] == INCOMPLETE


def test_an_invalid_run_is_never_completed():
    for metrics in (_metrics(usable=False, success=False, error="crash"),
                    _metrics(usable=False, success=True, error=None),
                    _metrics(usable=False, success=False, timeout=True)):
        record = _record(metrics)
        assert record["status"] != COMPLETED
        assert is_completed(record) is False


def test_build_record_keeps_provenance_and_grid_identity():
    provenance = {"code_version": "abc1234", "applied_mismatches": [],
                  "event_log_path": "logs/app-1"}
    record = build_record(SPEC, B0_RUN, _metrics(run_id=B0_RUN.run_id), provenance, 3)
    assert record["provenance"] is provenance
    assert record["attempt"] == 3
    assert record["run_spec"]["config_is_reference"] is True
    assert record["run_spec"]["split"] == "train"
    assert record["grid_fingerprint"]


# --- completion predicate ------------------------------------------------

def test_is_completed_requires_both_status_and_usable_metrics():
    assert is_completed(_record(_metrics())) is True
    assert is_completed({"status": COMPLETED, "metrics": {"usable": False}}) is False
    assert is_completed({"status": COMPLETED, "metrics": {}}) is False
    assert is_completed({"status": FAILED, "metrics": {"usable": True}}) is False
    assert is_completed({"status": INCOMPLETE, "metrics": {"usable": False}}) is False
    assert is_completed(None) is False
    assert is_completed({}) is False


def test_record_status_reads_the_stored_status():
    assert record_status(_record(_metrics())) == COMPLETED
    assert record_status(None) is None


# --- applied-configuration verification ---------------------------------

def test_verify_applied_accepts_a_matching_session():
    assert verify_applied(VARIED_RUN, _applied()) == []


def test_verify_applied_requires_b0_to_hold_sparks_own_default_parallelism():
    """B0 is checked on default.parallelism too, and an unset value is a mismatch.

    Not checking it is exactly what let a stale JVM-level value (8) leak into B0
    while the master still read local[2].
    """
    point = B0_RUN.config
    base = {"spark.master": point.master,
            "spark.sql.shuffle.partitions": str(point.shuffle_partitions),
            "spark.sql.adaptive.enabled": "false"}

    unset = dict(base, **{"spark.default.parallelism": None,
                          "sc.defaultParallelism": None})
    assert any("default.parallelism" in p for p in verify_applied(B0_RUN, unset))

    leaked = dict(base, **{"spark.default.parallelism": "8",
                           "sc.defaultParallelism": 8})
    assert any("default.parallelism" in p for p in verify_applied(B0_RUN, leaked))

    correct = dict(base, **{"spark.default.parallelism": "2",
                            "sc.defaultParallelism": 2})
    assert verify_applied(B0_RUN, correct) == []


def test_verify_applied_reports_a_master_mismatch():
    problems = verify_applied(VARIED_RUN, _applied(**{"spark.master": "local[1]"}))
    assert len(problems) == 1
    assert "master" in problems[0]


def test_verify_applied_reports_a_shuffle_partitions_mismatch():
    problems = verify_applied(
        VARIED_RUN, _applied(**{"spark.sql.shuffle.partitions": "200"}))
    assert len(problems) == 1
    assert "shuffle.partitions" in problems[0]


def test_verify_applied_reports_a_default_parallelism_mismatch():
    problems = verify_applied(
        VARIED_RUN, _applied(**{"spark.default.parallelism": "1"}))
    assert len(problems) == 1
    assert "default.parallelism" in problems[0]


@pytest.mark.parametrize("reported", ["true", "True", None, "TRUE"])
def test_verify_applied_always_rejects_an_aqe_enabled_session(reported):
    problems = verify_applied(
        VARIED_RUN, _applied(**{"spark.sql.adaptive.enabled": reported}))
    assert any("AQE must be OFF" in p for p in problems)


def test_verify_applied_reports_every_mismatch_at_once():
    problems = verify_applied(VARIED_RUN, _applied(**{
        "spark.master": "local[1]",
        "spark.sql.shuffle.partitions": "200",
        "spark.default.parallelism": "1",
        "spark.sql.adaptive.enabled": "true"}))
    assert len(problems) == 4


# --- record I/O ----------------------------------------------------------

def test_read_record_returns_none_for_a_missing_file(tmp_path):
    assert read_record(tmp_path / "nope.json") is None
    assert read_record(tmp_path) is None          # a directory is not a record


def test_read_record_returns_none_for_corrupt_json(tmp_path):
    corrupt = tmp_path / "rep1.json"
    corrupt.write_text("{ this is not json", encoding="utf-8")
    assert read_record(corrupt) is None


def test_read_record_round_trips_a_written_record(tmp_path):
    path = tmp_path / "rep1.json"
    record = _record(_metrics())
    _atomic_write_json(path, record)
    assert read_record(path) == record


def test_load_records_skips_unreadable_files_and_sorts_by_run_id(tmp_path):
    runs_dir = tmp_path / "runs"
    for run_id in ("exp002-zzz", "exp002-aaa", "exp002-mmm"):
        path = runs_dir / run_id / "rep1.json"
        _atomic_write_json(path, {"status": COMPLETED,
                                  "run_spec": {"run_id": run_id}})
    (runs_dir / "broken").mkdir(parents=True, exist_ok=True)
    (runs_dir / "broken" / "rep1.json").write_text("<<garbage>>", encoding="utf-8")

    records = load_records(tmp_path)
    assert [r["run_spec"]["run_id"] for r in records] == [
        "exp002-aaa", "exp002-mmm", "exp002-zzz"]


def test_load_records_returns_empty_for_an_empty_root(tmp_path):
    assert load_records(tmp_path) == []


# --- atomic write --------------------------------------------------------

def test_atomic_write_json_creates_parents_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "runs" / "F1_agg" / "small" / "seed0" / "B0" / "rep1.json"
    _atomic_write_json(path, {"status": COMPLETED, "attempt": 1})
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8")) == {"status": COMPLETED,
                                                            "attempt": 1}
    assert list(tmp_path.rglob("*.tmp")) == []


def test_atomic_write_json_overwrites_in_place_without_leftovers(tmp_path):
    path = tmp_path / "rep1.json"
    _atomic_write_json(path, {"attempt": 1})
    _atomic_write_json(path, {"attempt": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == {"attempt": 2}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["rep1.json"]
