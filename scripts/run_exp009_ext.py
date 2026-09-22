#!/usr/bin/env python
"""EXP-009 repetition extension runner - DEC-043 s3, VALIDATION only, 0 to SC6.

DEC-042 recorded SC6 clause 2 as INCONCLUSIVE: at n=5 every cell's 95%
bootstrap CI straddles both 0 and the 5% gate. DEC-043 authorizes additional
repetitions, per-cell n derived from that cell's own measured dispersion and
staged by resolution efficiency (lowest required n first).

WHY A SECOND DRIVER AND NOT AN EDIT TO run_exp009.py
  run_exp009.py is frozen to the DEC-040 design: REPS=5, a 120-entry queue
  whose artifact_id it refuses to run against a different design, and a
  refusal once summary.json exists. Editing it would mutate the DEC-040/042
  record. This driver leaves every DEC-040 artifact byte-identical and
  IMPORTS the canonical machinery from run_exp009.py - the same conditions,
  the same split guard, the same B0 config path, the same ledger probe, the
  same run-id scheme, the same STOP rule - so nothing methodological is
  re-typed here. Only the repetition COUNT differs, which is precisely and
  only what DEC-043 amends (DEC-043 preamble: "this amends only its s5
  repetition count").

WHAT IS UNCHANGED (DEC-043 s5)
  cells, the three conditions FULL/NO-SYSMON/NEITHER, interleaving within
  (cell, rep), AQE OFF, Day-3 timing semantics, the per-run manifest fields
  sysmon_enabled + event_log_enabled, separate reporting of the two
  components, the 5% acceptance (PLAN line 45), DEC-042's interval rule, and
  the F3_rdd|medium exclusion (DEC-040 s6, DEC-042 s2).

REPETITION SEMANTICS (DEC-043 s3, read literally)
  "repetitions per condition = that cell's own reps_needed_for_2pp_halfwidth
  (sysmon component)" with the table's "executions (x3)" column equal to n*3
  (96/348/423/495, cumulative 1362 for stages 1-4, and the wall-clock
  estimates are n*3*median_duration). So this driver executes n NEW
  repetitions per condition, numbered rep 6..n+5, and - per the same section
  - "already-recorded observations are retained and pooled with the new
  ones", giving n+5 analysed repetitions per condition. Nothing is discarded,
  re-run or overwritten.

LEDGER (DEC-043 s4)
  Every cell is validation split, seed 3. SC6 caps TRAIN. 0 charged; the
  ledger is probed before the stage and after every single run, and any
  movement is a STOP. Executions land on EXP-009's own register line.

STOP (DEC-043 s6 = DEC-040 s8 as corrected by DEC-042 s7)
  halt and keep the partial record on: a cell failing twice (counter keyed on
  the CELL, not the (cell, condition)); a cell outside DEC-040 s5; aqe true;
  any SC6 ledger movement.

Stages 5-7 are authorized by DEC-043 s3 but are NOT executed by the task that
introduced this file; stages are stoppable after any completed stage.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))


def _load_base_driver():
    """Import run_exp009.py as a module so the protocol is reused, not copied."""
    path = PROJECT / "scripts" / "run_exp009.py"
    spec = importlib.util.spec_from_file_location("run_exp009_canonical", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BASE = _load_base_driver()

from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import VALIDATION, RunSpec  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

PROTOCOL_VERSION = "exp009-ext/v1"
EXPERIMENT_ID = "EXP-009"
AUTHORIZED_BY = "DEC-043"
SEED = BASE.SEED
CONDITIONS = BASE.CONDITIONS
BASELINE_REPS = BASE.REPS                       # 5 already recorded per cond

EXT_DIR = BASE.OUT_DIR / "ext"
OBS_PATH = EXT_DIR / "observations_ext.jsonl"
BASELINE_SNAPSHOT = EXT_DIR / "baseline_pre_dec043.json"

# Provenance pins: the artifacts DEC-043 s3 derives its n from. If either
# changes, the derivation is no longer the one that was authorized and this
# driver refuses rather than silently running a different design.
SOURCE_ANALYSIS = PROJECT / "results" / "evaluation" / "exp009_analysis.json"
SOURCE_ANALYSIS_ARTIFACT_ID = (
    "4960f0ed86a86c7c5368323c7ff4905effdf70da953d6f1932c49c2f91e3c853")
BASELINE_OBS_SHA256 = (
    "e58a543e5ab42f5ab7bf592e368fb1863bb365906df851e190fadec40bff5ce2")

# DEC-043 s3, transcribed verbatim. Cross-checked at runtime against the n
# derived from SOURCE_ANALYSIS; a disagreement is a STOP, never a silent
# preference for one source over the other.
STAGES: tuple[dict[str, Any], ...] = (
    {"stage": 1, "family": "F5_mixed", "scale": "medium", "n": 32,
     "executions": 96, "cumulative": 96, "est_wall_clock": "~36 min"},
    {"stage": 2, "family": "F3_rdd", "scale": "small", "n": 116,
     "executions": 348, "cumulative": 444, "est_wall_clock": "~79 min"},
    {"stage": 3, "family": "F2_join", "scale": "medium", "n": 141,
     "executions": 423, "cumulative": 867, "est_wall_clock": "~121 min"},
    {"stage": 4, "family": "F2_join", "scale": "small", "n": 165,
     "executions": 495, "cumulative": 1362, "est_wall_clock": "~17 min"},
    {"stage": 5, "family": "F1_agg", "scale": "medium", "n": 202,
     "executions": 606, "cumulative": 1968, "est_wall_clock": "~398 min"},
    {"stage": 6, "family": "F1_agg", "scale": "small", "n": 242,
     "executions": 726, "cumulative": 2694, "est_wall_clock": "~263 min"},
    {"stage": 7, "family": "F5_mixed", "scale": "small", "n": 716,
     "executions": 2148, "cumulative": 4842, "est_wall_clock": "~147 min"},
)
STAGE_BY_ID = {s["stage"]: s for s in STAGES}
TARGET_HALFWIDTH_PP = 2.0        # DEC-042 s5 / DEC-043 s7, not a new parameter


def stage_spec_path(stage: int) -> Path:
    return EXT_DIR / ("stage%d_spec.json" % stage)


def stage_summary_path(stage: int) -> Path:
    return EXT_DIR / ("stage%d_summary.json" % stage)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(PROJECT),
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or "unknown"
    except Exception:                                          # noqa: BLE001
        return "unknown"


def load_source_analysis() -> dict[str, Any]:
    doc = json.loads(SOURCE_ANALYSIS.read_text(encoding="utf-8"))
    if doc.get("artifact_id") != SOURCE_ANALYSIS_ARTIFACT_ID:
        raise SystemExit(
            "refusing: %s artifact_id %r is not the DEC-043 s3 source %r"
            % (SOURCE_ANALYSIS, doc.get("artifact_id"),
               SOURCE_ANALYSIS_ARTIFACT_ID))
    return doc


def derived_n(analysis: dict[str, Any], family: str, scale: str) -> int:
    """n for this cell, DERIVED from the artifact DEC-043 s3 names."""
    cell = "%s|%s" % (family, scale)
    for entry in analysis.get("cells", []):
        if entry.get("cell") == cell:
            n = entry.get("reps_needed_for_2pp_halfwidth", {}).get("sysmon")
            if not isinstance(n, int):
                raise SystemExit("refusing: %s has no integer sysmon "
                                 "reps_needed_for_2pp_halfwidth" % cell)
            return n
    raise SystemExit("refusing: %s not present in %s" % (cell, SOURCE_ANALYSIS))


def check_baseline_untouched() -> None:
    """The DEC-040/042 observation record must be exactly as it was signed."""
    got = sha256_file(BASE.OBS_PATH)
    if got != BASELINE_OBS_SHA256:
        raise SystemExit(
            "STOP: baseline observations.jsonl changed (sha256 %s, expected "
            "%s). The DEC-040/042 record must not move."
            % (got, BASELINE_OBS_SHA256))


def build_queue(stage: dict[str, Any],
                base: SparkConfig) -> list[dict[str, Any]]:
    """n new repetitions per condition, rep-major, interleaved by condition.

    Reps are numbered BASELINE_REPS+1 .. BASELINE_REPS+n so no recorded
    observation is re-run and no run_id can collide with the DEC-040 record.
    """
    point = b0_point()
    family, scale = stage["family"], stage["scale"]
    queue: list[dict[str, Any]] = []
    index = 0
    for rep in range(BASELINE_REPS + 1, BASELINE_REPS + stage["n"] + 1):
        for cond in CONDITIONS:
            index += 1
            cfg = BASE.config_for(cond, base)
            queue.append({
                "queue_index": index, "rep": rep,
                "family": family, "scale": scale,
                "dataset_seed": SEED, "split": VALIDATION,
                "condition": cond["name"],
                "sysmon_enabled": cond["sysmon_enabled"],
                "event_log_enabled": cond["event_log_enabled"],
                "config_name": point.name,
                "config_fingerprint": point.fingerprint(),
                "base_fingerprint": base.fingerprint(),
                "event_log_fingerprint": cfg.fingerprint(),
                "timeout_seconds": float(base.timeout_seconds),
                "run_id": BASE.run_id_for(family, scale, cond["name"], rep),
            })
    if len(queue) != stage["executions"]:
        raise SystemExit("queue has %d runs, DEC-043 s3 authorizes %d"
                         % (len(queue), stage["executions"]))
    if len({e["run_id"] for e in queue}) != len(queue):
        raise SystemExit("refusing: duplicate run ids in queue")
    return queue


def spec_doc(stage: dict[str, Any], base: SparkConfig,
             queue: list[dict[str, Any]], n_src: int) -> dict[str, Any]:
    point = b0_point()
    doc = {
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "authorized_by": AUTHORIZED_BY,
        "authorization_scope": "DEC-043 s3 (repetition count only)",
        "amends": "DEC-040 s5 repetition count; nothing else (DEC-043 preamble)",
        "stage": stage["stage"],
        "cell": "%s|%s|s%d" % (stage["family"], stage["scale"], SEED),
        "reps_per_condition_new": stage["n"],
        "reps_per_condition_source": (
            "reps_needed_for_2pp_halfwidth.sysmon in "
            "results/evaluation/exp009_analysis.json"),
        "reps_per_condition_derived": n_src,
        "reps_per_condition_dec043_table": stage["n"],
        "reps_already_recorded_per_condition": BASELINE_REPS,
        "reps_pooled_per_condition": BASELINE_REPS + stage["n"],
        "pooling_rule": ("DEC-043 s3: already-recorded observations are "
                         "retained and pooled with the new ones; nothing is "
                         "discarded and no prior observation is re-run or "
                         "overwritten"),
        "target_ci_halfwidth_pp": TARGET_HALFWIDTH_PP,
        "executions_authorized": stage["executions"],
        "est_wall_clock_dec043": stage["est_wall_clock"],
        "conditions": [
            {"name": c["name"], "sysmon_enabled": c["sysmon_enabled"],
             "event_log_enabled": c["event_log_enabled"]} for c in CONDITIONS],
        "dataset_seed": SEED,
        "split": VALIDATION,
        "config": "B0 (frozen default)",
        "config_name": point.name,
        "config_fingerprint": point.fingerprint(),
        "base_config_path": BASE.BASE_CONFIG_PATH,
        "base_config_fingerprint": base.fingerprint(),
        "aqe_enabled": False,
        "metric": "execution_time_s",
        "metric_source_required": "runner",
        "warmup": "executed and discarded (PLAN 22)",
        "retry_policy": "no retry; failures first-class",
        "manifest_rule": "every run records sysmon+eventlog flags",
        "stop_rule": BASE.STOP_RULE_TEXT,
        "register_line": "EXP-009 (NOT charged to SC6 TRAIN cap 500)",
        "sc6_charge": 0,
        "source_analysis_artifact_id": SOURCE_ANALYSIS_ARTIFACT_ID,
        "baseline_observations_sha256": BASELINE_OBS_SHA256,
        "baseline_spec_artifact_id": json.loads(
            BASE.SPEC_PATH.read_text(encoding="utf-8")).get("artifact_id"),
        "excluded_cells": BASE.EXCLUDED_CELLS_RECORD,
        "contains_test_data": False,
        "queue": queue,
    }
    canon = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    doc["artifact_id"] = hashlib.sha256(canon).hexdigest()
    return doc


def read_existing() -> dict[str, dict[str, Any]]:
    done: dict[str, dict[str, Any]] = {}
    if OBS_PATH.exists():
        for line in OBS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["run_id"]] = row
    return done


def verify_resume(queue: list[dict[str, Any]],
                  done: dict[str, dict[str, Any]], stage: int) -> None:
    """Rows already recorded for THIS stage must match the frozen queue."""
    wanted = {e["run_id"]: e for e in queue}
    for run_id, row in done.items():
        if row.get("stage") != stage:
            continue
        want = wanted.get(run_id)
        if want is None:
            raise SystemExit("refusing: %s not in stage %d queue"
                             % (run_id, stage))
        if row.get("seed", row.get("dataset_seed")) != want["dataset_seed"]:
            raise SystemExit("refusing: %s disagrees on dataset_seed" % run_id)
        for key in ("family", "scale", "condition", "rep", "sysmon_enabled",
                    "event_log_enabled", "config_name", "config_fingerprint"):
            if row.get(key) != want[key]:
                raise SystemExit("refusing: %s disagrees on %s" % (run_id, key))


def collision_check(queue: list[dict[str, Any]]) -> None:
    """No new run_id may collide with the DEC-040 record or a prior stage."""
    baseline_ids = {json.loads(line)["run_id"]
                    for line in BASE.OBS_PATH.read_text(
                        encoding="utf-8").splitlines() if line.strip()}
    clash = sorted({e["run_id"] for e in queue} & baseline_ids)
    if clash:
        raise SystemExit("STOP: run_id collision with the DEC-040 record: %s"
                         % clash[:5])


def print_plan(stage: dict[str, Any], queue: list[dict[str, Any]],
               base: SparkConfig, n_src: int, done: int) -> None:
    print("EXP-009 repetition extension - DEC-043 s3, stage %d" % stage["stage"])
    print("  cell     : %s|%s seed %d (VALIDATION)"
          % (stage["family"], stage["scale"], SEED))
    print("  n/cond   : %d new (DEC-043 table %d, derived %d) + %d recorded "
          "= %d pooled"
          % (stage["n"], stage["n"], n_src, BASELINE_REPS,
             BASELINE_REPS + stage["n"]))
    print("  conds    : FULL(T,T) NO-SYSMON(F,T) NEITHER(F,F), rep-major")
    print("  execs    : %d authorized this stage (%s est.); %d already recorded"
          % (stage["executions"], stage["est_wall_clock"], done))
    print("  cfg      : B0 fp=%s... aqe=%s timeout=%s"
          % (base.fingerprint()[:16], base.aqe_enabled, base.timeout_seconds))
    print("  ledger   : EXP-009 own register line, 0 charged to SC6 (cap 500)")
    print("  target   : CI half-width -> ~%.1f pp (DEC-043 s7 prediction)"
          % TARGET_HALFWIDTH_PP)


def write_baseline_snapshot() -> int:
    """Read-only pre-DEC-043 evidence snapshot. 0 Spark, no result touched."""
    analysis = load_source_analysis()
    check_baseline_untouched()
    runsum = json.loads(BASE.SUMMARY_PATH.read_text(encoding="utf-8"))
    spec = json.loads(BASE.SPEC_PATH.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in
            BASE.OBS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    per_cell = []
    for entry in analysis["cells"]:
        fam, scale = entry["cell"].split("|")
        counts = {c: sum(1 for r in rows if r.get("family") == fam
                         and r.get("scale") == scale
                         and r.get("condition") == c
                         and r.get("timing_valid"))
                  for c in ("FULL", "NO-SYSMON", "NEITHER")}
        sys_ci = entry.get("sysmon_ci95_pct")
        elog_ci = entry.get("eventlog_ci95_pct")
        per_cell.append({
            "cell": entry["cell"],
            "n_timing_valid_per_condition": counts,
            "n_per_condition": BASELINE_REPS,
            "point_estimate_sysmon_pct": entry.get("overhead_sysmon_pct"),
            "point_estimate_eventlog_pct": entry.get("overhead_eventlog_pct"),
            "sysmon_ci95_pct": sys_ci,
            "eventlog_ci95_pct": elog_ci,
            "sysmon_ci_halfwidth_pp": (0.5 * (sys_ci[1] - sys_ci[0])
                                       if sys_ci else None),
            "eventlog_ci_halfwidth_pp": (0.5 * (elog_ci[1] - elog_ci[0])
                                         if elog_ci else None),
            "reps_needed_for_2pp_halfwidth": entry.get(
                "reps_needed_for_2pp_halfwidth"),
            "resolution_efficiency_rank_sysmon": None,
            "sysmon_verdict": entry.get("sysmon_verdict"),
            "eventlog_verdict": entry.get("eventlog_verdict"),
            "cell_verdict": entry.get("verdict"),
        })
    order = sorted(per_cell,
                   key=lambda c: c["reps_needed_for_2pp_halfwidth"]["sysmon"])
    for rank, entry in enumerate(order, start=1):
        entry["resolution_efficiency_rank_sysmon"] = rank
    body = {
        "schema_version": "exp009-ext-baseline/v1",
        "purpose": ("read-only snapshot of the pre-DEC-043 evidence, so a "
                    "reviewer can separate it from DEC-043 stage evidence"),
        "experiment_id": EXPERIMENT_ID,
        "captured_for": AUTHORIZED_BY,
        "spark_executions": 0,
        "git_head": git_head(),
        "baseline_observations_path": str(
            BASE.OBS_PATH.relative_to(PROJECT)).replace("\\", "/"),
        "baseline_observations_sha256": sha256_file(BASE.OBS_PATH),
        "baseline_spec_artifact_id": spec.get("artifact_id"),
        "baseline_run_summary_artifact_id": runsum.get("artifact_id"),
        "baseline_analysis_artifact_id": analysis.get("artifact_id"),
        "baseline_stage": runsum.get("stage"),
        "baseline_observation_counts": runsum.get("observation_counts"),
        "baseline_overall_verdict": analysis.get("verdict"),
        "sc6_ledger_live": BASE.ledger_live_total(),
        "sc6_cap": 500,
        "sc6_charged_by_dec043": 0,
        "test_touched": False,
        "threshold_pct": analysis.get("threshold_pct"),
        "threshold_source": analysis.get("threshold_source"),
        "target_ci_halfwidth_pp": TARGET_HALFWIDTH_PP,
        "bootstrap": analysis.get("uncertainty"),
        "cells": per_cell,
        "excluded_cells": analysis.get("excluded_cells"),
        "authorized_stages": [
            {k: s[k] for k in ("stage", "family", "scale", "n", "executions",
                               "cumulative", "est_wall_clock")}
            for s in STAGES],
        "stages_executed_by_this_task": [1, 2, 3, 4],
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    if BASELINE_SNAPSHOT.exists():
        prior = json.loads(BASELINE_SNAPSHOT.read_text(encoding="utf-8"))
        if prior.get("artifact_id") != body["artifact_id"]:
            raise SystemExit("refusing: baseline snapshot exists and differs")
        print("baseline snapshot already present and identical: %s"
              % BASELINE_SNAPSHOT)
        return 0
    BASELINE_SNAPSHOT.write_text(json.dumps(body, indent=1, sort_keys=True),
                                 encoding="utf-8")
    print("baseline snapshot written: %s" % BASELINE_SNAPSHOT)
    print("  head=%s ledger=%d/500 verdict=%s obs_sha=%s..."
          % (body["git_head"], body["sc6_ledger_live"],
             body["baseline_overall_verdict"],
             body["baseline_observations_sha256"][:16]))
    print("  0 Spark executions, 0 writes to any DEC-040/042 artifact.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", type=int, choices=sorted(STAGE_BY_ID),
                    help="DEC-043 s3 stage to plan or execute")
    ap.add_argument("--baseline", action="store_true",
                    help="write the read-only pre-DEC-043 snapshot; 0 Spark")
    ap.add_argument("--plan", action="store_true",
                    help="print the frozen stage queue; 0 Spark, 0 writes")
    ap.add_argument("--run", action="store_true",
                    help="execute (or resume) the frozen stage queue")
    ap.add_argument("--allow-spark", action="store_true",
                    help="explicitly permit Spark execution")
    args = ap.parse_args()
    if sum(bool(m) for m in (args.baseline, args.plan, args.run)) != 1:
        ap.error("pass exactly one of --baseline, --plan, --run")
    if args.baseline:
        return write_baseline_snapshot()
    if args.stage is None:
        ap.error("--plan and --run need --stage")

    stage = STAGE_BY_ID[args.stage]
    analysis = load_source_analysis()
    n_src = derived_n(analysis, stage["family"], stage["scale"])
    if n_src != stage["n"]:
        raise SystemExit(
            "STOP: derived n=%d for %s|%s disagrees with the DEC-043 s3 table "
            "n=%d; the authorization and its source no longer agree"
            % (n_src, stage["family"], stage["scale"], stage["n"]))
    check_baseline_untouched()

    base = SparkConfig.from_yaml(str(PROJECT / BASE.BASE_CONFIG_PATH))
    assert_b0_unchanged(base)
    if base.aqe_enabled:
        raise SystemExit("refusing: B0 has AQE on (PLAN s7)")
    queue = build_queue(stage, base)
    collision_check(queue)
    doc = spec_doc(stage, base, queue, n_src)
    done_rows = read_existing()
    verify_resume(queue, done_rows, stage["stage"])
    todo = [e for e in queue if e["run_id"] not in done_rows]

    if args.plan:
        print_plan(stage, queue, base, n_src, len(queue) - len(todo))
        print("  PLAN MODE: 0 Spark runs, 0 writes.")
        return 0
    if not args.allow_spark:
        print("REFUSED: --run needs --allow-spark. Spark executions: 0")
        return 2

    if not BASELINE_SNAPSHOT.exists():
        raise SystemExit("refusing: run --baseline first (Phase 2 snapshot)")
    before = BASE.ledger_live_total()
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    spath = stage_spec_path(stage["stage"])
    if spath.exists():
        prior = json.loads(spath.read_text(encoding="utf-8"))
        if prior.get("artifact_id") != doc["artifact_id"]:
            raise SystemExit("refusing: existing stage spec is another design")
    else:
        spath.write_text(json.dumps(doc, indent=1, sort_keys=True),
                         encoding="utf-8")
    sumpath = stage_summary_path(stage["stage"])
    if sumpath.exists():
        raise SystemExit("refusing: stage %d summary exists (no overwrite)"
                         % stage["stage"])

    print("EXP-009 ext stage %d (%s|%s) - DEC-043 s3 - SC6 live=%d"
          % (stage["stage"], stage["family"], stage["scale"], before))
    print("  recorded: %d  to execute: %d of %d"
          % (len(queue) - len(todo), len(todo), len(queue)))
    point = b0_point()
    guard = BASE.exp009_guard
    failures: dict[str, int] = {}
    started = time.time()
    sink = OBS_PATH.open("a", encoding="utf-8")
    try:
        for pos, e in enumerate(todo, start=1):
            guard(e["family"], e["scale"], e["dataset_seed"])
            cfg = BASE.config_for(
                {"event_log_enabled": e["event_log_enabled"]}, base)
            spec = RunSpec(
                run_id=e["run_id"], family=e["family"], scale=e["scale"],
                seed=e["dataset_seed"], rep=e["rep"], config=point,
                split=VALIDATION, timeout_seconds=e["timeout_seconds"],
                order_index=e["queue_index"] - 1,
                block_id="exp009-ext-s%d" % stage["stage"])
            metrics, _prov = execute_run(
                spec, cfg, sysmon_enabled=e["sysmon_enabled"],
                split_guard=guard)
            if metrics.aqe_enabled:
                raise SystemExit("STOP: aqe true for %s" % e["run_id"])
            timing_ok = (metrics.execution_time_s is not None
                         and metrics.execution_time_source == "runner"
                         and not metrics.timeout)
            cell_key = "%s|%s" % (e["family"], e["scale"])
            row = {
                "run_id": e["run_id"], "queue_index": e["queue_index"],
                "experiment_id": EXPERIMENT_ID,
                "protocol_version": PROTOCOL_VERSION,
                "authorized_by": AUTHORIZED_BY,
                "stage": stage["stage"],
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
                "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime()),
            }
            if not timing_ok:
                failures[cell_key] = failures.get(cell_key, 0) + 1
                if failures[cell_key] >= 2:
                    sink.write(json.dumps(row, sort_keys=True) + "\n")
                    sink.flush()
                    os.fsync(sink.fileno())
                    raise SystemExit(
                        "STOP (DEC-043 s6): %s failed twice; kept unanalysed"
                        % cell_key)
            sink.write(json.dumps(row, sort_keys=True) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
            elapsed = time.time() - started
            rate = elapsed / pos
            print("  [%d/%d] %-9s rep%-4d ok=%-5s t=%s elog=%-8s "
                  "%.1fs/run eta=%.0fm"
                  % (pos, len(todo), e["condition"], e["rep"], timing_ok,
                     ("%.4fs" % metrics.execution_time_s)
                     if metrics.execution_time_s is not None else "-",
                     metrics.event_log_status, rate,
                     (len(todo) - pos) * rate / 60.0), flush=True)
            if BASE.ledger_live_total() != before:
                raise SystemExit("STOP (DEC-043 s6): SC6 ledger moved")
    finally:
        sink.close()

    rows = [json.loads(line) for line in
            OBS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    mine = [r for r in rows if r.get("stage") == stage["stage"]]
    ok = sum(1 for r in mine if r.get("timing_valid"))
    per_cond = {c["name"]: sum(1 for r in mine
                               if r.get("condition") == c["name"]
                               and r.get("timing_valid"))
                for c in CONDITIONS}
    complete = len(mine) == stage["executions"] and ok == stage["executions"]
    body = {
        "schema_version": PROTOCOL_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "authorized_by": AUTHORIZED_BY,
        "authorization_scope": "DEC-043 s3 (repetition count only)",
        "stage": stage["stage"],
        "cell": "%s|%s|s%d" % (stage["family"], stage["scale"], SEED),
        "stage_status": ("complete (%d of %d)"
                         % (len(mine), stage["executions"]) if complete else
                         "partial (%d of %d)"
                         % (len(mine), stage["executions"])),
        "spec_artifact_id": doc["artifact_id"],
        "executions_authorized": stage["executions"],
        "executions_recorded": len(mine),
        "executions_timing_valid": ok,
        "executions_timing_invalid": len(mine) - ok,
        "timing_valid_per_condition_new": per_cond,
        "reps_per_condition_new": stage["n"],
        "reps_already_recorded_per_condition": BASELINE_REPS,
        "reps_pooled_per_condition": BASELINE_REPS + stage["n"],
        "register_line": "EXP-009 (0 charged to SC6)",
        "sc6_live_before": before,
        "sc6_live_after": BASE.ledger_live_total(),
        "sc6_charged": BASE.ledger_live_total() - before,
        "sc6_cap": 500,
        "contains_test_data": False,
        "baseline_observations_sha256": sha256_file(BASE.OBS_PATH),
        "no_analysis_rule": "runner records only; see analyze_exp009_ext",
        "wall_clock_seconds": round(time.time() - started, 3),
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    sumpath.write_text(json.dumps(body, indent=1, sort_keys=True),
                       encoding="utf-8")
    print("  stage %d: %s, %d timing-ok, SC6 %d -> %d (charged %d)"
          % (stage["stage"], body["stage_status"], ok,
             body["sc6_live_before"], body["sc6_live_after"],
             body["sc6_charged"]))
    print("  NO OVERHEAD CLAIM MADE DURING EXECUTION.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
