#!/usr/bin/env python
"""Day-28 analyzer: the first full bandit-mode training run (PLAN line 274).

Reads ONLY stored artifacts of a finished training run:

    <run>/manifest.json                 (rl-training-run/v1)
    <run>/episodes.jsonl                (rl-training-episode/v1, one per episode)
    <run>/checkpoints/policy-*.json     (policy/v1)
    <run>/transitions/**/rep*.json      (env transition records)

No Spark, no training, no PySpark import, no wall clock, no RNG: reading the
same run directory twice, in any order, produces a byte-identical artifact.

It writes <run>/analysis/day28_analysis.json atomically (tmp + os.replace) and
prints a human-readable summary, so the Day-28 audit document can cite the
artifact instead of hand-typed numbers.

Every reward/epsilon/budget number here is COPIED OR DERIVED from the files.
Nothing here supports a claim of learning, convergence, improvement or
superiority over a baseline. The reward-trend block is DESCRIPTIVE only: PLAN
freezes no numerical threshold, so no PASS/FAIL verdict is emitted. The frozen
early-stop rule is a BUDGET-SAVING HEURISTIC (the greedy argmax stopped
changing between epoch snapshots); it is NOT evidence of convergence.

Usage:
    python scripts/analyze_day28.py
    python scripts/analyze_day28.py --run results/training/<run-id>
    python scripts/analyze_day28.py --out /tmp/a.json --reverse-input
    python scripts/analyze_day28.py --self-check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
TRAINING_ROOT = PROJECT / "results" / "training"
DEFAULT_RUN = TRAINING_ROOT / "train-a0-d0-20260912T083120Z"

ANALYSIS_SCHEMA = "day28-analysis/v1"
MANIFEST_SCHEMA = "rl-training-run/v1"
EPISODE_SCHEMA = "rl-training-episode/v1"

# PLAN section 16, frozen. Used ONLY to re-check the stored epsilon trajectory.
EPSILON_START = 1.0
EPSILON_DECAY = 0.95
EPSILON_MIN = 0.05
EPSILON_TOL = 1e-12
LIVE_EXECUTION_CAP = 500

DEFAULT_ROLLING_WINDOW = 7      # = one epoch (7 eligible TRAIN cells)


class AnalysisError(RuntimeError):
    """An artifact is missing, unreadable or off-contract."""


# --- loading ------------------------------------------------------------------
@dataclass(frozen=True)
class Run:
    """One finished training run, loaded from disk. Nothing is mutated."""

    root: Path
    manifest: dict[str, Any]
    episodes: tuple[dict[str, Any], ...]
    final_policy: dict[str, Any] | None
    transitions: tuple[dict[str, Any], ...]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnalysisError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"{path} is not valid JSON: {exc}") from exc


def _relpath(root: Path, stored: str) -> Path:
    """Manifests written on Windows store 'checkpoints\\policy-x.json'."""
    return root.joinpath(*stored.replace("\\", "/").split("/"))


def load_run(root: Path, *, reverse_input: bool = False) -> Run:
    """Load a run directory. `reverse_input` is a determinism self-check only."""
    if not root.is_dir():
        raise AnalysisError(f"run directory not found: {root}")

    manifest = _read_json(root / "manifest.json")
    got = manifest.get("record_schema_version")
    if got != MANIFEST_SCHEMA:
        raise AnalysisError(
            f"{root / 'manifest.json'} has record_schema_version {got!r}, "
            f"expected {MANIFEST_SCHEMA!r}")

    log = root / str(manifest.get("files", {}).get("episode_log", "episodes.jsonl"))
    try:
        raw = log.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AnalysisError(f"cannot read {log}: {exc}") from exc
    episodes: list[dict[str, Any]] = []
    for n, line in enumerate(raw, start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"{log}:{n} is not valid JSON: {exc}") from exc
        if rec.get("record_schema_version") != EPISODE_SCHEMA:
            raise AnalysisError(
                f"{log}:{n} has record_schema_version "
                f"{rec.get('record_schema_version')!r}, expected {EPISODE_SCHEMA!r}")
        episodes.append(rec)
    if reverse_input:
        episodes.reverse()

    final = manifest.get("final_policy") or {}
    policy = _read_json(_relpath(root, final["path"])) if final.get("path") else None

    trans_root = root / str(manifest.get("files", {}).get("transitions_root",
                                                          "transitions"))
    transitions = [_read_json(p)
                   for p in sorted(trans_root.glob("**/*.json"))] \
        if trans_root.is_dir() else []

    return Run(root=root, manifest=manifest, episodes=tuple(episodes),
               final_policy=policy, transitions=tuple(transitions))


# --- small deterministic statistics -------------------------------------------
def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0


def _summary(xs: list[float]) -> dict[str, Any]:
    return {"n": len(xs), "mean": _mean(xs), "median": _median(xs),
            "min": min(xs) if xs else None, "max": max(xs) if xs else None}


def _ols_slope(ys: list[float]) -> float | None:
    """Least-squares slope of y against x = 1..n. DESCRIPTIVE, not a test."""
    n = len(ys)
    if n < 2:
        return None
    xbar = (n + 1) / 2.0
    ybar = sum(ys) / n
    sxx = sum((i + 1 - xbar) ** 2 for i in range(n))
    if sxx == 0.0:
        return None
    sxy = sum((i + 1 - xbar) * (y - ybar) for i, y in enumerate(ys))
    return sxy / sxx


def _rolling_mean(xs: list[float], window: int) -> list[float | None]:
    """Trailing mean; None until `window` points exist."""
    out: list[float | None] = []
    total = 0.0
    for i, x in enumerate(xs):
        total += x
        if i >= window:
            total -= xs[i - window]
        out.append(total / window if i >= window - 1 else None)
    return out


def _counter_dict(values: list[Any],
                  domain: list[Any] | None = None) -> dict[str, int]:
    """Count -> plain dict with a deterministic (key-sorted) order.

    `domain` forces every key of the full domain to appear, so a value that was
    NEVER observed shows up as 0 instead of silently vanishing from the table.
    """
    counts = Counter(values)
    for key in domain or ():
        counts.setdefault(key, 0)
    return {str(k): v for k, v in sorted(counts.items(),
                                         key=lambda kv: str(kv[0]))}


def _action_domain(policy: dict[str, Any] | None) -> list[int] | None:
    """The full action index domain, read off the stored Q rows (all equal)."""
    q = (policy or {}).get("q_table") or {}
    sizes = {len(row) for row in q.values()}
    return list(range(sizes.pop())) if len(sizes) == 1 else None


# --- report -------------------------------------------------------------------
def _expected_epsilon(n: int) -> float:
    return max(EPSILON_MIN, EPSILON_START * EPSILON_DECAY ** n)


def _epsilon_block(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    used = [float(e["epsilon_used"]) for e in episodes]
    expected = [_expected_epsilon(n) for n in range(len(used))]
    mismatches = [{"episode_index": episodes[i]["episode_index"],
                   "epsilon_used": used[i], "expected": expected[i]}
                  for i in range(len(used))
                  if abs(used[i] - expected[i]) > EPSILON_TOL]
    chained = [{"episode_index": episodes[i + 1]["episode_index"],
                "epsilon_after_previous": float(episodes[i]["epsilon_after"]),
                "epsilon_used": used[i + 1]}
               for i in range(len(episodes) - 1)
               if abs(float(episodes[i]["epsilon_after"]) - used[i + 1]) > EPSILON_TOL]
    return {
        "schedule": "epsilon_used[n] = max(0.05, 1.0 * 0.95 ** n), n from 0",
        "schedule_source": "PLAN section 16 (frozen)",
        "trajectory": used,
        "first": used[0] if used else None,
        "last": used[-1] if used else None,
        "floor_reached": any(u == EPSILON_MIN for u in used),
        "matches_frozen_schedule": not mismatches and not chained,
        "mismatches": mismatches,
        "chaining_mismatches": chained,
    }



def _policy_coverage(policy: dict[str, Any] | None,
                     episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """How much of the FINAL policy this run actually exercised.

    The early-stop rule compares the greedy argmax over the WHOLE stored table,
    including rows this run never visited (those keep their EXP-002 Q0 values and
    cannot move). Quantifying that is the sharpest available caveat on the
    stability signal, so it is derived here rather than described in prose.
    """
    if policy is None:
        return {"available": False, "note": "manifest carries no final_policy path"}
    q = policy.get("q_table") or {}
    visits: dict[str, dict[int, int]] = {}
    for e in episodes:
        key = e.get("state_key_before")
        if key is None:
            continue
        visits.setdefault(key, {})
        a = int(e["action_index"])
        visits[key][a] = visits[key].get(a, 0) + 1
    rows = []
    for state in sorted(q):
        row = [float(v) for v in q[state]]
        best = max(range(len(row)), key=lambda i: (row[i], -i)) if row else None
        seen = visits.get(state, {})
        rows.append({
            "state_key": state,
            "episodes_in_this_state": sum(seen.values()),
            "distinct_actions_tried": len(seen),
            "greedy_action_index": best,
            "greedy_action_executed_in_run": bool(seen.get(best, 0)),
            "greedy_action_executions": int(seen.get(best, 0)),
        })
    return {
        "available": True,
        "states_in_final_policy": len(q),
        "states_never_visited_in_run": sum(1 for r in rows
                                           if r["episodes_in_this_state"] == 0),
        "states_whose_greedy_action_was_never_executed":
            sum(1 for r in rows if not r["greedy_action_executed_in_run"]),
        "per_state": rows,
        "note": ("a greedy action that was never executed rests on the EXP-002 "
                 "offline Q0 value or the optimistic default, not on any "
                 "execution in this run; an unvisited row cannot change, so it "
                 "contributes stability to the early-stop snapshot for free"),
    }

def _q_table_block(policy: dict[str, Any] | None) -> dict[str, Any]:
    if policy is None:
        return {"available": False,
                "note": "manifest carries no final_policy path"}
    q = policy.get("q_table") or {}
    q0 = float((policy.get("learner_config") or {}).get("q0_default", 0.5))
    values = [float(v) for row in q.values() for v in row]
    per_state = []
    for state in sorted(q):
        row = [float(v) for v in q[state]]
        best = max(range(len(row)), key=lambda i: (row[i], -i)) if row else None
        per_state.append({
            "state_key": state,
            "actions": len(row),
            "greedy_action_index": best,
            "greedy_value": row[best] if best is not None else None,
            "min": min(row) if row else None,
            "max": max(row) if row else None,
            "pairs_differing_from_q0": sum(1 for v in row if v != q0),
        })
    return {
        "available": True,
        "policy_id": policy.get("policy_id"),
        "policy_schema": policy.get("policy_schema"),
        "episodes": policy.get("episodes"),
        "updates": policy.get("updates"),
        "epsilon": policy.get("epsilon"),
        "states": len(q),
        "pairs_total": len(values),
        "pairs_differing_from_q0": sum(1 for v in values if v != q0),
        "q0_default": q0,
        "value_min": min(values) if values else None,
        "value_max": max(values) if values else None,
        "per_state": per_state,
        "note": "greedy_action_index is argmax with ties broken to the lowest "
                "index; it is a stored table value, not a recommendation",
    }


def _cell_key(episode: dict[str, Any]) -> str:
    """Workload cell identity: family|scale. rep and dataset_seed are dropped
    on purpose, so repeated visits to the same cell aggregate together."""
    cell = episode.get("cell") or {}
    return f"{cell.get('family')}|{cell.get('scale')}"


def _per_cell_trend(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Decompose the epoch-mean movement over cells, and recompute it with each
    cell left out.

    DESCRIPTIVE ONLY. This partitions an arithmetic difference; it explains
    nothing, tests nothing and is not evidence of learning or convergence.
    """
    epochs = sorted({int(e["epoch_index"]) for e in episodes})
    by_cell: dict[str, dict[int, list[float]]] = {}
    for e in episodes:
        by_cell.setdefault(_cell_key(e), {}).setdefault(
            int(e["epoch_index"]), []).append(float(e["reward"]))
    first, last = epochs[0], epochs[-1]
    n_first = sum(1 for e in episodes if int(e["epoch_index"]) == first)
    n_last = sum(1 for e in episodes if int(e["epoch_index"]) == last)

    per_cell: dict[str, Any] = {}
    for key in sorted(by_cell):
        rows = by_cell[key]
        means = [_mean(rows.get(ep, [])) for ep in epochs]
        f, l = _mean(rows.get(first, [])), _mean(rows.get(last, []))
        delta = (l - f) if (f is not None and l is not None) else None
        # epoch_mean = sum_cell (n_cell / N) * cell_mean, so when a cell keeps
        # the same episode count in both epochs its exact share of the epoch
        # mean movement is (n_cell / N) * its own delta.
        balanced = (delta is not None and n_first == n_last
                    and len(rows.get(first, ())) == len(rows.get(last, ())))
        share = delta * len(rows[first]) / n_first if balanced else None
        # every epoch mean recomputed with this one cell removed
        others = [k for k in sorted(by_cell) if k != key]
        without = [_mean([v for k in others
                          for v in by_cell[k].get(ep, [])]) for ep in epochs]
        per_cell[key] = {
            "epoch_means": means,
            "first_epoch_mean": f,
            "last_epoch_mean": l,
            "last_minus_first": delta,
            "ols_slope_per_epoch": _ols_slope([v for v in means
                                               if v is not None]),
            "contribution_to_epoch_mean_delta": share,
            "epoch_means_excluding_this_cell": without,
            "last_minus_first_excluding_this_cell":
                (without[-1] - without[0]) if len(without) >= 2 else None,
            "ols_slope_per_epoch_excluding_this_cell": _ols_slope(
                [v for v in without if v is not None]),
        }
    shares = [c["contribution_to_epoch_mean_delta"] for c in per_cell.values()]
    return {
        "label": "DESCRIPTIVE ONLY - an arithmetic decomposition of a "
                 "difference, not an explanation of it and not a claim.",
        "first_epoch_index": first,
        "last_epoch_index": last,
        "per_cell": per_cell,
        "contribution_sum": sum(shares) if all(v is not None for v in shares)
        else None,
        "note": "contribution_sum must equal reward_trend_descriptive."
                "last_minus_first when every epoch has the same cell "
                "composition; leave-one-out columns show how much of that "
                "difference survives dropping a single cell",
    }


