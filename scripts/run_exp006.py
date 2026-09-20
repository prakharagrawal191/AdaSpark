"""EXP-006 generalization runner - specification-driven, DEC-022 authorized.

Consumes the SEALED pre-execution specification (never reconstructs it):

    results/evaluation/exp006_spec.json
    fingerprint 0f078dc2f89b726ef80a58c3b7161ded9cc071dfe48a34266725fe9872b7eb54
    (queue c88ba20c... , selected cells 5fea06f2...)

Authorized scope (DEC-022, verified independently of the spec's own
``authorized_by`` field): 5 selected cells x applicable frozen arms x 5 reps =
105 executable Spark executions + 20 DEC-019-class undefined B2 x F4_ski rows =
125 ledger rows. B3 is analytic-only and is never queued. B2 x F4_ski is
undefined-by-design: 0 Spark, no fallback, no substitution.

Safety shape (DEC-013 Model B, mirroring scripts/run_exp005.py):
  * ``execute_run`` is called with THIS driver's purpose-scoped ``split_guard``
    only; the TEST seal (``assert_test_execution_permitted``) stays untouched.
  * The guard authorizes a cell ONLY if it is TEST and one of the 5 frozen
    selected cells. Every other cell is refused.
  * ``--dry-slice``/``--continue`` require ``--allow-spark``; ``--plan``
    executes 0 Spark runs and performs 0 writes.
  * No retry. Failures are first-class observations. No research logic:
    no ranking, no medians, no significance, no SC5 evaluation, no policy
    or configuration adaptation of any kind.

Modes:
  --plan        validate the whole sealed spec + authorization; print counts.
  --dry-slice   execute ONLY queue indices 1-7 (all executable by construction)
                into results/experiments/exp-006-dry-slice/ (DRY_SLICE_ONLY),
                isolated from the production ledger.
  --continue    resume append-only PRODUCTION execution at the first missing
                queue index into results/experiments/exp-006/observations.jsonl
                (the later, separately instructed execution task).

The dry slice is harness validation ONLY - it is NOT EXP-006 evidence.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.policy_store import (  # noqa: E402
    load_policy, policy_fingerprint, agent_from_artifact)
from sparkrl.evaluation.freeze import (manifest_fingerprint,  # noqa: E402
                                       verify_artifact)
from sparkrl.evaluation.spec import authorize_test_cell  # noqa: E402
from sparkrl.evaluation.strategies import (  # noqa: E402
    StrategyResolutionError, build_grid, resolve)
from sparkrl.experiments.grid import assert_b0_unchanged, b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import TEST, RunSpec  # noqa: E402
from sparkrl.rl.action import ActionMapper  # noqa: E402
from sparkrl.rl.state import StateEncoder  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.workloads.base import FAMILIES  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

PROTOCOL_VERSION = "exp006/v1"
EXPERIMENT_ID = "EXP-006"

SPEC_PATH = PROJECT / "results" / "evaluation" / "exp006_spec.json"
DECISIONS_PATH = PROJECT / "DECISIONS.md"
RL_ARMS_ARTIFACT = PROJECT / "models" / "policies" / "exp005_rl_arms.json"
B0_YAML = PROJECT / "configs" / "baseline_b0.yaml"

# Frozen identity (DEC-021 s.9 / DEC-022 s.2). The runner refuses any drift.
FROZEN_SPEC_FP = ("0f078dc2f89b726ef80a58c3b7161ded9cc071dfe48a34266725f"
                  "e9872b7eb54")
FROZEN_QUEUE_FP = ("c88ba20c75a0654a81c2113a83aefd119a19271985bdccabd4c7e"
                   "f44ec917d4c")
FROZEN_SELECTED_FP = ("5fea06f272345a9d7bb0e11aca9208c416dac4a1bb5a37581"
                      "976c1f149da17e5")

EXECUTABLE_ARMS = ("B0", "B2", "RL-s0", "RL-s1", "RL-s2")
RL_ARM_IDS = {"RL-s0", "RL-s1", "RL-s2"}
TOTAL_RUNS = 125
EXECUTABLE_RUNS = 105
UNDEFINED_RUNS = 20
REPETITIONS = 5
SELECTED_CELLS = 5
UNIVERSE_CELLS = 36
DRY_SLICE = 7  # DEC-022-approved dry slice: B0 reps 1-5 + B2 reps 1-2

DRY_DIR = PROJECT / "results" / "experiments" / "exp-006-dry-slice"
DRY_OBS = DRY_DIR / "observations.jsonl"
PROD_DIR = PROJECT / "results" / "experiments" / "exp-006"
PROD_OBS = PROD_DIR / "observations.jsonl"

DATASET_ID_RE = re.compile(r"skew[\d.]+_(large|medium|small)_s\d+\Z")


class SplitAuthorization(PermissionError):
    """Any cell outside the purpose-scoped EXP-006 authorization."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_dec022(text: str | None = None) -> dict[str, bool]:
    """Independent authorization check against DECISIONS.md (DEC-022).

    The sealed spec's ``authorized_by.execution_authorized=false`` is NOT the
    runtime authority; authorization comes from DEC-022, which must exist
    exactly once, name EXP-006, record APPROVED, and bind to the frozen
    specification fingerprint.
    """
    text = (text if text is not None
            else DECISIONS_PATH.read_text(encoding="utf-8"))
    entries = text.count("## DEC-022")
    if entries != 1:
        raise SystemExit(
            f"refusing: DEC-022 must appear exactly once in DECISIONS.md; "
            f"found {entries}")
    start = text.index("## DEC-022")
    nxt = text.find("\n## DEC-", start + 1)
    section = text[start:nxt if nxt != -1 else len(text)]
    checks = {
        "single_entry": entries == 1,
        "names_experiment": "EXP-006" in section,
        "approved": "EXP-006 execution authorization = APPROVED" in section,
        "fingerprint_bound": FROZEN_SPEC_FP in section,
    }
    if not all(checks.values()):
        raise SystemExit(
            f"refusing: DEC-022 authorization incomplete: "
            f"{[k for k, v in checks.items() if not v]}")
    return checks


