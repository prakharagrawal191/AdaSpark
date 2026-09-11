#!/usr/bin/env python
"""EXP-002 configuration-sensitivity study driver (Day 22).

Executes the pre-registered EXP-002 queue defined by ``experiments/exp002.yaml``
using the existing Spark session/runner/monitoring stack. Resumable: an already
COMPLETED run is SKIPPED and never overwritten; FAILED/INCOMPLETE runs are retried.

This script performs NO analysis and evaluates NO gate - see
``scripts/analyze_exp002.py``. It selects nothing and tunes nothing.

Usage:
    python scripts/run_exp002.py                       # whole pre-registered queue
    python scripts/run_exp002.py --scales small        # one scale slice
    python scripts/run_exp002.py --dry-run             # print the plan, run nothing
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.experiments.runner import (COMPLETED, SKIPPED,  # noqa: E402
                                        RunOutcome, run_experiment,)
from sparkrl.experiments.spec import ExperimentSpec, summarize_plan  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

DEFAULT_SPEC = PROJECT / "experiments" / "exp002.yaml"


def _progress(outcome: RunOutcome, position: int, total: int) -> None:
    m = outcome.record.get("metrics", {}) or {}
    exec_s = m.get("execution_time_s")
    exec_txt = f"{exec_s:8.3f}s" if isinstance(exec_s, (int, float)) else "      n/a"
    mark = {COMPLETED: "ok ", SKIPPED: "skip"}.get(outcome.status, "FAIL")
    print(f"[{position:3d}/{total}] {mark} {outcome.run_spec.run_id:<46} "
          f"{exec_txt}  elog={m.get('event_log_status')}", flush=True)
    if outcome.status not in (COMPLETED, SKIPPED):
        print(f"        reason: {m.get('error')}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EXP-002 configuration-sensitivity study")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--scales", default=None,
                    help="comma list restricting the queue to these scales "
                         "(a slice of the SAME pre-registered plan, not a new design)")
    ap.add_argument("--families", default=None, help="comma list restricting families")
    ap.add_argument("--limit", type=int, default=None,
                    help="execute at most N planned runs (resumable slice)")
    ap.add_argument("--no-sysmon", action="store_true",
                    help="disable optional psutil sampling")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    spec = ExperimentSpec.from_yaml(args.spec)
    base = SparkConfig.from_yaml(str(PROJECT / spec.base_config_path))
    result_root = PROJECT / spec.result_root

    plan = list(spec.plan())
    if args.scales:
        keep = {s for s in args.scales.split(",") if s}
        unknown = keep - set(spec.scales)
        if unknown:
            print(f"ERROR: scale(s) {sorted(unknown)} are not in the pre-registered "
                  f"spec {list(spec.scales)}")
            return 2
        plan = [r for r in plan if r.scale in keep]
    if args.families:
        keep_f = {f for f in args.families.split(",") if f}
        unknown_f = keep_f - set(spec.families)
        if unknown_f:
            print(f"ERROR: family(ies) {sorted(unknown_f)} are not in the "
                  f"pre-registered spec {list(spec.families)}")
            return 2
        plan = [r for r in plan if r.family in keep_f]

    print(f"EXP-002 spec           : {args.spec}")
    print(f"spec fingerprint       : {spec.fingerprint()}")
    print(f"planned (full design)  : {spec.planned_run_count()} runs")
    print(f"this invocation        : {len(plan)} runs")
    print(f"result root            : {result_root}")
    print(f"AQE                    : {'ON (INVALID)' if spec.aqe_enabled else 'OFF'}")
    print(json.dumps(summarize_plan(plan), indent=1))

    if args.dry_run:
        for r in plan:
            print(f"  {r.order_index:4d} {r.run_id:<46} block={r.block_id}")
        return 0

    result_root.mkdir(parents=True, exist_ok=True)
    spec_snapshot = result_root / "spec.json"
    if not spec_snapshot.exists():
        spec_snapshot.write_text(
            json.dumps(spec.to_dict(include_plan=True), indent=2, sort_keys=True),
            encoding="utf-8")
        print(f"wrote pre-registered spec snapshot: {spec_snapshot}")

    t0 = time.perf_counter()
    outcomes = run_experiment(spec, base, result_root=result_root,
                              sysmon_enabled=not args.no_sysmon,
                              limit=args.limit, on_progress=_progress, plan=plan)
    elapsed = time.perf_counter() - t0

    valid = sum(1 for o in outcomes if o.status == COMPLETED)
    skipped = sum(1 for o in outcomes if o.status == SKIPPED)
    executed = sum(1 for o in outcomes if o.executed)
    invalid = len(outcomes) - valid - skipped
    print(f"\nEXP-002 pass complete in {elapsed/60:.1f} min")
    print(f"  attempted this pass : {executed}")
    print(f"  newly valid         : {valid}")
    print(f"  skipped (completed) : {skipped}")
    print(f"  invalid/failed      : {invalid}")
    print("  (invalid runs are recorded, never dropped; see attempts.jsonl)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