def _repeat_spread(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Spread of reward over repeated executions of the SAME (cell, action).

    Each group holds one cell, one action index and one config fingerprint, so
    what is left is per-execution variation of the measured runtime. It is a
    measured noise floor, not a result.
    """
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for e in episodes:
        groups.setdefault((_cell_key(e), int(e["action_index"])), []).append(e)
    out: dict[str, Any] = {}
    ranges: list[float] = []
    for (cell, action) in sorted(groups):
        rows = groups[(cell, action)]
        if len(rows) < 2:
            continue
        rs = [float(e["reward"]) for e in rows]
        n = len(rs)
        mean = _mean(rs)
        var = sum((r - mean) ** 2 for r in rs) / (n - 1)
        ranges.append(max(rs) - min(rs))
        out[f"{cell}|a{action}"] = {
            "n": n,
            "config_fingerprints": len({e["config_fingerprint"] for e in rows}),
            "t_ref_values": len({e["t_ref_s"] for e in rows}),
            "mean": mean, "min": min(rs), "max": max(rs),
            "range": max(rs) - min(rs),
            "stdev_sample": var ** 0.5,
            "epoch_indices": [int(e["epoch_index"]) for e in
                              sorted(rows, key=lambda r: int(r["epoch_index"]))],
            "rewards": [float(e["reward"]) for e in
                        sorted(rows, key=lambda r: int(r["epoch_index"]))],
        }
    return {
        "label": "MEASURED NOISE FLOOR - repeated executions of an identical "
                 "(cell, action, config fingerprint); no policy change is "
                 "involved in the spread within a group.",
        "groups": out,
        "groups_with_repeats": len(out),
        "max_range": max(ranges) if ranges else None,
    }


def _transition_block(run: Run) -> dict[str, Any]:
    failed = []
    for rec in run.transitions:
        metrics = rec.get("metrics") or {}
        if metrics.get("success") is not True or metrics.get("timeout") is True \
                or metrics.get("usable") is False:
            failed.append({"episode_key": rec.get("episode_key"),
                           "config_name": rec.get("config_name"),
                           "success": metrics.get("success"),
                           "timeout": metrics.get("timeout"),
                           "usable": metrics.get("usable"),
                           "error": metrics.get("error")})
    return {
        "records_found": len(run.transitions),
        "records_failed_or_unusable": len(failed),
        "failures": failed,
        "cached_records": sum(1 for r in run.transitions if r.get("cached")),
        "distinct_application_ids": len({(r.get("metrics") or {})
                                         .get("application_id")
                                         for r in run.transitions}),
    }


def _budget_block(run: Run, training_root: Path) -> dict[str, Any]:
    this = dict(run.manifest.get("budget") or {})
    ledger = []
    total = 0
    for path in sorted(training_root.glob("**/manifest.json")) \
            if training_root.is_dir() else []:
        rec = _read_json(path)
        live = int((rec.get("budget") or {}).get("live_executions", 0))
        total += live
        ledger.append({
            "manifest": path.relative_to(PROJECT).as_posix(),
            "run_id": rec.get("run_id"),
            "run_kind": rec.get("run_kind"),
            "live_executions": live,
        })
    return {
        "this_run": {
            "live_executions": this.get("live_executions"),
            "budget_limit_this_run": this.get("budget_limit_this_run"),
            "budget_remaining": this.get("budget_remaining"),
        },
        "cross_run_ledger": {
            "manifests": len(ledger),
            "live_executions_total": total,
            "live_execution_cap": LIVE_EXECUTION_CAP,
            "remaining_against_cap": LIVE_EXECUTION_CAP - total,
            "entries": ledger,
        },
        "enforcement": "REPORTED, not ENFORCED: the env counter is per-process; "
                       "durable cross-process enforcement is COMP-EXP-11 and "
                       "remains DEFERRED",
    }


def build_report(run: Run, *, rolling_window: int = DEFAULT_ROLLING_WINDOW
                 ) -> dict[str, Any]:
    """Derive every Day-28 number from the loaded artifacts. Order-independent."""
    episodes = sorted(run.episodes, key=lambda e: int(e["episode_index"]))
    indices = [int(e["episode_index"]) for e in episodes]
    if indices != list(range(1, len(indices) + 1)):
        raise AnalysisError(
            f"episode_index is not the contiguous sequence 1..{len(indices)}: "
            f"{indices[:5]}...{indices[-3:]}")
    rewards = [float(e["reward"]) for e in episodes]

    epoch_indices = sorted({int(e["epoch_index"]) for e in episodes})
    per_epoch = []
    for epoch in epoch_indices:
        rs = [float(e["reward"]) for e in episodes if int(e["epoch_index"]) == epoch]
        per_epoch.append({"epoch_index": epoch, "episodes": len(rs),
                          "mean_reward": _mean(rs), "median_reward": _median(rs),
                          "min_reward": min(rs), "max_reward": max(rs)})
    epoch_means = [p["mean_reward"] for p in per_epoch]

    cells: dict[str, list[float]] = {}
    for e in episodes:
        cells.setdefault(_cell_key(e), []).append(float(e["reward"]))

    manifest = run.manifest
    counts = dict(manifest.get("counts") or {})
    epochs_manifest = list(manifest.get("epochs") or [])
    early = dict(manifest.get("early_stop") or {})

    return {
        "analysis_schema_version": ANALYSIS_SCHEMA,
        "source": {
            "run_dir": run.root.relative_to(PROJECT).as_posix()
            if run.root.is_relative_to(PROJECT) else run.root.as_posix(),
            "run_id": manifest.get("run_id"),
            "run_kind": manifest.get("run_kind"),
            "started_utc": manifest.get("started_utc"),
            "finished_utc": manifest.get("finished_utc"),
            "code_version": manifest.get("code_version"),
            "manifest_schema": manifest.get("record_schema_version"),
            "episode_schema": EPISODE_SCHEMA,
            "agent_rng_seed": manifest.get("agent_rng_seed"),
            "dataset_seed": manifest.get("dataset_seed"),
            "contract_versions": manifest.get("contract_versions"),
            "hyperparameters": manifest.get("hyperparameters"),
        },
        "claims": {
            "learning_demonstrated": False,
            "convergence_demonstrated": False,
            "baseline_comparison": None,
            "note": "Day 28 is an OBSERVATION of one seed-0 run. The reward "
                    "trend below is descriptive; PLAN freezes no threshold and "
                    "this analysis emits no verdict on it.",
        },
        "counts": {
            "episodes_planned": counts.get("episodes_planned"),
            "episodes_completed": counts.get("episodes_completed"),
            "episodes_failed": counts.get("episodes_failed"),
            "episodes_updated": counts.get("episodes_updated"),
            "episode_lines_read": len(episodes),
            "episodes_executed": sum(1 for e in episodes if e.get("executed")),
            "episodes_marked_failed": sum(1 for e in episodes if e.get("failed")),
            "episodes_unusable": sum(1 for e in episodes
                                     if e.get("usable") is not True),
            "episodes_with_update_error": sum(1 for e in episodes
                                              if e.get("update_error")),
            "epochs_completed": len(epochs_manifest),
            "epochs_seen_in_episodes": len(epoch_indices),
        },
        "reward": {
            "per_episode": rewards,
            "per_epoch": per_epoch,
            "rolling_mean": {"window": rolling_window,
                             "values": _rolling_mean(rewards, rolling_window)},
            "overall": _summary(rewards),
        },
        "reward_trend_descriptive": {
            "label": "DESCRIPTIVE ONLY - no PASS/FAIL, no threshold, not "
                     "convergence. PLAN defines no reward-trend threshold.",
            "epoch_means": epoch_means,
            "first_epoch_mean": epoch_means[0] if epoch_means else None,
            "last_epoch_mean": epoch_means[-1] if epoch_means else None,
            "last_minus_first": (epoch_means[-1] - epoch_means[0])
            if len(epoch_means) >= 2 else None,
            "ols_slope_per_epoch": _ols_slope(epoch_means),
            "ols_note": "ordinary least squares of epoch mean reward on epoch "
                        "index 1..n; a single seed, n epochs, no error model",
        },
        "epsilon": _epsilon_block(episodes),
        "actions": {
            "action_mode": (manifest.get("contract_versions") or {}).get("action_mode"),
            "action_index_counts": _counter_dict(
                [e["action_index"] for e in episodes],
                domain=_action_domain(run.final_policy)),
            "actions_never_taken": sorted(
                int(k) for k, v in _counter_dict(
                    [e["action_index"] for e in episodes],
                    domain=_action_domain(run.final_policy)).items() if v == 0),
            "config_name_counts": _counter_dict([e["config_name"] for e in episodes]),
            "action_source_counts": _counter_dict([e["action_source"] for e in episodes]),
            "explore": sum(1 for e in episodes if e.get("action_source") == "explore"),
            "exploit": sum(1 for e in episodes if e.get("action_source") == "exploit"),
        },
        "per_cell_reward": {
            key: _summary(cells[key]) for key in sorted(cells)
        },
        "per_cell_trend_descriptive": _per_cell_trend(episodes),
        "repeat_execution_spread": _repeat_spread(episodes),
        "q_table_final": _q_table_block(run.final_policy),
        "policy_coverage": _policy_coverage(run.final_policy, episodes),
        "checkpoints": [
            {"episode_index": c.get("episode_index"), "episodes": c.get("episodes"),
             "updates": c.get("updates"), "epsilon": c.get("epsilon"),
             "policy_id": c.get("policy_id")}
            for c in manifest.get("checkpoints") or []
        ],
        "early_stop": {
            "triggered": early.get("triggered"),
            "at_epoch": early.get("at_epoch"),
            "rule": early.get("rule"),
            "stable_epochs_required": early.get("stable_epochs_required"),
            "stop_reason": manifest.get("stop_reason"),
            "epoch_snapshots": [
                {"epoch_index": e.get("epoch_index"), "episodes": e.get("episodes"),
                 "greedy_snapshot_sha256": e.get("greedy_snapshot_sha256"),
                 "stable_vs_previous": e.get("stable_vs_previous"),
                 "stability_streak": e.get("stability_streak"),
                 "visited_state_keys": list(e.get("visited_state_keys") or [])}
                for e in epochs_manifest
            ],
            "final_stability_streak": epochs_manifest[-1].get("stability_streak")
            if epochs_manifest else None,
            "interpretation": "BUDGET-SAVING HEURISTIC: the greedy argmax stopped "
                              "changing between epoch snapshots, so the run stopped "
                              "spending the frozen execution budget. This is NOT "
                              "evidence of convergence and NOT a learning claim.",
        },
        "transitions": _transition_block(run),
        "budget": _budget_block(run, TRAINING_ROOT),
    }


# --- rendering ----------------------------------------------------------------
def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_summary(report: dict[str, Any]) -> str:
    src = report["source"]
    counts = report["counts"]
    reward = report["reward"]
    trend = report["reward_trend_descriptive"]
    eps = report["epsilon"]
    acts = report["actions"]
    qt = report["q_table_final"]
    stop = report["early_stop"]
    budget = report["budget"]
    out: list[str] = []
    w = out.append

    w("=" * 78)
    w("DAY 28 - FIRST FULL BANDIT-MODE TRAINING RUN (OBSERVATION ONLY)")
    w("=" * 78)
    w(f"run_id            {src['run_id']}  ({src['run_kind']})")
    w(f"run_dir           {src['run_dir']}")
    w(f"window_utc        {src['started_utc']} -> {src['finished_utc']}")
    w(f"code_version      {src['code_version']}")
    w(f"seeds             agent_rng_seed={src['agent_rng_seed']} "
      f"dataset_seed={src['dataset_seed']}")
    hp = src.get("hyperparameters") or {}
    w(f"hyperparameters   alpha={hp.get('alpha')} gamma={hp.get('gamma')} "
      f"(bandit) q0={hp.get('q0_default')} "
      f"eps {hp.get('epsilon_start')}->{hp.get('epsilon_min')} "
      f"x{hp.get('epsilon_decay')}")

    w("")
    w("-- counts -------------------------------------------------------------")
    w(f"episodes planned {counts['episodes_planned']}, completed "
      f"{counts['episodes_completed']}, log lines {counts['episode_lines_read']}")
    w(f"episodes failed {counts['episodes_marked_failed']}, unusable "
      f"{counts['episodes_unusable']}, update errors "
      f"{counts['episodes_with_update_error']}, updated "
      f"{counts['episodes_updated']}")
    w(f"epochs completed {counts['epochs_completed']}")
    tr = report["transitions"]
    w(f"transition records {tr['records_found']}, failed/unusable "
      f"{tr['records_failed_or_unusable']}, cached {tr['cached_records']}")

    w("")
    w("-- reward -------------------------------------------------------------")
    o = reward["overall"]
    w(f"overall n={o['n']} mean={_fmt(o['mean'])} median={_fmt(o['median'])} "
      f"min={_fmt(o['min'])} max={_fmt(o['max'])}")
    w(f"{'epoch':>6} {'n':>3} {'mean':>9} {'median':>9} {'min':>9} {'max':>9}")
    for row in reward["per_epoch"]:
        w(f"{row['epoch_index']:>6} {row['episodes']:>3} "
          f"{_fmt(row['mean_reward']):>9} {_fmt(row['median_reward']):>9} "
          f"{_fmt(row['min_reward']):>9} {_fmt(row['max_reward']):>9}")
    roll = reward["rolling_mean"]
    shown = ", ".join(_fmt(v) for v in roll["values"] if v is not None)
    w(f"rolling mean (window {roll['window']}): {shown}")

    w("")
    w("-- reward trend (DESCRIPTIVE ONLY) ------------------------------------")
    w("PLAN freezes no reward-trend threshold; no PASS/FAIL is emitted here and")
    w("nothing below is a claim of learning, convergence or improvement.")
    w("epoch means: " + ", ".join(_fmt(v) for v in trend["epoch_means"]))
    w(f"last - first = {_fmt(trend['last_minus_first'])}   "
      f"OLS slope per epoch = {_fmt(trend['ols_slope_per_epoch'], 6)}")

    w("")
    w("-- epsilon ------------------------------------------------------------")
    w(f"schedule {eps['schedule']}")
    w(f"trajectory {_fmt(eps['first'])} -> {_fmt(eps['last'])} over "
      f"{len(eps['trajectory'])} episodes; floor reached: {eps['floor_reached']}")
    w(f"matches frozen schedule: {eps['matches_frozen_schedule']} "
      f"({len(eps['mismatches'])} value mismatch(es), "
      f"{len(eps['chaining_mismatches'])} chaining mismatch(es))")

    w("")
    w("-- actions ------------------------------------------------------------")
    w(f"action_mode {acts['action_mode']}; explore {acts['explore']} / "
      f"exploit {acts['exploit']}")
    w("action_index counts: " + ", ".join(f"{k}={v}" for k, v
                                          in acts["action_index_counts"].items()))
    w("config_name counts:  " + ", ".join(f"{k}={v}" for k, v
                                          in acts["config_name_counts"].items()))
    never = acts["actions_never_taken"]
    w(f"actions never taken: {never if never else 'none'} "
      "(0 counts are shown above, not omitted)")

    w("")
    w("-- per-cell reward (family|scale; reps aggregated) --------------------")
    w(f"{'cell':<20} {'n':>3} {'mean':>9} {'median':>9} {'min':>9} {'max':>9}")
    for key, s in report["per_cell_reward"].items():
        w(f"{key:<20} {s['n']:>3} {_fmt(s['mean']):>9} {_fmt(s['median']):>9} "
          f"{_fmt(s['min']):>9} {_fmt(s['max']):>9}")

    w("")
    w("-- epoch-mean movement by cell (DESCRIPTIVE ONLY) ---------------------")
    trend_cells = report["per_cell_trend_descriptive"]
    w(f"decomposition of last - first over epochs "
      f"{trend_cells['first_epoch_index']}..{trend_cells['last_epoch_index']}; "
      f"contributions sum to {_fmt(trend_cells['contribution_sum'], 6)}")
    w(f"{'cell':<20} {'delta':>9} {'share':>9} {'%':>7} {'excl:last-first':>16}"
      f" {'excl:slope':>11}")
    for key, row in trend_cells["per_cell"].items():
        total = trend_cells["contribution_sum"]
        share = row["contribution_to_epoch_mean_delta"]
        pct = (100.0 * share / total) if (share is not None and total) else None
        w(f"{key:<20} {_fmt(row['last_minus_first']):>9} {_fmt(share):>9} "
          f"{_fmt(pct, 1):>7} "
          f"{_fmt(row['last_minus_first_excluding_this_cell'], 6):>16} "
          f"{_fmt(row['ols_slope_per_epoch_excluding_this_cell'], 6):>11}")

    w("")
    w("-- repeat-execution spread (same cell, same action) -------------------")
    spread = report["repeat_execution_spread"]
    w(f"{spread['groups_with_repeats']} group(s) with >= 2 executions; "
      f"largest reward range {_fmt(spread['max_range'], 6)}")
    w(f"{'cell|action':<24} {'n':>3} {'fps':>4} {'range':>9} {'sd':>9}")
    for key, g in spread["groups"].items():
        w(f"{key:<24} {g['n']:>3} {g['config_fingerprints']:>4} "
          f"{_fmt(g['range']):>9} {_fmt(g['stdev_sample']):>9}")
    w("Spread within a group involves no policy change: it is per-execution")
    w("variation of the measured runtime, i.e. a measured noise floor.")

    w("")
    w("-- final Q-table ------------------------------------------------------")
    if not qt.get("available"):
        w(qt.get("note", "no final policy"))
    else:
        w(f"policy_id {qt['policy_id']} ({qt['policy_schema']}), "
          f"episodes={qt['episodes']} updates={qt['updates']}")
        w(f"states {qt['states']}, pairs {qt['pairs_total']}, differing from "
          f"q0={qt['q0_default']}: {qt['pairs_differing_from_q0']}")
        w(f"value range [{_fmt(qt['value_min'])}, {_fmt(qt['value_max'])}]")
        w(f"{'state':<32} {'greedy a':>8} {'value':>9} {'!=q0':>5}")
        for row in qt["per_state"]:
            w(f"{row['state_key']:<32} {row['greedy_action_index']:>8} "
              f"{_fmt(row['greedy_value']):>9} "
              f"{row['pairs_differing_from_q0']:>5}")

    w("")
    w("-- early stop ---------------------------------------------------------")
    w(f"triggered {stop['triggered']} at epoch {stop['at_epoch']}; rule: "
      f"{stop['rule']}")
    w(f"stability streaks: " + ", ".join(
        f"e{e['epoch_index']}={e['stability_streak']}"
        for e in stop["epoch_snapshots"]))
    w("Early stop is a BUDGET-SAVING HEURISTIC (the greedy argmax stopped")
    w("changing). It is NOT evidence of convergence.")

    w("")
    w("-- budget -------------------------------------------------------------")
    this = budget["this_run"]
    ledger = budget["cross_run_ledger"]
    w(f"this run: {this['live_executions']} live executions of a "
      f"{this['budget_limit_this_run']}-execution plan "
      f"({this['budget_remaining']} unspent)")
    w(f"cross-run SC6 ledger: {ledger['live_executions_total']} live executions "
      f"over {ledger['manifests']} manifest(s) under results/training/")
    w(f"vs the frozen cap {ledger['live_execution_cap']}: "
      f"{ledger['remaining_against_cap']} remaining (REPORTED, not ENFORCED; "
      f"COMP-EXP-11 deferred)")
    w("=" * 78)
    return "\n".join(out)


def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# --- self-check ---------------------------------------------------------------
def self_check() -> int:
    """Smallest runnable check of the non-trivial derivations."""
    assert _median([3.0, 1.0, 2.0]) == 2.0
    assert _median([4.0, 1.0, 3.0, 2.0]) == 2.5
    assert _ols_slope([1.0, 2.0, 3.0]) == 1.0
    assert _ols_slope([2.0, 2.0, 2.0]) == 0.0
    assert _ols_slope([1.0]) is None
    assert _rolling_mean([1.0, 2.0, 3.0], 2) == [None, 1.5, 2.5]
    assert _expected_epsilon(0) == 1.0
    assert abs(_expected_epsilon(1) - 0.95) < 1e-12
    assert _expected_epsilon(200) == EPSILON_MIN
    assert _counter_dict(["b", "a", "b"]) == {"a": 1, "b": 2}
    # a value in the domain but never observed must survive as an explicit 0
    assert _counter_dict([0, 0, 2], domain=[0, 1, 2]) == {"0": 2, "1": 0, "2": 1}
    assert _action_domain({"q_table": {"s": [0.0] * 12, "t": [0.0] * 12}})         == list(range(12))
    assert _action_domain({"q_table": {"s": [0.0], "t": [0.0, 0.0]}}) is None
    # the per-cell shares must reconstruct the epoch-mean difference exactly
    _eps = [{"epoch_index": 1, "reward": 0.2, "cell": {"family": "A", "scale": "s"}},
            {"epoch_index": 1, "reward": 0.4, "cell": {"family": "B", "scale": "s"}},
            {"epoch_index": 2, "reward": 0.6, "cell": {"family": "A", "scale": "s"}},
            {"epoch_index": 2, "reward": 0.5, "cell": {"family": "B", "scale": "s"}}]
    _t = _per_cell_trend(_eps)
    assert abs(_t["contribution_sum"] - (0.55 - 0.3)) < 1e-12
    assert abs(_t["per_cell"]["A|s"]["contribution_to_epoch_mean_delta"]
               - 0.2) < 1e-12
    assert _t["per_cell"]["A|s"]["epoch_means_excluding_this_cell"] == [0.4, 0.5]
    assert list(_counter_dict([2, 10, 1])) == ["1", "10", "2"]
    # order independence of the reward statistics
    xs = [0.3, 0.9, 0.1]
    assert _summary(xs) == _summary(list(reversed(xs)))
    print("self-check OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Day-28 analyzer over stored training artifacts (no Spark)")
    ap.add_argument("--run", default=str(DEFAULT_RUN),
                    help="run directory (default: the Day-28 run of record)")
    ap.add_argument("--out", default=None,
                    help="output JSON path (default <run>/analysis/"
                         "day28_analysis.json)")
    ap.add_argument("--rolling-window", type=int, default=DEFAULT_ROLLING_WINDOW,
                    help="rolling-mean window in episodes (default 7 = one epoch)")
    ap.add_argument("--reverse-input", action="store_true",
                    help="determinism self-check: reverse the episode list after "
                         "loading; the report must be unchanged")
    ap.add_argument("--print-only", action="store_true",
                    help="print the summary without writing any file")
    ap.add_argument("--self-check", action="store_true",
                    help="run the built-in statistics assertions and exit")
    args = ap.parse_args(argv)

    if args.self_check:
        return self_check()
    if args.rolling_window < 1:
        print("ERROR: --rolling-window must be >= 1")
        return 2

    try:
        # resolve() first: source.run_dir must not embed the spelling of the
        # --run argument, or the report is not byte-identical across forms.
        run = load_run(Path(args.run).resolve(),
                       reverse_input=args.reverse_input)
        report = build_report(run, rolling_window=args.rolling_window)
    except AnalysisError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(render_summary(report))
    if args.print_only:
        return 0

    out = Path(args.out) if args.out else run.root / "analysis" / "day28_analysis.json"
    write_atomic(out, report_json(report))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
