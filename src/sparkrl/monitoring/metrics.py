"""RuntimeMetrics construction: RunResult + event log -> RuntimeMetrics (Day 16).

Provenance rules (frozen COMP-MEAS-05 contract):
- execution_time_s: runner-sourced (Day-3 harness) when a RunResult is
  supplied; otherwise derived from the event log's ApplicationStart ->
  ApplicationEnd wall clock (source flagged "event_log"). If BOTH clocks are
  missing the build aborts (missing clock -> abort), per contract.
- event-log metrics require EventLogStatus.COMPLETE; for INCOMPLETE logs the
  caller may request diagnostic metrics explicitly (include_incomplete=True)
  and the result is flagged, but they must never be treated as experiment
  results (see validate.py).
- No reward/score is computed here (that is COMP-RL-08, later phase).
"""
from __future__ import annotations

from typing import Any

from sparkrl.monitoring.eventlog_parser import ParsedEventLog, parse_event_log
from sparkrl.monitoring.schemas import EventLogStatus, RuntimeMetrics


def build_runtime_metrics(run_result: Any | None,
                          parsed_log: ParsedEventLog,
                          run_id: str | None = None,
                          include_incomplete: bool = False) -> RuntimeMetrics:
    """Merge a Day-3 RunResult (optional) with a parsed event log.

    Raises:
        ValueError: on MISSING/MALFORMED logs, on INCOMPLETE logs when
            ``include_incomplete`` is False, or when no execution-time clock
            is available.
    """
    if parsed_log.status in (EventLogStatus.MISSING, EventLogStatus.MALFORMED):
        raise ValueError(
            f"event log unusable (status={parsed_log.status.value}): {parsed_log.path}")
    if (parsed_log.status == EventLogStatus.INCOMPLETE
            and not include_incomplete):
        raise ValueError(
            f"event log incomplete (status=INCOMPLETE): {parsed_log.path}; "
            "pass include_incomplete=True for diagnostics only")

    # --- execution time: runner clock first, event-log clock as fallback ----
    execution_time: float | None = None
    source: str | None = None
    if run_result is not None and getattr(run_result, "execution_time", None):
        execution_time = float(run_result.execution_time)
        source = "runner"
    elif (parsed_log.application_start_ms is not None
          and parsed_log.application_end_ms is not None):
        execution_time = (parsed_log.application_end_ms
                          - parsed_log.application_start_ms) / 1000.0
        source = "event_log"
    if execution_time is None:
        raise ValueError(
            "no execution-time clock available: RunResult has no "
            "execution_time and the event log lacks ApplicationStart/End")

    return RuntimeMetrics(
        run_id=run_id or (getattr(run_result, "workload_id", None)
                          if run_result is not None else None),
        application_id=(getattr(run_result, "spark_app_id", None)
                        if run_result is not None else None)
        or parsed_log.application_id,
        execution_time_s=execution_time,
        execution_time_source=source,
        stage_count=parsed_log.stage_count,
        task_count=parsed_log.task_end_count,
        failed_task_count=parsed_log.failed_task_count,
        shuffle_read_bytes=parsed_log.shuffle_read_bytes,
        shuffle_write_bytes=parsed_log.shuffle_write_bytes,
        memory_spill_bytes=parsed_log.memory_spill_bytes,
        disk_spill_bytes=parsed_log.disk_spill_bytes,
        total_spill_bytes=(parsed_log.memory_spill_bytes
                           + parsed_log.disk_spill_bytes),
        task_duration_mean_s=parsed_log.task_duration_mean_s,
        task_duration_median_s=parsed_log.task_duration_median_s,
        task_duration_std_s=parsed_log.task_duration_std_s,
        task_duration_cv=parsed_log.task_duration_cv,
        aqe_enabled=parsed_log.aqe_enabled,
        event_log_status=parsed_log.status.value,
        event_log_total_events=parsed_log.parsed_lines,
        malformed_event_count=parsed_log.malformed_lines,
        unknown_event_count=sum(parsed_log.unknown_event_types.values()),
    )


def metrics_for_run(run_result: Any | None,
                    event_log_path: str | None,
                    run_id: str | None = None,
                    include_incomplete: bool = False) -> RuntimeMetrics:
    """Convenience wrapper: parse a log path (if any) then merge.

    A missing log path with a valid RunResult yields wall-clock-only metrics
    flagged with event_log_status=MISSING (contract: missing log ->
    wall-clock-only + flag), provided include_incomplete=True is passed by
    the caller to acknowledge the degraded provenance.
    """
    if event_log_path is None:
        if run_result is None or not getattr(run_result, "execution_time", None):
            raise ValueError("no event log and no RunResult clock: cannot build metrics")
        if not include_incomplete:
            raise ValueError(
                "event log MISSING: pass include_incomplete=True to build "
                "wall-clock-only diagnostics (never a complete result)")
        # Wall-clock-only diagnostics: no event-log metrics are fabricated.
        return RuntimeMetrics(
            run_id=run_id or getattr(run_result, "workload_id", None),
            application_id=getattr(run_result, "spark_app_id", None),
            execution_time_s=float(run_result.execution_time),
            execution_time_source="runner",
            event_log_status=EventLogStatus.MISSING.value,
        )
    parsed = parse_event_log(event_log_path)
    return build_runtime_metrics(run_result, parsed,
                                 run_id=run_id,
                                 include_incomplete=include_incomplete)
