# Day 18 Event-Log Audit

Day 18 hardens the Day-16 `src/sparkrl/monitoring/` parser into the
experiment-ready state required before the automated runner (Day 20). The
parser itself was already correct; Day 18 adds hand-checked expectations,
explicit negative/edge fixtures, a real-log cross-check, and a structural
validator. No parser semantic was redefined on Day 18.

## Parser Contract

- **Input:** Spark 3.5.9 plain JSON-lines event log
  (`spark.eventLog.compress=false`), streamed line by line. Aggregation
  state only (counters, byte sums, compact `array('d')` of task durations);
  no per-event object retention (flat ~0.5 MB peak regardless of log size).
- **Output:** `ParsedEventLog` -> `RuntimeMetrics` (via Day-3 `RunResult`
  merge in `metrics.py`).
- **Completeness:** COMPLETE requires BOTH `SparkListenerLogStart` AND
  `SparkListenerApplicationEnd`; MISSING = no such file; MALFORMED = cannot
  be opened/decoded at all OR zero parseable events; otherwise INCOMPLETE.
  Individual malformed lines are counted (first 5 sampled) but never
  downgrade an otherwise complete log.
- **Unknown events:** tolerated and counted by type, never fatal.
- **Stages:** `stage_count` = one per `SparkListenerStageCompleted` record.
- **Tasks:** `task_count` = number of `TaskEnd` records, attempts inclusive
  (retries/speculative duplicates NOT deduplicated); `failed_task_count`
  tracks `Failed`/`Killed` separately. Byte sums include failed tasks'
  reported metrics (real costs); the count lets analysis filter explicitly.
- **Shuffle:** summed ONCE over `TaskEnd` metrics only (single authoritative
  level — real `StageInfo` carries no aggregates, so double counting is
  structurally impossible): read = Local + Remote + Remote-To-Disk;
  write = `Shuffle Bytes Written`.
- **Spill:** `memory_spill_bytes` + `disk_spill_bytes` summed separately;
  `total_spill_bytes = memory + disk` (explicit derived field, validated).
- **Task duration:** wall-clock `Finish Time − Launch Time` (ms → s).
  `Executor Run Time` is a different quantity and is deliberately ignored
  (see Task Duration/CV Check).
- **CV:** sample std (ddof=1) / mean (project convention); `None` when
  n=0 or mean=0; never NaN.
- **Execution time:** runner clock when a `RunResult` exists (authoritative,
  workload-only timing); event-log ApplicationStart→End clock as fallback
  (flagged in `execution_time_source`); both missing → abort.

## Hand-Checked Fixture

`tests/fixtures/eventlogs/valid.jsonl` (11 events: LogStart, AppStart,
EnvironmentUpdate, StageSubmitted, StageCompleted(0), TaskEnd(0),
TaskEnd(1), JobStart, StageCompleted(1), TaskEnd(2), ApplicationEnd).
Hand-calculations live in `valid.expected.json` next to the calculations
they document; the derivation was done from the fixture's literal JSON
(no parser output consulted).
## Expected Values

| Metric | Hand-calc | Parser |
|---|---|---|
| stage_count | 2 | 2 OK |
| task_count | 3 | 3 OK |
| shuffle_read_bytes | 350+0+1000 = 1350 | 1350 OK |
| shuffle_write_bytes | 500+700+0 = 1200 | 1200 OK |
| memory_spill_bytes | 10+0+5 = 15 | 15 OK |
| disk_spill_bytes | 20+0+0 = 20 | 20 OK |
| total_spill_bytes | 15+20 = 35 | 35 OK |
| task durations (s) | [2.0, 3.0, 1.0] | identical OK |
| mean / median / std / cv | 2.0 / 2.0 / 1.0 / 0.5 | identical OK |
| app wall time (s) | 8.0 | 8.0 OK |
| app id / version / status | app-fixture-0001 / 3.5.9 / COMPLETE | identical OK |
| unknown events | 2 (StageSubmitted, JobStart) | 2 OK |
| malformed lines | 0 | 0 OK |
| aqe_enabled | false | false OK |

**21/21 hand-checked fields match exactly.** The file-level test
`test_hand_checked_expected_file_matches_parser` pins this.

## Real Spark Log Cross-Check

Real complete log from a Day-17 B0 calibration run
(`results/baseline/F2_join/small/seed0/run-2.json` →
`local-1789057871232`, **not** committed — fixture discipline):

