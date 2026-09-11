"""Versioned merged run-metrics schema (Day 19).

One deterministic record per completed run, combining:
  A. identity (run/workload/dataset/config),
  B. execution (runner-authoritative timing + validity),
  C. Spark/event-log metrics (Day-18 parser semantics, unchanged),
  D. optional system monitoring (psutil summary; never fabricated),
  E. provenance (schema/config/code versions, event-log path, statuses).

Measurement rules (frozen, see Day-19 audit):
  1. runner execution time authoritative; event-log wall clock fallback only;
  2. shuffle sums come from TaskEnd metrics once (no double count);
  3. task count attempts-inclusive; failed count kept separately;
  4. task-duration CV = sample std (ddof=1) / mean; None when undefined;
  5. missing metrics stay None - NEVER fabricated as 0;
  6. psutil distinguishes unavailable (sampled=False + reason) from zero;
  7. timing in seconds (float), bytes as integer counts.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "run_metrics/v1"

REQUIRED_TOP_LEVEL = (
    "schema_version", "run_id", "workload_id", "family", "scale", "seed",
    "dataset_id", "config_fingerprint",
    "execution_time_s", "execution_time_source", "success", "usable",
    "event_log_status",
)


@dataclass
class RunMetrics:
    """Merged, validated, deterministic run record (schema v1)."""

    # A. identity
    schema_version: str = SCHEMA_VERSION
    run_id: str | None = None
    workload_id: str | None = None
    family: str | None = None
    scale: str | None = None
    seed: int | None = None
    dataset_id: str | None = None
    dataset_fingerprint: str | None = None
    schema_fingerprint: str | None = None
    config_fingerprint: str | None = None
    aqe_enabled: bool | None = None
    spark_version: str | None = None
    result_signature: str | None = None
    timestamp: str | None = None
    # B. execution (runner-authoritative)
    execution_time_s: float | None = None
    execution_time_source: str | None = None  # "runner" | "event_log"
    warmup_time_s: float | None = None
    total_time_s: float | None = None
    success: bool = False
    usable: bool = False
    timeout: bool = False
    error: str | None = None
    # C. Spark/event-log metrics (Day-18 semantics, explicit None if absent)
    application_id: str | None = None
    stage_count: int | None = None
    task_count: int | None = None
    failed_task_count: int | None = None
    shuffle_read_bytes: int | None = None
    shuffle_write_bytes: int | None = None
    memory_spill_bytes: int | None = None
    disk_spill_bytes: int | None = None
    total_spill_bytes: int | None = None
    task_duration_mean_s: float | None = None
    task_duration_median_s: float | None = None
    task_duration_std_s: float | None = None
    task_duration_cv: float | None = None
    rows_processed: int | None = None
    # D. optional system monitoring (psutil; None/unset means NOT measured)
    sysmon_sampled: bool = False
    sysmon_reason: str | None = None
    sysmon_sample_count: int = 0
    sysmon_window_s: float | None = None
    rss_bytes_max: int | None = None
    rss_bytes_mean: int | None = None
    proc_cpu_time_s: float | None = None
    proc_cpu_percent_mean: float | None = None
    sys_cpu_percent_mean: float | None = None
    sys_mem_available_bytes_min: int | None = None
    sys_mem_percent_max: float | None = None
    # E. provenance
    event_log_status: str | None = None
    event_log_path: str | None = None
    event_log_total_events: int | None = None
    malformed_event_count: int | None = None
    unknown_event_count: int | None = None
    code_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Deterministic serialization (sorted keys at write time)."""
        return dataclasses.asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RunMetrics":
        """Rebuild from a dict; ignores unknown keys (forward-compatible)."""
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})


def validate_run_metrics(m: RunMetrics) -> list[str]:
    """Return invariant violations ([] = valid). Structural, not scientific."""
    errors: list[str] = []

    if m.schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version {m.schema_version!r} != {SCHEMA_VERSION!r}")

    def _neg(name: str, value) -> None:
        if value is not None and isinstance(value, (int, float)) and value < 0:
            errors.append(f"{name} is negative ({value})")

    for name in ("stage_count", "task_count", "failed_task_count",
                 "shuffle_read_bytes", "shuffle_write_bytes",
                 "memory_spill_bytes", "disk_spill_bytes", "total_spill_bytes",
                 "rows_processed", "sysmon_sample_count",
                 "rss_bytes_max", "rss_bytes_mean",
                 "sys_mem_available_bytes_min"):
        _neg(name, getattr(m, name))
    for name in ("execution_time_s", "warmup_time_s", "total_time_s",
                 "task_duration_mean_s", "task_duration_median_s",
                 "task_duration_std_s", "proc_cpu_time_s", "sysmon_window_s"):
        _neg(name, getattr(m, name))

    # byte fields that are present must be integers (no floats-as-bytes)
    for name in ("shuffle_read_bytes", "shuffle_write_bytes",
                 "memory_spill_bytes", "disk_spill_bytes", "total_spill_bytes",
                 "rss_bytes_max", "rss_bytes_mean",
                 "sys_mem_available_bytes_min"):
        value = getattr(m, name)
        if value is not None and not isinstance(value, int):
            errors.append(f"{name} must be an integer byte count, got "
                          f"{type(value).__name__}")

    if (m.memory_spill_bytes is not None and m.disk_spill_bytes is not None
            and m.total_spill_bytes is not None
            and m.total_spill_bytes != m.memory_spill_bytes + m.disk_spill_bytes):
        errors.append("total_spill_bytes != memory_spill + disk_spill")

    if m.task_duration_cv is not None:
        if m.task_duration_cv < 0:
            errors.append("task_duration_cv is negative")
        if m.task_duration_mean_s in (None, 0):
            errors.append("task_duration_cv set although mean is zero/missing")

    if m.execution_time_source not in (None, "runner", "event_log"):
        errors.append(f"unknown execution_time_source: {m.execution_time_source!r}")
    if m.usable and m.execution_time_s is None:
        errors.append("usable=True but execution_time_s is missing")
    if m.usable and not m.success:
        errors.append("usable=True but success=False")

    # sysmon consistency: unsampled => metrics must be None, never 0
    if not m.sysmon_sampled:
        for name in ("rss_bytes_max", "rss_bytes_mean", "proc_cpu_time_s",
                     "proc_cpu_percent_mean", "sys_cpu_percent_mean",
                     "sys_mem_available_bytes_min", "sys_mem_percent_max"):
            if getattr(m, name) is not None:
                errors.append(f"sysmon unsampled but {name} is set "
                              f"(None-vs-zero rule)")

    return errors


def assert_valid_run_metrics(m: RunMetrics) -> None:
    errors = validate_run_metrics(m)
    if errors:
        raise ValueError("RunMetrics invariants violated: " + "; ".join(errors))