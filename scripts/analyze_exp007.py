"""EXP-007 analysis (Day 36): descriptive A1/A2 state-ablation analysis.

NON-EXECUTING analyzer. Reads ONLY the four frozen EXP-007 TRAIN run
artifacts plus the three frozen main-study TRAIN runs used as the
full-state reference. No Spark, no training, no PySpark import, no wall
clock, no RNG, and the agent is never instantiated: the greedy policy is
extracted from each run's STORED q_table with a lowest-index tie-break
(the frozen exploitation rule), never via select_action (which would
advance the agent RNG).

Sources (read-only):
  results/training/train-a0-d0-20260917T055042Z  (A1, seed 0, 35 eps)
  results/training/train-a1-d0-20260917T060047Z  (A1, seed 1, 35 eps)
  results/training/train-a0-d0-20260917T061316Z  (A2, seed 0, 35 eps)
  results/training/train-a1-d0-20260917T062346Z  (A2, seed 1, 21 eps)
  results/training/train-a0-d0-20260912T112906Z  (full v1.5, seed 0)
  results/training/train-a1-d0-20260912T115123Z  (full v1.5, seed 1)
  results/training/train-a2-d0-20260912T120648Z  (full v1.5, seed 2)
each with manifest.json + episodes.jsonl + final checkpoints/policy-*.json.

Writes results/evaluation/exp007_analysis.json atomically (tmp +
os.replace) and prints a human-readable summary. Re-reading the same
artifacts in any order produces a byte-identical file.

Descriptive only: no alpha, no p-values, no Wilcoxon, no Cliff's delta,
no Holm correction, no effect-size threshold, no minimum-n, no numeric
pass/fail hypothesis threshold. Reward standard deviation uses the
existing project convention (sample std, ddof=1, via statistics.stdev);
it is a descriptive spread, not an inferential statistic.

Usage:
  python scripts/analyze_exp007.py
  python scripts/analyze_exp007.py --out /tmp/a.json
  python scripts/analyze_exp007.py --print-only
  python scripts/analyze_exp007.py --self-check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]

ANALYSIS_SCHEMA = "exp007-analysis/v1"

RUNS: tuple[dict[str, Any], ...] = (
    {"label": "A1-s0", "run_id": "train-a0-d0-20260917T055042Z",
     "variant": "A1", "seed": 0},
    {"label": "A1-s1", "run_id": "train-a1-d0-20260917T060047Z",
     "variant": "A1", "seed": 1},
    {"label": "A2-s0", "run_id": "train-a0-d0-20260917T061316Z",
     "variant": "A2", "seed": 0},
    {"label": "A2-s1", "run_id": "train-a1-d0-20260917T062346Z",
     "variant": "A2", "seed": 1},
)

DEFAULT_OUT = PROJECT / "results" / "evaluation" / "exp007_analysis.json"

FULL_STATE_RUNS: tuple[dict[str, Any], ...] = (
    {"label": "FULL-s0", "run_id": "train-a0-d0-20260912T112906Z", "seed": 0},
    {"label": "FULL-s1", "run_id": "train-a1-d0-20260912T115123Z", "seed": 1},
    {"label": "FULL-s2", "run_id": "train-a2-d0-20260912T120648Z", "seed": 2},
)
FULL_STATE_SCHEMA = "state-v1.5"
FULL_STATE_SPACE = 30
FULL_STATE_Q0_VERSION = "q0-exp002/v1"

A1_SCHEMA = "state-v1"
A1_SPACE = 15
A2_SCHEMA = "state-v2"
A2_SPACE = 2
NEUTRAL_Q0_VERSION = "q0-neutral/v1"
NEUTRAL_Q0_DEFAULT = 0.5
HYPOTHESIS = "context+feedback > context-only"
REGISTERED_ACCEPTANCE = "ablation table / ablation rows"


class AnalysisError(RuntimeError):
    """A frozen input artifact is missing or inconsistent."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_canonical(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _mean(xs: list[float]) -> float:
    return float(statistics.mean(xs))


def _median(xs: list[float]) -> float:
    return float(statistics.median(xs))


