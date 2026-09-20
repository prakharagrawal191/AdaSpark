"""EXP-005 main comparison - 7 arms x 7 frozen TEST instances x 5 reps = 245.

Authorized by DEC-014 (as amended) + DEC-018 (Decision B): the dedicated
purpose-scoped EXP-005 entry point. The 245 runs belong to the EXP-005
experiment register line and are NOT charged to the SC6 TRAIN cap (500).

Safety shape (DEC-013 Model B):
  * ``execute_run`` is called with THIS driver's ``split_guard`` only;
    the default TRAIN guard and ``assert_test_execution_permitted`` (the
    execution seal) are untouched and stay sealed for every other caller.
  * The guard authorizes a cell ONLY if (a) ``authorize_test_cell`` agrees
    the cell is TEST and (b) the cell is one of the 7 frozen instances in
    results/evaluation/exp005_instances.json. Every other TEST cell,
    TRAIN cell and VALIDATION cell is refused.
  * ``--run`` requires ``--allow-spark``; ``--plan`` executes 0 Spark runs.
  * No retry. Failures are first-class observations.
  * FROZEN arms: B0, B1, B2, B4 (static, via sparkrl.evaluation.strategies)
    and RL-s0/RL-s1/RL-s2 (frozen policy artifacts, greedy, no Q update,
    no exploration). B3 is analytical only; B0' belongs to EXP-005b and is
    NOT an arm here.

Dry slice: the first 7 frozen queue entries are executed as harness
validation only. NO performance conclusion may be drawn from a dry slice.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.policy_store import (  # noqa: E402
    agent_from_artifact, load_policy, policy_fingerprint)
from sparkrl.evaluation.spec import authorize_test_cell  # noqa: E402
from sparkrl.evaluation.strategies import (  # noqa: E402
    StrategyResolutionError, build_grid, resolve)
from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import (  # noqa: E402
    TEST, ConfigPoint, RunSpec, split_of)
from sparkrl.rl.action import ActionMapper  # noqa: E402
from sparkrl.rl.state import StateEncoder  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

PROTOCOL_VERSION = "exp005/v1"
ARMS = ("B0", "B1", "B2", "B4", "RL-s0", "RL-s1", "RL-s2")
RL_ARM_IDS = {"RL-s0", "RL-s1", "RL-s2"}
INSTANCES_ARTIFACT = PROJECT / "results" / "evaluation" / "exp005_instances.json"
RL_ARMS_ARTIFACT = PROJECT / "models" / "policies" / "exp005_rl_arms.json"
OUT_DIR = PROJECT / "results" / "experiments" / "exp-005"
SPEC_PATH = OUT_DIR / "spec.json"
OBS_PATH = OUT_DIR / "observations.jsonl"
TOTAL_RUNS = 245  # 7 instances x 7 arms x 5 reps (DEC-018 Decision B)
DRY_SLICE = 7


class SplitAuthorization(PermissionError):
    """Any cell outside the purpose-scoped EXP-005 authorization."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_instances() -> tuple[list[dict[str, Any]], str]:
    """The frozen 7-instance list, in file order. Never reordered here."""
    art = json.loads(INSTANCES_ARTIFACT.read_text(encoding="utf-8"))
    instances = art["instances"]
    if art.get("executed") is not False or len(instances) != 7:
        raise SystemExit(
            f"refusing: {INSTANCES_ARTIFACT.name} must hold exactly 7 frozen, "
            f"unexecuted TEST instances; got {len(instances)}")
    for inst in instances:
        if split_of(inst["family"], inst["scale"], inst["dataset_seed"]) != TEST:
            raise SystemExit(
                f"refusing: {inst} is not split='test'; frozen list corrupted")
    return instances, art["fingerprint"]


def load_rl_arms() -> tuple[dict[str, Any], str]:
    art = json.loads(RL_ARMS_ARTIFACT.read_text(encoding="utf-8"))
    return art, art["fingerprint"]


