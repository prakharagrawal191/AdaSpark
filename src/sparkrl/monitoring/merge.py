"""Dedicated merge layer (Day 19): RunResult + RuntimeMetrics + SystemSummary.

Produces one validated ``RunMetrics`` (schema ``run_metrics/v1``) per run.
Inputs are never mutated. Merge semantics follow the frozen measurement
rules: runner execution time authoritative, event-log Spark metrics from
Day-18 semantics, psutil summary optional and explicit.

Backward compatibility: ``RunMetrics.from_dict`` ignores unknown keys, and
the Day-17 B0 files map losslessly into v1 (see ``read_legacy_manifest``).
"""
from __future__ import annotations

from typing import Any

from sparkrl.monitoring.run_metrics import (RunMetrics,
                                            assert_valid_run_metrics,)
from sparkrl.monitoring.schemas import RuntimeMetrics
from sparkrl.monitoring.sysmon import SystemSummary


def merge_run_metrics(*,
                      run_id: str | None,
                      workload: Any | None,
                      dataset: Any | None,
                      run_result: Any | None,
                      runtime: RuntimeMetrics,
                      system: SystemSummary | None = None,
                      code_version: str | None = None,
                      timestamp: str | None = None) -> RunMetrics:
    """Build a validated RunMetrics. Raises ValueError on invalid merges."""
    system = system or SystemSummary.unavailable("not sampled")
    spec = getattr(workload, "spec", None)
    # WorkloadResult payload (Day-15): signature/rows/columns/measurements.
    payload = getattr(run_result, "checksum", None)
    signature = getattr(payload, "result_signature", None)
    rows = getattr(payload, "rows_processed", None)

    merged = RunMetrics(
        run_id=run_id,
        workload_id=(getattr(run_result, "workload_id", None)
                     if run_result is not None else None),
        family=getattr(spec, "family", None),
        scale=getattr(spec, "scale", None),
        seed=getattr(spec, "seed", None),
        dataset_id=getattr(dataset, "dataset_id", None),
        dataset_fingerprint=getattr(dataset, "dataset_fingerprint", None),
        schema_fingerprint=getattr(dataset, "schema_fingerprint", None),
        config_fingerprint=(getattr(run_result, "config_fingerprint", None)
                            if run_result is not None else None),
        aqe_enabled=runtime.aqe_enabled,
        spark_version=None,
        result_signature=signature,
        timestamp=timestamp,
        execution_time_s=runtime.execution_time_s,
        execution_time_source=runtime.execution_time_source,
        warmup_time_s=(getattr(run_result, "warmup_time", None)
                       if run_result is not None else None),
        total_time_s=(getattr(run_result, "total_time", None)
                      if run_result is not None else None),
        success=bool(run_result.success) if run_result is not None else False,
        usable=False,  # decided below; never inherited silently
        timeout=bool(getattr(run_result, "timeout", False)),
        error=(getattr(run_result, "error", None)
               if run_result is not None else None),
        application_id=runtime.application_id,
        stage_count=runtime.stage_count,
        task_count=runtime.task_count,
        failed_task_count=runtime.failed_task_count,
        shuffle_read_bytes=runtime.shuffle_read_bytes,
        shuffle_write_bytes=runtime.shuffle_write_bytes,
        memory_spill_bytes=runtime.memory_spill_bytes,
        disk_spill_bytes=runtime.disk_spill_bytes,
        task_duration_mean_s=runtime.task_duration_mean_s,
        task_duration_median_s=runtime.task_duration_median_s,
        task_duration_std_s=runtime.task_duration_std_s,
        task_duration_cv=runtime.task_duration_cv,
        rows_processed=rows,
        sysmon_sampled=system.sampled,
        sysmon_reason=system.reason,
        sysmon_sample_count=system.sample_count,
        sysmon_window_s=system.window_s,
        rss_bytes_max=system.rss_bytes_max,
        rss_bytes_mean=system.rss_bytes_mean,
        proc_cpu_time_s=system.proc_cpu_time_s,
        proc_cpu_percent_mean=system.proc_cpu_percent_mean,
        sys_cpu_percent_mean=system.sys_cpu_percent_mean,
        sys_mem_available_bytes_min=system.sys_mem_available_bytes_min,
        sys_mem_percent_max=system.sys_mem_percent_max,
        event_log_status=runtime.event_log_status,
        event_log_path=None,
        event_log_total_events=runtime.event_log_total_events,
        malformed_event_count=runtime.malformed_event_count,
        unknown_event_count=runtime.unknown_event_count,
        code_version=code_version,
    )
    # usable is a deliberate construction decision, not an input echo:
    merged.usable = bool(merged.success
                         and merged.execution_time_s is not None
                         and merged.event_log_status == "COMPLETE"
                         and merged.result_signature is not None)
    assert_valid_run_metrics(merged)
    return merged


def read_legacy_manifest(raw: dict[str, Any]) -> RunMetrics:
    """Map a Day-17 B0 manifest (flat correctness/performance/monitoring
    sections) into schema v1. Lossless for the frozen fields; psutil block
    stays unsampled (it was not measured on Day 17)."""
    get = raw.get
    merged = RunMetrics(
        run_id=get("run_id"),
        workload_id=get("workload_id"),
        family=get("family"),
        scale=get("scale"),
        seed=get("seed"),
        dataset_id=get("dataset_id"),
        dataset_fingerprint=get("dataset_fingerprint"),
        schema_fingerprint=get("schema_fingerprint"),
        config_fingerprint=get("configuration_fingerprint"),
        aqe_enabled=(get("aqe_mode") == "on") if get("aqe_mode") else None,
        spark_version=get("spark_version"),
        result_signature=get("result_signature"),
        timestamp=get("timestamp"),
        execution_time_s=get("execution_time_s"),
        execution_time_source="runner",
        warmup_time_s=get("warmup_time_s"),
        total_time_s=get("total_time_s"),
        success=bool(get("success")),
        timeout=bool(get("timeout")),
        error=get("error"),
        application_id=get("application_id"),
        stage_count=get("stage_count"),
        task_count=get("task_count"),
        failed_task_count=get("failed_task_count"),
        shuffle_read_bytes=get("shuffle_read_bytes"),
        shuffle_write_bytes=get("shuffle_write_bytes"),
        memory_spill_bytes=get("memory_spill_bytes"),
        disk_spill_bytes=get("disk_spill_bytes"),
        total_spill_bytes=get("total_spill_bytes"),
        task_duration_mean_s=get("task_duration_mean_s"),
        task_duration_cv=get("task_duration_cv"),
        rows_processed=get("rows_processed"),
        event_log_status=get("event_log_status"),
        code_version=get("code_version"),
    )
    merged.usable = bool(merged.success
                         and merged.execution_time_s is not None
                         and merged.event_log_status == "COMPLETE"
                         and merged.result_signature is not None)
    assert_valid_run_metrics(merged)
    return merged