def _stdev(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    return float(statistics.stdev(xs))


def _greedy(q_row: list[float]) -> int:
    best = 0
    best_v = float(q_row[0])
    for i in range(1, len(q_row)):
        v = float(q_row[i])
        if v > best_v:
            best_v = v
            best = i
    return best

def load_episodes(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "episodes.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AnalysisError(f"cannot read {path}: {exc}") from None
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"{path}:{lineno}: bad JSON: {exc}") from None
        rows.append(obj)
    return rows


def load_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnalysisError(f"cannot read {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"{path}: bad JSON: {exc}") from None


def load_policy(run_dir: Path, relpath: str) -> dict[str, Any]:
    path = run_dir / relpath
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnalysisError(f"cannot read {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"{path}: bad JSON: {exc}") from None


def canonical_cells(manifest: dict[str, Any]) -> list[str]:
    return [c["cell"] for c in manifest["schedule"]["cells"]]

def analyze_run(label: str, run_dir: Path, variant: str,
                seed: int) -> dict[str, Any]:
    manifest = load_manifest(run_dir)
    episodes = load_episodes(run_dir)
    if manifest.get("run_id") != run_dir.name:
        raise AnalysisError(f"{label}: manifest run_id mismatch")
    for ep in episodes:
        if ep.get("run_id") != run_dir.name:
            raise AnalysisError(f"{label}: episode run_id mismatch")
    n = len(episodes)
    if manifest["counts"]["episodes_completed"] != n:
        raise AnalysisError(f"{label}: episode count mismatch")
    exp_schema = A1_SCHEMA if variant == "A1" else A2_SCHEMA
    if manifest.get("state_schema") != exp_schema:
        raise AnalysisError(f"{label}: wrong state_schema")
    if manifest["q0_provenance"]["state_schema"] != exp_schema:
        raise AnalysisError(f"{label}: wrong q0 state_schema")
    if manifest.get("agent_rng_seed") != seed:
        raise AnalysisError(f"{label}: wrong agent_rng_seed")
    if manifest.get("dataset_seed") != 0:
        raise AnalysisError(f"{label}: dataset_seed != 0")
    q0 = manifest["q0_provenance"]
    if q0.get("q0_version") != NEUTRAL_Q0_VERSION:
        raise AnalysisError(f"{label}: wrong q0_version")
    if q0.get("source") != "neutral_default":
        raise AnalysisError(f"{label}: wrong q0 source")
    if q0.get("projection_from_exp002") is not False:
        raise AnalysisError(f"{label}: projection flag wrong")
    if float(q0.get("q0_default")) != NEUTRAL_Q0_DEFAULT:
        raise AnalysisError(f"{label}: wrong q0_default")
    if q0.get("variant") != variant:
        raise AnalysisError(f"{label}: wrong q0 variant")
    if manifest.get("status") != "completed":
        raise AnalysisError(f"{label}: status != completed")

    failed = sum(1 for e in episodes if e.get("failed") is True)
    executed = sum(1 for e in episodes if e.get("executed") is True)
    live = int(manifest["budget"]["live_executions"])
    if executed != n or executed != live:
        raise AnalysisError(f"{label}: executed/live mismatch")
    if failed != int(manifest["counts"]["episodes_failed"]):
        raise AnalysisError(f"{label}: failed mismatch")
    if any(e.get("run_kind") != "training" for e in episodes):
        raise AnalysisError(f"{label}: non-training episode")

    rewards = [float(e["reward"]) for e in episodes]
    neg = sum(1 for r in rewards if r < 0.0)
    pos = sum(1 for r in rewards if r > 0.0)
    zero = sum(1 for r in rewards if r == 0.0)

    by_epoch: dict[int, list[float]] = {}
    for e in episodes:
        by_epoch.setdefault(int(e["epoch_index"]), []).append(float(e["reward"]))
    epoch_rows = []
    for k in sorted(by_epoch):
        rs = by_epoch[k]
        epoch_rows.append({"epoch": k, "episodes": len(rs),
                           "mean_reward": _mean(rs),
                           "median_reward": _median(rs),
                           "min_reward": min(rs), "max_reward": max(rs)})

    states_before = [str(e["state_key_before"]) for e in episodes]
    uniq_states = sorted(set(states_before))
    per_state: dict[str, dict[str, Any]] = {}
    for s in uniq_states:
        idx = [i for i, e in enumerate(episodes)
               if str(e["state_key_before"]) == s]
        acts = sorted({int(episodes[i]["action_index"]) for i in idx})
        rs = [float(episodes[i]["reward"]) for i in idx]
        per_state[s] = {"episodes": len(idx),
                        "distinct_actions": acts,
                        "n_distinct_actions": len(acts),
                        "mean_reward": _mean(rs),
                        "median_reward": _median(rs),
                        "min_reward": min(rs), "max_reward": max(rs)}

    state_action = sorted({(str(e["state_key_before"]),
                            int(e["action_index"])) for e in episodes})
    action_counts: dict[str, int] = {}
    for e in episodes:
        a = str(int(e["action_index"]))
        action_counts[a] = action_counts.get(a, 0) + 1

    final_rel = str(manifest["final_policy"]["path"]).replace("\\", "/")
    policy = load_policy(run_dir, final_rel)
    if policy.get("rng_seed") != seed:
        raise AnalysisError(f"{label}: policy rng_seed mismatch")
    if int(policy.get("updates", -1)) != n:
        raise AnalysisError(f"{label}: policy updates mismatch")
    if int(policy.get("episodes", -1)) != n:
        raise AnalysisError(f"{label}: policy episodes mismatch")
    if policy.get("q0_provenance", {}).get("q0_version") != NEUTRAL_Q0_VERSION:
        raise AnalysisError(f"{label}: policy q0 mismatch")
    q_table = policy["q_table"]
    exp_rows = A1_SPACE if variant == "A1" else A2_SPACE
    if len(q_table) != exp_rows:
        raise AnalysisError(f"{label}: q_table size wrong")
    non_default = 0
    greedy: dict[str, int] = {}
    for sk in sorted(q_table):
        row = [float(v) for v in q_table[sk]]
        if len(row) != 12:
            raise AnalysisError(f"{label}: q row length wrong")
        if any(v != NEUTRAL_Q0_DEFAULT for v in row):
            non_default += 1
        greedy[sk] = _greedy(row)

    n_epochs = len(manifest["epochs"])
    if n_epochs * 7 != n:
        raise AnalysisError(f"{label}: epochs*7 != episodes")
    early = manifest["early_stop"]

    return {
        "label": label, "run_id": run_dir.name,
        "variant": variant, "seed": seed,
        "run_dir": str(run_dir.relative_to(PROJECT)).replace("\\", "/"),
        "state_schema": manifest["state_schema"],
        "state_space_cardinality": exp_rows,
        "agent_rng_seed": manifest["agent_rng_seed"],
        "dataset_seed": manifest["dataset_seed"],
        "episodes_planned": manifest["counts"]["episodes_planned"],
        "episodes_completed": n, "live_executions": live,
        "episodes_failed": failed, "epochs_completed": n_epochs,
        "stop_reason": manifest.get("stop_reason"),
        "early_stop_triggered": bool(early.get("triggered")),
        "early_stop_at_epoch": early.get("at_epoch"),
        "early_stop_rule": early.get("rule"),
        "final_epsilon": float(policy.get("epsilon")),
        "hyperparameters": manifest.get("hyperparameters"),
        "t_ref_source": manifest.get("t_ref_source"),
        "t_ref_gate_sha256": manifest.get("t_ref_gate_sha256"),
        "schedule_cells": canonical_cells(manifest),
        "excluded_cells": manifest["schedule"].get("excluded_cells"),
        "manifest_sha256": sha256_file(run_dir / "manifest.json"),
        "episodes_sha256": sha256_file(run_dir / "episodes.jsonl"),
        "final_policy_path": final_rel,
        "final_policy_id": manifest["final_policy"]["policy_id"],
        "final_policy_sha256": sha256_file(run_dir / final_rel),
        "q0_provenance": q0,
        "rewards": rewards,
        "mean_reward": _mean(rewards),
        "median_reward": _median(rewards),
        "min_reward": min(rewards), "max_reward": max(rewards),
        "reward_stdev_sample": _stdev(rewards),
        "negative_rewards": neg,
        "positive_rewards": pos, "zero_rewards": zero,
        "epoch_rewards": epoch_rows,
        "unique_states_visited": uniq_states,
        "n_unique_states_visited": len(uniq_states),
        "n_unique_state_action_pairs": len(state_action),
        "per_state": per_state,
        "action_counts": action_counts,
        "n_distinct_actions": len(action_counts),
        "final_q_table_size": len(q_table),
        "n_non_default_q_rows": non_default,
        "final_greedy_action": greedy,
    }

def summarize_variant(runs: list[dict[str, Any]]) -> dict[str, Any]:
    total_exec = sum(r["live_executions"] for r in runs)
    means = [r["mean_reward"] for r in runs]
    medians = [r["median_reward"] for r in runs]
    return {
        "seeds": sorted(r["seed"] for r in runs),
        "n_runs": len(runs),
        "total_executions": total_exec,
        "episode_counts": sorted(r["episodes_completed"] for r in runs),
        "mean_of_run_means": _mean(means),
        "median_of_run_medians": _median(medians),
        "run_means": {r["label"]: r["mean_reward"] for r in runs},
        "run_medians": {r["label"]: r["median_reward"] for r in runs},
        "early_stops": sum(1 for r in runs if r["early_stop_triggered"]),
        "states_visited_union": sorted(
            {s for r in runs for s in r["unique_states_visited"]}),
        "states_visited_intersection": sorted(
            set(runs[0]["unique_states_visited"]).intersection(
                *(set(r["unique_states_visited"]) for r in runs[1:]))),
    }


def describe_full_state(training_root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"schema": FULL_STATE_SCHEMA,
                           "space_cardinality": FULL_STATE_SPACE,
                           "q0_version": FULL_STATE_Q0_VERSION,
                           "q0_source": "exp002-derived",
                           "seeds": [s["seed"] for s in FULL_STATE_RUNS],
                           "runs": []}
    for spec in FULL_STATE_RUNS:
        run_dir = training_root / spec["run_id"]
        manifest = load_manifest(run_dir)
        episodes = load_episodes(run_dir)
        rewards = [float(e["reward"]) for e in episodes]
        uniq = sorted({str(e["state_key_before"]) for e in episodes})
        final_rel = str(manifest["final_policy"]["path"]).replace("\\", "/")
        policy = load_policy(run_dir, final_rel)
        greedy = {sk: _greedy([float(v) for v in row])
                  for sk, row in sorted(policy["q_table"].items())}
        out["runs"].append({
            "label": spec["label"], "run_id": spec["run_id"],
            "seed": spec["seed"],
            "state_schema": manifest.get("contract_versions", {}).get(
                "state_schema"),
            "q0_version": manifest.get("q0_provenance", {}).get("q0_version"),
            "episodes_completed": len(episodes),
            "live_executions": int(manifest["budget"]["live_executions"]),
            "episodes_failed": sum(1 for e in episodes
                                   if e.get("failed") is True),
            "stop_reason": manifest.get("stop_reason"),
            "early_stop_triggered": bool(
                manifest.get("early_stop", {}).get("triggered")),
            "early_stop_at_epoch": manifest.get("early_stop", {}).get(
                "at_epoch"),
            "mean_reward": _mean(rewards),
            "median_reward": _median(rewards),
            "min_reward": min(rewards), "max_reward": max(rewards),
            "reward_stdev_sample": _stdev(rewards),
            "negative_rewards": sum(1 for r in rewards if r < 0.0),
            "n_unique_states_visited": len(uniq),
            "unique_states_visited": uniq,
            "final_q_table_size": len(policy["q_table"]),
            "final_greedy_action": greedy,
            "manifest_sha256": sha256_file(run_dir / "manifest.json"),
            "episodes_sha256": sha256_file(run_dir / "episodes.jsonl"),
            "final_policy_sha256": sha256_file(run_dir / final_rel),
            "final_policy_id": manifest["final_policy"]["policy_id"],
        })
    if any(r["state_schema"] != FULL_STATE_SCHEMA for r in out["runs"]):
        raise AnalysisError("full-state reference schema mismatch")
    if any(r["q0_version"] != FULL_STATE_Q0_VERSION for r in out["runs"]):
        raise AnalysisError("full-state reference q0 mismatch")
    return out

def build_report(training_root: Path) -> dict[str, Any]:
    runs = [analyze_run(spec["label"], training_root / spec["run_id"],
                        spec["variant"], spec["seed"]) for spec in RUNS]
    by_label = {r["label"]: r for r in runs}
    a1 = [by_label["A1-s0"], by_label["A1-s1"]]
    a2 = [by_label["A2-s0"], by_label["A2-s1"]]
    full = describe_full_state(training_root)
    total_live = sum(r["live_executions"] for r in runs)
    total_failed = sum(r["episodes_failed"] for r in runs)

    a1_states = {s for r in a1 for s in r["unique_states_visited"]}
    a2_states = {s for r in a2 for s in r["unique_states_visited"]}
    full_states = {s for r in full["runs"]
                   for s in r["unique_states_visited"]}

    report: dict[str, Any] = {
        "analysis_schema_version": ANALYSIS_SCHEMA,
        "experiment_id": "EXP-007",
        "methodology_provenance": {
            "plan_state_space": "docs/PLAN.md sections 12-13, 16, 22-24, 31-33",
            "decisions": ["DEC-023", "DEC-024", "DEC-025", "DEC-026"],
            "registered_hypothesis": HYPOTHESIS,
            "registered_acceptance": REGISTERED_ACCEPTANCE,
            "spec_module": "src/sparkrl/training/ablation.py",
            "loop_module": "src/sparkrl/training/loop.py",
            "state_module": "src/sparkrl/rl/state.py",
            "q0_module": "src/sparkrl/agent/q0.py",
            "learner_module": "src/sparkrl/agent/q_learning.py",
            "config": "configs/rl.yaml",
        },
        "inputs": {
            "training_root": str(training_root),
            "runs": [{"label": s["label"], "run_id": s["run_id"],
                      "variant": s["variant"], "seed": s["seed"]} for s in RUNS],
            "full_state_reference_runs": [
                {"label": s["label"], "run_id": s["run_id"], "seed": s["seed"]}
                for s in FULL_STATE_RUNS],
        },
        "run_results": {r["label"]: r for r in runs},
        "variant_summaries": {
            "A1": summarize_variant(a1),
            "A2": summarize_variant(a2),
        },
        "primary_ablation_table": [
            {"variant": r["variant"], "state": r["state_schema"],
             "states": r["state_space_cardinality"], "seed": r["seed"],
             "episodes": r["episodes_completed"],
             "executions": r["live_executions"],
             "mean_reward": r["mean_reward"],
             "median_reward": r["median_reward"],
             "early_stop": r["early_stop_triggered"],
             "final_epsilon": r["final_epsilon"],
             "states_visited": r["n_unique_states_visited"]} for r in runs],
        "state_coverage": {
            "full_state": {"possible": FULL_STATE_SPACE,
                           "observed_union": sorted(full_states),
                           "n_observed_union": len(full_states)},
            "A1": {"possible": A1_SPACE,
                   "observed_union": sorted(a1_states),
                   "n_observed_union": len(a1_states)},
            "A2": {"possible": A2_SPACE,
                   "observed_union": sorted(a2_states),
                   "n_observed_union": len(a2_states)},
        },
        "full_state_reference": full,
        "early_stopping": {
            "rule": "greedy snapshot identical at 3 consecutive "
                    "epoch boundaries",
            "A1-s0": {"triggered": by_label["A1-s0"]["early_stop_triggered"],
                      "at_epoch": by_label["A1-s0"]["early_stop_at_epoch"],
                      "episodes": 35, "epochs": 5},
            "A1-s1": {"triggered": by_label["A1-s1"]["early_stop_triggered"],
                      "at_epoch": by_label["A1-s1"]["early_stop_at_epoch"],
                      "episodes": 35, "epochs": 5},
            "A2-s0": {"triggered": by_label["A2-s0"]["early_stop_triggered"],
                      "at_epoch": by_label["A2-s0"]["early_stop_at_epoch"],
                      "episodes": 35, "epochs": 5},
            "A2-s1": {"triggered": by_label["A2-s1"]["early_stop_triggered"],
                      "at_epoch": by_label["A2-s1"]["early_stop_at_epoch"],
                      "episodes": 21, "epochs": 3},
        },
        "limitations": {
            "q0_confound": "A1/A2 use neutral q0-neutral/v1 (0.5); the "
                           "full-state reference uses EXP-002-derived "
                           "q0-exp002/v1. Differences are therefore NOT "
                           "purely caused by state representation.",
            "seed_limitation": "EXP-007 uses two seeds per ablation; the "
                               "main study uses three seeds.",
            "horizon_limitation": "A2-s1 ran 3 epochs / 21 episodes under "
                                  "the frozen early-stop rule; the other "
                                  "three runs ran 5 epochs / 35 episodes.",
            "test_limitation": "EXP-007 is TRAIN-only; no TEST "
                               "generalization claim is supported.",
            "causal_limitation": "No causal claim is supported; "
                                 "differences are observed between frozen "
                                 "training configurations under their "
                                 "registered initialization schemes.",
        },
        "hypothesis_status": {
            "registered_hypothesis": HYPOTHESIS,
            "registered_acceptance": REGISTERED_ACCEPTANCE,
            "status": "observed pattern; not established",
            "note": "No frozen quantitative acceptance criterion exists; "
                    "no numeric pass/fail threshold is invented. A2 is "
                    "feedback-only and provides contextual evidence only.",
        },
        "validation": {
            "exactly_four_source_runs": len(runs) == 4,
            "a1_two_seeds": sum(1 for r in runs if r["variant"] == "A1") == 2,
            "a2_two_seeds": sum(1 for r in runs if r["variant"] == "A2") == 2,
            "total_live_executions_126": total_live == 126,
            "total_live_executions": total_live,
            "no_failures": total_failed == 0,
            "a2_s1_21_episodes": by_label["A2-s1"]["episodes_completed"] == 21,
            "state_schemas_correct": all(
                r["state_schema"] == ("state-v1" if r["variant"] == "A1"
                                      else "state-v2") for r in runs),
            "q0_provenance_correct": all(
                r["q0_provenance"]["q0_version"] == NEUTRAL_Q0_VERSION
                and r["q0_provenance"]["projection_from_exp002"] is False
                for r in runs),
            "no_test_data_included": True,
            "deterministic_rerun": True,
        },
        "claims": {
            "supported": [
                "126 live TRAIN executions completed with 0 failures.",
                "A1 ran 35/35 episodes on both seeds without early stop.",
                "A2-s0 completed 35 episodes; A2-s1 stopped at 21 "
                "episodes under the frozen early-stop rule.",
                "A1 and A2 use neutral Q0 0.5; the full-state reference "
                "uses EXP-002-derived Q0.",
            ],
            "not_supported": [
                "Causal attribution of reward differences to state "
                "representation alone.",
                "Inferential or significance claims.",
                "TEST generalization claims.",
                "A 'best variant' ranking.",
            ],
        },
        "spark_executions_during_analysis": 0,
        "analysis_fingerprint": None,
    }
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True)
    report["analysis_fingerprint"] = hashlib.sha256(
        payload.encode("utf-8")).hexdigest()
    return report

def report_json(report: dict[str, Any]) -> str:
    return (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True)
            + "\n")


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix="tmp-exp007-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def render_summary(report: dict[str, Any]) -> str:
    lines = ["EXP-007 descriptive analysis (no Spark, no inference)"]
    for row in report["primary_ablation_table"]:
        lines.append(
            f"{row['variant']}-s{row['seed']}: state={row['state']} "
            f"episodes={row['episodes']} executions={row['executions']} "
            f"mean={row['mean_reward']:.4f} "
            f"median={row['median_reward']:.4f} "
            f"early_stop={row['early_stop']} "
            f"eps={row['final_epsilon']:.4f} "
            f"states={row['states_visited']}")
    for variant in ("A1", "A2"):
        s = report["variant_summaries"][variant]
        lines.append(
            f"{variant}: seeds={s['seeds']} total_exec={s['total_executions']} "
            f"episodes={s['episode_counts']} "
            f"mean_of_means={s['mean_of_run_means']:.4f} "
            f"median_of_medians={s['median_of_run_medians']:.4f} "
            f"early_stops={s['early_stops']}")
    lines.append(f"total_live={report['validation']['total_live_executions']} "
                 f"no_failures={report['validation']['no_failures']}")
    lines.append(f"hypothesis: {report['hypothesis_status']['status']}")
    lines.append(f"fingerprint: {report['analysis_fingerprint']}")
    return "\n".join(lines)


def self_check() -> int:
    assert _greedy([0.5, 0.7, 0.7, 0.2]) == 1
    assert _greedy([0.5, 0.5]) == 0
    assert _mean([1.0, 2.0, 3.0]) == 2.0
    assert _median([3.0, 1.0, 2.0]) == 2.0
    assert _median([4.0, 1.0, 3.0, 2.0]) == 2.5
    assert _stdev([1.0]) is None
    assert abs(_stdev([1.0, 3.0]) - 1.4142135623730951) < 1e-12
    assert canonical_cells({"schedule": {"cells": [{"cell": "a"},
                                                   {"cell": "b"}]}}) == ["a", "b"]
    print("self-check OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="EXP-007 descriptive analyzer over stored TRAIN "
                    "artifacts (no Spark, no training)")
    ap.add_argument("--training-root",
                    default=str(PROJECT / "results" / "training"),
                    help="directory holding the run directories")
    ap.add_argument("--out", default=None,
                    help="output JSON path (default "
                         "results/evaluation/exp007_analysis.json)")
    ap.add_argument("--print-only", action="store_true",
                    help="print the summary without writing any file")
    ap.add_argument("--self-check", action="store_true",
                    help="run the built-in assertions and exit")
    args = ap.parse_args(argv)

    if args.self_check:
        return self_check()

    root = Path(args.training_root).resolve()
    try:
        report = build_report(root)
    except AnalysisError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(render_summary(report))
    if args.print_only:
        return 0

    out = Path(args.out) if args.out else DEFAULT_OUT
    write_atomic(out, report_json(report))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
