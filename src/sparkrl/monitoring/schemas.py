"""RuntimeMetrics schema (frozen COMP-MEAS-05 contract, Day 16).

Units are strictly SI: bytes for byte metrics, seconds for durations.
Event-log timestamps are milliseconds and are converted at parse time.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventLogStatus(str, Enum):
    """Completeness status of a parsed Spark event log (Day-16 policy).

    COMPLETE   -> LogStart AND ApplicationEnd observed; metrics may be used.
    INCOMPLETE -> log started but ApplicationEnd (or LogStart) missing;
                  diagnostic use only, never a valid experiment result.
    MALFORMED  -> file exists but cannot be read/parsed as JSON Lines.
    MISSING    -> referenced file does not exist.
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    MALFORMED = "MALFORMED"
    MISSING = "MISSING"


@dataclass
class RuntimeMetrics:
    """Aggregated runtime metrics for one Spark execution.

    Provenance is explicit: every value is either runner-sourced (Day-3
    timing harness) or event-log-sourced (parsed SparkListener events).
    No metric is silently mixed; ``execution_time_source`` records which
    clock produced ``execution_time_s``.
    """

    run_id: str | None = None
    application_id: str | None = None
    # runner-sourced when available (Day-3 harness), else derived from
    # SparkListenerApplicationStart->ApplicationEnd wall clock.
    execution_time_s: float | None = None
    execution_time_source: str | None = None  # "runner" | "event_log"
    # event-log-sourced aggregates
    stage_count: int | None = None            # SparkListenerStageCompleted records
    task_count: int | None = None             # SparkListenerTaskEnd records (attempts incl. retries)
    failed_task_count: int | None = None      # TaskEnd where task Failed or Killed
    shuffle_read_bytes: int | None = None
    shuffle_write_bytes: int | None = None
    memory_spill_bytes: int | None = None
    disk_spill_bytes: int | None = None
    total_spill_bytes: int | None = None      # derived: memory + disk spill
    task_duration_mean_s: float | None = None
    task_duration_median_s: float | None = None
    task_duration_std_s: float | None = None  # sample std (ddof=1), 0.0 for n=1
    task_duration_cv: float | None = None     # std/mean; None when undefined
    aqe_enabled: bool | None = None           # recorded from event log properties (never set here)
    # parser diagnostics
    event_log_status: str | None = None       # EventLogStatus value
    event_log_total_events: int | None = None
    malformed_event_count: int | None = None
    unknown_event_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RuntimeMetrics":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})
