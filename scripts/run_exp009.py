#!/usr/bin/env python
"""EXP-009 monitoring-overhead runner - DEC-040 authorized, VALIDATION only.

Frozen protocol (DEC-040 s5; implemented, never extended):
  cells  {F1_agg,F2_join,F3_rdd,F5_mixed} x {small,medium} x seed 3 (8 cells)
  conds  FULL(T,T) / NO-SYSMON(F,T) / NEITHER(F,F); 5 reps; rep-major order
  timing execution_time_s source runner, warm-up discarded (PLAN 22)
  config frozen B0, AQE OFF (PLAN 7)

Micro note: DEC-040 s5 authorizes micro (5 MB) + 8 validation cells. Micro is
NOT executable via the frozen stack (resolver/WorkloadSpec/split_of admit
small/medium/large only; index.json has zero micro entries; no micro data;
new capability forbidden). Per DEC-040 s6 (acceptance over what actually ran)
this driver runs the 8 authorized validation cells with F3_rdd|medium excluded
(105 in-scope execs of 120 planned, 0 SC6 charge) and
records micro as authorized-but-unexecutable in spec/summary. No TRAIN, no
TEST, no F4, no large, no fabricated micro timing.

House pattern (run_exp005/run_exp006): purpose-scoped split_guard; --run
needs --allow-spark; --plan runs 0 Spark, 0 writes; no retry; every run
writes sysmon_enabled + event_log_enabled into its manifest.
STOP (DEC-040 s8): halt, keep partial unanalysed, on: 2nd failure on the
same cell (per-cell counter across conditions); cell outside s5; aqe true;
SC6 ledger move; any TRAIN/TEST cell.
Excluded (DEC-040 s6, recorded reduced coverage): F3_rdd|medium — retained
on disk, never executed further, excluded from analysis (see EXCLUDED_CELLS).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.evaluation.spec import authorize_validation_cell  # noqa: E402
from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import VALIDATION, RunSpec, split_of  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

PROTOCOL_VERSION = "exp009/v1"
EXPERIMENT_ID = "EXP-009"
AUTHORIZED_BY = "DEC-040"
BASE_CONFIG_PATH = "configs/baseline_b0.yaml"
OUT_DIR = PROJECT / "results" / "experiments" / "exp-009"
OBS_PATH = OUT_DIR / "observations.jsonl"
SPEC_PATH = OUT_DIR / "spec.json"
SUMMARY_PATH = OUT_DIR / "summary.json"

SEED = 3
REPS = 5
FAMILIES = ("F1_agg", "F2_join", "F3_rdd", "F5_mixed")
SCALES = ("small", "medium")
CELLS = tuple((f, s) for f in FAMILIES for s in SCALES)
CONDITIONS = (
    {"name": "FULL", "sysmon_enabled": True, "event_log_enabled": True},
    {"name": "NO-SYSMON", "sysmon_enabled": False, "event_log_enabled": True},
    {"name": "NEITHER", "sysmon_enabled": False, "event_log_enabled": False},
)
TOTAL_RUNS = len(CELLS) * len(CONDITIONS) * REPS  # 8 x 3 x 5 = 120
# DEC-040 s6 recorded reduced coverage: F3_rdd|medium is EXCLUDED from further
# execution and from analysis. Its 12 already-recorded rows stay on disk as
# execution records (never deleted, never re-executed). Evidence: EXP-002
# 18 FAILED / 8 COMPLETED for F3_rdd|medium vs 25 COMPLETED / 1 FAILED for
# F3_rdd|small; results/baseline/F3_rdd/ holds small only (no medium baseline).
# Scope after exclusion: 7 cells x 3 conds x 5 reps = 105 in-scope executions.
EXCLUDED_CELLS = (("F3_rdd", "medium"),)
IN_SCOPE_CELLS = tuple(c for c in CELLS if c not in EXCLUDED_CELLS)

# Recorded strings for spec.json (DEC-040 s6 exclusion + s8 stop-rule
# correction, both documented in DEC-042). Kept as constants so spec.json and
# any driver regeneration carry byte-identical text.
STOP_RULE_TEXT = (
    "halt on: 2nd failure on the same cell across conditions (DEC-040 s8; "
    "corrected from the originally implemented per-(cell,cond) counter - "
    "see DEC-042); cell outside s5; aqe true; SC6 ledger move; "
    "any TRAIN/TEST cell")
REDUCED_COVERAGE_NOTE = (
    "DEC-040 s6: acceptance is computed over whatever was actually run. "
    "F3_rdd|medium is EXCLUDED - long-standing fragility, not an EXP-009 "
    "regression: EXP-002 recorded 18 FAILED / 8 COMPLETED for F3_rdd|medium "
    "vs 25 COMPLETED / 1 FAILED for F3_rdd|small, and results/baseline/"
    "F3_rdd/ holds small only (no medium baseline was ever produced). "
    "Scope after exclusion: 7 cells x 3 conds x 5 reps = 105 in-scope "
    "executions; the recorded F3_rdd|medium rows stay in observations.jsonl "
    "as execution records.")
EXCLUDED_CELLS_RECORD = [
    {"cell": "F3_rdd|medium",
     "scope": ("excluded from further execution and from analysis; "
               "retained on disk"),
     "authority": "DEC-040 s6 (acceptance over whatever was actually run)",
     "evidence": ("EXP-002: F3_rdd|medium 18 FAILED / 8 COMPLETED vs "
                  "F3_rdd|small 25 COMPLETED / 1 FAILED; "
                  "results/baseline/F3_rdd/ holds small only, "
                  "no medium baseline")},
]
TOTAL_IN_SCOPE = len(IN_SCOPE_CELLS) * len(CONDITIONS) * REPS  # 7x3x5 = 105


class SplitAuthorization(PermissionError):
    """Any cell outside the purpose-scoped EXP-009 authorization."""


def exp009_guard(family: str, scale: str, seed: int) -> str:
    """Authorize exactly the 8 frozen VALIDATION cells, nothing else."""
    split = authorize_validation_cell(
        family, scale, seed, stage="EXP-009 monitoring overhead")
    if seed != SEED or (family, scale) not in CELLS:
        raise SplitAuthorization(
            "EXP-009 allows only 8 validation cells x seed 3 (DEC-040 s5); "
            "got %s/%s/seed%s" % (family, scale, seed))
    if split != VALIDATION:
        raise SplitAuthorization(
            "EXP-009 allows VALIDATION only; got %r" % split)
    return split


def ledger_live_total() -> int:
    """Current SC6 live total via the production ledger (read-only)."""
    path = PROJECT / "scripts" / "validate_day31.py"
    spec = importlib.util.spec_from_file_location("day31_ledger_live", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return int(mod.ledger_from_manifests()[1])


def config_for(condition: dict[str, Any], base: SparkConfig) -> SparkConfig:
    """B0 with only the event-log switch adjusted for this condition."""
    cfg = base.with_overrides(
        event_log_enabled=bool(condition["event_log_enabled"]))
    if cfg.aqe_enabled:
        raise SystemExit("refusing: AQE became enabled (PLAN s7)")
    return cfg


def run_id_for(family: str, scale: str, condition: str, rep: int) -> str:
    return ("exp009-%s-%s-s%d-%s-r%d" % (family, scale, SEED, condition, rep)
            ).replace("_", "-").lower()

def build_queue(base: SparkConfig) -> list[dict[str, Any]]:
    """Deterministic 120-entry queue: rep-major, then cell, then condition."""
    point = b0_point()
    queue: list[dict[str, Any]] = []
    index = 0
    for rep in range(1, REPS + 1):
        for family, scale in CELLS:
            split = split_of(family, scale, SEED)
            if split != VALIDATION:
                raise SystemExit("refusing: %s|%s|s%d is %r, not validation"
                                 % (family, scale, SEED, split))
            for cond in CONDITIONS:
                index += 1
                cfg = config_for(cond, base)
                queue.append({
                    "queue_index": index, "rep": rep,
                    "family": family, "scale": scale,
                    "dataset_seed": SEED, "split": split,
                    "condition": cond["name"],
                    "sysmon_enabled": cond["sysmon_enabled"],
                    "event_log_enabled": cond["event_log_enabled"],
                    "config_name": point.name,
                    "config_fingerprint": point.fingerprint(),
                    "base_fingerprint": base.fingerprint(),
                    "event_log_fingerprint": cfg.fingerprint(),
                    "timeout_seconds": float(base.timeout_seconds),
                    "run_id": run_id_for(family, scale, cond["name"], rep),
                })
    if len(queue) != TOTAL_RUNS:
        raise SystemExit("queue has %d runs, frozen %d"
                         % (len(queue), TOTAL_RUNS))
    if len({e["run_id"] for e in queue}) != len(queue):
        raise SystemExit("refusing: duplicate run ids in queue")
    return queue


def spec_doc(base: SparkConfig, queue: list[dict[str, Any]]) -> dict[str, Any]:
    point = b0_point()
    doc = {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "authorized_by": AUTHORIZED_BY,
        "register_line": "EXP-009 (NOT charged to SC6 TRAIN cap 500)",
        "sc6_charge": 0,
        "purpose": "monitoring-overhead paired measurement",
        "cells": ["%s|%s|s%d" % (f, s, SEED) for f, s in CELLS],
        "cells_authorized_but_unexecutable": [{
            "cell": "micro (5 MB)",
            "reason": ("zero micro entries in data/generated/index.json; "
                       "resolver/WorkloadSpec/split_of admit small/medium/"
                       "large only; new capability forbidden"),
            "spark_executions": 0}],
        "reduced_coverage_note": REDUCED_COVERAGE_NOTE,
        "conditions": [
            {"name": c["name"], "sysmon_enabled": c["sysmon_enabled"],
             "event_log_enabled": c["event_log_enabled"]} for c in CONDITIONS
        ],
        "dataset_seed": SEED,
        "repetitions_per_cell_condition": REPS,
        "total_planned": TOTAL_RUNS,
        "config": "B0 (frozen default)",
        "config_name": point.name,
        "config_fingerprint": point.fingerprint(),
        "base_config_path": BASE_CONFIG_PATH,
        "base_config_fingerprint": base.fingerprint(),
        "aqe_enabled": False,
        "metric": "execution_time_s",
        "metric_source_required": "runner",
        "warmup": "executed and discarded (PLAN 22)",
        "retry_policy": "no retry; failures first-class",
        "manifest_rule": "every run records sysmon+eventlog flags",
        "stop_rule": STOP_RULE_TEXT,
        "excluded_cells": EXCLUDED_CELLS_RECORD,
        "queue": queue,
    }
    canon = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    doc["artifact_id"] = hashlib.sha256(canon).hexdigest()
    return doc


def read_existing() -> dict[str, dict[str, Any]]:
    """Observations already on disk, keyed by run_id (resume support)."""
    done: dict[str, dict[str, Any]] = {}
    if OBS_PATH.exists():
        for line in OBS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["run_id"]] = row
    return done

def verify_resume(spec: dict[str, Any],
                  done: dict[str, dict[str, Any]]) -> None:
    """Queued entries already recorded must match the frozen queue exactly."""
    wanted = {e["run_id"]: e for e in spec["queue"]}
    for run_id, row in done.items():
        want = wanted.get(run_id)
        if want is None:
            raise SystemExit("refusing: %s not in frozen queue" % run_id)
        # Recorded rows store the dataset seed under "seed"; the frozen queue
        # stores it under "dataset_seed" (same value, different key name).
        row_seed = row.get("seed", row.get("dataset_seed"))
        if row_seed != want["dataset_seed"]:
            raise SystemExit("refusing: %s disagrees on %s" % (run_id, "dataset_seed"))
        for key in ("family", "scale", "condition",
                    "sysmon_enabled", "event_log_enabled", "config_name",
                    "config_fingerprint"):
            if row.get(key) != want[key]:
                raise SystemExit("refusing: %s disagrees on %s" % (run_id, key))


def print_plan(queue: list[dict[str, Any]], base: SparkConfig) -> None:
    print("EXP-009 monitoring overhead (DEC-040 s5, VALIDATION only)")
    print("  cells : %s (seed %d)"
          % (", ".join("%s|%s" % c for c in CELLS), SEED))
    print("  conds : FULL(T,T) NO-SYSMON(F,T) NEITHER(F,F)")
    print("  plan  : %d runs (8 cells x 3 conds x %d reps, rep-major)"
          % (len(queue), REPS))
    print("  scope : %d in scope (7 cells, F3_rdd|medium excluded per DEC-040 s6; "
          "retained on disk, never executed further)" % TOTAL_IN_SCOPE)
    print("  cfg   : B0 fp=%s... aqe=%s timeout=%s"
          % (base.fingerprint()[:16], base.aqe_enabled,
             base.timeout_seconds))
    print("  micro : authorized-but-unexecutable, 0 Spark (see spec)")
    print("  ledger: EXP-009 own line, 0 to SC6 (cap 500)")
    by_cell: dict[str, int] = {}
    for e in queue:
        key = "%s|%s %s" % (e["family"], e["scale"], e["condition"])
        by_cell[key] = by_cell.get(key, 0) + 1
    for key in sorted(by_cell):
        print("    %-28s x%d" % (key, by_cell[key]))

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true",
                    help="print frozen queue; 0 Spark, 0 writes")
    ap.add_argument("--run", action="store_true",
                    help="execute (or resume) the frozen 120-run queue")
    ap.add_argument("--allow-spark", action="store_true",
                    help="explicitly permit Spark execution")
    args = ap.parse_args()
    if sum(bool(m) for m in (args.plan, args.run)) != 1:
        ap.error("pass exactly one of --plan, --run")

    base = SparkConfig.from_yaml(str(PROJECT / BASE_CONFIG_PATH))
    assert_b0_unchanged(base)
    if base.aqe_enabled:
        raise SystemExit("refusing: B0 has AQE on (PLAN s7)")
    queue = build_queue(base)
    doc = spec_doc(base, queue)

    if args.plan:
        print_plan(queue, base)
        print("  PLAN MODE: 0 Spark runs, 0 writes.")
        return 0
    if not args.allow_spark:
        print("REFUSED: --run needs --allow-spark. Spark executions: 0")
        return 2

    before = ledger_live_total()
    print("EXP-009 execution (DEC-040 s5) - SC6 live=%d" % before)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if SPEC_PATH.exists():
        prior = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        if prior.get("artifact_id") != doc["artifact_id"]:
            raise SystemExit("refusing: existing spec is another design")
    else:
        SPEC_PATH.write_text(json.dumps(doc, indent=1, sort_keys=True),
                             encoding="utf-8")
    done = read_existing()
    verify_resume(doc, done)
    todo_all = [e for e in queue if e["run_id"] not in done]
    todo = [e for e in todo_all
            if (e["family"], e["scale"]) not in EXCLUDED_CELLS]
    skipped_excluded = len(todo_all) - len(todo)
    print("  recorded: %d  to execute: %d (of %d; %d queued-but-excluded, never run)"
          % (len(done), len(todo), len(queue), skipped_excluded))
    if SUMMARY_PATH.exists():
        raise SystemExit("refusing: summary.json exists (no overwrite)")

    guard = functools.partial(exp009_guard)
    point = b0_point()
    failures: dict[str, int] = {}
    sink = OBS_PATH.open("a", encoding="utf-8")
    try:
        for e in todo:
            if (e["family"], e["scale"]) in EXCLUDED_CELLS:
                print("  [%d/%d] %-8s %-14s rep%d SKIP excluded (DEC-040 s6; retained on disk)"
                      % (e["queue_index"], len(queue), e["condition"],
                         "%s|%s" % (e["family"], e["scale"]), e["rep"]), flush=True)
                continue
            guard(e["family"], e["scale"], e["dataset_seed"])
            cfg = config_for({"event_log_enabled": e["event_log_enabled"]},
                             base)

            spec = RunSpec(
                run_id=e["run_id"], family=e["family"], scale=e["scale"],
                seed=e["dataset_seed"], rep=e["rep"], config=point,
                split=VALIDATION, timeout_seconds=e["timeout_seconds"],
                order_index=e["queue_index"] - 1, block_id="exp009")
            metrics, _prov = execute_run(
                spec, cfg, sysmon_enabled=e["sysmon_enabled"],
                split_guard=guard)
            if metrics.aqe_enabled:
                raise SystemExit("STOP: aqe true for %s" % e["run_id"])
            # NEITHER runs carry event_log_status MISSING by design; that is
            # NOT a failure. Timing-ok = runner clock + runner source + live.
            timing_ok = (metrics.execution_time_s is not None
                         and metrics.execution_time_source == "runner"
                         and not metrics.timeout)
            cell_key = "%s|%s" % (e["family"], e["scale"])
            row = {
                "run_id": e["run_id"], "queue_index": e["queue_index"],
                "experiment_id": EXPERIMENT_ID,
                "protocol_version": PROTOCOL_VERSION,
                "family": e["family"], "scale": e["scale"],
                "seed": e["dataset_seed"], "rep": e["rep"],
                "split": VALIDATION, "condition": e["condition"],
                "sysmon_enabled": e["sysmon_enabled"],
                "event_log_enabled": e["event_log_enabled"],
                "config_name": point.name,
                "config_fingerprint": point.fingerprint(),
                "event_log_fingerprint": e["event_log_fingerprint"],
                "aqe_enabled": bool(metrics.aqe_enabled),
                "usable": bool(metrics.usable),
                "timing_valid": timing_ok,
                "timeout": bool(metrics.timeout),
                "execution_time_s": metrics.execution_time_s,
                "execution_time_source": metrics.execution_time_source,
                "event_log_status": metrics.event_log_status,
                "sysmon_sampled": bool(metrics.sysmon_sampled),
                "sysmon_reason": metrics.sysmon_reason,
                "sysmon_sample_count": metrics.sysmon_sample_count,
                "dataset_fingerprint": metrics.dataset_fingerprint,
                "result_signature": metrics.result_signature,
                "error": metrics.error,
            }
            if not timing_ok:
                failures[cell_key] = failures.get(cell_key, 0) + 1
                if failures[cell_key] >= 2:
                    sink.write(json.dumps(row, sort_keys=True) + "\n")
                    sink.flush()
                    os.fsync(sink.fileno())
                    raise SystemExit(
                        "STOP (DEC-040 s8): %s failed twice; kept unanalysed"
                        % cell_key)
            sink.write(json.dumps(row, sort_keys=True) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
            tag = ("%.4fs" % metrics.execution_time_s
                   if metrics.execution_time_s is not None else "-")
            print("  [%d/%d] %-8s %-14s rep%d ok=%-5s t=%s elog=%s"
                  % (e["queue_index"], len(queue), e["condition"],
                     "%s|%s" % (e["family"], e["scale"]), e["rep"],
                     timing_ok, tag, metrics.event_log_status), flush=True)
            if ledger_live_total() != before:
                raise SystemExit("STOP (DEC-040 s8): SC6 ledger moved")
    finally:
        sink.close()

    obs = [json.loads(line) for line in
           OBS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_ok = sum(1 for o in obs if o.get("timing_valid"))
    in_scope = [o for o in obs
                if (o.get("family"), o.get("scale")) not in EXCLUDED_CELLS]
    excluded_n = len(obs) - len(in_scope)
    in_scope_missing = TOTAL_IN_SCOPE - len(in_scope)
    body = {
        "schema_version": PROTOCOL_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "stage": ("complete (105 of 105 in scope; 12 excluded retained)"
                  if len(in_scope) == TOTAL_IN_SCOPE and in_scope_missing == 0
                  else "partial (%d of %d in scope; %d excluded retained)"
                  % (len(in_scope), TOTAL_IN_SCOPE, excluded_n)),
        "protocol_version": PROTOCOL_VERSION,
        "spec_artifact_id": doc["artifact_id"],
        "authorized_by": AUTHORIZED_BY,
        "observation_counts": {
            "planned": TOTAL_RUNS, "planned_in_scope": TOTAL_IN_SCOPE,
            "recorded": len(obs), "recorded_in_scope": len(in_scope),
            "recorded_excluded_retained": excluded_n,
            "timing_valid": n_ok, "timing_invalid": len(obs) - n_ok,
            "remaining": TOTAL_RUNS - len(obs),
            "remaining_in_scope": max(in_scope_missing, 0)},
        "excluded_cells": [{"cell": "%s|%s" % c,
                            "scope": "excluded from further execution and from analysis; retained on disk",
                            "authority": "DEC-040 s6 (acceptance over whatever was actually run)",
                            "evidence": ("EXP-002: F3_rdd|medium 18 FAILED / 8 COMPLETED vs "
                                         "F3_rdd|small 25 COMPLETED / 1 FAILED; "
                                         "results/baseline/F3_rdd/ holds small only, no medium baseline")}
                           for c in EXCLUDED_CELLS],
        "coverage": "7-of-8 cells (F3_rdd|medium excluded per DEC-040 s6)",
        "register_line": "EXP-009 (0 charged to SC6)",
        "sc6_live_before": before,
        "sc6_live_after": ledger_live_total(),
        "contains_test_data": False,
        "no_analysis_rule": "runner records only; see analyze_exp009",
        "micro_note": "micro authorized-but-unexecutable, 0 Spark",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    canon = json.dumps(body, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    SUMMARY_PATH.write_text(json.dumps(body, indent=1, sort_keys=True),
                            encoding="utf-8")
    print("  ledger: %d/%d recorded (%d in scope of %d), %d timing-ok, %d in-scope remaining"
          % (len(obs), TOTAL_RUNS, len(in_scope), TOTAL_IN_SCOPE, n_ok, max(in_scope_missing, 0)))
    print("  NO OVERHEAD CLAIM MADE DURING EXECUTION.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