- application ID: local-1789057871232
- file size: 11,941,466 bytes; events parsed: 3,757 (malformed 0)
- spark version from LogStart: 3.5.9; status COMPLETE
- stages / tasks / failed: 23 / 1,821 / 0
- shuffle read / write: 272,593 / 175,426 B; spill mem / disk: 0 / 0 B
- task mean/median/std/cv: 0.0053 / 0.002 / 0.0161 / 3.0174 s
- app wall time: 5.953 s vs runner exec 1.812 s (authoritative; different
  scope — runner excludes session/warm-ups, wall clock includes them)
- unknown types tolerated: 11 real Spark-3.5 types
- parse time / peak memory: 0.366 s / 0.49 MB for 11.9 MB
- deterministic reparse: identical metrics
- RuntimeMetrics build: source=event_log, total_spill=0, status=COMPLETE

Findings: zero malformed lines on a real log; Runner vs wall-clock
difference is expected scope semantics, NOT a discrepancy; per-task
shuffle sums are consistent with the manifest medians recorded on Day 17.

## Malformed/Incomplete Behavior

- `incomplete.jsonl` (missing ApplicationEnd -> INCOMPLETE; metrics still
  extractable for diagnostics with `include_incomplete=True`).
- `incomplete_nostart.jsonl` (AppStart + AppEnd but no LogStart ->
  INCOMPLETE).
- `empty.jsonl` (0 lines -> INCOMPLETE, distinguished from MALFORMED).
- `garbage.jsonl` (unparseable lines only -> MALFORMED).
- `malformed_line.jsonl` (one bad line among valid events -> still
  COMPLETE, malformed_lines=1, sample captured, parsing continues).
- `build_runtime_metrics` rejects MISSING/MALFORMED outright and requires
  the explicit flag for INCOMPLETE diagnostics.

## Unknown Events

`unknown_event.jsonl` pins an explicit future-type event tolerated and
counted with metrics intact; the real-log cross-check shows 11 genuine
Spark-3.5 types tolerated. Forward-compatible by design.

## Task Duration/CV Check

`wallclock_vs_executor.jsonl` pins: wall-clock durations [3.0, 1.0] are
used (mean 2.0, std 1.4142, cv 0.7071), NOT the `Executor Run Time` values
(0.75 s, 0.25 s) in the same events. CV = sample-std/ddof-1 / mean;
n=0 -> `None`; n=1 -> std 0.0, cv 0.0 (only if mean>0); mean=0 -> `None`;
no NaN paths. Same convention (`utils/stats`) continues downstream.

## Streaming Check

Parser retains only counters, sums and `array('d')` durations (~8 B/task);
no `json.load(entire_file)` / `file.read()` anywhere in the module
(grepped). Real-log peak 0.49 MB for 11.9 MB input (flat across the
0.2-12.4 MB sample measured on Day 16). No regression introduced on Day 18.

## Determinism

Same file -> identical metrics across runs (unit test
`test_parser_is_deterministic`; also verified on the real log above).
No timestamps, hostnames, or machine state in the aggregation path;
durations derive from event timestamps only.

## Remaining Issues

1. Executor poll metrics (RSS, JVM heap) are observed in `Task Executor
   Metrics` but not aggregated — possible future extension if EXP design
   needs CPU/RSS state features (documented in day16_monitoring.md).
2. zstd/rolling v2 event-log format is not parsed (frozen config writes
   plain JSON lines; out of scope).
3. Speculative/retried attempts are all included; analysis must use
   `failed_task_count` deliberately (documented semantics).
4. The giant 807 MB log was censused on Day 16 but not re-parsed on
   Day 18; the B0-run cross-check above covers real-log validation
   without repository bloat.
## Shuffle Double-Counting Check

Task-level sum is the single aggregation source. Spark `StageInfo` exposes
no shuffle byte aggregates, and `_handle_stage_completed` reads only
id/name/times/counts — no byte field is referenced there. Pinned by
`test_shuffle_stage_level_values_never_summed` and the 1350/1200
hand-checks.

## Spill Check

Mem/disk summed separately and persisted as separate `RuntimeMetrics`
fields; total only as an explicit validated derived sum (15+20=35 in the
fixture; `validate_metrics` rejects inconsistent totals).