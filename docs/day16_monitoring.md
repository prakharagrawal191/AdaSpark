# Day 16 Monitoring Infrastructure

## Purpose

Provide the frozen COMP-MEAS-05 monitoring layer: convert successful Spark
executions (Day-3 `RunResult`) and Spark 3.5.9 event logs into the frozen
`RuntimeMetrics` contract that later feed reward calculation (COMP-RL-08),
experiment logging, baseline comparison, and analysis. Day 16 proves the
monitoring layer can reliably extract the required metrics from the frozen
Spark execution environment. It does **not** prove the metrics are
scientifically validated for optimization, and makes **no** ≤5% overhead
claim (that is EXP-009, later).

## Event Log Format Observed

Observed on the frozen backend (PySpark 3.5.9, Windows local mode,
`spark.eventLog.compress=false`): one JSON object per line. Metric-relevant
events (verified against a real 12,103-task / 122-stage log):

- `SparkListenerLogStart` — carries `"Spark Version": "3.5.9"`.
- `SparkListenerApplicationStart` / `...ApplicationEnd` — `App ID`,
  `Timestamp` (ms).
- `SparkListenerStageCompleted` — `Stage Info` with `Stage ID`,
  `Stage Attempt ID`, `Stage Name`, `Number of Tasks`, `Submission Time`,
  `Completion Time`, `Failure Reason`. **StageInfo carries no aggregate task
  metrics** (the Spark UI derives those from task accumulables).
- `SparkListenerTaskEnd` — `Task Info` (`Launch Time`, `Finish Time`,
  `Failed`, `Killed`, `Attempt`), `Task End Reason`, `Task Metrics` with
  `Shuffle Read Metrics` (`Local Bytes Read`, `Remote Bytes Read`,
  `Remote Bytes Read To Disk`), `Shuffle Write Metrics`
  (`Shuffle Bytes Written`), `Memory Bytes Spilled`, `Disk Bytes Spilled`,
  `Executor Run Time`.
- `SparkListenerEnvironmentUpdate` — `Spark Properties` (record-only source
  of `spark.sql.adaptive.enabled`).

The session layer also produced Spark rolling `eventlog_v2_*` zstd-format
logs in earlier experiments; the frozen config writes plain JSON lines and
the parser/discovery skips the v2 directories.

## Parser Architecture

`src/sparkrl/monitoring/`:

- `eventlog_parser.py` — streaming line-by-line JSON Lines parse into
  `ParsedEventLog` (aggregation state only: counters, byte sums, a compact
  `array('d')` of task durations in seconds). Never retains per-event
  objects. `find_event_log(dir, application_id)` for discovery: exact or
  glob match on the application id, **no fallthrough** to unrelated logs.
- `metrics.py` — `build_runtime_metrics(run_result, parsed_log)` merge and
  the `metrics_for_run` convenience wrapper.
- `schemas.py` — `RuntimeMetrics` dataclass + `EventLogStatus` enum.
- `validate.py` — invariant checks (structural, not scientific).

## Completeness Rules

Statuses: **COMPLETE** (`SparkListenerLogStart` AND
`SparkListenerApplicationEnd` observed), **INCOMPLETE** (either missing —
crash/partial-flush signature, cf. the Day-1 incident), **MALFORMED** (file
unreadable or contains no parseable event at all), **MISSING** (file absent).
Individual malformed lines are counted and sampled but do not by themselves
downgrade a log that still contains the completeness markers.

## Runtime Metrics Schema

See `docs/monitoring_metrics.md` for the full field-by-field table. All
units SI: bytes, seconds; event-log ms converted at parse time.

## Execution-Time Source

Runner-sourced (`RunResult.execution_time`, Day-3 harness, workload-only
timing) is authoritative whenever available; the event-log wall clock
(`ApplicationStart → ApplicationEnd`) is the fallback and is flagged
`execution_time_source="event_log"`. The two are never mixed silently:
the real-log cross-check for F2_join small showed 17.37 s event-log
wall-clock vs 3.22 s runner time — consistent, because the wall clock
covers session start, the warm-up micro-job, two discarded warm-up runs,
and teardown, while the runner times only the timed execution. No clock
available ⇒ build aborts (frozen contract: missing clock → abort).

## Shuffle Metrics

Aggregated once, over `SparkListenerTaskEnd` task metrics only (the single
authoritative source — StageInfo has no aggregates, so double counting is
structurally impossible): `shuffle_read_bytes = Local + Remote +
Remote To Disk Bytes Read`; `shuffle_write_bytes = Shuffle Bytes Written`.

## Spill Metrics

`memory_spill_bytes` and `disk_spill_bytes` summed separately from
`Memory Bytes Spilled` / `Disk Bytes Spilled`; `total_spill_bytes` is an
explicit derived field (memory + disk), never a replacement for the
individual values.

## Task Duration / CV

