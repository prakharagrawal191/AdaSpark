"""Unit tests for Day-19 merge schema, merge layer, and psutil sampler.

Pure-Python only (no Spark): fixtures are synthetic RunResult/RuntimeMetrics
stand-ins, so these run in the ``unit`` marker set.
"""
from __future__ import annotations

import dataclasses
import time
from types import SimpleNamespace

import pytest

from sparkrl.monitoring.merge import merge_run_metrics, read_legacy_manifest
from sparkrl.monitoring.run_metrics import (SCHEMA_VERSION, RunMetrics,
                                            assert_valid_run_metrics,
                                            validate_run_metrics,)
from sparkrl.monitoring.schemas import RuntimeMetrics
from sparkrl.monitoring.sysmon import SamplerConfig, SystemSampler, SystemSummary

pytestmark = [pytest.mark.unit]


def _workload():
    return SimpleNamespace(spec=SimpleNamespace(family="F2_join",
                                                scale="small", seed=0))


def _dataset():
    return SimpleNamespace(dataset_id="skew1_small_s0",
                           dataset_fingerprint="aa" * 32,
                           schema_fingerprint="bb" * 32)


def _run_result(**over):
    base = dict(success=True, execution_time=1.812, warmup_time=3.0,
                total_time=9.0, timeout=False, error=None,
                spark_app_id="local-1", config_fingerprint="cc" * 32,
                workload_id="F2_join_v1")
    base.update(over)
    payload = SimpleNamespace(result_signature="8d7c822ef7e22db0",
                              rows_processed=365)
    base["checksum"] = payload
    return SimpleNamespace(**base)


def _runtime(**over):
    base = dict(run_id=None, application_id="local-1",
                execution_time_s=1.812, execution_time_source="runner",
                stage_count=23, task_count=1821, failed_task_count=0,
                shuffle_read_bytes=272593, shuffle_write_bytes=175426,
                memory_spill_bytes=0, disk_spill_bytes=0, total_spill_bytes=0,
                task_duration_mean_s=0.0056, task_duration_median_s=0.002,
                task_duration_std_s=0.016, task_duration_cv=2.9,
                aqe_enabled=False, event_log_status="COMPLETE",
                event_log_total_events=3757, malformed_event_count=0,
                unknown_event_count=11)
    base.update(over)
    return RuntimeMetrics(**base)


def test_schema_version_frozen():
    assert SCHEMA_VERSION == "run_metrics/v1"
    assert RunMetrics().schema_version == SCHEMA_VERSION


def test_merge_happy_path_keeps_provenance():
    merged = merge_run_metrics(run_id="b0-F2-join-small-s0-r2",
                               workload=_workload(), dataset=_dataset(),
                               run_result=_run_result(), runtime=_runtime(),
                               code_version="day19", timestamp="2026-01-01T00:00:00Z")
    assert validate_run_metrics(merged) == []
    assert merged.family == "F2_join" and merged.seed == 0
    assert merged.execution_time_s == 1.812
    assert merged.execution_time_source == "runner"  # runner authoritative
    assert merged.shuffle_read_bytes == 272593
    assert merged.result_signature == "8d7c822ef7e22db0"
    assert merged.usable is True
    # psutil absent by default: unsampled, metrics None (not zero)
    assert merged.sysmon_sampled is False
    assert merged.rss_bytes_max is None
    assert merged.sysmon_reason == "not sampled"


def test_merge_runner_time_wins_over_event_log_clock():
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(execution_time_s=5.953,
                                                execution_time_source="event_log"),
                               code_version="day19")
    # build_runtime_metrics already resolved authority upstream; the merge
    # layer echoes whatever the RuntimeMetrics carried (no silent override).
    assert merged.execution_time_s == 5.953
def test_merge_with_real_sampler_summary():
    summary = SystemSummary(sampled=True, reason=None, sample_count=4,
                            window_s=3.1, rss_bytes_max=10**8,
                            rss_bytes_mean=9 * 10**7, proc_cpu_time_s=0.5,
                            proc_cpu_percent_mean=12.5,
                            sys_cpu_percent_mean=40.0,
                            sys_mem_available_bytes_min=2 * 10**10,
                            sys_mem_percent_max=35.0)
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(), system=summary,
                               code_version="day19")
    assert validate_run_metrics(merged) == []
    assert merged.sysmon_sampled is True
    assert merged.rss_bytes_max == 10**8
    assert isinstance(merged.rss_bytes_max, int)  # bytes are ints


