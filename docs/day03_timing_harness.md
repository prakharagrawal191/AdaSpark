# Day-3 Timing Harness — Design & Validation

*AdaSpark · 2026-09-07 · backend frozen per DEC-007 (PySpark 3.5.9 / Java 17 / native Windows)*

## 1. Purpose

Every later experiment (EXP-001…EXP-012) measures Spark execution time. Day 3 builds the
**trustworthy measurement foundation**: a reusable config-driven session, a validated
configuration model with a fingerprint (needed by the Day-20 experiment cache), and a
runner that separates warm-up from timed execution and enforces timeouts.

## 2. Modules

| Module | Responsibility |
|---|---|
| `src/sparkrl/spark/config.py` | `SparkConfig` frozen dataclass; YAML/dict loading; validation; `to_spark_settings()`; `fingerprint()` (SHA-256 of canonical JSON). |
| `src/sparkrl/spark/session.py` | `build_session(config)` — config-driven SparkSession, version check vs DEC-007, event-log + local-dir wiring via `utils.paths`, optional micro-job soak; `stop_session()`. |
| `src/sparkrl/spark/runner.py` | `run_workload(spark, workload, config)` → `RunResult`; warm-up loop; timed execution in a daemon thread with `cancelJobGroup` timeout; structured result. |
| `src/sparkrl/utils/stats.py` | `timing_stats()` — mean/median/sample-std/CV (pure stdlib). |
| `src/sparkrl/workloads/baseline.py` | `BaselineWorkload` (`baseline_agg_v1`): deterministic filter + groupBy-sum; pure-Python `reference_check()` for tests. |
| `scripts/run_smoke_warm.py` | Day-3 validation runner (3 cold + 5 warm observations). |

## 3. Timing definitions

- **execution_time** — wall-clock of `workload.run(spark, config)` only. Session startup,
  warm-up, and cleanup are excluded. This is the research metric.
- **warmup_time** — aggregated wall-clock of the discarded warm-up runs inside one
  `run_workload` call.
- **total_time** — warm-up + execution + teardown bookkeeping.
- **CV** — `sample_std / mean` (ddof=1), computed consistently project-wide.

## 4. Warm-up policy

Why warm-up is necessary: the first executions on a fresh JVM pay class-loading, JIT
compilation, and Spark internal initialization that are *not* part of the workload's
steady-state cost. Timing them would inflate variance (Day-2 benchmark: cold rep 1
session 2.1 s vs warm 0.05 s). Policy (config `execution.warmup_runs`):

- COLD observations: `warmup_runs=0` — used only to quantify cold-start overhead.
- WARM observations: `warmup_runs=N` (default 2) discarded runs precede every timed run.
- Session start also runs a micro-job (`execution.warmup_micro_job`) to soak JVM init.

COLD and WARM are never mixed in a single statistic.

## 5. Timeout policy

- **value**: `execution.timeout_seconds` (default 300 s), config-driven.
- **behavior**: the timed run executes in a daemon thread; on timeout, Spark
  `cancelJobGroup` is invoked (cancels only this job group — safe, no cross-process
  killing), then a `timeout_grace_seconds` join is attempted.
- **recorded**: `timeout=True`, `error` message, `thread_cancelled_late` if the Python
  thread is still alive after the grace window.
- **Windows limitation (documented)**: a stuck Python thread cannot be force-killed on
  Windows. After cancel, the thread may linger as a daemon (it never blocks process exit).
  Spark jobs are cancelled; only the Python-side wrapper may remain.

## 6. Repeatability methodology (Day-3 validation)

1. Build one session.
2. 3 COLD observations (`warmup_runs=0`).
3. 2 explicit discarded warm-up runs.
4. 5 WARM observations (each preceded by `warmup_runs=2`).
5. Statistics computed over successful, non-timeout runs only.
6. Target: warm CV < 10%. If CV ≥ 10%: report the measured CV and diagnose (startup vs
   job variability, background load, GC, dataset size) — never silently drop outliers.

## 7. Results

- `results/validation/day03_timing.json` + `.csv` — labelled **DAY-3 VALIDATION RESULTS
  (not research findings; EXP-001 is Day 22)**.

## 8. Reproduction

```powershell
& "$env:USERPROFILE\sparkrl_env311\Scripts\python.exe" scripts\run_smoke_warm.py --config configs\spark.yaml
```