def validate_spec(doc: dict[str, Any]) -> None:
    """Structural validation of the sealed EXP-006 specification.

    Raises SystemExit on any deviation from the frozen protocol shape:
    exp006/v1, 36-cell universe, 5 selected cells, 125 queue rows
    (105 executable + 20 undefined B2 x F4_ski), 5 reps, split=test,
    executable arms exactly {B0, B2, RL-s0, RL-s1, RL-s2}, B3 absent,
    no public/F5-unseen material.
    """
    if doc.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit(f"refusing: experiment_id {doc.get('experiment_id')!r}")
    if doc.get("protocol_version") != PROTOCOL_VERSION:
        raise SystemExit(
            f"refusing: protocol {doc.get('protocol_version')!r} != "
            f"{PROTOCOL_VERSION!r}")
    if doc.get("split") != "test":
        raise SystemExit("refusing: spec split is not 'test'")
    if doc.get("repetitions") != REPETITIONS:
        raise SystemExit(f"refusing: repetitions {doc.get('repetitions')!r}")

    uni = doc.get("candidate_universe") or {}
    if uni.get("remaining_count") != UNIVERSE_CELLS:
        raise SystemExit(
            f"refusing: candidate universe {uni.get('remaining_count')!r} != "
            f"{UNIVERSE_CELLS}")
    sel = doc.get("selected_cells") or {}
    cells = sel.get("cells") or []
    if sel.get("count") != SELECTED_CELLS or len(cells) != SELECTED_CELLS:
        raise SystemExit(
            f"refusing: selected cells {sel.get('count')} != {SELECTED_CELLS}")
    selkeys = set()
    for c in cells:
        if c.get("split") != "test":
            raise SystemExit(f"refusing: selected cell {c} is not split=test")
        key = (c["family"], c["scale"], int(c["seed"]))
        if key in selkeys:
            raise SystemExit(f"refusing: duplicate selected cell {key}")
        selkeys.add(key)
        if c["family"] not in FAMILIES:
            raise SystemExit(
                f"refusing: unknown family {c['family']!r} (no invented "
                f"families/material permitted)")
        if not DATASET_ID_RE.fullmatch(c.get("dataset_id", "")):
            raise SystemExit(
                f"refusing: dataset_id {c.get('dataset_id')!r} is not a "
                f"frozen synthetic generator identity (public/F5-unseen "
                f"material is forbidden)")

    q = doc.get("queue") or {}
    rows = q.get("rows") or []
    if q.get("count") != TOTAL_RUNS or len(rows) != TOTAL_RUNS:
        raise SystemExit(
            f"refusing: queue count {q.get('count')}/{len(rows)} != {TOTAL_RUNS}")
    idx = [r.get("queue_index") for r in rows]
    if idx != list(range(1, TOTAL_RUNS + 1)):
        raise SystemExit(
            "refusing: queue indices are not exactly 1..125 contiguous "
            "(duplicate or missing index)")
    if any(r.get("split") != "test" for r in rows):
        raise SystemExit("refusing: a queue row is not split=test")
    if any(r.get("rep") not in range(1, REPETITIONS + 1) for r in rows):
        raise SystemExit("refusing: a queue row has rep outside 1..5")
    arms = sorted({r.get("arm") for r in rows})
    if arms != sorted(EXECUTABLE_ARMS):
        raise SystemExit(
            f"refusing: queue arms {arms} != {sorted(EXECUTABLE_ARMS)} "
            f"(B3 must be absent; RL seeds distinct)")
    ex = [r for r in rows if r.get("executable")]
    un = [r for r in rows if not r.get("executable")]
    if len(ex) != EXECUTABLE_RUNS or len(un) != UNDEFINED_RUNS:
        raise SystemExit(
            f"refusing: executable/undefined {len(ex)}/{len(un)} != "
            f"{EXECUTABLE_RUNS}/{UNDEFINED_RUNS}")
    for r in un:
        if r["arm"] != "B2" or r["family"] != "F4_ski":
            raise SystemExit(
                f"refusing: undefined row {r['queue_index']} is not B2 x F4_ski")
        if (r.get("identity") or {}).get("kind") != "undefined":
            raise SystemExit(
                f"refusing: undefined row {r['queue_index']} has a resolvable "
                f"identity kind {(r.get('identity') or {}).get('kind')!r}")
    for r in ex:
        kind = (r.get("identity") or {}).get("kind")
        if kind not in ("config", "policy"):
            raise SystemExit(
                f"refusing: executable row {r['queue_index']} has identity "
                f"kind {kind!r}")
        if r["arm"] == "B2" and r["family"] == "F4_ski":
            raise SystemExit(
                f"refusing: B2 x F4_ski row {r['queue_index']} is executable "
                f"(DEC-019 violation)")
        if (r["family"], r["scale"], int(r["dataset_seed"])) not in selkeys:
            raise SystemExit(
                f"refusing: row {r['queue_index']} is not one of the 5 "
                f"selected cells")
    per_cell = Counter((r["family"], r["scale"], int(r["dataset_seed"]),
                        r["arm"]) for r in rows)
    for c in cells:
        cell_arms = ["B0", "RL-s0", "RL-s1", "RL-s2"]
        if c["family"] != "F4_ski":
            cell_arms.append("B2")
        for a in cell_arms:
            if per_cell[(c["family"], c["scale"], int(c["seed"]), a)] != REPETITIONS:
                raise SystemExit(
                    f"refusing: cell {c} arm {a} does not have exactly "
                    f"{REPETITIONS} repetitions")

    arms_doc = doc.get("arms") or {}
    if sorted(arms_doc.get("executable") or []) != sorted(EXECUTABLE_ARMS):
        raise SystemExit("refusing: spec executable-arm list drifted")
    if "B3" in (arms_doc.get("executable") or []):
        raise SystemExit("refusing: B3 must never be an executable arm")
    if (arms_doc.get("identities") or {}).get("B2", {}).get(
            "undefined_on") != ["F4_ski"]:
        raise SystemExit("refusing: B2 undefined_on drifted from ['F4_ski']")
    if "analytic-only" not in str(arms_doc.get("b3", "")):
        raise SystemExit("refusing: B3 analytic-only statement missing")


