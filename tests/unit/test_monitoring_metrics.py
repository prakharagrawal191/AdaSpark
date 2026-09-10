"""Unit tests for RuntimeMetrics construction, serialization, and policy."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

import pytest

from sparkrl.monitoring.eventlog_parser import parse_event_log
from sparkrl.monitoring.metrics import build_runtime_metrics, metrics_for_run
from sparkrl.monitoring.schemas import EventLogStatus, RuntimeMetrics
from sparkrl.monitoring.validate import assert_valid, validate_metrics

pytestmark = [pytest.mark.unit]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "eventlogs"


@dataclass
class FakeRunResult:  # minimal Day-3 RunResult stand-in
    success: bool = True
    execution_time: float = 12.5
    warmup_time: float = 1.0
    total_time: float = 14.0
    timeout: bool = False
    error: str | None = None
    spark_app_id: str | None = "app-runner-1"
    workload_id: str = "F2_join_v1"


def test_build_from_runner_and_log():
    log = parse_event_log(FIXTURES / "valid.jsonl")
    m = build_runtime_metrics(FakeRunResult(), log)
    assert m.execution_time_s == 12.5
    assert m.execution_time_source == "runner"
    assert m.application_id == "app-runner-1"  # runner wins identity
    assert m.stage_count == 2
    assert m.task_count == 3
    assert m.total_spill_bytes == m.memory_spill_bytes + m.disk_spill_bytes
    assert m.event_log_status == "COMPLETE"
    assert validate_metrics(m) == []


def test_execution_time_falls_back_to_event_log_clock():
    log = parse_event_log(FIXTURES / "valid.jsonl")
    m = build_runtime_metrics(None, log)
    assert m.execution_time_s == pytest.approx(8.0)  # (9000-1000)/1000
    assert m.execution_time_source == "event_log"
    assert m.application_id == "app-fixture-0001"


def test_missing_both_clocks_aborts():
    log = parse_event_log(FIXTURES / "incomplete.jsonl")
    with pytest.raises(ValueError, match="execution-time clock"):
        build_runtime_metrics(None, log, include_incomplete=True)


def test_incomplete_log_requires_diagnostic_flag():
    log = parse_event_log(FIXTURES / "incomplete.jsonl")
    with pytest.raises(ValueError, match="incomplete"):
        build_runtime_metrics(FakeRunResult(), log)
    m = build_runtime_metrics(FakeRunResult(), log, include_incomplete=True)
    assert m.event_log_status == "INCOMPLETE"
    assert m.shuffle_write_bytes == 42
    errors = validate_metrics(m)
    assert any("INCOMPLETE" in e for e in errors)  # surfaced, never silent
    with pytest.raises(ValueError):
        assert_valid(m)


def test_missing_and_malformed_logs_rejected():
    with pytest.raises(ValueError, match="MISSING"):
        build_runtime_metrics(FakeRunResult(),
                              parse_event_log(FIXTURES / "nope.jsonl"))
    with pytest.raises(ValueError, match="MALFORMED"):
        build_runtime_metrics(FakeRunResult(),
                              parse_event_log(FIXTURES / "garbage.jsonl"))


def test_wall_clock_only_when_log_absent():
    m = metrics_for_run(FakeRunResult(), None, include_incomplete=True)
    assert m.execution_time_s == 12.5
    assert m.event_log_status == "MISSING"
    assert m.task_count is None  # no event-log metrics fabricated
    with pytest.raises(ValueError, match="MISSING"):
        metrics_for_run(FakeRunResult(), None)  # flag required


def test_serialization_round_trip():
    log = parse_event_log(FIXTURES / "valid.jsonl")
    m = build_runtime_metrics(FakeRunResult(), log, run_id="run-9")
    raw = m.to_dict()
    assert raw["task_duration_cv"] == m.task_duration_cv
    m2 = RuntimeMetrics.from_dict(raw)
    assert m2 == m
    # unknown keys are ignored (forward compatibility)
    assert RuntimeMetrics.from_dict({**raw, "future_field": 1}) == m


def test_validate_catches_bad_invariants():
    base = build_runtime_metrics(FakeRunResult(),
                                 parse_event_log(FIXTURES / "valid.jsonl"))
    bad = RuntimeMetrics.from_dict(
        {**base.to_dict(), "shuffle_read_bytes": -1})
    assert any("negative" in e for e in validate_metrics(bad))
    bad2 = RuntimeMetrics.from_dict(
        {**base.to_dict(), "total_spill_bytes": 999})
    assert any("total_spill" in e for e in validate_metrics(bad2))


def test_unknown_event_count_aggregated():
    m = build_runtime_metrics(FakeRunResult(),
                              parse_event_log(FIXTURES / "valid.jsonl"))
    assert m.unknown_event_count == 2  # StageSubmitted + JobStart tolerated
    assert m.event_log_total_events == 11
