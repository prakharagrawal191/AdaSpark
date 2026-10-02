"""EXP-013 confirmatory re-evaluation - frozen arms on the full frozen TEST identity.

Pre-registered by DEC-053 (docs/research/DEC_053_EXP013_CONFIRMATORY_PREREGISTRATION.md).
PURPOSE: affirm OR refute the manuscript's stated main-comparison conclusions under a
drift-controlled design - never to obtain better numbers. Every arm, configuration,
policy, threshold and the analysis code is frozen before the first execution; nothing
is tuned on TEST. Executions belong to EXP-013's own register line and are NOT charged
to the SC6 TRAIN cap (500).

Design (DEC-053 section 2):
  * cells: the 43 frozen TEST cells (results/evaluation/test_freeze.json) minus
    F3_rdd|large|s3 (40/40 prior structural failures: EXP-005 all arms + X6 B0') = 42;
  * execution units per cell, resolved with the EXP-005 driver's OWN frozen code
    (imported, not re-implemented): B0; B1 (= B3, identity verified); B4 executed
    separately although it resolves to B1's configuration - the A/A control; RL (the
    frozen RL-s0 artifact, greedy; RL-s1/RL-s2 are identity-mapped wherever their
    configuration fingerprint equals RL-s0's, else they become their own units); B2
    only where its configuration differs from both B1 and RL. On the 7 EXP-005
    instances also B0' (AQE-on default, DEC-047 gate), compared with B0 only;
  * randomized complete block design, block = (cell, rep): stage-major, then rep-major,
    cells shuffled per (stage, rep), units shuffled per block, from seed 20261001;
  * F3_rdd|large probe rule: the rep-1 block of each F3_rdd large cell starts with B0
    and RL; if both fail, the cell is STRUCTURAL-INCOMPLETE and every later entry of it
    is recorded NOT_EXECUTED with 0 Spark executions.

Safety shape (DEC-013 Model B, exactly as EXP-005):
  * execute_run receives THIS driver's guard only - authorize_test_cell AND membership
    in the 42 cells; B0' units additionally require an EXP-005 instance and are the only
    units run with allow_aqe=True. assert_test_execution_permitted stays sealed.
  * --plan executes 0 Spark and writes nothing; --run requires --allow-spark.
  * No retry; failures are first-class rows; completed rows are never rewritten; an
    interruption loses at most the run in flight and --run resumes at the next index.
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

from sparkrl.evaluation.spec import authorize_test_cell  # noqa: E402
from sparkrl.evaluation.strategies import StrategyResolutionError, resolve  # noqa: E402
from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import TEST, RunSpec  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.utils.paths import resolve_data_root  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_exp005", PROJECT / "scripts" / "run_exp005.py")
R5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R5)

PROTOCOL_VERSION = "exp013/v1"
AUTHORIZED_BY = "DEC-053"
SEED = 20261001
REPS = 5
STAGES = ("A", "B", "C", "D")
TEST_FREEZE_ID = "699e98dfe6e706cede7a0dc11d66c54beeb5a629fc8437c5c68182fef4e5b67f"
EXCLUDED = {("F3_rdd", "large", 3):
            "40/40 prior structural failures (EXP-005 all arms + X6 B0'), AQE-independent"}
PROBE_UNITS = ("B0", "RL")
RL_ARMS = ("RL-s0", "RL-s1", "RL-s2")
MIN_FREE_BYTES = 5 * 2**30
FREEZE_PATH = PROJECT / "results" / "evaluation" / "test_freeze.json"
OUT_DIR = PROJECT / "results" / "experiments" / "exp-013"
SPEC_PATH = OUT_DIR / "spec.json"
OBS_PATH = OUT_DIR / "observations.jsonl"
ANALYSIS_CODE = ("scripts/analyze_exp013.py", "src/sparkrl/analysis/inference.py",
                 "scripts/run_exp013.py")
RESOURCE_FIELDS = ("stage_count", "task_count", "failed_task_count", "shuffle_read_bytes",
                   "shuffle_write_bytes", "memory_spill_bytes", "disk_spill_bytes",
                   "rows_processed", "sysmon_sample_count", "rss_bytes_max", "rss_bytes_mean",
                   "proc_cpu_time_s", "proc_cpu_percent_mean", "sys_cpu_percent_mean",
                   "sys_mem_available_bytes_min", "sys_mem_percent_max", "warmup_time_s",
                   "total_time_s", "task_duration_cv")


class SplitAuthorization(PermissionError):
    """Any cell or unit outside the purpose-scoped EXP-013 authorization."""


def sha256_file(rel: str) -> str:
    """LF-normalised digest (DEC-037 s4): CRLF and LF checkouts of the same code agree."""
    return hashlib.sha256((PROJECT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def cell_key(cell: tuple[str, str, int]) -> str:
    return "%s|%s|s%d" % cell


def load_cells() -> list[tuple[str, str, int]]:
    """The 43 frozen TEST cells in file order, minus the pre-registered exclusion."""
    art = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if art.get("artifact_id") != TEST_FREEZE_ID or len(art["cells"]) != 43:
        raise SystemExit("refusing: test_freeze.json is not the frozen 43-cell identity")
    cells = [(c["family"], c["scale"], int(c["seed"])) for c in art["cells"]]
    return [c for c in cells if c not in EXCLUDED]


def exp005_cells() -> set[tuple[str, str, int]]:
    instances, _fp = R5.load_instances()
    return {(i["family"], i["scale"], int(i["dataset_seed"])) for i in instances}


def stage_of(cell: tuple[str, str, int], exp005_instances: set) -> str:
    if cell in exp005_instances:
        return "A"
    if cell[0] == "F4_ski":
        return "B"
    return "C" if cell[1] != "large" else "D"


def is_probe_cell(cell: tuple[str, str, int]) -> bool:
    return cell[0] == "F3_rdd" and cell[1] == "large"


def exp013_guard(family: str, scale: str, seed: int, *, frozen: set) -> None:
    """The ONLY split_guard for non-B0' units (DEC-013 Model B)."""
    authorize_test_cell(family, scale, seed, stage="EXP-013 confirmatory re-evaluation")
    if (family, scale, seed) not in frozen:
        raise SplitAuthorization(f"{family}/{scale}/seed{seed} is not one of the 42 "
                                 "EXP-013 cells; executing it is unauthorized")


