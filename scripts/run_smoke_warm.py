#!/usr/bin/env python
"""AdaSpark Day-3 validation: repeated baseline timing through the common harness.

Runs 3 cold observations (no warm-up) then 5 warmed observations (each preceded by the
configured warm-up runs), and reports mean/median/std/CV. Results are VALIDATION data
(backend/timing-harness stability), NOT research findings (that is EXP-001, Day 22).

Outputs:
    results/validation/day03_timing.json
    results/validation/day03_timing.csv

Usage:
    python scripts/run_smoke_warm.py --config configs/spark.yaml [--cold 3] [--warm 5]

Exit 0 if all runs succeed and warm CV < 10% (target); exit 2 if warm CV >= 10%
(measured honestly, not suppressed).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.spark import config as spark_config  # noqa: E402
from sparkrl.spark import runner as spark_runner  # noqa: E402
from sparkrl.spark import session as spark_session  # noqa: E402
from sparkrl.utils.paths import project_root  # noqa: E402
from sparkrl.utils.stats import timing_stats  # noqa: E402
from sparkrl.workloads.baseline import BaselineWorkload  # noqa: E402

SCALE_ROWS = {"micro": 100_000, "small": 250_000, "medium": 1_000_000, "large": 5_000_000}
def main() -> int:
    parser = argparse.ArgumentParser(description="Day-3 timing-harness validation")
    parser.add_argument("--config", default=str(PROJECT / "configs" / "spark.yaml"))
    parser.add_argument("--cold", type=int, default=3, help="cold observations")
    parser.add_argument("--warm", type=int, default=5, help="warmed observations")
    args = parser.parse_args()

    cfg = spark_config.SparkConfig.from_yaml(args.config)
    rows = SCALE_ROWS.get(cfg.baseline_scale, cfg.baseline_rows)
    print("=== AdaSpark Day-3 timing validation ===")
    print(f"config fingerprint: {cfg.fingerprint()[:16]}… "
          f"(scale={cfg.baseline_scale}, rows={rows}, warmup_runs={cfg.warmup_runs}, "
          f"timeout={cfg.timeout_seconds}s)")
    wl = BaselineWorkload(rows=rows, seed=cfg.seed)

    no_warm_cfg = cfg.with_overrides(warmup_runs=0)
    warm_cfg = cfg.with_overrides(warmup_runs=cfg.warmup_runs)

    spark = spark_session.build_session(cfg, app_suffix="day03")
    results: list[dict] = []
    try:
        for i in range(1, args.cold + 1):
            r = spark_runner.run_workload(spark, wl, no_warm_cfg)
            results.append({"phase": "cold", "rep": i, **r.to_dict()})
            print(f"[cold {i}/{args.cold}] exec={r.execution_time:.3f}s "
                  f"ok={r.success} checksum={r.checksum}")

        print(f"explicit warm-up: {cfg.warmup_runs} discarded run(s)")
        for _ in range(cfg.warmup_runs):
            spark_runner.run_workload(spark, wl, no_warm_cfg)

        for i in range(1, args.warm + 1):
            r = spark_runner.run_workload(spark, wl, warm_cfg)
            results.append({"phase": "warm", "rep": i, **r.to_dict()})
            print(f"[warm {i}/{args.warm}] exec={r.execution_time:.3f}s "
                  f"ok={r.success} checksum={r.checksum}")
    finally:
        spark_session.stop_session(spark)

    cold_ok = [r for r in results if r["phase"] == "cold" and r["success"] and not r["timeout"]]
    warm_ok = [r for r in results if r["phase"] == "warm" and r["success"] and not r["timeout"]]
    cold_stats = timing_stats([r["execution_time_s"] for r in cold_ok])
    warm_stats = timing_stats([r["execution_time_s"] for r in warm_ok])

    print("\n--- Timing summary (execution_time only; startup/warm-up excluded) ---")
    print(f"{'phase':<6} {'n':>3} {'mean(s)':>9} {'median(s)':>10} {'std(s)':>8} {'CV':>8}")
    for label, st in (("cold", cold_stats), ("warm", warm_stats)):
        print(f"{label:<6} {st['n']:>3} {st['mean_s']:>9.3f} {st['median_s']:>10.3f} "
              f"{st['std_s']:>8.4f} {st['cv']:>8.4f}")

    out_dir = project_root() / "results" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": "DAY-3 VALIDATION RESULTS (not research findings; EXP-001 is Day 22)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "workload_id": wl.workload_id, "rows": rows, "scale": cfg.baseline_scale,
        "seed": cfg.seed, "config_fingerprint": cfg.fingerprint(),
        "cold": cold_stats, "warm": warm_stats,
        "runs": results,
    }
    (out_dir / "day03_timing.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with open(out_dir / "day03_timing.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["phase", "rep", "execution_time_s",
                                                "warmup_time_s", "total_time_s", "success",
                                                "timeout", "checksum", "spark_app_id"])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in
                             ["phase", "rep", "execution_time_s", "warmup_time_s",
                              "total_time_s", "success", "timeout", "checksum",
                              "spark_app_id"]})
    print(f"\nResults: {out_dir / 'day03_timing.json'}")

    all_succeeded = len(warm_ok) == args.warm and len(cold_ok) == args.cold
    cv_target_met = (warm_stats["cv"] is not None and warm_stats["cv"] < 0.10)
    if not all_succeeded:
        print("FAILED: some runs did not succeed/timed out — CV not computed on failures.")
        return 2
    if not cv_target_met:
        print(f"PARTIAL: warm CV={warm_stats['cv']:.4f} >= 0.10 target — "
              "measured honestly, investigate per Day-3 §10.")
        return 2
    print(f"\nDAY-3 ACCEPTANCE: PASS (warm CV={warm_stats['cv']:.4f} < 0.10)")
    return 0


if __name__ == "__main__":
    sys.exit(main())