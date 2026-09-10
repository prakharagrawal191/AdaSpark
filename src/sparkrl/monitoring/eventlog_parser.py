"""Streaming parser for Spark 3.5.9 JSON-lines event logs (Day 16).

Observed format (real PySpark 3.5.9 local-mode logs, ``spark.eventLog.compress=false``):
one JSON object per line; the metrics-relevant events are
``SparkListenerLogStart`` (carries "Spark Version"),
``SparkListenerApplicationStart`` / ``SparkListenerApplicationEnd``,
``SparkListenerStageSubmitted`` / ``SparkListenerStageCompleted`` (Stage Info:
Stage ID, Attempt, Number of Tasks, Submission/Completion Time, Failure Reason),
``SparkListenerTaskEnd`` (Task Info: Launch/Finish Time, Failed, Killed;
Task Metrics: Shuffle Read/Write Metrics, Memory/Disk Bytes Spilled,
Executor Run Time) and ``SparkListenerEnvironmentUpdate`` ("Spark Properties").
Unknown event types are tolerated and counted, never fatal (STEP 2 census of a
real 8.07e8-byte log: 12103 TaskEnd / 122 StageCompleted / 61 JobEnd / ...).

The parser streams line by line and keeps only aggregation state (counters,
sums, and a compact ``array('d')`` of task durations in seconds — 8 bytes per
task; exact median/std computed at finalize). No per-event object retention.
"""
from __future__ import annotations

import array
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkrl.monitoring.schemas import EventLogStatus

logger = logging.getLogger(__name__)

_APP_START = "SparkListenerApplicationStart"
_APP_END = "SparkListenerApplicationEnd"
_LOG_START = "SparkListenerLogStart"
_STAGE_COMPLETED = "SparkListenerStageCompleted"
_TASK_END = "SparkListenerTaskEnd"
_ENV_UPDATE = "SparkListenerEnvironmentUpdate"

_MAX_MALFORMED_SAMPLES = 5


@dataclass
class StageSummary:
    """Aggregated summary for one SparkListenerStageCompleted record."""

    stage_id: int
    attempt_id: int
    name: str
    num_tasks: int | None
    submission_time_ms: int | None
    completion_time_ms: int | None
    failure_reason: str | None


@dataclass
class ParsedEventLog:
    """Aggregation state + diagnostics from one event-log file."""

    status: EventLogStatus = EventLogStatus.MISSING
    path: str | None = None
    spark_version: str | None = None
    application_id: str | None = None
    application_start_ms: int | None = None
    application_end_ms: int | None = None
    aqe_enabled: bool | None = None
    total_lines: int = 0
    parsed_lines: int = 0
    malformed_lines: int = 0
    malformed_samples: list[str] = field(default_factory=list)
    unknown_event_types: dict[str, int] = field(default_factory=dict)
    stage_count: int = 0
    task_end_count: int = 0
    failed_task_count: int = 0
    shuffle_read_bytes: int = 0
    shuffle_write_bytes: int = 0
    memory_spill_bytes: int = 0
    disk_spill_bytes: int = 0
    _task_durations_s: array.array = field(
        default_factory=lambda: array.array("d"), repr=False)
    stages: list[StageSummary] = field(default_factory=list)

    # -- derived, documented metrics ----------------------------------------

    @property
    def task_duration_mean_s(self) -> float | None:
        n = len(self._task_durations_s)
        return (sum(self._task_durations_s) / n) if n else None

    @property
    def task_duration_median_s(self) -> float | None:
        vals = sorted(self._task_durations_s)
        n = len(vals)
        if not n:
            return None
        mid = n // 2
        return float(vals[mid]) if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0

    @property
    def task_duration_std_s(self) -> float | None:
        """Sample std (ddof=1); 0.0 for n=1 (project-wide convention, utils/stats)."""
        vals = self._task_durations_s
        n = len(vals)
        if not n:
            return None
        if n == 1:
            return 0.0
        mean = sum(vals) / n
        return (sum((v - mean) ** 2 for v in vals) / (n - 1)) ** 0.5

    @property
    def task_duration_cv(self) -> float | None:
        """cv = sample_std / mean (ddof=1 convention, sparkrl.utils.stats)."""
        mean = self.task_duration_mean_s
        if not mean:  # n==0 or mean==0 -> mathematically undefined
            return None
        std = self.task_duration_std_s or 0.0
        return std / mean


def _task_metrics_bytes(event: dict[str, Any]) -> dict[str, int] | None:
    """Extract per-task byte metrics from one TaskEnd event (single source).

    Aggregation definitions (documented, no double counting — Spark StageInfo
    carries NO aggregate task metrics, so TaskEnd is the only source):
    - shuffle_read_bytes  = Local Bytes Read + Remote Bytes Read
                            + Remote Bytes Read To Disk
    - shuffle_write_bytes = Shuffle Write Metrics -> Shuffle Bytes Written
    - memory_spill_bytes  = Memory Bytes Spilled
    - disk_spill_bytes    = Disk Bytes Spilled
    """
    metrics = event.get("Task Metrics")
    if not isinstance(metrics, dict):
        return None
    read = metrics.get("Shuffle Read Metrics") or {}
    write = metrics.get("Shuffle Write Metrics") or {}
    return {
        "shuffle_read_bytes": int(read.get("Local Bytes Read", 0) or 0)
        + int(read.get("Remote Bytes Read", 0) or 0)
        + int(read.get("Remote Bytes Read To Disk", 0) or 0),
        "shuffle_write_bytes": int(write.get("Shuffle Bytes Written", 0) or 0),
        "memory_spill_bytes": int(metrics.get("Memory Bytes Spilled", 0) or 0),
        "disk_spill_bytes": int(metrics.get("Disk Bytes Spilled", 0) or 0),
    }


