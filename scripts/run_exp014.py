"""EXP-014 monitoring-overhead confirmation under DEC-044 D3's pre-registered paired statistic.

Pre-registered by DEC-054 (docs/research/DEC_054_EXP014_OVERHEAD_CONFIRMATION.md).
PURPOSE: affirm OR refute the manuscript's monitoring-overhead conclusion with a fresh
measurement analysed by the statistic DEC-044 D3 fixed - before any such data existed - as
the primary acceptance quantity for every future overhead measurement. Executions are on
the VALIDATION split (seed 3), exactly like EXP-009, so 0 is charged to SC6 (DEC-040 s2).

Design (DEC-054 s2):
  * cells: the 7 EXP-009 analysed cells; F3_rdd|medium stays excluded (DEC-040 s6);
  * conditions FULL / NO-SYSMON / NEITHER, configuration B0, AQE OFF - taken from
    scripts/run_exp009.py itself (CONDITIONS, config_for, exp009_guard), never re-implemented;
  * repetitions per cell fixed from precision alone before any EXP-014 data (DEC-054 s2);
  * rep-major; cells shuffled per rep and the three conditions shuffled per (cell, rep)
    block, from seed 20261002 - randomizing the order removes the fixed-order position
    effect EXP-009's FULL -> NO-SYSMON -> NEITHER sequence could carry into a paired statistic.

Safety: EXP-009's own validation-only guard; --plan executes 0 Spark and writes nothing;
--run requires --allow-spark; no retry; resumable; failures are first-class rows.
STOP (DEC-040 s8, as corrected by DEC-042): halt on the 2nd timing-invalid run of a cell
(across conditions), on aqe_enabled true, or on less than 5 GiB free on the data root.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import VALIDATION, RunSpec  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.utils.paths import resolve_data_root  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_exp009", PROJECT / "scripts" / "run_exp009.py")
R9 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R9)

PROTOCOL_VERSION = "exp014/v1"
AUTHORIZED_BY = "DEC-054"
ORDER_SEED = 20261002
# DEC-054 s2: smallest n in {10, 15, 20, 30} whose mean windowed paired half-width (both
# components) is <= 2.5 pp in the committed EXP-009 extension data - precision, not outcome.
REPS_PER_CELL = {("F1_agg", "medium"): 10, ("F1_agg", "small"): 15,
                 ("F2_join", "medium"): 10, ("F2_join", "small"): 10,
                 ("F3_rdd", "small"): 10, ("F5_mixed", "medium"): 15,
                 ("F5_mixed", "small"): 20}
MIN_FREE_BYTES = 5 * 2**30
OUT_DIR = PROJECT / "results" / "experiments" / "exp-014"
SPEC_PATH = OUT_DIR / "spec.json"
OBS_PATH = OUT_DIR / "observations.jsonl"
FROZEN_CODE = ("scripts/run_exp014.py", "scripts/analyze_exp014.py",
               "scripts/run_exp009.py", "scripts/analyze_exp009.py")


def sha256_file(rel: str) -> str:
    """LF-normalised digest (DEC-037 s4)."""
    return hashlib.sha256((PROJECT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_queue() -> list[dict[str, Any]]:
    if set(REPS_PER_CELL) != set(R9.IN_SCOPE_CELLS):
        raise SystemExit("refusing: EXP-014 cells must equal EXP-009's analysed cells")
    queue: list[dict[str, Any]] = []
    for rep in range(1, max(REPS_PER_CELL.values()) + 1):
        cells = [c for c in R9.IN_SCOPE_CELLS if REPS_PER_CELL[c] >= rep]
        random.Random(f"{ORDER_SEED}|{rep}").shuffle(cells)
        for family, scale in cells:
            conds = list(R9.CONDITIONS)
            random.Random(f"{ORDER_SEED}|{family}|{scale}|{rep}").shuffle(conds)
            for c in conds:
                queue.append({"queue_index": len(queue) + 1, "rep": rep, "family": family,
                              "scale": scale, "dataset_seed": R9.SEED, "condition": c["name"],
                              "sysmon_enabled": c["sysmon_enabled"],
                              "event_log_enabled": c["event_log_enabled"]})
    return queue


def queue_fingerprint(queue: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(queue, sort_keys=True).encode("utf-8")).hexdigest()


def setup() -> dict[str, Any]:
    base = SparkConfig.from_yaml(PROJECT / R9.BASE_CONFIG_PATH)
    assert_b0_unchanged(base)
    timeouts = {(e["family"], e["scale"]): e["timeout_seconds"] for e in R9.build_queue(base)}
    queue = build_queue()
    return {"base": base, "queue": queue, "queue_fp": queue_fingerprint(queue),
            "timeouts": timeouts}


def run(ctx: dict[str, Any], max_minutes: float) -> int:
    if SPEC_PATH.exists():
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        if spec["queue_fingerprint"] != ctx["queue_fp"]:
            raise SystemExit("refusing: rebuilt queue differs from the frozen spec.json")
        drift = [r for r, h in spec["code_sha256"].items() if sha256_file(r) != h]
        if drift:
            raise SystemExit(f"refusing: frozen code changed since the spec: {drift}")
    else:
        spec = {"experiment_id": "EXP-014", "protocol_version": PROTOCOL_VERSION,
                "authorized_by": AUTHORIZED_BY, "split": VALIDATION, "seed": R9.SEED,
                "order_seed": ORDER_SEED, "conditions": list(R9.CONDITIONS),
                "reps_per_cell": {"%s|%s" % k: v for k, v in REPS_PER_CELL.items()},
                "excluded_cells": R9.EXCLUDED_CELLS_RECORD, "base_fingerprint":
                ctx["base"].fingerprint(), "queue": ctx["queue"],
                "queue_fingerprint": ctx["queue_fp"],
                "code_sha256": {r: sha256_file(r) for r in FROZEN_CODE}, "sc6_charge": 0}
        spec["artifact_id"] = hashlib.sha256(
            json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()
        OUT_DIR.mkdir(parents=True, exist_ok=False)
        SPEC_PATH.write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("  spec frozen:", SPEC_PATH.relative_to(PROJECT), spec["artifact_id"][:16])

    done = {}
    if OBS_PATH.exists():
        for line in OBS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["queue_index"]] = row
    failures: dict[tuple, int] = {}
    for row in done.values():
        if not row["timing_valid"]:
            key = (row["family"], row["scale"])
            failures[key] = failures.get(key, 0) + 1
    todo = [e for e in ctx["queue"] if e["queue_index"] not in done]
    print("  to execute: %d of %d entries" % (len(todo), len(ctx["queue"])))
    point = b0_point()
    started = time.monotonic()
    executed = 0
    with OBS_PATH.open("a", encoding="utf-8") as sink:
        for e in todo:
            if (time.monotonic() - started) / 60.0 >= max_minutes:
                print("  time budget reached; resume with the same command")
                break
            if shutil.disk_usage(resolve_data_root()).free < MIN_FREE_BYTES:
                raise SystemExit("STOP (DEC-054 s5): less than 5 GiB free on the data root")
            cell = (e["family"], e["scale"])
            cfg = R9.config_for({"event_log_enabled": e["event_log_enabled"]}, ctx["base"])
            run_id = ("exp014-%s-%s-s%d-%s-r%d" % (e["family"], e["scale"], R9.SEED,
                                                   e["condition"], e["rep"])
                      ).replace("_", "-").lower()
            run_spec = RunSpec(run_id=run_id, family=e["family"], scale=e["scale"],
                               seed=R9.SEED, rep=e["rep"], config=point, split=VALIDATION,
                               timeout_seconds=ctx["timeouts"][cell],
                               order_index=e["queue_index"] - 1, block_id="exp014")
            metrics, prov = execute_run(run_spec, cfg, sysmon_enabled=e["sysmon_enabled"],
                                        split_guard=R9.exp009_guard)
            timing_ok = (metrics.execution_time_s is not None
                         and metrics.execution_time_source == "runner" and not metrics.timeout)
            row = {"run_id": run_id, "queue_index": e["queue_index"], "rep": e["rep"],
                   "family": e["family"], "scale": e["scale"], "seed": R9.SEED,
                   "split": VALIDATION, "condition": e["condition"],
                   "sysmon_enabled": e["sysmon_enabled"],
                   "event_log_enabled": e["event_log_enabled"], "config_name": point.name,
                   "config_fingerprint_applied": metrics.config_fingerprint,
                   "aqe_enabled": bool(metrics.aqe_enabled), "usable": bool(metrics.usable),
                   "timing_valid": timing_ok, "timeout": bool(metrics.timeout),
                   "execution_time_s": metrics.execution_time_s,
                   "execution_time_source": metrics.execution_time_source,
                   "event_log_status": metrics.event_log_status,
                   "sysmon_sampled": bool(metrics.sysmon_sampled), "error": metrics.error,
                   "sys_cpu_percent_mean": metrics.sys_cpu_percent_mean,
                   "wall_started_utc": prov["wall_started_utc"],
                   "wall_finished_utc": prov["wall_finished_utc"],
                   "code_version": prov["code_version"], "protocol_version": PROTOCOL_VERSION,
                   "authorized_by": AUTHORIZED_BY}
            sink.write(json.dumps(row, sort_keys=True) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
            executed += 1
            print("  [%d/%d] %-9s %-16s r%-2d timing_valid=%-5s %s"
                  % (e["queue_index"], len(ctx["queue"]), e["condition"], "%s|%s" % cell,
                     e["rep"], timing_ok, ("%.3fs" % metrics.execution_time_s)
                     if metrics.execution_time_s else "-"), flush=True)
            if row["aqe_enabled"]:
                raise SystemExit(f"STOP (DEC-040 s8): aqe true for {run_id}")
            if not timing_ok:
                failures[cell] = failures.get(cell, 0) + 1
                if failures[cell] >= 2:
                    raise SystemExit(f"STOP (DEC-040 s8): 2nd failure on {cell}")
    print("  executed this invocation: %d Spark runs" % executed)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true", help="validate and print; 0 Spark, 0 writes")
    ap.add_argument("--run", action="store_true", help="execute the frozen queue")
    ap.add_argument("--max-minutes", type=float, default=100.0)
    ap.add_argument("--allow-spark", action="store_true", help="required with --run")
    args = ap.parse_args()
    if args.run and not args.allow_spark:
        ap.error("--run requires --allow-spark")
    if not (args.plan or args.run):
        ap.error("nothing to do: pass --plan or --run")
    ctx = setup()
    if args.run:
        return run(ctx, args.max_minutes)
    q = ctx["queue"]
    print("EXP-014 plan  (0 Spark, 0 writes)")
    print("  entries: %d over %d cells; reps per cell %s" % (
        len(q), len(REPS_PER_CELL), {"%s|%s" % k: v for k, v in REPS_PER_CELL.items()}))
    print("  queue fingerprint:", ctx["queue_fp"])
    print("  timeouts:", {"%s|%s" % k: v for k, v in ctx["timeouts"].items()})
    for e in q[:6]:
        print("   ", e["queue_index"], e["rep"], e["family"], e["scale"], e["condition"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