def b0prime_guard(family: str, scale: str, seed: int, *, frozen: set, exp005_instances: set) -> None:
    exp013_guard(family, scale, seed, frozen=frozen)
    if (family, scale, seed) not in exp005_instances:
        raise SplitAuthorization("B0' (AQE-on) is authorized only on the 7 EXP-005 instances")


def resolve_units(cell, base, prime, by_arm, exp005_instances) -> tuple[list[dict], dict[str, str]]:
    """Execution units of one cell + the arm -> unit identity map. 0 Spark."""
    def unit(name, point, cfg_base, **extra):
        return {"unit": name, "config_name": point.name, "point": point,
                "config_fingerprint": point.fingerprint(),
                "applied_fingerprint": point.apply_to(cfg_base).fingerprint(),
                "aqe": bool(cfg_base.aqe_enabled), "rl_action": None, "rl_state_key": None,
                **extra}

    units = [unit(arm, R5.resolve_static_arm(arm, *cell, base)[0], base)
             for arm in ("B0", "B1", "B4")]
    identity = {"B0": "B0", "B1": "B1", "B4": "B4"}
    b1 = units[1]
    rs3 = resolve("B3", family=cell[0], scale=cell[1], dataset_seed=cell[2], base_config=base)
    if rs3.config_name != b1["config_name"] or rs3.config.fingerprint() != b1["applied_fingerprint"]:
        raise SystemExit(f"refusing: B3 no longer resolves to B1's configuration on "
                         f"{cell_key(cell)}; DEC-053's identity premise is broken")
    identity["B3"] = "B1"
    rl = {}
    for arm in RL_ARMS:
        point, action, skey, _d, _p = R5.resolve_rl_arm(by_arm[arm], *cell, base)
        rl[arm] = unit("RL" if arm == "RL-s0" else arm, point, base,
                       rl_action=action, rl_state_key=list(skey))
    units.append(rl["RL-s0"])
    identity["RL-s0"] = "RL"
    for arm in ("RL-s1", "RL-s2"):
        if rl[arm]["config_fingerprint"] == rl["RL-s0"]["config_fingerprint"]:
            identity[arm] = "RL"
        else:
            units.append(rl[arm])
            identity[arm] = arm
    try:
        b2 = unit("B2", R5.resolve_static_arm("B2", *cell, base)[0], base)
        same = [u["unit"] for u in units if u["config_fingerprint"] == b2["config_fingerprint"]
                and u["unit"] in ("B1", "RL")]
        if same:
            identity["B2"] = same[0]
        else:
            units.append(b2)
            identity["B2"] = "B2"
    except StrategyResolutionError:
        identity["B2"] = "UNDEFINED"     # B2 x F4_ski, DEC-019 Option A
    if cell in exp005_instances:
        units.append(unit("B0'", b0_point(), prime, config_name="B0-prime"))
        identity["B0'"] = "B0'"
    return units, identity