def _handle_task_end(log: ParsedEventLog, event: dict[str, Any]) -> None:
    log.task_end_count += 1
    info = event.get("Task Info") or {}
    if info.get("Failed") or info.get("Killed"):
        log.failed_task_count += 1
    # Wall-clock task duration (documented formula): Finish Time - Launch Time,
    # in milliseconds -> seconds. "Executor Run Time" is a DIFFERENT quantity
    # (executor-side execution only) and is deliberately not aggregated here.
    launch = info.get("Launch Time")
    finish = info.get("Finish Time")
    if isinstance(launch, (int, float)) and isinstance(finish, (int, float)):
        log._task_durations_s.append(max(0.0, (finish - launch) / 1000.0))
    bytes_metrics = _task_metrics_bytes(event)
    if bytes_metrics:
        log.shuffle_read_bytes += bytes_metrics["shuffle_read_bytes"]
        log.shuffle_write_bytes += bytes_metrics["shuffle_write_bytes"]
        log.memory_spill_bytes += bytes_metrics["memory_spill_bytes"]
        log.disk_spill_bytes += bytes_metrics["disk_spill_bytes"]


def _handle_stage_completed(log: ParsedEventLog, event: dict[str, Any]) -> None:
    log.stage_count += 1
    info = event.get("Stage Info") or {}
    log.stages.append(StageSummary(
        stage_id=int(info.get("Stage ID", -1)),
        attempt_id=int(info.get("Stage Attempt ID", 0)),
        name=str(info.get("Stage Name", "")),
        num_tasks=(int(info["Number of Tasks"])
                   if info.get("Number of Tasks") is not None else None),
        submission_time_ms=info.get("Submission Time"),
        completion_time_ms=info.get("Completion Time"),
        failure_reason=info.get("Failure Reason"),
    ))


def _handle_environment_update(log: ParsedEventLog, event: dict[str, Any]) -> None:
    props = event.get("Spark Properties") or {}
    value = props.get("spark.sql.adaptive.enabled")
    if value is not None:
        log.aqe_enabled = str(value).strip().lower() == "true"


def parse_event_log(path: str | Path) -> ParsedEventLog:
    """Stream-parse one Spark event-log file into a ParsedEventLog.

    Status policy (Day-16):
    - MISSING   : path does not exist.
    - MALFORMED : file exists but cannot be opened/decoded at all.
    - INCOMPLETE: readable but missing SparkListenerLogStart or
                  SparkListenerApplicationEnd (e.g. crash / partial flush).
    - COMPLETE  : LogStart AND ApplicationEnd observed.
    Individual malformed JSON lines are counted (and sampled) but do NOT by
    themselves make the log MALFORMED; unknown event types are tolerated.
    """
    log = ParsedEventLog(path=str(path))
    file = Path(path)
    if not file.is_file():
        log.status = EventLogStatus.MISSING
        return log

    seen_log_start = False
    seen_app_end = False
    try:
        with file.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                log.total_lines += 1
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    log.malformed_lines += 1
                    if len(log.malformed_samples) < _MAX_MALFORMED_SAMPLES:
                        log.malformed_samples.append(line[:200])
                    continue
                if not isinstance(event, dict):
                    log.malformed_lines += 1
                    continue
                log.parsed_lines += 1
                etype = event.get("Event", "<no-event-field>")
                if etype == _LOG_START:
                    seen_log_start = True
                    log.spark_version = event.get("Spark Version")
                elif etype == _APP_START:
                    log.application_id = event.get("App ID")
                    log.application_start_ms = event.get("Timestamp")
                elif etype == _APP_END:
                    seen_app_end = True
                    log.application_end_ms = event.get("Timestamp")
                elif etype == _TASK_END:
                    _handle_task_end(log, event)
                elif etype == _STAGE_COMPLETED:
                    _handle_stage_completed(log, event)
                elif etype == _ENV_UPDATE:
                    _handle_environment_update(log, event)
                else:
                    log.unknown_event_types[str(etype)] = (
                        log.unknown_event_types.get(str(etype), 0) + 1)
    except OSError as exc:
        logger.error("event log unreadable: %s (%s)", path, exc)
        log.status = EventLogStatus.MALFORMED
        return log

    log.status = (EventLogStatus.MALFORMED
                  if log.parsed_lines == 0 and log.total_lines > 0
                  else EventLogStatus.COMPLETE
                  if seen_log_start and seen_app_end
                  else EventLogStatus.INCOMPLETE)
    return log


def find_event_log(directory: str | Path,
                   application_id: str | None = None) -> Path | None:
    """Locate the event log for a run.

    Prefers an application-id-specific file (``*<application_id>*``) inside
    ``directory``; otherwise returns the newest plain event-log file. Spark's
    rolling ``eventlog_v2_*`` directories (zstd streams) are skipped — the
    frozen session layer writes plain uncompressed JSON lines
    (``spark.eventLog.compress=false``). Returns None when nothing matches.
    """
    base = Path(directory)
    if not base.is_dir():
        return None
    if application_id:
        exact = base / str(application_id)
        if exact.is_file():
            return exact
        hits = sorted(p for p in base.glob(f"*{application_id}*") if p.is_file())
        # No fallthrough: a specific application id that matches nothing
        # must return None, not an unrelated newest log.
        return hits[-1] if hits else None
    candidates = sorted((p for p in base.iterdir() if p.is_file()),
                        key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None