def exp005_test_guard(family: str, scale: str, seed: int,
                      frozen: set[tuple[str, str, int]]) -> None:
    """The ONLY split_guard used by this driver (DEC-013 Model B).

    TEST is authorized exclusively through this purpose-scoped path and
    exclusively for the 7 frozen instances. assert_test_execution_permitted
    (the seal) is NOT modified and remains sealed for every other caller.
    """
    authorize_test_cell(family, scale, seed, stage="EXP-005 test evaluation")
    if (family, scale, seed) not in frozen:
        raise SplitAuthorization(
            f"{family}/{scale}/seed{seed} is TEST but is NOT one of the 7 "
            "frozen EXP-005 instances; executing it is unauthorized")


def build_queue(instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Canonical deterministic enumeration: instance-major (file order),
    then frozen arm order, then rep 1..5. An ordering, not a sampling
    scheme; recorded in the spec artifact BEFORE any execution."""
    queue: list[dict[str, Any]] = []
    for inst in instances:
        for arm in ARMS:
            for rep in range(1, 6):
                queue.append({
                    "queue_index": len(queue) + 1,
                    "family": inst["family"], "scale": inst["scale"],
                    "dataset_seed": inst["dataset_seed"], "arm": arm,
                    "rep": rep})
    if len(queue) != TOTAL_RUNS:
        raise SystemExit(f"queue is {len(queue)} entries; authorized {TOTAL_RUNS}")
    return queue


def resolve_static_arm(arm: str, family: str, scale: str, dataset_seed: int,
                       base: SparkConfig) -> tuple[ConfigPoint, str, dict[str, Any]]:
    """Frozen static arm -> (ConfigPoint, describe, provenance). No dynamics."""
    rs = resolve(arm, family=family, scale=scale, dataset_seed=dataset_seed,
                 base_config=base)
    if arm == "B0":
        point = b0_point()
    else:
        matches = [p for p in build_grid(include_b0=True) if p.name == rs.config_name]
        if len(matches) != 1:
            raise SystemExit(f"refusing: {arm} resolved to unknown config {rs.config_name!r}")
        point = matches[0]
        applied = point.apply_to(base)
        if applied.fingerprint() != rs.config.fingerprint():
            raise SystemExit(
                f"refusing: {arm} resolved config {rs.config.fingerprint()} does not "
                f"match grid point {point.name} applied to base ({applied.fingerprint()})")
    return point, rs.describe, dict(rs.provenance)


def resolve_rl_arm(arm_entry: dict[str, Any], family: str, scale: str,
                   dataset_seed: int, base: SparkConfig
                   ) -> tuple[ConfigPoint, int, tuple, str, dict[str, Any]]:
    """Frozen RL arm -> (ConfigPoint, greedy_action, state_key, describe, prov).

    Uses the frozen agent machinery itself (agent_from_artifact +
    select_action(epsilon=0.0)); no hand-rolled Q extraction, no Q update,
    no exploration. Greedy state convention (frozen Day-29/30):
    feedback_bin is the pessimistic bin for last_reward=None.
    """
    art = load_policy(arm_entry["policy_id"], PROJECT / "models" / "policies")
    fp = policy_fingerprint(art)
    if fp != arm_entry["policy_id"]:
        raise SystemExit(
            f"refusing: {arm_entry['arm']} artifact fingerprint {fp} != frozen "
            f"policy_id {arm_entry['policy_id']}")
    if art["learner_config"]["gamma"] != 0.0:
        raise SystemExit("refusing: RL arm artifact gamma != 0.0 (bandit mode frozen)")
    agent = agent_from_artifact(art)          # frozen rng_seed from artifact
    res = resolve_dataset(family, scale, dataset_seed)
    input_bytes = (int(res.orders_manifest["total_bytes"])
                   + int(res.lineitem_manifest["total_bytes"]))
    state = StateEncoder().encode(family, input_bytes, last_reward=None)
    action = agent.select_action(state, epsilon=0.0)
    cfg, point, _ = ActionMapper().to_config(action, base)
    prov = {"policy_id": arm_entry["policy_id"],
            "policy_fingerprint": fp,
            "agent_rng_seed": arm_entry["agent_rng_seed"],
            "episodes": arm_entry["episodes"], "updates": arm_entry["updates"],
            "contract_versions": arm_entry["contract_versions"]}
    return point, action, state.key(), (
        f"greedy action {action} via frozen policy {arm_entry['policy_id'][:12]}"), prov


def build_spec(instances: list[dict[str, Any]], inst_fp: str,
               queue: list[dict[str, Any]], rl_arms: dict[str, Any], rl_fp: str,
               base: SparkConfig) -> dict[str, Any]:
    static_prov = {arm: resolve_static_arm(arm, instances[0]["family"],
                                           instances[0]["scale"],
                                           instances[0]["dataset_seed"], base)[1]
                   for arm in ARMS if arm not in RL_ARM_IDS}
    doc = {
        "experiment_id": "EXP-005",
        "protocol_version": PROTOCOL_VERSION,
        "authorized_by": ["DEC-014 (as amended, approved via DEC-018)",
                          "DEC-018 Decision B (dedicated purpose-scoped entry point)"],
        "register_line": "EXP-005 (NOT charged to the SC6 TRAIN cap of 500)",
        "total_runs": TOTAL_RUNS,
        "dry_slice": {"size": DRY_SLICE, "queue_entries": [1, DRY_SLICE],
                      "purpose": "harness validation only; NO performance conclusion"},
        "repetitions": 5,
        "instances_fingerprint": inst_fp,
        "instances": instances,
        "arms": list(ARMS),
        "arm_provenance": {"static_describe": static_prov,
                           "rl_manifest_fingerprint": rl_fp,
                           "rl_arms": [{"arm": a["arm"], "policy_id": a["policy_id"],
                                        "agent_rng_seed": a["agent_rng_seed"]}
                                       for a in rl_arms["arms"]]},
        "excluded": {"B3": "analytical finding, not an EXP-005 arm",
                     "B0-prime": "EXP-005b only; never executes here"},
        "timing": {"metric": "execution_time_s",
                   "clock": "authoritative Day-3 runner clock",
                   "timeout_seconds": float(base.timeout_seconds)},
        "failure_protocol": ("no automatic retry; failures are first-class observations; "
                             "<5 usable reps marks a strategy-cell incomplete"),
        "noise_floor": {"source": "DEC-018", "exp001_worst_cell_cv": 0.1189,
                        "rule": ("do not describe a within-cell arm difference below "
                                 "~12% as an independently established effect without "
                                 "additional justification")},
        "no_analysis_rule": ("the dry slice ranks nothing; no significance test, no "
                             "winner selection, no retuning, no queue alteration"),
        "split_policy": ("TEST only via exp005_test_guard (authorize_test_cell + 7 frozen "
                         "instances); assert_test_execution_permitted stays sealed for "
                         "every other caller; TRAIN/VALIDATION refused"),
        "queue": queue,
    }
    canonical = json.dumps(doc, sort_keys=True, indent=1)
    doc["artifact_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return doc


def run_continuation(queue: list[dict[str, Any]], inst_fp: str,
                     by_arm: dict[str, Any], base: SparkConfig,
                     frozen: set[tuple], dry_run: bool) -> int:
    """Execute the uncompleted tail of the ALREADY-FROZEN queue.

    Never rebuilds, reorders or edits the queue: the queue is recomputed from the
    frozen instances and then verified ENTRY BY ENTRY against the queue stored in
    the existing spec.json. Any difference aborts before Spark starts.

    DEC-019 (Option A): the 15 B2 x F4_ski entries (indices 116-120, 186-190,
    221-225) are UNDEFINED - B2's frozen validation map covers only
    {F1_agg, F2_join, F3_rdd, F5_mixed} and F4_ski never appears in validation
    by design (PLAN section 18). They are recorded as INCOMPLETE rows with
    usable=false and NO Spark execution (0 Spark runs for those indices):
    no fallback config, no TEST tuning, queue stays 245 entries. Every other
    entry executes the frozen protocol unchanged.

    Completed observations are never rewritten. Each new observation is appended
    and flushed to disk the moment its run returns, so an interruption loses at
    most the run in flight and re-invoking resumes at the next uncompleted index.
    """
    if not (SPEC_PATH.exists() and OBS_PATH.exists()):
        raise SystemExit(
            "refusing: --continue requires an existing spec.json and "
            "observations.jsonl; there is no frozen queue to continue")

    spec_doc = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    stored = spec_doc.get("queue") or []
    if len(stored) != TOTAL_RUNS or len(queue) != TOTAL_RUNS:
        raise SystemExit(
            f"refusing: stored queue {len(stored)}, rebuilt {len(queue)}, "
            f"authorized {TOTAL_RUNS}")
    key_of = lambda e: (e["queue_index"], e["arm"], e["rep"], e["family"],
                        e["scale"], e["dataset_seed"])
    drift = [i for i, (a, b) in enumerate(zip(stored, queue), 1)
             if key_of(a) != key_of(b)]
    if drift:
        raise SystemExit(
            f"refusing: rebuilt queue differs from the frozen spec at "
            f"entry/entries {drift[:5]}; the queue is frozen and must not change")
    if spec_doc.get("instances_fingerprint") != inst_fp:
        raise SystemExit("refusing: instances fingerprint changed since the spec")

    done: dict[int, dict[str, Any]] = {}
    for line in OBS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        idx = o["queue_index"]
        if idx in done:
            raise SystemExit(f"refusing: duplicate queue_index {idx} already on disk")
        done[idx] = o
    todo = [e for e in queue if e["queue_index"] not in done]

    print("EXP-005 continuation")
    print("  queue verified identical to the frozen spec: %d entries" % TOTAL_RUNS)
    print("  already completed : %d  (indices %d..%d)"
          % (len(done), min(done), max(done)) if done else "  already completed : 0")
    print("  to execute        : %d  (next index %s)"
          % (len(todo), todo[0]["queue_index"] if todo else "-"))
    if not todo:
        print("  nothing to do: all %d entries are accounted for." % TOTAL_RUNS)
        return 0
    if dry_run:
        print("  PLAN MODE: 0 Spark runs, 0 writes.")
        return 0

    guard = functools.partial(exp005_test_guard, frozen=frozen)
    executed = 0
    failed = 0
    b2_undefined = 0
    B2_UNDEFINED_ERROR = (
        "INCOMPLETE (DEC-019 Option A): B2 is per-family static tuned on "
        "VALIDATION, which contains only {F1_agg, F2_join, F3_rdd, F5_mixed}; "
        "F4_ski is the deliberately unseen TEST family (PLAN section 18), so B2 "
        "has no frozen configuration for it. No Spark execution, no fallback, "
        "no TEST tuning; queue entry preserved.")
    with OBS_PATH.open("a", encoding="utf-8") as sink:
        for e in todo:
            key = (e["family"], e["scale"], e["dataset_seed"])
            arm = e["arm"]
            if arm == "B2" and e["family"] == "F4_ski":
                # DEC-019 Option A: specification gap, not a runtime failure.
                # Record the queue entry as INCOMPLETE with 0 Spark runs and
                # continue the frozen queue unchanged (no skip, no reorder).
                run_id = ("exp005-%s-%s-s%d-%s-r%d"
                          % (e["family"], e["scale"], e["dataset_seed"], arm, e["rep"])
                          ).replace("_", "-").lower()
                row = {
                    "run_id": run_id, "queue_index": e["queue_index"],
                    "arm": arm, "family": e["family"], "scale": e["scale"],
                    "seed": e["dataset_seed"], "rep": e["rep"], "split": TEST,
                    "config_name": None,
                    "config_fingerprint": None,
                    "rl_action": None, "rl_state_key": None,
                    "arm_provenance": {
                        "decision": "DEC-019 Option A",
                        "status": "INCOMPLETE-undefined",
                        "strategy_version": "exp005-strategies/v1",
                    },
                    "usable": False, "timeout": False,
                    "execution_time_s": None,
                    "execution_time_source": None,
                    "error": B2_UNDEFINED_ERROR,
                    "config_fingerprint_applied": None,
                    "dataset_fingerprint": None,
                    "event_log_status": "NOT_EXECUTED",
                    "protocol_version": PROTOCOL_VERSION,
                }
                sink.write(json.dumps(row, sort_keys=True) + "\n")
                sink.flush()
                os.fsync(sink.fileno())
                b2_undefined += 1
                failed += 1
                print("  [%d/%d] %-6s %-22s rep%d -> INCOMPLETE (B2 undefined on F4_ski, DEC-019; 0 Spark)"
                      % (e["queue_index"], TOTAL_RUNS, arm,
                         "%s|%s|s%d" % (e["family"], e["scale"], e["dataset_seed"]),
                         e["rep"]), flush=True)
                continue
            try:
                if arm in RL_ARM_IDS:
                    point, action, skey, _d, prov = resolve_rl_arm(by_arm[arm], *key, base)
                else:
                    point, _d, prov = resolve_static_arm(arm, *key, base)
                    action, skey = None, None
            except StrategyResolutionError as exc:
                raise SystemExit(
                    f"refusing at queue index {e['queue_index']} ({arm} x "
                    f"{e['family']}|{e['scale']}|s{e['dataset_seed']}): {exc}. "
                    f"B2 x F4_ski is the DEC-019 case; any other undefined "
                    f"resolution is a new gap and stops execution.") from exc
            run_id = ("exp005-%s-%s-s%d-%s-r%d"
                      % (e["family"], e["scale"], e["dataset_seed"], arm, e["rep"])
                      ).replace("_", "-").lower()
            run_spec = RunSpec(
                run_id=run_id, family=e["family"], scale=e["scale"],
                seed=e["dataset_seed"], rep=e["rep"], config=point, split=TEST,
                timeout_seconds=float(base.timeout_seconds),
                order_index=e["queue_index"] - 1, block_id="exp005-main")
            # identical protocol to the dry slice: guard first, failures are
            # first-class, no retry, no substitution, error preserved
            metrics, _p = execute_run(run_spec, base, split_guard=guard)
            usable = bool(metrics.usable) and not metrics.timeout
            if not usable:
                failed += 1
            row = {
                "run_id": run_id, "queue_index": e["queue_index"],
                "arm": arm, "family": e["family"], "scale": e["scale"],
                "seed": e["dataset_seed"], "rep": e["rep"], "split": TEST,
                "config_name": point.name,
                "config_fingerprint": point.fingerprint(),
                "rl_action": action, "rl_state_key": list(skey) if skey else None,
                "arm_provenance": prov,
                "usable": usable, "timeout": bool(metrics.timeout),
                "execution_time_s": metrics.execution_time_s,
                "execution_time_source": metrics.execution_time_source,
                "error": metrics.error,
                "config_fingerprint_applied": metrics.config_fingerprint,
                "dataset_fingerprint": metrics.dataset_fingerprint,
                "event_log_status": metrics.event_log_status,
                "protocol_version": PROTOCOL_VERSION,
            }
            sink.write(json.dumps(row, sort_keys=True) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
            executed += 1
            print("  [%d/%d] %-6s %-22s rep%d -> %-12s usable=%-5s %s"
                  % (e["queue_index"], TOTAL_RUNS, arm,
                     "%s|%s|s%d" % (e["family"], e["scale"], e["dataset_seed"]),
                     e["rep"], point.name, usable,
                     ("%.4fs" % metrics.execution_time_s)
                     if metrics.execution_time_s else "-"), flush=True)

    obs = [json.loads(l) for l in OBS_PATH.read_text(encoding="utf-8").splitlines()
           if l.strip()]
    obs.sort(key=lambda o: o["queue_index"])
    counts = {"planned": TOTAL_RUNS, "started": len(obs),
              "completed": sum(1 for o in obs if o["usable"]),
              "failed": sum(1 for o in obs if not o["usable"]),
              "remaining_total": TOTAL_RUNS - len(obs)}
    summary = {
        "experiment_id": "EXP-005",
        "stage": ("complete (245 of 245)" if not counts["remaining_total"]
                  else "partial (%d of %d)" % (len(obs), TOTAL_RUNS)),
        "protocol_version": PROTOCOL_VERSION,
        "spec_artifact_id": spec_doc["artifact_id"],
        "instances_fingerprint": inst_fp,
        "observation_counts": counts,
        "contains_test_data": True,
        "no_analysis_rule": spec_doc["no_analysis_rule"],
        "noise_floor": spec_doc["noise_floor"],
        "next_gate": ("EXP-005 execution complete -> pre-registered analysis"
                      if not counts["remaining_total"]
                      else "queue incomplete; resume with --continue"),
    }
    canonical = json.dumps({**summary, "observations": obs}, sort_keys=True)
    summary["artifact_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("  executed this pass: %d Spark (%d failed incl. %d B2-undefined INCOMPLETE, 0 Spark)"
          % (executed, failed, b2_undefined))
    print("  ledger: %d/%d accounted for, %d usable, %d failed, %d remaining"
          % (len(obs), TOTAL_RUNS, counts["completed"], counts["failed"],
             counts["remaining_total"]))
    print("  summary artifact_id", summary["artifact_id"][:16])
    print("  NO STATISTICAL / PERFORMANCE CONCLUSION DRAWN DURING EXECUTION.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true",
                    help="validate identities and print the slice; 0 Spark, 0 writes")
    ap.add_argument("--run", action="store_true", help="execute the 7-run dry slice")
    ap.add_argument("--continue", dest="continue_run", action="store_true",
                    help="execute the uncompleted tail of the frozen queue")
    ap.add_argument("--allow-spark", action="store_true",
                    help="required with --run/--continue; explicit Spark acknowledgement")
    args = ap.parse_args()
    if args.run and not args.allow_spark:
        ap.error("--run requires --allow-spark")
    if args.continue_run and not (args.allow_spark or args.plan):
        ap.error("--continue requires --allow-spark (or --plan to preview)")
    if not (args.plan or args.run or args.continue_run):
        ap.error("nothing to do: pass --plan, --run or --continue")

    instances, inst_fp = load_instances()
    rl_arms, rl_fp = load_rl_arms()
    by_arm = {a["arm"]: a for a in rl_arms["arms"]}
    missing = RL_ARM_IDS - set(by_arm)
    if missing:
        raise SystemExit(f"refusing: RL arm manifest lacks {sorted(missing)}")
    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    assert_b0_unchanged(base)
    frozen = {(i["family"], i["scale"], i["dataset_seed"]) for i in instances}
    queue = build_queue(instances)

    print("EXP-005 dry slice -- plan")
    print("  instances fp:", inst_fp[:16], "arms:", ", ".join(ARMS))
    print("  rl manifest fp:", rl_fp[:16])
    print("  b0 fp:", base.fingerprint()[:16])

    if args.continue_run:
        return run_continuation(queue, inst_fp, by_arm, base, frozen,
                                dry_run=bool(args.plan))

    slice_entries = queue[:DRY_SLICE]
    slice_instances: list[tuple[str, str, int]] = []
    for e in slice_entries:
        key = (e["family"], e["scale"], e["dataset_seed"])
        if key not in slice_instances:
            slice_instances.append(key)
    resolutions: dict[tuple, dict[str, Any]] = {}
    for key in slice_instances:
        for arm in ARMS:
            if arm in RL_ARM_IDS:
                point, action, skey, _d, _p = resolve_rl_arm(by_arm[arm], *key, base)
                resolutions[(key, arm)] = {"config_name": point.name, "action": action,
                                           "state_key": list(skey)}
            else:
                point, _d, _p = resolve_static_arm(arm, *key, base)
                resolutions[(key, arm)] = {"config_name": point.name}
    print("  identity validation: %d slice instance(s) x %d arms resolved"
          % (len(slice_instances), len(ARMS)))

    if args.plan:
        print("  slice queue entries:")
        for e in slice_entries:
            r = resolutions[((e["family"], e["scale"], e["dataset_seed"]), e["arm"])]
            extra = ""
            if "action" in r:
                extra = " action=%d state=%s" % (r["action"], "/".join(map(str, r["state_key"])))
            print("    %2d. %-6s %-22s rep%d -> %s%s"
                  % (e["queue_index"], e["arm"],
                     "%s|%s|s%d" % (e["family"], e["scale"], e["dataset_seed"]),
                     e["rep"], r["config_name"], extra))
        print("  PLAN MODE: 0 Spark runs, 0 writes.")
        return 0

    # ---- RUN MODE: the authorized 7-run dry slice (harness only) ----
    if SPEC_PATH.exists() or OBS_PATH.exists():
        raise SystemExit(
            f"refusing to overwrite existing EXP-005 artifacts in {OUT_DIR}; "
            "the frozen protocol forbids regeneration")
    spec_doc = build_spec(instances, inst_fp, queue, rl_arms, rl_fp, base)
    OUT_DIR.mkdir(parents=True)
    SPEC_PATH.write_text(json.dumps(spec_doc, indent=1, sort_keys=True) + "\n",
                         encoding="utf-8")
    print("  spec written:", SPEC_PATH.relative_to(PROJECT),
          "artifact_id", spec_doc["artifact_id"][:16])

    guard = functools.partial(exp005_test_guard, frozen=frozen)
    obs: list[dict[str, Any]] = []
    failed = 0
    for e in slice_entries:
        key = (e["family"], e["scale"], e["dataset_seed"])
        arm = e["arm"]
        if arm in RL_ARM_IDS:
            point, action, skey, _d, prov = resolve_rl_arm(by_arm[arm], *key, base)
        else:
            point, _d, prov = resolve_static_arm(arm, *key, base)
            action, skey = None, None
        run_id = ("exp005-%s-%s-s%d-%s-r%d"
                  % (e["family"], e["scale"], e["dataset_seed"], arm, e["rep"])
                  ).replace("_", "-").lower()
        run_spec = RunSpec(
            run_id=run_id, family=e["family"], scale=e["scale"],
            seed=e["dataset_seed"], rep=e["rep"], config=point, split=TEST,
            timeout_seconds=float(base.timeout_seconds),
            order_index=e["queue_index"] - 1, block_id="exp005-dry-slice")
        # guard runs inside execute_run BEFORE anything; failures are
        # first-class (no retry, no substitution, error preserved)
        metrics, _p = execute_run(run_spec, base, split_guard=guard)
        usable = bool(metrics.usable) and not metrics.timeout
        if not usable:
            failed += 1
        obs.append({
            "run_id": run_id, "queue_index": e["queue_index"],
            "arm": arm, "family": e["family"], "scale": e["scale"],
            "seed": e["dataset_seed"], "rep": e["rep"], "split": TEST,
            "config_name": point.name,
            "config_fingerprint": point.fingerprint(),
            "rl_action": action, "rl_state_key": list(skey) if skey else None,
            "arm_provenance": prov,
            "usable": usable, "timeout": bool(metrics.timeout),
            "execution_time_s": metrics.execution_time_s,
            "execution_time_source": metrics.execution_time_source,
            "error": metrics.error,
            "config_fingerprint_applied": metrics.config_fingerprint,
            "dataset_fingerprint": metrics.dataset_fingerprint,
            "event_log_status": metrics.event_log_status,
            "protocol_version": PROTOCOL_VERSION,
        })
        print("  [%d/%d] %-6s %-22s rep%d -> %-12s usable=%-5s %s"
              % (e["queue_index"], TOTAL_RUNS, arm,
                 "%s|%s|s%d" % (e["family"], e["scale"], e["dataset_seed"]),
                 e["rep"], point.name, usable,
                 ("%.4fs" % metrics.execution_time_s)
                 if metrics.execution_time_s else "-"))

    counts = {"planned": DRY_SLICE, "started": len(obs),
              "completed": sum(1 for o in obs if o["usable"]),
              "failed": failed,
              "remaining_slice": DRY_SLICE - len(obs),
              "remaining_total": TOTAL_RUNS - len(obs)}
    summary = {
        "experiment_id": "EXP-005", "stage": "dry-slice (first 7 of 245)",
        "protocol_version": PROTOCOL_VERSION,
        "spec_artifact_id": spec_doc["artifact_id"],
        "instances_fingerprint": inst_fp,
        "observation_counts": counts,
        "contains_test_data": True,   # TEST observations, by design (EXP-005 only)
        "no_analysis_rule": spec_doc["no_analysis_rule"],
        "noise_floor": spec_doc["noise_floor"],
        "next_gate": ("dry slice passed -> the remaining 238 runs proceed only "
                      "on explicit operator instruction"),
    }
    canonical = json.dumps({**summary, "observations": obs}, sort_keys=True)
    summary["artifact_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    OBS_PATH.write_text(
        "".join(json.dumps(o, sort_keys=True) + "\n" for o in obs),
        encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("  ledger: %d/%d dry-slice runs complete, %d failed, "
          "%d remaining in slice, %d of %d total EXP-005 runs remain"
          % (counts["started"], DRY_SLICE, failed, counts["remaining_slice"],
             counts["remaining_total"], TOTAL_RUNS))
    print("  summary written:", (OUT_DIR / "summary.json").relative_to(PROJECT),
          "artifact_id", summary["artifact_id"][:16])
    print("  NO PERFORMANCE CONCLUSION DRAWN FROM THE 7-RUN SLICE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