def build_queue(cells, units_of, exp005_instances) -> list[dict[str, Any]]:
    """Frozen randomized complete block order. Deterministic from SEED (str seeds hash
    with sha512, independent of PYTHONHASHSEED)."""
    queue: list[dict[str, Any]] = []
    for stage in STAGES:
        stage_cells = [c for c in cells if stage_of(c, exp005_instances) == stage]
        for rep in range(1, REPS + 1):
            order = list(stage_cells)
            random.Random(f"{SEED}|{stage}|{rep}").shuffle(order)
            for cell in order:
                names = [u["unit"] for u in units_of[cell]]
                random.Random(f"{SEED}|{cell_key(cell)}|{rep}").shuffle(names)
                if rep == 1 and is_probe_cell(cell):
                    names = ([n for n in names if n in PROBE_UNITS]
                             + [n for n in names if n not in PROBE_UNITS])
                for name in names:
                    queue.append({"queue_index": len(queue) + 1, "stage": stage, "rep": rep,
                                  "family": cell[0], "scale": cell[1], "dataset_seed": cell[2],
                                  "unit": name,
                                  "probe": rep == 1 and is_probe_cell(cell) and name in PROBE_UNITS})
    return queue


def queue_fingerprint(queue: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(queue, sort_keys=True).encode("utf-8")).hexdigest()


def structural_cells(done: dict[int, dict], queue: list[dict]) -> set:
    """F3_rdd large cells whose two probe entries were both executed and both failed."""
    probes: dict[tuple, list[bool]] = {}
    for e in queue:
        if e["probe"] and e["queue_index"] in done:
            row = done[e["queue_index"]]
            if row.get("event_log_status") != "NOT_EXECUTED":
                probes.setdefault((e["family"], e["scale"], e["dataset_seed"]), []).append(
                    bool(row["usable"]))
    return {c for c, ok in probes.items() if len(ok) == len(PROBE_UNITS) and not any(ok)}


def failed_twice(done: dict[int, dict], cell: tuple, unit: str, rep: int) -> bool:
    """True iff this (cell, unit) was executed and failed in both of the two previous reps."""
    prev = {r["rep"]: r for r in done.values() if r["unit"] == unit
            and (r["family"], r["scale"], r["seed"]) == cell
            and r.get("event_log_status") != "NOT_EXECUTED"}
    return all(k in prev and not prev[k]["usable"] for k in (rep - 1, rep - 2))


def setup() -> dict[str, Any]:
    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    assert_b0_unchanged(base)
    prime = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0_prime.yaml")
    if not prime.aqe_enabled:
        raise SystemExit("refusing: baseline_b0_prime.yaml must have AQE enabled")
    rl_arms, rl_fp = R5.load_rl_arms()
    by_arm = {a["arm"]: a for a in rl_arms["arms"]}
    cells = load_cells()
    exp005_instances = exp005_cells()
    resolved = {c: resolve_units(c, base, prime, by_arm, exp005_instances) for c in cells}
    units_of = {c: resolved[c][0] for c in cells}
    queue = build_queue(cells, units_of, exp005_instances)
    return {"base": base, "prime": prime, "rl_fp": rl_fp, "cells": cells, "exp005": exp005_instances,
            "units_of": units_of, "identity": {c: resolved[c][1] for c in cells},
            "queue": queue, "queue_fp": queue_fingerprint(queue)}