def test_none_vs_zero_semantics_merge_preserves_none():
    # Missing Spark metrics stay None (never fabricated as 0)
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(shuffle_read_bytes=None,
                                                stage_count=None),
                               code_version="day19")
    assert merged.shuffle_read_bytes is None
    assert merged.stage_count is None


def test_byte_fields_must_be_ints():
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(), code_version="day19")
    bad = dataclasses.replace(merged, shuffle_read_bytes=272593.0)
    assert any("integer byte count" in e for e in validate_run_metrics(bad))


def test_usable_requires_complete_log_and_signature():
    rt = _runtime(event_log_status="INCOMPLETE")
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=rt, code_version="day19")
    # record preserved for audit trail, but marked unusable
    assert merged.usable is False
    assert merged.event_log_status == "INCOMPLETE"
    assert merged.execution_time_s == 1.812  # runner time still recorded


def test_invalid_schema_rejected():
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(), code_version="day19")
    bad = dataclasses.replace(merged, schema_version="run_metrics/v9")
    with pytest.raises(ValueError):
        assert_valid_run_metrics(bad)
    bad2 = dataclasses.replace(merged, shuffle_write_bytes=-1)
    assert any("negative" in e for e in validate_run_metrics(bad2))


def test_unsampled_sysmon_metrics_must_be_none():
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(), code_version="day19")
    planted = dataclasses.replace(merged, rss_bytes_max=0)  # zero != absent
    assert any("None-vs-zero" in e for e in validate_run_metrics(planted))


def test_deterministic_serialization():
    merged = merge_run_metrics(run_id="r", workload=_workload(),
                               dataset=_dataset(), run_result=_run_result(),
                               runtime=_runtime(), code_version="day19")
    assert merged.to_json() == merged.to_json()
    assert RunMetrics.from_dict(merged.to_dict()) == merged
    assert RunMetrics.from_dict({**merged.to_dict(), "future": 1}) == merged


def test_legacy_day17_manifest_reads_losslessly():
    raw = {
        "run_id": "b0-F2-join-small-s0-r2", "workload_id": "F2_join_v1",
        "family": "F2_join", "scale": "small", "seed": 0,
        "dataset_id": "skew1_small_s0", "dataset_fingerprint": "aa" * 32,
        "schema_fingerprint": "bb" * 32, "configuration_fingerprint": "cc" * 32,
        "aqe_mode": "off", "spark_version": "3.5.9",
        "result_signature": "8d7c822ef7e22db0", "timestamp": "t",
        "execution_time_s": 1.812, "warmup_time_s": 3.0, "total_time_s": 9.0,
        "success": True, "timeout": False, "error": None,
        "application_id": "local-1", "stage_count": 23, "task_count": 1821,
        "failed_task_count": 0, "shuffle_read_bytes": 272593,
        "shuffle_write_bytes": 175426, "memory_spill_bytes": 0,
        "disk_spill_bytes": 0, "total_spill_bytes": 0,
        "task_duration_mean_s": 0.0056, "task_duration_cv": 2.9,
        "rows_processed": 365, "event_log_status": "COMPLETE",
        "code_version": "day17",
        "correctness": {"validated": True}, "performance": {}, "monitoring": {},
    }
    merged = read_legacy_manifest(raw)
    assert validate_run_metrics(merged) == []
    assert merged.schema_version == SCHEMA_VERSION
    assert merged.usable is True
    assert merged.sysmon_sampled is False  # not measured on Day 17
    assert merged.aqe_enabled is False     # aqe_mode "off" mapped
    assert merged.execution_time_source == "runner"


def test_sampler_disabled_never_fails():
    s = SystemSampler(SamplerConfig(enabled=False))
    s.start()
    time.sleep(0.05)
    s.stop()
    summary = s.summary()
    assert summary.sampled is False
    assert summary.reason == "disabled by config"
    assert summary.rss_bytes_max is None  # absent, not zero


def test_sampler_bounded_and_live():
    s = SystemSampler(SamplerConfig(interval_s=0.05, max_samples=5))
    s.start()
    time.sleep(0.4)
    s.stop()
    summary = s.summary()
    assert summary.sampled is True
    assert summary.sample_count <= 5
    assert summary.rss_bytes_max is not None and summary.rss_bytes_max > 0
    assert summary.window_s is not None and summary.window_s > 0


def test_sampler_context_manager_never_swallows():
    try:
        with SystemSampler(SamplerConfig(interval_s=0.05)):
            time.sleep(0.12)
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    else:  # pragma: no cover - sampler must not swallow
        raise AssertionError("sampler swallowed caller exception")