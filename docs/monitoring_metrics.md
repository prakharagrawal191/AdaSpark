# Monitoring Metrics Reference (RuntimeMetrics, COMP-MEAS-05)

Reference for Day 17+. Units: bytes / seconds (SI). "Event log" = Spark
3.5.9 `SparkListener*` JSON-lines events. Nothing here is fabricated: every
event-log field is traceable, and the runner field is the Day-3 harness.

| Metric | Type | Unit | Source | Aggregation | Missing behavior |
|--------|------|------|--------|-------------|------------------|
| run_id | str \| None | — | caller / RunResult.workload_id | as given | None allowed |
| application_id | str \| None | — | RunResult.spark_app_id, else event log `SparkListenerApplicationStart.App ID` | as given | None allowed |
| execution_time_s | float \| None | s | **runner** `RunResult.execution_time`; fallback event log `ApplicationEnd − ApplicationStart` | single value | both absent → build aborts (ValueError) |
| execution_time_source | str \| None | — | "runner" or "event_log" | provenance flag | None when build aborts |
| stage_count | int \| None | count | event log `SparkListenerStageCompleted` | count of records | MISSING/MALFORMED log → None (or abort in build) |
| task_count | int \| None | count | event log `SparkListenerTaskEnd` | count of records (attempts incl. retries) | as above |
| failed_task_count | int \| None | count | event log `Task Info.Failed` / `.Killed` | count where True | as above |
| shuffle_read_bytes | int \| None | B | event log `Task Metrics.Shuffle Read Metrics` | sum of Local + Remote + Remote To Disk over TaskEnd (single source, no double count) | as above |
| shuffle_write_bytes | int \| None | B | event log `Task Metrics.Shuffle Write Metrics.Shuffle Bytes Written` | sum over TaskEnd | as above |
| memory_spill_bytes | int \| None | B | event log `Task Metrics.Memory Bytes Spilled` | sum over TaskEnd | as above |
| disk_spill_bytes | int \| None | B | event log `Task Metrics.Disk Bytes Spilled` | sum over TaskEnd | as above |
| total_spill_bytes | int \| None | B | **derived** | memory_spill + disk_spill (validated) | as above |
| task_duration_mean_s | float \| None | s | event log `Task Info.Finish Time − Launch Time` (wall clock) | arithmetic mean over TaskEnd | 0 tasks → None |
| task_duration_median_s | float \| None | s | same | exact median | 0 tasks → None |
| task_duration_std_s | float \| None | s | same | sample std, ddof=1; n=1 → 0.0 | 0 tasks → None |
| task_duration_cv | float \| None | ratio | same | std/mean (ddof=1 convention); n=0 or mean=0 → None | None, never NaN |
| aqe_enabled | bool \| None | — | event log `SparkListenerEnvironmentUpdate` → `spark.sql.adaptive.enabled` | recorded only (never set by monitoring) | property absent → None |
| event_log_status | str \| None | — | parser | COMPLETE / INCOMPLETE / MALFORMED / MISSING | always set by parser; MISSING for wall-clock-only builds |
| event_log_total_events | int \| None | count | parser | parsed (JSON-valid) event count | None for wall-clock-only builds |
| malformed_event_count | int \| None | count | parser | non-JSON / non-dict lines | as above |
| unknown_event_count | int \| None | count | parser | events outside the frozen metric set (tolerated) | as above |

Deliberately NOT included in v1: `Executor Run Time` (distinct from
wall-clock task duration; preserved in raw events, not aggregated), executor
poll metrics (RSS/CPU — possible later extension), reward/state/action
fields (later phases), timestamps and app ids are metadata only.
