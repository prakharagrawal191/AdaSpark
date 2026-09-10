"""Unit tests for the Day-16 event-log parser (fixtures are hand-calculable)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sparkrl.monitoring.eventlog_parser import find_event_log, parse_event_log
from sparkrl.monitoring.schemas import EventLogStatus

pytestmark = [pytest.mark.unit]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "eventlogs"


def parse(name: str):
    return parse_event_log(FIXTURES / name)


def test_valid_log_complete_status_and_identity():
    log = parse("valid.jsonl")
    assert log.status == EventLogStatus.COMPLETE
    assert log.spark_version == "3.5.9"
    assert log.application_id == "app-fixture-0001"
    assert log.application_start_ms == 1000
    assert log.application_end_ms == 9000


def test_valid_log_event_accounting():
    log = parse("valid.jsonl")
    assert log.total_lines == 11
    assert log.parsed_lines == 11
    assert log.malformed_lines == 0
    # StageSubmitted + JobStart are not in the frozen metric set -> tolerated
    assert log.unknown_event_types == {"SparkListenerStageSubmitted": 1,
                                       "SparkListenerJobStart": 1}


def test_valid_log_stage_and_task_counts():
    log = parse("valid.jsonl")
    assert log.stage_count == 2
    assert log.task_end_count == 3
    assert log.failed_task_count == 0
    assert [s.stage_id for s in log.stages] == [0, 1]
    assert log.stages[0].num_tasks == 2


def test_shuffle_read_aggregation_no_double_counting():
    # task0: 100 local + 200 remote + 50 to-disk = 350; task1: 0; task2: 1000
    log = parse("valid.jsonl")
    assert log.shuffle_read_bytes == 1350


def test_shuffle_write_aggregation():
    log = parse("valid.jsonl")
    assert log.shuffle_write_bytes == 500 + 700 + 0


def test_spill_aggregation_distinct_memory_vs_disk():
    log = parse("valid.jsonl")
    assert log.memory_spill_bytes == 10 + 5
    assert log.disk_spill_bytes == 20


def test_task_duration_wall_clock_formula():
    # durations from Launch/Finish times: [2.0, 3.0, 1.0] seconds
    log = parse("valid.jsonl")
    assert log.task_duration_mean_s == pytest.approx(2.0)
    assert log.task_duration_median_s == pytest.approx(2.0)
    assert log.task_duration_std_s == pytest.approx(1.0)  # sample std ddof=1
    assert log.task_duration_cv == pytest.approx(0.5)


def test_failed_tasks_counted_and_metrics_still_summed():
    log = parse("failed_tasks.jsonl")
    assert log.task_end_count == 4
    assert log.failed_task_count == 2
    assert log.shuffle_read_bytes == 100
    assert log.memory_spill_bytes == 7
    assert log.task_duration_cv == pytest.approx(1.2909944 / 2.5, rel=1e-4)


def test_aqe_mode_recorded_not_set():
    log = parse("valid.jsonl")
    assert log.aqe_enabled is False


def test_empty_log_is_incomplete():
    log = parse("empty.jsonl")
    assert log.status == EventLogStatus.INCOMPLETE
    assert log.parsed_lines == 0
    assert log.task_end_count == 0
    assert log.task_duration_cv is None  # 0 tasks -> mathematically undefined


def test_incomplete_log_missing_application_end():
    log = parse("incomplete.jsonl")
    assert log.status == EventLogStatus.INCOMPLETE
    assert log.application_end_ms is None


def test_malformed_line_counted_not_fatal():
    log = parse("malformed_line.jsonl")
    assert log.status == EventLogStatus.COMPLETE  # LogStart + AppEnd present
    assert log.malformed_lines == 1
    assert log.parsed_lines == 3
    assert len(log.malformed_samples) == 1


def test_garbage_log_is_malformed():
    log = parse("garbage.jsonl")
    assert log.status == EventLogStatus.MALFORMED
    assert log.parsed_lines == 0


def test_missing_log():
    log = parse("does_not_exist.jsonl")
    assert log.status == EventLogStatus.MISSING


def test_missing_task_metrics_tolerated():
    # TaskEnd without 'Task Metrics' contributes counts but zero bytes
    log = parse("incomplete.jsonl")
    assert log.task_end_count == 1
    assert log.shuffle_write_bytes == 42  # present in this fixture
    empty = parse("empty.jsonl")
    assert empty.task_duration_std_s is None  # 0 durations -> None, not NaN
    assert empty.task_duration_cv is None


def test_parser_is_deterministic():
    a = parse("valid.jsonl")
    b = parse("valid.jsonl")
    assert (a.shuffle_read_bytes, a.shuffle_write_bytes, a.stage_count,
            a.task_end_count, a.task_duration_cv) == (
        b.shuffle_read_bytes, b.shuffle_write_bytes, b.stage_count,
        b.task_end_count, b.task_duration_cv)


def test_find_event_log_prefers_application_id(tmp_path):
    (tmp_path / "local-111").write_text("{}", encoding="utf-8")
    (tmp_path / "local-222").write_text("{}", encoding="utf-8")
    assert find_event_log(tmp_path).name == "local-222"  # newest
    assert find_event_log(tmp_path, "app-xyz") is None
    (tmp_path / "app-xyz_333").write_text("{}", encoding="utf-8")
    assert find_event_log(tmp_path, "app-xyz").name == "app-xyz_333"
    assert find_event_log(tmp_path / "nope") is None