def build_spec(ctx: dict[str, Any]) -> dict[str, Any]:
    cells = ctx["cells"]
    doc = {
        "experiment_id": "EXP-013", "protocol_version": PROTOCOL_VERSION,
        "authorized_by": AUTHORIZED_BY,
        "purpose": ("confirmatory: affirm or refute the stated main-comparison conclusions "
                    "under randomized interleaving with an A/A control; nothing tuned"),
        "test_freeze_artifact_id": TEST_FREEZE_ID,
        "excluded_cells": {cell_key(c): why for c, why in EXCLUDED.items()},
        "cells": [{"cell": cell_key(c), "stage": stage_of(c, ctx["exp005"])} for c in cells],
        "units": {cell_key(c): [{k: v for k, v in u.items() if k != "point"}
                                for u in ctx["units_of"][c]] for c in cells},
        "identity_map": {cell_key(c): ctx["identity"][c] for c in cells},
        "rl_arms_manifest_fingerprint": ctx["rl_fp"],
        "base_config_fingerprints": {"B0": ctx["base"].fingerprint(),
                                     "B0'": ctx["prime"].fingerprint()},
        "seed": SEED, "reps": REPS, "stages": list(STAGES),
        "probe_rule": "rep-1 block of F3_rdd large cells starts with B0 and RL; both fail "
                      "-> STRUCTURAL-INCOMPLETE, later entries NOT_EXECUTED (0 Spark)",
        "noise_rule": {"cv": 0.1189, "source": "EXP-001 worst-cell CV; DEC-018 Decision F"},
        "queue": ctx["queue"], "queue_fingerprint": ctx["queue_fp"],
        "code_sha256": {rel: sha256_file(rel) for rel in ANALYSIS_CODE},
        "sc6_charge": 0, "split": TEST,
    }
    doc["artifact_id"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()
    return doc


def read_done() -> dict[int, dict]:
    done: dict[int, dict] = {}
    if OBS_PATH.exists():
        for line in OBS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["queue_index"] in done:
                    raise SystemExit(f"refusing: duplicate queue_index {row['queue_index']}")
                done[row["queue_index"]] = row
    return done


def make_row(e: dict, u: dict, identity: dict, **fields) -> dict[str, Any]:
    cell = (e["family"], e["scale"], e["dataset_seed"])
    return {"run_id": ("exp013-%s-%s-s%d-%s-r%d" % (*cell, u["unit"], e["rep"])
                       ).replace("_", "-").replace("'", "p").lower(),
            "queue_index": e["queue_index"], "stage": e["stage"], "rep": e["rep"],
            "block": "%s|r%d" % (cell_key(cell), e["rep"]), "unit": u["unit"],
            "arms": sorted(a for a, v in identity.items() if v == u["unit"]),
            "family": cell[0], "scale": cell[1], "seed": cell[2], "split": TEST,
            "config_name": u["config_name"], "config_fingerprint": u["config_fingerprint"],
            "aqe_enabled": u["aqe"], "rl_action": u["rl_action"],
            "rl_state_key": u["rl_state_key"], "probe": e["probe"],
            "protocol_version": PROTOCOL_VERSION, "authorized_by": AUTHORIZED_BY, **fields}


def run(ctx: dict[str, Any], stages: set[str], max_minutes: float) -> int:
    if SPEC_PATH.exists():
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        if spec["queue_fingerprint"] != ctx["queue_fp"]:
            raise SystemExit("refusing: rebuilt queue differs from the frozen spec.json")
        drift = [rel for rel, h in spec["code_sha256"].items() if sha256_file(rel) != h]
        if drift:
            raise SystemExit(f"refusing: frozen code changed since the spec: {drift}")
    else:
        spec = build_spec(ctx)
        OUT_DIR.mkdir(parents=True, exist_ok=False)
        SPEC_PATH.write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("  spec frozen:", SPEC_PATH.relative_to(PROJECT), spec["artifact_id"][:16])

    frozen = set(ctx["cells"])
    guard = functools.partial(exp013_guard, frozen=frozen)
    guard_prime = functools.partial(b0prime_guard, frozen=frozen, exp005_instances=ctx["exp005"])
    done = read_done()
    todo = [e for e in ctx["queue"] if e["stage"] in stages and e["queue_index"] not in done]
    print("  to execute in stage(s) %s: %d of %d entries"
          % ("".join(sorted(stages)), len(todo), len(ctx["queue"])))
    started = time.monotonic()
    executed = 0
    with OBS_PATH.open("a", encoding="utf-8") as sink:
        for e in todo:
            if (time.monotonic() - started) / 60.0 >= max_minutes:
                print("  time budget reached; resume with the same command")
                break
            if shutil.disk_usage(resolve_data_root()).free < MIN_FREE_BYTES:
                raise SystemExit("halt (DEC-053 s5): less than 5 GiB free on the data root")
            cell = (e["family"], e["scale"], e["dataset_seed"])
            u = next(x for x in ctx["units_of"][cell] if x["unit"] == e["unit"])
            identity = ctx["identity"][cell]
            skip = None
            if cell in structural_cells(done, ctx["queue"]):
                skip = "both probe entries failed"
            elif is_probe_cell(cell) and failed_twice(done, cell, u["unit"], e["rep"]):
                skip = "this unit failed in its two previous repetitions of a probe cell"
            if skip:
                row = make_row(e, u, identity, usable=False, timeout=False,
                               execution_time_s=None, execution_time_source=None,
                               error=f"STRUCTURAL-INCOMPLETE (DEC-053 probe rule): {skip}; "
                                     "not executed", event_log_status="NOT_EXECUTED")
            else:
                is_prime = u["unit"] == "B0'"
                run_spec = RunSpec(
                    run_id=make_row(e, u, identity)["run_id"], family=cell[0],
                    scale=cell[1], seed=cell[2], rep=e["rep"], config=u["point"],
                    split=TEST, timeout_seconds=float(ctx["base"].timeout_seconds),
                    order_index=e["queue_index"] - 1, block_id=f"exp013-{e['stage']}")
                metrics, prov = execute_run(
                    run_spec, ctx["prime"] if is_prime else ctx["base"],
                    split_guard=guard_prime if is_prime else guard, allow_aqe=is_prime)
                md = metrics.to_dict()
                row = make_row(
                    e, u, identity, usable=bool(metrics.usable) and not metrics.timeout,
                    timeout=bool(metrics.timeout), execution_time_s=metrics.execution_time_s,
                    execution_time_source=metrics.execution_time_source, error=metrics.error,
                    event_log_status=metrics.event_log_status,
                    config_fingerprint_applied=metrics.config_fingerprint,
                    dataset_fingerprint=metrics.dataset_fingerprint,
                    code_version=prov["code_version"],
                    wall_started_utc=prov["wall_started_utc"],
                    wall_finished_utc=prov["wall_finished_utc"],
                    resources={k: md.get(k) for k in RESOURCE_FIELDS})
                executed += 1
            sink.write(json.dumps(row, sort_keys=True) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
            done[e["queue_index"]] = row
            print("  [%d/%d] %s %-5s %-22s r%d %-11s usable=%-5s %s"
                  % (e["queue_index"], len(ctx["queue"]), e["stage"], u["unit"],
                     cell_key(cell), e["rep"], u["config_name"], row["usable"],
                     ("%.3fs" % row["execution_time_s"]) if row["execution_time_s"]
                     else row["event_log_status"] or "-"), flush=True)
            if (not row["usable"] and not is_probe_cell(cell)
                    and failed_twice(done, cell, u["unit"], e["rep"] + 1)):
                raise SystemExit(f"halt (DEC-053 s5): {u['unit']} on {cell_key(cell)} "
                                 "failed in two consecutive repetitions")
    print("  executed this invocation: %d Spark runs; rows on disk: %d of %d"
          % (executed, len(done), len(ctx["queue"])))
    return 0


def plan(ctx: dict[str, Any]) -> int:
    queue = ctx["queue"]
    per_stage = {s: sum(1 for e in queue if e["stage"] == s) for s in STAGES}
    print("EXP-013 plan  (0 Spark, 0 writes)")
    print("  cells: %d (excluded: %s)" % (len(ctx["cells"]), ", ".join(map(cell_key, EXCLUDED))))
    print("  queue entries: %d  per stage %s" % (len(queue), per_stage))
    print("  queue fingerprint:", ctx["queue_fp"])
    print("  B0 base fp %s | B0' base fp %s | RL manifest fp %s" % (
        ctx["base"].fingerprint()[:16], ctx["prime"].fingerprint()[:16], ctx["rl_fp"][:16]))
    missing = []
    for c in ctx["cells"]:
        try:
            resolve_dataset(*c)
        except (FileNotFoundError, ValueError) as exc:
            missing.append((cell_key(c), str(exc)[:80]))
    print("  datasets resolvable on disk: %d/%d %s" % (len(ctx["cells"]) - len(missing),
                                                       len(ctx["cells"]), missing or ""))
    for c in ctx["cells"]:
        units = ", ".join("%s=%s" % (u["unit"], u["config_name"]) for u in ctx["units_of"][c])
        print("  %s %-22s %s | identity %s" % (stage_of(c, ctx["exp005"]), cell_key(c), units,
                                               ctx["identity"][c]))
    return 0 if not missing else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true", help="validate and print; 0 Spark, 0 writes")
    ap.add_argument("--run", action="store_true", help="execute queue entries of --stage")
    ap.add_argument("--stage", default="A", help="stages to execute, e.g. A or AB or ABCD")
    ap.add_argument("--max-minutes", type=float, default=100.0,
                    help="stop cleanly between runs after this many minutes")
    ap.add_argument("--allow-spark", action="store_true",
                    help="required with --run; explicit Spark acknowledgement")
    args = ap.parse_args()
    if args.run and not args.allow_spark:
        ap.error("--run requires --allow-spark")
    if not (args.plan or args.run):
        ap.error("nothing to do: pass --plan or --run")
    stages = set(args.stage.upper())
    if not stages <= set(STAGES):
        ap.error(f"--stage must use letters from {''.join(STAGES)}")
    ctx = setup()
    return plan(ctx) if args.plan else run(ctx, stages, args.max_minutes)


if __name__ == "__main__":
    raise SystemExit(main())
