#!/usr/bin/env python
"""B4 equal-budget random search on TRAIN (DEC-016 Decision C, completed by DEC-017).

Protocol, frozen and not adjustable from the command line:

    schedule     round-robin over the 7 eligible TRAIN cells x 12 cycles = 84
                 executions, mirroring RL-s0's 7 cells x 12 epochs so the
                 "equal budget" is equal in DISTRIBUTION as well as count
    draw         action uniform over the frozen 12-action grid, seeded RNG,
                 seed 0 (the parallel to RL-s0)
    metric       execution_time_s / T_ref(cell)  -- NORMALISED
    aggregation  per-action median over its normalised observations
    eligibility  an action needs >= 1 usable observation; actions with none are
                 reported ineligible, never ranked on a shorter panel
    tie-break    lowest frozen grid index (the Day-26 / Day-31 rule)

WHY NORMALISED. Cell runtimes span 2.21 s to 36.67 s, a 16.6x spread, so a raw
per-action median would select whichever action happened to draw fast cells
rather than the better configuration. Balancing coverage instead would need
exactly one observation per (action, cell) pair, and 12 x 7 = 84 equals the
budget exactly - so that degenerates into the exhaustive grid, which is no longer
random and duplicates EXP-002's TRAIN scan. Normalising by the frozen T_ref
removes the cell effect while keeping the draw genuinely random, and reuses an
existing frozen mechanism: R3 already normalises by T_ref for the same reason.

TRAIN ONLY. Every cell comes from the frozen Day-27 scheduler, which admits TRAIN
at dataset seed 0 exclusively; execute_run's default assert_train_only guard is
left in place and is never overridden here. This search never reads VALIDATION or
TEST, and writes no TEST artifact.

Spark is refused without --allow-spark. --plan runs nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.experiments.grid import build_grid                      # noqa: E402
from sparkrl.experiments.runner import execute_run                   # noqa: E402
from sparkrl.experiments.spec import TRAIN, RunSpec, split_of        # noqa: E402
from sparkrl.rl.tref import TRefStore                                # noqa: E402
from sparkrl.spark.config import SparkConfig                         # noqa: E402
from sparkrl.training.loop import trainable_cells                    # noqa: E402

SCHEMA = "b4-selection/v1"
OUT = PROJECT / "results" / "evaluation" / "b4_selection.json"
BUDGET = 84
CYCLES = 12
SEED = 0
METRIC = "execution_time_s / T_ref(cell)"
TIE_BREAK = "lowest frozen grid index"


def build_plan() -> list[dict]:
    """Deterministic 84-execution plan. Pure; runs nothing."""
    cells = sorted(trainable_cells(), key=lambda c: c.key())
    if len(cells) * CYCLES != BUDGET:
        raise SystemExit(
            f"plan shape mismatch: {len(cells)} cells x {CYCLES} cycles "
            f"= {len(cells) * CYCLES}, but the authorized budget is {BUDGET}. "
            f"Refusing to invent a decomposition (DEC-017).")
    grid = list(build_grid(include_b0=False))
    rng = random.Random(SEED)
    plan = []
    for cycle in range(1, CYCLES + 1):
        for cell in cells:
            point = grid[rng.randrange(len(grid))]
            split = split_of(cell.family, cell.scale, cell.dataset_seed)
            if split != TRAIN:                       # defence in depth
                raise SystemExit(f"non-TRAIN cell {cell.key()} in the B4 plan")
            plan.append({
                "index": len(plan) + 1, "cycle": cycle,
                "family": cell.family, "scale": cell.scale,
                "dataset_seed": cell.dataset_seed, "split": split,
                "config_name": point.name, "grid_index": point.grid_index,
                "t_ref_s": cell.t_ref_s,
            })
    return plan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true", help="print the plan; no Spark")
    ap.add_argument("--run", action="store_true", help="execute the search")
    ap.add_argument("--allow-spark", action="store_true",
                    help="explicitly permit Spark execution")
    args = ap.parse_args()

    plan = build_plan()
    cells = sorted({(p["family"], p["scale"], p["dataset_seed"]) for p in plan})
    by_action: dict[str, int] = {}
    for p in plan:
        by_action[p["config_name"]] = by_action.get(p["config_name"], 0) + 1

    print("B4 equal-budget random search on TRAIN (DEC-016 C / DEC-017)")
    print("  schedule    : %d cells x %d cycles = %d executions"
          % (len(cells), CYCLES, len(plan)))
    print("  seed        : %d      metric: %s" % (SEED, METRIC))
    print("  TRAIN cells : %s" % ", ".join("%s|%s" % (f, s) for f, s, _ in cells))
    print("  draws per action (uniform over the frozen 12):")
    for name in sorted(by_action):
        print("      %-12s %d" % (name, by_action[name]))
    print("  splits in plan: %s" % sorted({p["split"] for p in plan}))

    if not args.run:
        print("\n  PLAN ONLY - nothing executed. Spark executions: 0")
        return 0
    if not args.allow_spark:
        print("\n  REFUSED: --run needs --allow-spark. Spark executions: 0")
        return 2

    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    grid = {p.name: p for p in build_grid(include_b0=False)}
    trefs = TRefStore()
    obs, failed = [], 0
    for step in plan:
        point = grid[step["config_name"]]
        run_id = ("b4-%s-%s-s%d-%s-c%d"
                  % (step["family"], step["scale"], step["dataset_seed"],
                     point.name, step["cycle"])).replace("_", "-").lower()
        spec = RunSpec(run_id=run_id, family=step["family"], scale=step["scale"],
                       seed=step["dataset_seed"], rep=step["cycle"], config=point,
                       split=TRAIN, timeout_seconds=float(base.timeout_seconds),
                       order_index=step["index"] - 1, block_id="b4-search")
        metrics, _prov = execute_run(spec, base)      # TRAIN-only guard intact
        t_ref = trefs.get(step["family"], step["scale"], step["dataset_seed"])
        usable = bool(metrics.usable) and not metrics.timeout
        norm = (metrics.execution_time_s / t_ref) if (usable and t_ref) else None
        if not usable:
            failed += 1
        obs.append({**step, "run_id": run_id, "usable": usable,
                    "execution_time_s": metrics.execution_time_s,
                    "normalised": norm, "error": metrics.error})
        print("  [%2d/%d] %-18s %-12s usable=%-5s norm=%s"
              % (step["index"], len(plan), "%s|%s" % (step["family"], step["scale"]),
                 point.name, usable, ("%.4f" % norm) if norm is not None else "-"))

    # per-action aggregation with the pre-declared eligibility rule
    cand = []
    for name, point in sorted(grid.items(), key=lambda kv: kv[1].grid_index):
        vals = [o["normalised"] for o in obs
                if o["config_name"] == name and o["normalised"] is not None]
        cand.append({"config_name": name, "grid_index": point.grid_index,
                     "n_usable": len(vals), "n_drawn": by_action.get(name, 0),
                     "median_normalised": statistics.median(vals) if vals else None,
                     "eligible": bool(vals),
                     "ineligible_reason": None if vals else
                     "no usable observation; never ranked on a shorter panel"})
    eligible = [c for c in cand if c["eligible"]]
    if not eligible:
        raise SystemExit("no eligible candidate; nothing selected, nothing written")
    best = min(eligible, key=lambda c: (c["median_normalised"], c["grid_index"]))

    body = {
        "schema_version": SCHEMA, "decision": "DEC-016 Decision C / DEC-017",
        "split": "train", "budget": BUDGET, "cycles": CYCLES, "seed": SEED,
        "metric": METRIC, "statistic": "median", "tie_break": TIE_BREAK,
        "eligibility_rule": "an action needs >= 1 usable observation; actions "
                            "with none are reported ineligible, never ranked",
        "selected_config": best["config_name"],
        "candidates": cand, "observations": obs,
        "observation_counts": {"total": len(obs), "usable": len(obs) - failed,
                               "failed": failed},
        "train_cells": ["%s|%s|seed%d" % c for c in cells],
        "contains_test_data": False,
        "no_research_claim": "A TRAIN calibration. It establishes nothing about "
                             "any strategy's performance on TEST.",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    canon = json.dumps({k: v for k, v in body.items() if k != "written_utc"},
                       sort_keys=True, separators=(",", ":")).encode()
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, OUT)
    print("\n  B4 selected: %s (median normalised %.4f over %d usable)"
          % (best["config_name"], best["median_normalised"], best["n_usable"]))
    print("  failed observations: %d (recorded, never dropped, never retried)" % failed)
    print("  artifact: %s (%s)" % (OUT.relative_to(PROJECT), body["artifact_id"][:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
