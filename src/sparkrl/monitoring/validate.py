"""Metric invariant validation (Day 16, structural not scientific)."""
from __future__ import annotations

from sparkrl.monitoring.schemas import EventLogStatus, RuntimeMetrics


def validate_metrics(m: RuntimeMetrics) -> list[str]:
    """Return a list of invariant violations (empty list = valid).

    Invariants: non-negative counts/bytes, CV consistency with mean/std,
    derived spill consistency, COMPLETE status required for a full metrics
    object, and no negative durations.
    """
    errors: list[str] = []

    def _neg(name: str, value) -> None:
        if value is not None and value < 0:
            errors.append(f"{name} is negative ({value})")

    for name in ("stage_count", "task_count", "failed_task_count",
                 "shuffle_read_bytes", "shuffle_write_bytes",
                 "memory_spill_bytes", "disk_spill_bytes"):
        _neg(name, getattr(m, name))
    for name in ("execution_time_s", "task_duration_mean_s",
                 "task_duration_median_s", "task_duration_std_s"):
        _neg(name, getattr(m, name))

    if (m.memory_spill_bytes is not None and m.disk_spill_bytes is not None
            and m.total_spill_bytes is not None
            and m.total_spill_bytes != m.memory_spill_bytes + m.disk_spill_bytes):
        errors.append("total_spill_bytes != memory_spill + disk_spill")

    if m.task_duration_cv is not None:
        if m.task_duration_cv < 0:
            errors.append("task_duration_cv is negative")
        if (m.task_duration_mean_s in (None, 0)
                and m.task_duration_cv is not None):
            errors.append("task_duration_cv set although mean is zero/missing")

    if m.event_log_status == EventLogStatus.INCOMPLETE.value:
        errors.append(
            "INCOMPLETE metrics presented without diagnostic flagging — must "
            "never be treated as a complete experiment result")
    if m.event_log_status == EventLogStatus.MISSING.value and (
            m.stage_count is not None or m.task_count is not None):
        errors.append("MISSING log but event-log-sourced metrics present")

    return errors


def assert_valid(m: RuntimeMetrics) -> None:
    errors = validate_metrics(m)
    if errors:
        raise ValueError("RuntimeMetrics invariants violated: " + "; ".join(errors))