def verify_sealed_spec(path: Path | None = None) -> dict[str, Any]:
    """Load and fully verify the sealed specification; return the document."""
    path = path or SPEC_PATH
    if not path.exists():
        raise SystemExit(f"refusing: sealed specification missing: {path}")
    try:
        verify_artifact(path)
    except Exception as exc:  # noqa: BLE001 - any seal failure is fatal
        raise SystemExit(
            f"refusing: specification seal verification failed: {exc}") from exc
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("artifact_id") != FROZEN_SPEC_FP:
        raise SystemExit(
            f"refusing: spec fingerprint {doc.get('artifact_id')} != frozen "
            f"{FROZEN_SPEC_FP}")
    fps = doc.get("fingerprints") or {}
    if fps.get("queue") != FROZEN_QUEUE_FP:
        raise SystemExit("refusing: queue fingerprint drifted from DEC-022")
    if fps.get("selected_cells") != FROZEN_SELECTED_FP:
        raise SystemExit("refusing: selected-cells fingerprint drifted")
    validate_spec(doc)
    # Content-level tamper detection: the stored fingerprints must reproduce
    # from the actual rows/cells (catches structural edits that keep counts).
    qfp = hashlib.sha256(json.dumps(
        doc["queue"]["rows"], sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()
    if qfp != doc["fingerprints"]["queue"]:
        raise SystemExit(
            "refusing: queue rows do not reproduce the sealed queue "
            "fingerprint (content tampering)")
    sfp = manifest_fingerprint(
        [{"family": c["family"], "scale": c["scale"], "seed": c["seed"]}
         for c in doc["selected_cells"]["cells"]])
    if sfp != doc["fingerprints"]["selected_cells"]:
        raise SystemExit(
            "refusing: selected cells do not reproduce the sealed "
            "selected-cells fingerprint (content tampering)")
    return doc


def exp006_test_guard(family: str, scale: str, seed: int,
                      frozen: set[tuple[str, str, int]]) -> None:
    """The ONLY split_guard used by this driver (DEC-013 Model B).

    TEST is authorized exclusively through this purpose-scoped path and
    exclusively for the 5 frozen selected cells. The TEST seal
    (``assert_test_execution_permitted``) is NOT modified.
    """
    authorize_test_cell(family, scale, seed, stage="EXP-006 test evaluation")
    if (family, scale, seed) not in frozen:
        raise SplitAuthorization(
            f"{family}/{scale}/seed{seed} is TEST but is NOT one of the 5 "
            "frozen EXP-006 selected cells; executing it is unauthorized")


def resolve_static_arm(arm: str, family: str, scale: str, dataset_seed: int,
                       base: SparkConfig, identity: dict[str, Any]
                       ) -> tuple[Any, str, dict[str, Any]]:
    """Frozen static arm -> (ConfigPoint, describe, provenance); drift-checked
    against the sealed spec identity. No dynamics."""
    rs = resolve(arm, family=family, scale=scale, dataset_seed=dataset_seed,
                 base_config=base)
    if rs.config_fingerprint != identity.get("config_fingerprint"):
        raise SystemExit(
            f"refusing: {arm} resolved fingerprint {rs.config_fingerprint} "
            f"!= sealed identity {identity.get('config_fingerprint')}")
    if rs.config_name != identity.get("config_name"):
        raise SystemExit(
            f"refusing: {arm} resolved config {rs.config_name!r} != sealed "
            f"identity {identity.get('config_name')!r}")
    if arm == "B0":
        point = b0_point()
    else:
        matches = [p for p in build_grid(include_b0=True)
                   if p.name == rs.config_name]
        if len(matches) != 1:
            raise SystemExit(
                f"refusing: {arm} resolved to unknown config {rs.config_name!r}")
        point = matches[0]
        applied = point.apply_to(base)
        if applied.fingerprint() != rs.config.fingerprint():
            raise SystemExit(
                f"refusing: {arm} grid point {point.name} applied to base "
                f"({applied.fingerprint()}) != resolved "
                f"({rs.config.fingerprint()})")
    prov = {"decision": "DEC-021 s.6 / DEC-022 (frozen arm identities)",
            "spec_fingerprint": FROZEN_SPEC_FP,
            "strategy_describe": rs.describe}
    return point, rs.describe, prov


def resolve_rl_arm(arm: str, arm_entry: dict[str, Any], family: str,
                   scale: str, dataset_seed: int, base: SparkConfig,
                   identity: dict[str, Any]
                   ) -> tuple[Any, int, tuple, str, dict[str, Any]]:
    """Frozen RL arm -> (ConfigPoint, greedy_action, state_key, describe, prov).

    Uses the frozen agent machinery itself (agent_from_artifact +
    select_action(epsilon=0.0)); no Q update, no exploration, no adaptation.
    """
    if identity.get("policy_id") != arm_entry["policy_id"]:
        raise SystemExit(
            f"refusing: {arm} sealed policy_id {identity.get('policy_id')} != "
            f"manifest {arm_entry['policy_id']}")
    art = load_policy(arm_entry["policy_id"], PROJECT / "models" / "policies")
    fp = policy_fingerprint(art)
    if fp != arm_entry["policy_id"]:
        raise SystemExit(
            f"refusing: {arm} artifact fingerprint {fp} != frozen policy_id "
            f"{arm_entry['policy_id']}")
    if art["learner_config"]["gamma"] != 0.0:
        raise SystemExit("refusing: RL arm artifact gamma != 0.0 (bandit frozen)")
    agent = agent_from_artifact(art)
    res = resolve_dataset(family, scale, dataset_seed)
    input_bytes = (int(res.orders_manifest["total_bytes"])
                   + int(res.lineitem_manifest["total_bytes"]))
    state = StateEncoder().encode(family, input_bytes, last_reward=None)
    action = agent.select_action(state, epsilon=0.0)
    cfg, point, _ = ActionMapper().to_config(action, base)
    prov = {"decision": "DEC-021 s.6 / DEC-022 (frozen policy, greedy)",
            "spec_fingerprint": FROZEN_SPEC_FP,
            "policy_id": arm_entry["policy_id"], "policy_fingerprint": fp,
            "agent_rng_seed": arm_entry["agent_rng_seed"],
            "episodes": arm_entry["episodes"], "updates": arm_entry["updates"]}
    return point, action, state.key(), (
        f"greedy action {action} via frozen policy "
        f"{arm_entry['policy_id'][:12]}"), prov


UNDEFINED_ERROR = (
    "INCOMPLETE (DEC-019 Option A / DEC-022 scope): B2 is per-family static "
    "tuned on VALIDATION, which contains only {F1_agg, F2_join, F3_rdd, "
    "F5_mixed}; F4_ski is the deliberately unseen TEST family (PLAN section "
    "18), so B2 has no frozen configuration for it. No Spark execution, no "
    "fallback (explicitly not B1), no substitution, no TEST tuning; queue "
    "entry preserved for accounting.")


def run_id_of(entry: dict[str, Any]) -> str:
    return ("exp006-%s-%s-s%d-%s-r%d"
            % (entry["family"], entry["scale"], entry["dataset_seed"],
               entry["arm"], entry["rep"])).replace("_", "-").lower()


def undefined_row(entry: dict[str, Any]) -> dict[str, Any]:
    """The DEC-019-class row for B2 x F4_ski: 0 Spark, null config/runtime."""
    return {
        "run_id": run_id_of(entry), "queue_index": entry["queue_index"],
        "arm": entry["arm"], "family": entry["family"],
        "scale": entry["scale"], "seed": entry["dataset_seed"],
        "rep": entry["rep"], "split": TEST,
        "config_name": None, "config_fingerprint": None,
        "rl_action": None, "rl_state_key": None,
        "arm_provenance": {
            "decision": "DEC-019 Option A / DEC-022 s.5 (undefined-by-design)",
            "status": "INCOMPLETE-undefined",
            "spec_fingerprint": FROZEN_SPEC_FP,
            "strategy_version": "exp006-strategies/v1",
        },
        "undefined": True,
        "usable": False, "timeout": False,
        "execution_time_s": None, "execution_time_source": None,
        "error": UNDEFINED_ERROR,
        "config_fingerprint_applied": None,
        "dataset_fingerprint": None,
        "event_log_status": "NOT_EXECUTED",
        "protocol_version": PROTOCOL_VERSION,
    }


def append_observation(path: Path, row: dict[str, Any]) -> None:
    """Append one observation durably: write, flush, fsync. Append-only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as sink:
        sink.write(json.dumps(row, sort_keys=True) + "\n")
        sink.flush()
        os.fsync(sink.fileno())


def load_observations(path: Path) -> dict[int, dict[str, Any]]:
    """Existing observations keyed by queue_index; duplicates are fatal."""
    done: dict[int, dict[str, Any]] = {}
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        idx = o["queue_index"]
        if idx in done:
            raise SystemExit(
                f"refusing: duplicate queue_index {idx} already on disk in "
                f"{path}")
        done[idx] = o
    return done


def resume_indices(entries: list[dict[str, Any]], done: dict[int, Any]
                   ) -> list[dict[str, Any]]:
    """Entries whose queue_index is missing from ``done`` (append-only resume)."""
    return [e for e in entries if e["queue_index"] not in done]


def run_entries(entries: list[dict[str, Any]], obs_path: Path,
                base: SparkConfig, rl_by_arm: dict[str, Any],
                identities: dict[str, Any], b2_map: dict[str, Any],
                frozen: set[tuple[str, str, int]],
                execute_fn: Callable | None = None,
                block: str = "exp006-main") -> dict[str, int]:
    """Execute queue entries append-only; failures are first-class.

    Undefined B2 x F4_ski rows are written with 0 Spark and the run continues.
    Real Spark failures are recorded verbatim (no retry, no imputation, no
    conversion into undefined rows). Every durable write is fsynced.

    ``execute_fn`` defaults to the frozen ``execute_run`` resolved at CALL
    time (not def time) so tests can substitute a fake without Spark.
    """
    if execute_fn is None:
        execute_fn = globals()["execute_run"]
    guard = functools.partial(exp006_test_guard, frozen=frozen)
    counts = {"spark_attempted": 0, "usable": 0, "failed": 0, "undefined": 0}
    for e in entries:
        arm = e["arm"]
        key = (e["family"], e["scale"], e["dataset_seed"])
        if not e["executable"]:
            append_observation(obs_path, undefined_row(e))
            counts["undefined"] += 1
            print("  [%d/125] %-6s %-22s rep%d -> INCOMPLETE (B2 undefined on "
                  "F4_ski, DEC-019/DEC-022; 0 Spark)"
                  % (e["queue_index"], arm, "%s|%s|s%d" % key, e["rep"]),
                  flush=True)
            continue
        ident = per_row_identity(e, identities, b2_map)
        try:
            if arm in RL_ARM_IDS:
                point, action, skey, _d, prov = resolve_rl_arm(
                    arm, rl_by_arm[arm], *key, base, ident)
            else:
                point, _d, prov = resolve_static_arm(arm, *key, base, ident)
                action, skey = None, None
        except StrategyResolutionError as exc:
            raise SystemExit(
                f"refusing at queue index {e['queue_index']} ({arm} x "
                f"{key[0]}|{key[1]}|s{key[2]}): {exc}. B2 x F4_ski is the only "
                f"authorized undefined case; any other resolution gap stops "
                f"execution.") from exc
        run_spec = RunSpec(
            run_id=run_id_of(e), family=e["family"], scale=e["scale"],
            seed=e["dataset_seed"], rep=e["rep"], config=point, split=TEST,
            timeout_seconds=float(base.timeout_seconds),
            order_index=e["queue_index"] - 1, block_id=block)
        counts["spark_attempted"] += 1
        try:
            metrics, _p = execute_fn(run_spec, base, split_guard=guard)
            usable = bool(metrics.usable) and not metrics.timeout
            row = observation_row(e, arm, point, action, skey, prov, usable,
                                  metrics)
        except Exception as exc:  # noqa: BLE001 - durable first-class failure
            row = observation_row(e, arm, point, action, skey, prov, False,
                                  None, crash=f"{type(exc).__name__}: {exc}")
        append_observation(obs_path, row)
        counts["usable" if row["usable"] else "failed"] += 1
        print("  [%d/125] %-6s %-22s rep%d -> %-12s usable=%-5s %s"
              % (e["queue_index"], arm, "%s|%s|s%d" % key, e["rep"],
                 point.name, row["usable"],
                 ("%.4fs" % row["execution_time_s"])
                 if row["execution_time_s"] else "-"), flush=True)
    return counts


def observation_row(entry: dict[str, Any], arm: str, point: Any,
                    action: int | None, skey: tuple | None,
                    prov: dict[str, Any], usable: bool, metrics: Any,
                    crash: str | None = None) -> dict[str, Any]:
    """One production-shape observation (EXP-005 row schema + EXP-006 refs)."""
    if metrics is not None:
        exec_s = metrics.execution_time_s
        exec_src = metrics.execution_time_source
        applied = metrics.config_fingerprint
        ds_fp = metrics.dataset_fingerprint
        ev = metrics.event_log_status
        err = metrics.error
        timeout = bool(metrics.timeout)
    else:  # orchestration-level crash: durable first-class failure, no Spark data
        exec_s = exec_src = applied = ds_fp = err = None
        ev = "MISSING"
        timeout = False
        err = crash
    return {
        "run_id": run_id_of(entry), "queue_index": entry["queue_index"],
        "arm": arm, "family": entry["family"], "scale": entry["scale"],
        "seed": entry["dataset_seed"], "rep": entry["rep"], "split": TEST,
        "config_name": point.name,
        "config_fingerprint": point.fingerprint(),
        "rl_action": action,
        "rl_state_key": list(skey) if skey else None,
        "arm_provenance": prov,
        "undefined": False,
        "usable": usable, "timeout": timeout,
        "execution_time_s": exec_s, "execution_time_source": exec_src,
        "error": err,
        "config_fingerprint_applied": applied,
        "dataset_fingerprint": ds_fp,
        "event_log_status": ev,
        "protocol_version": PROTOCOL_VERSION,
    }


def verify_configs(doc: dict[str, Any]) -> SparkConfig:
    """Frozen B0/B2 configuration guard; returns the base config.

    B2 on F4_ski MUST be unresolvable: if it resolves to anything executable,
    the runner stops (DEC-019/DEC-022 violation).
    """
    base = SparkConfig.from_yaml(B0_YAML)
    assert_b0_unchanged(base)
    ident = doc["arms"]["identities"]
    if resolve("B0", family="F1_agg", scale="large",
               dataset_seed=0).config_fingerprint != \
            ident["B0"]["config_fingerprint"]:
        raise SystemExit("refusing: frozen B0 configuration drifted")
    b2_map = ident["B2"]["by_family"]
    for family, entry in b2_map.items():
        rs = resolve("B2", family=family, scale="large", dataset_seed=3)
        if rs.config_name != entry["config_name"] or \
                rs.config_fingerprint != entry["config_fingerprint"]:
            raise SystemExit(
                f"refusing: frozen B2 configuration for {family} drifted")
    if "F4_ski" in b2_map:
        raise SystemExit("refusing: B2 gained an F4_ski configuration")
    try:
        resolve("B2", family="F4_ski", scale="large", dataset_seed=0)
    except StrategyResolutionError:
        return base
    raise SystemExit(
        "refusing: B2 x F4_ski resolved to an executable configuration; "
        "DEC-019/DEC-022 forbid any B2 configuration on the unseen family")


def verify_policies(doc: dict[str, Any]) -> str:
    """Frozen RL policy guard; returns the manifest fingerprint."""
    manifest = json.loads(RL_ARMS_ARTIFACT.read_text(encoding="utf-8"))
    by_arm = {a["arm"]: a for a in manifest["arms"]}
    if sorted(by_arm) != sorted(RL_ARM_IDS):
        raise SystemExit(f"refusing: RL manifest arms {sorted(by_arm)}")
    rl_ids = doc["arms"]["identities"]["RL"]["arms"]
    for arm in sorted(RL_ARM_IDS):
        entry = by_arm[arm]
        art = load_policy(entry["policy_id"], PROJECT / "models" / "policies")
        if policy_fingerprint(art) != entry["policy_id"]:
            raise SystemExit(f"refusing: {arm} policy artifact drifted")
        if rl_ids[arm]["policy_id"] != entry["policy_id"]:
            raise SystemExit(f"refusing: {arm} sealed policy_id drifted")
        if rl_ids[arm]["agent_rng_seed"] != entry["agent_rng_seed"]:
            raise SystemExit(f"refusing: {arm} sealed rng seed drifted")
    return manifest["fingerprint"]


def verify_datasets(doc: dict[str, Any]) -> None:
    """Dataset identity guard: every selected cell's frozen dataset exists
    with the exact sealed fingerprints. Never substitutes a dataset."""
    for c in doc["selected_cells"]["cells"]:
        res = resolve_dataset(c["family"], c["scale"], int(c["seed"]))
        if res.dataset_id != c["dataset_id"]:
            raise SystemExit(
                f"refusing: dataset id drift for {c['dataset_id']}: "
                f"resolved {res.dataset_id}")
        if res.dataset_fingerprint != c["dataset_fingerprint"]:
            raise SystemExit(
                f"refusing: dataset fingerprint drift for {c['dataset_id']}")
        if not res.schema_fingerprint.startswith(c["schema_fingerprint"]):
            raise SystemExit(
                f"refusing: schema fingerprint drift for {c['dataset_id']}")


def preflight() -> tuple[dict[str, Any], SparkConfig, dict[str, Any],
                         dict[str, Any], dict[str, Any],
                         set[tuple[str, str, int]]]:
    """Full guard chain: sealed spec + DEC-022 + configs + policies + datasets."""
    doc = verify_sealed_spec()
    verify_dec022()
    base = verify_configs(doc)
    verify_policies(doc)
    verify_datasets(doc)
    rl_by_arm = {a["arm"]: a for a in json.loads(
        RL_ARMS_ARTIFACT.read_text(encoding="utf-8"))["arms"]}
    rl_ids = doc["arms"]["identities"]["RL"]["arms"]
    identities = {"B0": doc["arms"]["identities"]["B0"],
                  "B2": None,
                  "RL-s0": rl_ids["RL-s0"],
                  "RL-s1": rl_ids["RL-s1"],
                  "RL-s2": rl_ids["RL-s2"]}
    b2_map = doc["arms"]["identities"]["B2"]["by_family"]
    frozen = {(c["family"], c["scale"], int(c["seed"]))
              for c in doc["selected_cells"]["cells"]}
    return doc, base, rl_by_arm, identities, b2_map, frozen


def per_row_identity(entry: dict[str, Any], identities: dict[str, Any],
                     b2_map: dict[str, Any]) -> dict[str, Any]:
    """The frozen identity applying to one queue row."""
    if entry["arm"] == "B2":
        return b2_map[entry["family"]]
    return identities[entry["arm"]]


def print_plan(doc: dict[str, Any], auth: dict[str, bool]) -> None:
    rows = doc["queue"]["rows"]
    un_cells = sorted({(r["family"], r["scale"], r["dataset_seed"])
                       for r in rows if not r["executable"]})
    print("EXP-006 plan (spec-driven; DEC-022 authorized)")
    print("  spec fp:", doc["artifact_id"])
    print("  queue fp:", doc["fingerprints"]["queue"])
    print("  DEC-022:", auth)
    print("  universe %d cells; selected %d; queue %d rows (%d executable + "
          "%d undefined); reps %d"
          % (doc["candidate_universe"]["remaining_count"],
             doc["selected_cells"]["count"], len(rows),
             sum(1 for r in rows if r["executable"]),
             sum(1 for r in rows if not r["executable"]),
             doc["repetitions"]))
    print("  arms:", ", ".join(doc["arms"]["executable"]),
          "| B3: analytic-only, never queued")
    print("  undefined B2 x F4_ski blocks:",
          "; ".join("%s|%s|s%d" % c for c in un_cells))
    for r in rows[:DRY_SLICE]:
        print("    %3d. %-6s %-22s rep%d (%s)"
              % (r["queue_index"], r["arm"],
                 "%s|%s|s%d" % (r["family"], r["scale"], r["dataset_seed"]),
                 r["rep"], r["identity"]["kind"]))


def dry_slice() -> int:
    """The authorized 7-row dry slice, isolated from production evidence."""
    doc, base, rl_by_arm, identities, b2_map, frozen = preflight()
    rows = doc["queue"]["rows"]
    entries = rows[:DRY_SLICE]
    if any(not e["executable"] for e in entries):
        raise SystemExit(
            "refusing: dry slice must consist of executable rows only")
    composition = Counter((e["arm"], e["rep"]) for e in entries)
    expected = Counter([("B0", r) for r in range(1, 6)]
                       + [("B2", 1), ("B2", 2)])
    if composition != expected:
        raise SystemExit(
            "refusing: dry slice is not B0 reps 1-5 + B2 reps 1-2 "
            f"(got {sorted(composition)})")
    done = load_observations(DRY_OBS)
    todo = resume_indices(entries, done)
    if len(done) > DRY_SLICE:
        raise SystemExit("refusing: dry-slice ledger exceeds 7 rows")
    if not todo:
        print("  dry slice already complete: %d/7 rows on disk" % len(done))
        return 0
    DRY_DIR.mkdir(parents=True, exist_ok=True)
    marker = DRY_DIR / "DRY_SLICE_ONLY"
    marker.write_text(json.dumps({
        "marker": "DRY_SLICE_ONLY",
        "experiment": EXPERIMENT_ID,
        "purpose": ("harness validation only; NOT EXP-006 evidence; no "
                    "performance conclusion permitted"),
        "spec_fingerprint": doc["artifact_id"],
        "queue_fingerprint": doc["fingerprints"]["queue"],
        "queue_indices": [1, DRY_SLICE],
        "production_ledger": "results/experiments/exp-006/observations.jsonl",
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("EXP-006 dry slice (indices 1-7; harness validation only)")
    counts = run_entries(todo, DRY_OBS, base, rl_by_arm, identities, b2_map,
                         frozen, block="exp006-dry-slice")
    obs = [json.loads(l) for l in
           DRY_OBS.read_text(encoding="utf-8").splitlines() if l.strip()]
    summary = {
        "experiment_id": EXPERIMENT_ID, "stage": "dry-slice (7 of 125)",
        "protocol_version": PROTOCOL_VERSION,
        "dry_slice_only": True,
        "spec_fingerprint": doc["artifact_id"],
        "queue_fingerprint": doc["fingerprints"]["queue"],
        "counts": {"planned": DRY_SLICE, "recorded": len(obs),
                   "spark_attempted": counts["spark_attempted"],
                   "usable": sum(1 for o in obs if o["usable"]),
                   "failed": sum(1 for o in obs if not o["usable"]),
                   "undefined": sum(1 for o in obs if o.get("undefined"))},
        "no_analysis_rule": ("the dry slice ranks nothing; no significance "
                             "test, no winner selection, no retuning, no "
                             "queue alteration; NOT EXP-006 evidence"),
        "production_ledger_status": ("not created by this dry slice; full "
                                     "queue execution is a separate task"),
    }
    summary["artifact_id"] = hashlib.sha256(json.dumps(
        {**summary, "observations": obs}, sort_keys=True).encode(
            "utf-8")).hexdigest()
    (DRY_DIR / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("  dry ledger: %d/7 rows, summary artifact_id %s"
          % (len(obs), summary["artifact_id"][:16]))
    print("  NO PERFORMANCE CONCLUSION DRAWN FROM THE DRY SLICE.")
    return 0


def continue_run() -> int:
    """Production execution: resume append-only at the first missing index."""
    doc, base, rl_by_arm, identities, b2_map, frozen = preflight()
    rows = doc["queue"]["rows"]
    done = load_observations(PROD_OBS)
    todo = resume_indices(rows, done)
    print("EXP-006 production continuation")
    print("  queue verified against sealed spec: %d entries" % len(rows))
    print("  already recorded: %d; to execute: %d (next index %s)"
          % (len(done), len(todo), todo[0]["queue_index"] if todo else "-"))
    if not todo:
        print("  nothing to do: all %d entries accounted for." % TOTAL_RUNS)
        return 0
    counts = run_entries(todo, PROD_OBS, base, rl_by_arm, identities, b2_map,
                         frozen, block="exp006-main")
    obs = [json.loads(l) for l in
           PROD_OBS.read_text(encoding="utf-8").splitlines() if l.strip()]
    full = {"planned": TOTAL_RUNS, "recorded": len(obs),
            "usable": sum(1 for o in obs if o["usable"]),
            "failed": sum(1 for o in obs if not o["usable"]),
            "undefined": sum(1 for o in obs if o.get("undefined")),
            "remaining": TOTAL_RUNS - len(obs)}
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "stage": ("complete (125 of 125)" if not full["remaining"]
                  else "partial (%d of 125)" % len(obs)),
        "protocol_version": PROTOCOL_VERSION,
        "spec_fingerprint": doc["artifact_id"],
        "queue_fingerprint": doc["fingerprints"]["queue"],
        "authorized_by": "DEC-022",
        "counts": full,
        "no_analysis_rule": ("the runner records execution evidence only; no "
                             "ranking, medians, significance, SC5 evaluation, "
                             "or seed selection"),
    }
    summary["artifact_id"] = hashlib.sha256(json.dumps(
        {**summary, "observations": obs}, sort_keys=True).encode(
            "utf-8")).hexdigest()
    (PROD_DIR / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("  executed this pass: %d Spark, %d undefined rows (0 Spark)"
          % (counts["spark_attempted"], counts["undefined"]))
    print("  ledger: %d/125 accounted for, %d usable, %d failed (incl. "
          "%d undefined INCOMPLETE), %d remaining"
          % (full["recorded"], full["usable"], full["failed"],
             full["undefined"], full["remaining"]))
    print("  NO STATISTICAL / PERFORMANCE CONCLUSION DRAWN DURING EXECUTION.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true",
                    help="validate the sealed spec + authorization; 0 Spark, "
                         "0 writes")
    ap.add_argument("--dry-slice", action="store_true",
                    help="execute ONLY queue indices 1-7 into the isolated "
                         "exp-006-dry-slice directory")
    ap.add_argument("--continue", dest="continue_run", action="store_true",
                    help="PRODUCTION mode: resume append-only execution of "
                         "the full frozen queue")
    ap.add_argument("--allow-spark", action="store_true",
                    help="required with --dry-slice/--continue; explicit "
                         "Spark acknowledgement")
    args = ap.parse_args()
    modes = [args.plan, args.dry_slice, args.continue_run]
    if sum(bool(m) for m in modes) != 1:
        ap.error("pass exactly one of --plan, --dry-slice, --continue")
    if (args.dry_slice or args.continue_run) and not args.allow_spark:
        ap.error("--dry-slice/--continue require --allow-spark")
    if args.plan:
        doc = verify_sealed_spec()
        print_plan(doc, verify_dec022())
        verify_configs(doc)
        verify_policies(doc)
        verify_datasets(doc)
        print("  preflight: configs, policies, datasets all verified")
        print("  PLAN MODE: 0 Spark runs, 0 writes.")
        return 0
    if args.dry_slice:
        return dry_slice()
    return continue_run()


if __name__ == "__main__":
    raise SystemExit(main())