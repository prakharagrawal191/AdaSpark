#!/usr/bin/env python
"""EXP-001 noise calibration on TRAIN (user-authorized Day-32 protocol).

Frozen protocol (authoritative for this task; not adjustable from CLI):

    cells        F1_agg|small, F1_agg|medium, F2_join|small, F2_join|medium
    config       frozen B0/default (configs/baseline_b0.yaml)
    seed         0 for all cells (TRAIN-only; no seed 3/4)
    reps         5 per cell x 4 cells = 20 executions, rep-major block order
    metric       execution_time_s (Day-3 runner clock; nothing substituted)
    retry        NONE - failures are first-class, never replaced or dropped
    CV           per cell: sample_sd / mean; summary = median of 4 cell CVs
    acceptance   median CV <= 10% (PLAN:308 / Day-22 row)

Descriptive/calibration evidence only. Changes nothing (B1/B2/B4/RL/TEST).
SC6 TRAIN cap: 20 executions charged (316 -> 336 of 500).

Spark is refused without --allow-spark. --plan runs nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import TRAIN, RunSpec, split_of  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

SCHEMA = "exp001/v1"
SPEC_VERSION = "exp001-spec/v1"
OUT_DIR = PROJECT / "results" / "experiments" / "exp-001"
SEED = 0
REPS = 5
CELLS = (("F1_agg", "small"), ("F1_agg", "medium"),
         ("F2_join", "small"), ("F2_join", "medium"))
METRIC = "execution_time_s"
THRESHOLD = 0.10
BASE_CONFIG_PATH = "configs/baseline_b0.yaml"


def build_plan(base: SparkConfig) -> list[dict]:
    """Deterministic 20-execution plan. Pure; runs nothing."""
    point = b0_point()
    plan = []
    for rep in range(1, REPS + 1):
        for family, scale in CELLS:
            split = split_of(family, scale, SEED)
            if split != TRAIN:  # defence in depth
                raise SystemExit(f"non-TRAIN cell {family}|{scale}|seed{SEED}")
            run_id = ("exp001-%s-%s-s%d-b0-r%d"
                      % (family, scale, SEED, rep)).replace("_", "-").lower()
            plan.append({
                "index": len(plan) + 1, "rep": rep,
                "family": family, "scale": scale,
                "dataset_seed": SEED, "split": split,
                "config_name": point.name,
                "timeout_seconds": float(base.timeout_seconds),
                "run_id": run_id,
            })
    if len(plan) != 20:
        raise SystemExit(f"plan has {len(plan)} runs, authorized 20; refusing")
    return plan


def spec_doc(base: SparkConfig) -> dict:
    return {
        "schema_version": SCHEMA, "spec_version": SPEC_VERSION,
        "experiment_id": "EXP-001",
        "purpose": "independent run-to-run timing-noise calibration (TRAIN)",
        "cells": ["%s|%s" % c for c in CELLS],
        "dataset_seed": SEED, "repetitions_per_cell": REPS,
        "total_planned": 20,
        "config": "B0 (frozen default)",
        "base_config_path": BASE_CONFIG_PATH,
        "base_config_fingerprint": base.fingerprint(),
        "metric": METRIC, "metric_source_required": "runner",
        "retry_policy": "no-retry; failures first-class, never replaced",
        "cv_rule": "per-cell sample_sd/mean; summary = median of 4 cell CVs",
        "acceptance": "median CV <= 0.10 (PLAN:308)",
        "split_authority": "sparkrl.experiments.spec.split_of",
        "sc6_charge": "20 TRAIN executions (316 -> 336 of 500)",
        "not_a_tuning_loop": True,
    }



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true", help="print plan; no Spark")
    ap.add_argument("--run", action="store_true", help="execute the 20 runs")
    ap.add_argument("--allow-spark", action="store_true",
                    help="explicitly permit Spark execution")
    args = ap.parse_args()

    base = SparkConfig.from_yaml(str(PROJECT / BASE_CONFIG_PATH))
    assert_b0_unchanged(base)  # read-only drift check; raises on any drift
    plan = build_plan(base)
    point = b0_point()

    print("EXP-001 noise calibration on TRAIN (user-authorized Day-32 protocol)")
    print("  cells : %s (seed %d)" % (", ".join(f"{f}|{s}" for f, s in CELLS), SEED))
    print("  config: B0 fp=%s... (aqe=%s)" % (base.fingerprint()[:16], base.aqe_enabled))
    print("  plan  : %d runs (4 cells x %d reps, rep-major)" % (len(plan), REPS))
    print("  splits: %s" % sorted({p["split"] for p in plan}))

    if not args.run:
        print("\n  PLAN ONLY - nothing executed. Spark executions: 0")
        return 0
    if not args.allow_spark:
        print("\n  REFUSED: --run needs --allow-spark. Spark executions: 0")
        return 2
    if OUT_DIR.exists():
        raise SystemExit(f"{OUT_DIR} exists; refusing to overwrite results")

    OUT_DIR.mkdir(parents=True, exist_ok=False)
    (OUT_DIR / "spec.json").write_text(
        json.dumps(spec_doc(base), indent=1, sort_keys=True), encoding="utf-8")

    obs, failed = [], 0
    for step in plan:
        spec = RunSpec(run_id=step["run_id"], family=step["family"],
                       scale=step["scale"], seed=step["dataset_seed"],
                       rep=step["rep"], config=point, split=TRAIN,
                       timeout_seconds=step["timeout_seconds"],
                       order_index=step["index"] - 1, block_id="exp001")
        metrics, _prov = execute_run(spec, base)  # TRAIN-only guard intact
        usable = bool(metrics.usable) and not metrics.timeout
        if metrics.execution_time_source not in (None, "runner") and usable:
            usable = False  # never accept a substituted clock
        if not usable:
            failed += 1
        obs.append({**step, "usable": usable,
                    "execution_time_s": metrics.execution_time_s,
                    "execution_time_source": metrics.execution_time_source,
                    "timeout": bool(metrics.timeout), "error": metrics.error})
        print("  [%2d/20] %-16s rep%d usable=%-5s t=%s" % (
            step["index"], "%s|%s" % (step["family"], step["scale"]),
            step["rep"], usable,
            ("%.3f" % metrics.execution_time_s)
            if metrics.execution_time_s is not None else "-"), flush=True)

    with open(OUT_DIR / "observations.jsonl", "w", encoding="utf-8") as fh:
        for o in obs:
            fh.write(json.dumps(o, sort_keys=True) + "\n")

    cells = []
    for family, scale in CELLS:
        vals = [o["execution_time_s"] for o in obs
                if o["family"] == family and o["scale"] == scale
                and o["usable"] and o["execution_time_s"] is not None]
        n = len(vals)
        mean = statistics.mean(vals) if n else None
        sd = statistics.stdev(vals) if n >= 2 else None
        cv = (sd / mean) if (sd is not None and mean) else None
        cells.append({"cell": f"{family}|{scale}", "n_usable": n,
                      "n_required": REPS, "complete": n == REPS,
                      "mean_s": mean, "sample_sd_s": sd, "cv": cv})
    cvs = [c["cv"] for c in cells if c["cv"] is not None]
    median_cv = statistics.median(cvs) if len(cvs) == 4 else None
    verdict = ("PASS" if (median_cv is not None and median_cv <= THRESHOLD
                          and all(c["complete"] for c in cells))
               else "FAIL")
    body = {"schema_version": SCHEMA, "experiment_id": "EXP-001",
            "metric": METRIC, "statistic": "median_of_cell_cvs",
            "cells": cells, "median_cv": median_cv,
            "threshold": THRESHOLD, "verdict": verdict,
            "observation_counts": {"total": len(obs),
                                   "usable": len(obs) - failed,
                                   "failed": failed},
            "contains_test_data": False,
            "no_research_claim": "TRAIN noise calibration only; tunes nothing.",
            "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    canon = json.dumps({k: v for k, v in body.items() if k != "written_utc"},
                       sort_keys=True, separators=(",", ":")).encode()
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    tmp = OUT_DIR / "summary.json.tmp"
    tmp.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, OUT_DIR / "summary.json")
    print("\n  median CV: %s  verdict: %s  failed: %d"
          % (("%.4f" % median_cv) if median_cv is not None else "n/a",
             verdict, failed))
    print("  artifact: results/experiments/exp-001/summary.json (%s)"
          % body["artifact_id"][:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