Task duration = **wall-clock** `Finish Time − Launch Time` (ms → s).
`Executor Run Time` (executor-side execution only) is a different quantity
and is deliberately not aggregated. `cv = sample_std / mean` with
ddof=1 (project-wide convention, `sparkrl.utils.stats`); n=1 → std 0.0,
cv 0.0; n=0 or mean 0 → `None` (never NaN). Durations are stored in a
compact `array('d')` (8 B/task; ~1 M tasks ≈ 8 MB) for exact mean/median/std.

## Stage/Task Counts

`stage_count` = number of `SparkListenerStageCompleted` records.
`task_count` = number of `SparkListenerTaskEnd` records — attempts,
including retries and speculative duplicates; no silent de-duplication.
`failed_task_count` counts TaskEnd where the task is `Failed` or `Killed`.
Byte sums include failed tasks' reported metrics (they are real costs);
the separate failed count lets later analysis exclude them explicitly.

## Error Handling

MISSING/MALFORMED logs and both-clocks-missing raise `ValueError` (fail
clearly). Unknown event types are tolerated and counted by type
(`SparkListenerStageSubmitted`, `SparkListenerJobStart`, SQL-UI events, …).
Invalid combinations (negative sums, inconsistent spill totals, missing-log
metrics) are caught by `validate.py`.

## Incomplete Log Policy

COMPLETE → metrics may be used. INCOMPLETE → diagnostic only; construction
requires `include_incomplete=True` and `validate_metrics` flags it — never
a valid experiment result. MALFORMED → surfaced, rejected. MISSING → with a
runner clock, `metrics_for_run(..., include_incomplete=True)` yields
wall-clock-only diagnostics flagged `event_log_status=MISSING` (frozen
contract: missing log → wall-clock-only + flag); no event-log metrics are
fabricated.

## Integration with RunResult

`RunResult` + parsed event log → `RuntimeMetrics` via
`build_runtime_metrics`. Provenance is explicit per field
(`execution_time_source`; every event-log value traceable to a documented
event field). The interface stays narrow: no reward, no state, no cache,
no orchestration — later components consume `RuntimeMetrics` as-is.

## Testing

- 26 unit tests (`tests/unit/test_monitoring_parser.py`,
  `test_monitoring_metrics.py`) over six hand-calculable fixtures
  (`tests/fixtures/eventlogs/`): valid, failed-tasks, incomplete,
  malformed-line, garbage, empty — plus discovery behavior.
- Integration (`tests/integration/test_monitoring_pipeline.py`): frozen
  session → tiny shuffle job → event log → parser → `RuntimeMetrics`
  → invariants → serialization round-trip.
- Real-log cross-check (Day-16 verification run): F2_join small
  (`local-17890229590893`) parsed COMPLETE, 3757 events, 0 malformed,
  metrics consistent with the run (see Execution-Time Source); additional
  real logs parse with flat ~0.5 MB peak memory.

## Limitations

- Parser targets plain (uncompressed) JSON-lines logs; zstd-compressed or
  rolling v2 logs are not parsed (out of frozen-config scope).
- Executor-metrics poll events (`Task Executor Metrics`: RSS, JVM heap) are
  observed in logs but not yet aggregated; CPU%/RSS for PLAN §13 state
  features may need a later extension if EXP design requires them.
- Task durations of speculative/retried attempts are all included; analysis
  must use `failed_task_count` to filter deliberately.
- No claim is made that monitoring overhead ≤5% (EXP-009 decides that), and
  no scientific validation of metric usefulness is claimed.
## Day-18 Hardening Notes

Day 18 reviewed the parser without redefining any semantic and added:

- `tests/fixtures/eventlogs/valid.expected.json`: hand-checked expectations
  (21 fields, 21/21 match exactly; pinned by
  `test_hand_checked_expected_file_matches_parser`).
- New edge fixtures: `incomplete_nostart.jsonl` (missing LogStart ->
  INCOMPLETE), `unknown_event.jsonl` (explicit future-type event tolerated),
  `wallclock_vs_executor.jsonl` (proves wall-clock Finish-Launch is used,
  NEVER `Executor Run Time` — pinned by
  `test_task_duration_uses_wall_clock_not_executor_run_time`).
- Explicit EMPTY vs MALFORMED test (`test_empty_log_distinguished_from_garbage`
  for the empty-file; garbage-only logs stay MALFORMED).
- Shuffle double-counting guard (`test_shuffle_stage_level_values_never_summed`):
  task-level is the single aggregation level; stage handlers read no byte fields.
- Real-log cross-check (Day-17 `local-1789057871232`, 11.9 MB): COMPLETE,
  3,757 events, 0 malformed, 0.366 s / 0.49 MB peak, deterministic reparse.
- Structural validator `scripts/validate_eventlog_parser.py`; full audit in
  `docs/research/DAY18_EVENTLOG_AUDIT.md`.
- No parser, workload, B0, RL, or architecture changes on Day 18.

