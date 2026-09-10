#!/usr/bin/env python
"""B0 default baseline calibration runner (Day 17, PLAN §17, M5).

Executes the frozen workloads under the pinned B0 (Spark default, AQE off)
configuration using the shared Spark session/runner, the workload registry,
and the Day-16 monitoring layer. For every run it writes a machine-readable
baseline manifest, then emits a per-condition summary
(results/baseline/b0_summary.json) and a run registry (results/baseline/runs.json).

B0 means the frozen/default Spark configuration — no tuning is performed.
This is calibration, not an experiment: no EXP-002 grid, no RL, nothing
beyond B0, and no statistical significance testing.

Usage:
    python scripts/run_baseline.py --families F1_agg,F2_join,F3_rdd,F4_ski,F5_mixed \\
        --scales small --seeds 0 --reps 3 [--spot medium,large]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.monitoring import (build_runtime_metrics, find_event_log,  # noqa: E402
                                parse_event_log,)
from sparkrl.spark import config as spark_config  # noqa: E402
from sparkrl.spark import runner as spark_runner  # noqa: E402
from sparkrl.spark import session as spark_session  # noqa: E402
from sparkrl.utils.paths import eventlog_dir  # noqa: E402
from sparkrl.workloads.registry import REGISTRY  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

ALL_FAMILIES = sorted(REGISTRY)
ALL_SCALES = ("small", "medium", "large")
ALL_SEEDS = (0, 1, 2, 3, 4)
DEFAULT_CONFIG = PROJECT / "configs" / "baseline_b0.yaml"


def _clock() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stats(values: list[float]) -> dict:
    """mean/median/std/cv/min/max (ddof=1 std, project convention).

    All reported values are rounded to 4 dp for stable manifests.
    """
    if not values:
        return {"n": 0, "min": None, "max": None, "mean": None,
                "median": None, "std": None, "cv": None}
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "n": len(values), "min": round(min(values), 4),
        "max": round(max(values), 4), "mean": round(mean, 4),
        "median": round(statistics.median(values), 4),
        "std": round(std, 4), "cv": round(std / mean, 6) if mean else None,
    }
def build_manifest(cfg, run_id: str, family: str, scale: str, seed: int,
                   rep: int, resolved, workload, run_result, workload_result,
                   metrics, spark_version: str, code_version: str) -> dict:
    """Assemble the baseline manifest (identity + config + correctness + perf + monitoring)."""
    aqe_mode = "on" if cfg.aqe_enabled else "off"
    event_log_status = metrics.event_log_status or "MISSING"
    return {
        "calibration_id": "B0-DAY17",
        "baseline_id": "B0",
        "run_id": run_id,
        "family": family,
        "scale": scale,
        "seed": seed,
        "rep": rep,
        "workload_id": workload.workload_id,
        "workload_version": workload.workload_version,
        "spark_version": spark_version,
        "dataset_id": resolved.dataset_id,
        "dataset_fingerprint": resolved.dataset_fingerprint,
        "schema_fingerprint": resolved.schema_fingerprint,
        "configuration_fingerprint": run_result.config_fingerprint,
        "aqe_mode": aqe_mode,
        "warmup_runs": cfg.warmup_runs,
        "execution_time_s": round(run_result.execution_time, 4),
        "warmup_time_s": round(run_result.warmup_time, 4),
        "total_time_s": round(run_result.total_time, 4),
        "timeout": run_result.timeout,
        "error": run_result.error or workload_result.error,
        "application_id": run_result.spark_app_id,
        "result_signature": workload_result.result_signature,
        "rows_processed": workload_result.rows_processed,
        "stage_count": metrics.stage_count,
        "task_count": metrics.task_count,
        "failed_task_count": metrics.failed_task_count,
        "shuffle_read_bytes": metrics.shuffle_read_bytes,
        "shuffle_write_bytes": metrics.shuffle_write_bytes,
        "memory_spill_bytes": metrics.memory_spill_bytes,
        "disk_spill_bytes": metrics.disk_spill_bytes,
        "total_spill_bytes": metrics.total_spill_bytes,
        "task_duration_mean_s": metrics.task_duration_mean_s,
        "task_duration_cv": metrics.task_duration_cv,
        "event_log_status": event_log_status,
        "success": bool(workload_result.success and run_result.success),
        "usable": bool(workload_result.success and run_result.success
                       and event_log_status == "COMPLETE"
                       and metrics.execution_time_s is not None),
        "correctness": {"validated": workload.validate(workload_result),
                        "columns": list(workload_result.columns),
                        "measurements": dict(workload_result.measurements)},
        "performance": {"execution_time_s": round(run_result.execution_time, 4),
                        "warmup_time_s": round(run_result.warmup_time, 4)},
        "monitoring": {"event_log_status": event_log_status,
                       "stage_count": metrics.stage_count,
                       "task_count": metrics.task_count,
                       "shuffle_read_bytes": metrics.shuffle_read_bytes,
                       "shuffle_write_bytes": metrics.shuffle_write_bytes,
                       "memory_spill_bytes": metrics.memory_spill_bytes,
                       "disk_spill_bytes": metrics.disk_spill_bytes,
                       "total_spill_bytes": metrics.total_spill_bytes,
                       "task_duration_cv": metrics.task_duration_cv},
        "timestamp": _clock(),
        "code_version": code_version,
    }


def run_one(cfg, family: str, scale: str, seed: int, rep: int,
            code_version: str) -> dict:
    """Execute one B0 run (fresh session, warm-up, timed execution, monitor)."""
    resolved = resolve_dataset(family, scale, seed)
    workload = REGISTRY[family](scale=scale, seed=seed)
    spark = spark_session.build_session(
        cfg, app_suffix=f"b0-{family}-{scale}-s{seed}-r{rep}")
    run_result = None
    try:
        spark_version = spark.version
        run_result = spark_runner.run_workload(spark, workload, cfg)
    finally:
        spark_session.stop_session(spark)

    workload_result = run_result.checksum if run_result else None
    app_id = run_result.spark_app_id if run_result else None
    metrics = None
    if run_result and run_result.success and workload_result is not None:
        event_log_path = find_event_log(eventlog_dir(), app_id)
        if event_log_path is not None:
            parsed = parse_event_log(event_log_path)
            try:
                metrics = build_runtime_metrics(run_result, parsed)
            except ValueError:
                metrics = build_runtime_metrics(run_result, parsed,
                                                include_incomplete=True)
        else:
            from sparkrl.monitoring.schemas import RuntimeMetrics
            metrics = RuntimeMetrics(
                application_id=app_id,
                execution_time_s=run_result.execution_time,
                execution_time_source="runner",
                event_log_status="MISSING")

    if metrics is None or workload_result is None:
        return {"run_id": None, "family": family, "scale": scale, "seed": seed,
                "rep": rep, "success": False, "usable": False,
                "error": (run_result.error if run_result else "hard run failure"),
                "event_log_status": "MISSING",
                "execution_time_s": (run_result.execution_time
                                     if run_result else None)}

    run_id = f"b0-{family}-{scale}-s{seed}-r{rep}".replace("_", "-")
    return build_manifest(cfg, run_id, family, scale, seed, rep, resolved,
                          workload, run_result, workload_result, metrics,
                          spark_version, code_version)
def summarize(runs: list[dict]) -> dict:
    """Per (family, scale) summary over usable runs (authoritative timing only)."""
    import collections
    groups: dict = collections.defaultdict(list)
    for r in runs:
        if r.get("usable"):
            groups[(r["family"], r["scale"])].append(r)
    summary = {}
    for (family, scale), group in groups.items():
        times = [r["execution_time_s"] for r in group]
        shuffle_r = [r.get("shuffle_read_bytes") or 0 for r in group]
        shuffle_w = [r.get("shuffle_write_bytes") or 0 for r in group]
        spill = [(r.get("memory_spill_bytes") or 0)
                 + (r.get("disk_spill_bytes") or 0) for r in group]
        task_cvs = [r["task_duration_cv"] for r in group
                    if r.get("task_duration_cv") is not None]
        stage_counts = [r["stage_count"] for r in group
                        if r.get("stage_count") is not None]
        task_counts = [r["task_count"] for r in group
                       if r.get("task_count") is not None]
        summary[f"{family}|{scale}"] = {
            "baseline_id": "B0", "family": family, "scale": scale,
            "n": len(group),
            "seeds": sorted({r["seed"] for r in group}),
            "execution_time_s": _stats(times),
            "shuffle_read_bytes_median": statistics.median(shuffle_r),
            "shuffle_write_bytes_median": statistics.median(shuffle_w),
            "spill_bytes_median": statistics.median(spill),
            "task_duration_cv_median": (statistics.median(task_cvs)
                                        if task_cvs else None),
            "stage_count_median": (statistics.median(stage_counts)
                                   if stage_counts else None),
            "task_count_median": (statistics.median(task_counts)
                                  if task_counts else None),
        }
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B0 default baseline calibration")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--families", default=",".join(ALL_FAMILIES))
    ap.add_argument("--scales", default="small")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--spot", default=None,
                    help="comma list of extra scales for an F1 spot check")
    ap.add_argument("--out", default=str(PROJECT / "results" / "baseline"))
    ap.add_argument("--code-version", default="day17")
    args = ap.parse_args(argv)

    cfg = spark_config.SparkConfig.from_yaml(args.config)
    if cfg.aqe_enabled:
        print("ERROR: baseline_b0.yaml must have aqe_enabled=false (main study)")
        return 2

    families = [f for f in args.families.split(",") if f]
    scales = [s for s in args.scales.split(",") if s]
    seeds = [int(s) for s in args.seeds.split(",") if s]
    if not all(f in ALL_FAMILIES for f in families):
        print("ERROR: invalid family in", families, "expected", ALL_FAMILIES)
        return 2
    if not all(s in ALL_SCALES for s in scales):
        print("ERROR: invalid scale in", scales)
        return 2
    if not all(s in ALL_SEEDS for s in seeds):
        print("ERROR: invalid seed in", seeds)
        return 2

    tasks = [(f, s, seed, rep) for f in families for s in scales
             for seed in seeds for rep in range(1, args.reps + 1)]
    if args.spot:
        for s in args.spot.split(","):
            if s in ALL_SCALES:
                tasks.append(("F2_join", s, 0, 1))
    print(f"B0 calibration: {len(tasks)} runs "
          f"(families={families} scales={scales} seeds={seeds} reps={args.reps})")

    runs: list[dict] = []
    fails = 0
    out_root = Path(args.out)
    for family, scale, seed, rep in tasks:
        print(f"[RUN] {family} {scale} s{seed} r{rep} ...", flush=True)
        try:
            m = run_one(cfg, family, scale, seed, rep, args.code_version)
        except Exception as exc:  # noqa: BLE001 - calibration must not kill the batch
            print(f"  ERROR: {type(exc).__name__}: {exc}", flush=True)
            m = {"run_id": None, "family": family, "scale": scale,
                 "seed": seed, "rep": rep, "success": False, "usable": False,
                 "error": f"{type(exc).__name__}: {exc}",
                 "event_log_status": "MISSING", "execution_time_s": None}
        runs.append(m)
        if not m.get("usable"):
            fails += 1
            print(f"  ! NOT USABLE (status={m.get('event_log_status')} "
                  f"success={m.get('success')} err={m.get('error')})", flush=True)
        if m.get("run_id"):
            run_dir = out_root / m["family"] / m["scale"] / f"seed{m['seed']}"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / f"run-{m['rep']}.json").write_text(
                json.dumps(m, indent=2, sort_keys=True), encoding="utf-8")
            print(f"  manifest={run_dir / ('run-' + str(m['rep']) + '.json')} "
                  f"sig={m['result_signature'][:16]} exec={m['execution_time_s']}s",
                  flush=True)

    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "runs.json").write_text(json.dumps(runs, indent=2, sort_keys=True),
                                        encoding="utf-8")
    summary = summarize(runs)
    (out_root / "b0_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    valid = sum(1 for r in runs if r.get("usable"))
    print(f"\nB0 done: {valid}/{len(runs)} usable runs; {len(runs)-valid} not usable.")
    print(f"summary: {out_root / 'b0_summary.json'}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())