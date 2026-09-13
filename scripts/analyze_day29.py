#!/usr/bin/env python
"""Day-29 analyzer: training replicates + policy agreement, the M8 gate.

PLAN line 275 (frozen, verbatim):

    | 29 | Training replicates | seeds {0,1,2}; policy inspection |
    | policies agree >= 70% (M8) |

Reads ONLY stored artifacts of three finished training runs:

    <run>/manifest.json                 (rl-training-run/v1)
    <run>/episodes.jsonl                (rl-training-episode/v1, one per episode)
    <run>/checkpoints/policy-*.json     (policy/v1)

No Spark, no training, no PySpark import, no wall clock, no RNG, and the agent
is never instantiated: select_action would advance the agent RNG, so the greedy
policy is extracted from the STORED q_table instead. Reading the same run
directories twice, in any order, produces a byte-identical artifact.

It writes results/training/analysis/day29_policy_agreement.json atomically
(tmp + os.replace) and prints a human-readable summary. The artifact is written
OUTSIDE every individual run directory: a finished run directory is an
immutable research record.

THE METRIC WAS PRE-SPECIFIED IN WRITING BEFORE ANY POLICY WAS INSPECTED.
PLAN gives the phrase "policies agree >= 70%" and no computation - no state
universe, no denominator, no unanimous-vs-pairwise rule - so the operator fixed
one in advance and it is binding. It is reproduced in PRE_SPECIFICATION below
and implemented literally here. The variants V1-V4 are reported for
transparency; they are NOT alternative verdicts and the primary denominator is
not reconsidered in the light of the number it produced.

THE GATE FAILED. M8 over the pre-specified primary denominator is 0.2000
against a 0.70 threshold. That is reported plainly, as a result.

NO LEARNING CLAIM IS MADE ANYWHERE. Agreement measures replicate consistency of
an argmax over stored tables, nothing more. It is not learning, not
convergence, not optimality and not a comparison against any baseline.

Usage:
    python scripts/analyze_day29.py
    python scripts/analyze_day29.py --out /tmp/a.json --reverse-input
    python scripts/analyze_day29.py --print-only
    python scripts/analyze_day29.py --self-check
"""
from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
TRAINING_ROOT = PROJECT / "results" / "training"
DEFAULT_OUT = TRAINING_ROOT / "analysis" / "day29_policy_agreement.json"

ANALYSIS_SCHEMA = "day29-policy-agreement/v1"
MANIFEST_SCHEMA = "rl-training-run/v1"
EPISODE_SCHEMA = "rl-training-episode/v1"

# The three replicate runs of record. Frozen: these ARE the Day-29 replicates.
REPLICATES: tuple[tuple[int, str], ...] = (
    (0, "train-a0-d0-20260912T112906Z"),
    (1, "train-a1-d0-20260912T115123Z"),
    (2, "train-a2-d0-20260912T120648Z"),
)

# Day-28's separate seed-0 run. NOT a replicate; a same-seed comparison point.
DAY28_SEED0_RUN = "train-a0-d0-20260912T083120Z"

M8_THRESHOLD = 0.70             # PLAN line 275, frozen

PRE_SPECIFICATION = {
    "fixed_before_any_policy_was_inspected": True,
    "why_a_pre_specification_was_needed":
        "PLAN line 275 freezes the phrase 'policies agree >= 70%' and no "
        "computation: no state universe, no denominator, no "
        "unanimous-vs-pairwise rule. A denominator chosen after seeing the "
        "policies would be a chosen result, so one was fixed in writing first "
        "and is binding regardless of the number it produces.",
    "greedy_extraction":
        "argmax over the frozen 12 actions of the stored policy/v1 q_table, "
        "ties broken to the LOWEST action index (frozen Day-26 rule). The "
        "agent is never instantiated and select_action is never called: that "
        "would advance the agent RNG. The stored artifact is read, nothing "
        "else.",
    "primary_denominator": "D_all3",
    "D_all3":
        "state keys visited (>= 1 episode) in ALL THREE runs. M8 = the "
        "fraction of those where all three greedy actions are equal.",
    "primary_rationale":
        "an unvisited state keeps its offline EXP-002 Q0 row, and all three "
        "replicates share the IDENTICAL frozen Q0, so such a state agrees "
        "trivially and carries no evidence about replicate consistency.",
    "V1_D_union_any": "states in the union of the three stored q_tables",
    "V2_D_visited_any": "states visited in at least one run",
    "V3_pairwise": "mean pairwise agreement over D_all3",
    "V4_trivial": "count of union states visited by NO run",
    "variants_are_not_verdicts":
        "V1-V4 are reported for transparency. The verdict is the primary "
        "denominator only; it is not reconsidered in the light of its result.",
}

NO_LEARNING_CLAIM = (
    "Agreement measures replicate consistency of an argmax over stored Q "
    "tables. It is NOT learning, NOT convergence, NOT optimality and NOT a "
    "comparison against any baseline. No such claim is made anywhere in this "
    "analysis."
)


class AnalysisError(RuntimeError):
    """An artifact is missing, unreadable or off-contract."""


# --- loading ------------------------------------------------------------------
@dataclass(frozen=True)
class Run:
    """One finished training run, loaded from disk. Nothing is mutated."""

    seed: int
    root: Path
    manifest: dict[str, Any]
    episodes: tuple[dict[str, Any], ...]
    final_policy: dict[str, Any] | None


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


def load_run(seed: int, root: Path, *, reverse_input: bool = False) -> Run:
    """Load a run directory. `reverse_input` is a determinism self-check only."""
    if not root.is_dir():
        raise AnalysisError(f"run directory not found: {root}")

    manifest = _read_json(root / "manifest.json")
    got = manifest.get("record_schema_version")
    if got != MANIFEST_SCHEMA:
        raise AnalysisError(
            f"{root / 'manifest.json'} has record_schema_version {got!r}, "
            f"expected {MANIFEST_SCHEMA!r}")
    stored_seed = manifest.get("agent_rng_seed")
    if stored_seed != seed:
        raise AnalysisError(
            f"{root.name} records agent_rng_seed {stored_seed!r}, expected "
            f"{seed!r}: this is not the replicate it is being loaded as")

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
    if policy is None:
        raise AnalysisError(f"{root.name} manifest carries no final_policy path: "
                            "the greedy policy cannot be extracted")

    return Run(seed=seed, root=root, manifest=manifest,
               episodes=tuple(episodes), final_policy=policy)


# --- small deterministic statistics -------------------------------------------
def _mean(xs: list[float]) -> float | None:
    # order-independent so the determinism self-check (--reverse-input)
    # produces byte-identical JSON; naive sum() is not.
    return math.fsum(xs) / len(xs) if xs else None


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0


# --- policy inspection --------------------------------------------------------
def greedy_policy(policy: dict[str, Any]) -> dict[str, int]:
    """argmax per state over the stored q_table, ties to the LOWEST index.

    Frozen Day-26 tie rule. The agent is NOT instantiated and select_action is
    NOT called: calling it would advance the agent RNG and mutate nothing that
    belongs to this analysis. Only the stored artifact is read.
    """
    q = policy.get("q_table") or {}
    out: dict[str, int] = {}
    for state in sorted(q):
        row = [float(v) for v in q[state]]
        if not row:
            raise AnalysisError(f"empty q_table row for state {state!r}")
        out[state] = max(range(len(row)), key=lambda i: (row[i], -i))
    return out


def visit_counts(episodes: tuple[dict[str, Any], ...]) -> dict[str, dict[int, int]]:
    """state_key_before -> action_index -> episode count. Order-independent."""
    visits: dict[str, dict[int, int]] = {}
    for e in episodes:
        key = e.get("state_key_before")
        if key is None:
            continue
        row = visits.setdefault(key, {})
        a = int(e["action_index"])
        row[a] = row.get(a, 0) + 1
    return visits


def _run_summary(run: Run) -> dict[str, Any]:
    m = run.manifest
    counts = dict(m.get("counts") or {})
    rewards = [float(e["reward"]) for e in run.episodes]
    eps_used = [float(e["epsilon_used"]) for e in
                sorted(run.episodes, key=lambda e: int(e["episode_index"]))]
    policy = run.final_policy or {}
    return {
        "agent_rng_seed": m.get("agent_rng_seed"),
        "dataset_seed": m.get("dataset_seed"),
        "run_id": m.get("run_id"),
        "run_dir": run.root.relative_to(PROJECT).as_posix()
        if run.root.is_relative_to(PROJECT) else run.root.as_posix(),
        "started_utc": m.get("started_utc"),
        "finished_utc": m.get("finished_utc"),
        "code_version": m.get("code_version"),
        "episodes_planned": counts.get("episodes_planned"),
        "episodes_completed": counts.get("episodes_completed"),
        "episodes_failed": counts.get("episodes_failed"),
        "episode_lines_read": len(run.episodes),
        "epochs_completed": len(m.get("epochs") or []),
        "stop_reason": m.get("stop_reason"),
        "early_stop_triggered": (m.get("early_stop") or {}).get("triggered"),
        "early_stop_at_epoch": (m.get("early_stop") or {}).get("at_epoch"),
        "live_executions": (m.get("budget") or {}).get("live_executions"),
        "budget_limit_this_run": (m.get("budget") or {}).get("budget_limit_this_run"),
        "mean_reward": _mean(rewards),
        "median_reward": _median(rewards),
        "min_reward": min(rewards) if rewards else None,
        "max_reward": max(rewards) if rewards else None,
        "final_epsilon_used": eps_used[-1] if eps_used else None,
        "final_policy_id": policy.get("policy_id"),
        "final_policy_schema": policy.get("policy_schema"),
        "states_in_final_policy": len(policy.get("q_table") or {}),
    }


# --- the M8 computation -------------------------------------------------------
def _fraction(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def agreement_block(greedy: dict[int, dict[str, int]],
                    visits: dict[int, dict[str, dict[int, int]]],
                    seeds: tuple[int, ...]) -> dict[str, Any]:
    """The pre-specified primary M8 figure plus variants V1-V4.

    Nothing here chooses a denominator: PRE_SPECIFICATION fixed the primary one
    before any policy was read, and it is applied literally.
    """
    union = sorted({s for seed in seeds for s in greedy[seed]})
    visited_any = sorted({s for seed in seeds for s in visits[seed]})
    d_all3 = sorted(s for s in union
                    if all(visits[seed].get(s) for seed in seeds))

    def unanimous(state: str) -> bool:
        actions = {greedy[seed].get(state) for seed in seeds}
        return len(actions) == 1 and None not in actions

    primary_agree = [s for s in d_all3 if unanimous(s)]
    v1_agree = [s for s in union if unanimous(s)]
    v2_agree = [s for s in visited_any if unanimous(s)]

    pairs = [(a, b) for i, a in enumerate(seeds) for b in seeds[i + 1:]]
    pairwise = {}
    for a, b in pairs:
        n = sum(1 for s in d_all3 if greedy[a].get(s) == greedy[b].get(s))
        pairwise[f"seed{a}_vs_seed{b}"] = {
            "states_compared": len(d_all3),
            "states_equal": n,
            "agreement": _fraction(n, len(d_all3)),
        }
    pair_values = [p["agreement"] for p in pairwise.values()]

    never_visited = [s for s in union if not any(visits[seed].get(s)
                                                 for seed in seeds)]

    per_state = []
    for state in union:
        actions = [greedy[seed].get(state) for seed in seeds]
        counts = {seed: sum(visits[seed].get(state, {}).values())
                  for seed in seeds}
        evidence = all(counts[seed] > 0 for seed in seeds)
        per_state.append({
            "state_key": state,
            "greedy_action_by_seed": {f"seed{seed}": actions[i]
                                      for i, seed in enumerate(seeds)},
            "episodes_in_state_by_seed": {f"seed{seed}": counts[seed]
                                          for seed in seeds},
            "distinct_actions_tried_by_seed": {
                f"seed{seed}": len(visits[seed].get(state, {}))
                for seed in seeds},
            "in_D_all3": evidence,
            "unanimous": unanimous(state),
            "agreement_is_trivial": (not any(counts[seed] > 0 for seed in seeds)
                                     and unanimous(state)),
            "note": ("evidence-bearing: visited by every run"
                     if evidence else
                     "NOT evidence-bearing: at least one run never visited this "
                     "state, so its row is still the shared frozen EXP-002 Q0"),
        })

    primary = _fraction(len(primary_agree), len(d_all3))
    passed = primary is not None and primary >= M8_THRESHOLD
    return {
        "pre_specification": PRE_SPECIFICATION,
        "seeds": list(seeds),
        "threshold": M8_THRESHOLD,
        "primary": {
            "denominator": "D_all3",
            "definition": PRE_SPECIFICATION["D_all3"],
            "states": d_all3,
            "states_total": len(d_all3),
            "states_unanimous": len(primary_agree),
            "unanimous_states": primary_agree,
            "disagreeing_states": [s for s in d_all3 if s not in primary_agree],
            "agreement": primary,
        },
        "variants": {
            "V1_D_union_any": {
                "definition": PRE_SPECIFICATION["V1_D_union_any"],
                "states_total": len(union),
                "states_unanimous": len(v1_agree),
                "agreement": _fraction(len(v1_agree), len(union)),
            },
            "V2_D_visited_any": {
                "definition": PRE_SPECIFICATION["V2_D_visited_any"],
                "states_total": len(visited_any),
                "states_unanimous": len(v2_agree),
                "agreement": _fraction(len(v2_agree), len(visited_any)),
            },
            "V3_pairwise_mean_over_D_all3": {
                "definition": PRE_SPECIFICATION["V3_pairwise"],
                "pairs": pairwise,
                "mean_agreement": _mean([v for v in pair_values
                                         if v is not None]),
            },
            "V4_union_states_visited_by_no_run": {
                "definition": PRE_SPECIFICATION["V4_trivial"],
                "states": never_visited,
                "count": len(never_visited),
                "of_union_total": len(union),
                "note": "these rows are still the shared frozen EXP-002 Q0, so "
                        "they agree for free and inflate any denominator that "
                        "includes them",
            },
            "note": PRE_SPECIFICATION["variants_are_not_verdicts"],
        },
        "verdict": {
            "gate": "M8",
            "plan_line": "PLAN line 275: policies agree >= 70% (M8)",
            "metric": primary,
            "threshold": M8_THRESHOLD,
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "statement": (
                "M8 PASSED" if passed else
                ("M8 FAILED: the pre-specified primary denominator D_all3 "
                 "is EMPTY (0 evidence-bearing states), so no agreement "
                 "figure exists; the empty-denominator rule fails the gate."
                 if primary is None else
                "M8 FAILED: greedy policy agreement over the pre-specified "
                "primary denominator D_all3 is "
                f"{primary:.4f} ({len(primary_agree)} of {len(d_all3)} "
                f"evidence-bearing states unanimous), below the frozen "
                f"{M8_THRESHOLD:.2f} threshold. This is the recorded result of "
                "Day 29. No denominator is re-chosen and no hyperparameter is "
                "retuned to move it.")),
        },
        "per_state": per_state,
        "no_learning_claim": NO_LEARNING_CLAIM,
    }


def evidence_density(greedy: dict[int, dict[str, int]],
                     visits: dict[int, dict[str, dict[int, int]]],
                     seeds: tuple[int, ...],
                     d_all3: list[str]) -> dict[str, Any]:
    """How thin the evidence behind each argmax actually is.

    Every greedy action in this analysis rests on the episodes listed here. A
    state with a handful of episodes spread over 12 actions has seen most of
    its actions zero times, so its argmax is largely the frozen EXP-002 Q0
    ordering, not anything the run measured.
    """
    per_seed = {}
    for seed in seeds:
        rows = {s: visits[seed].get(s, {}) for s in d_all3}
        episodes = {s: sum(r.values()) for s, r in rows.items()}
        total = sum(episodes.values())
        action_slots = {len(row) for row in
                        ((greedy[seed] and {}) or {}).values()} or None
        per_seed[f"seed{seed}"] = {
            "evidence_bearing_states": len(d_all3),
            "episodes_in_evidence_bearing_states": total,
            "episodes_per_evidence_bearing_state":
                _fraction(total, len(d_all3)),
            "episodes_by_state": {s: episodes[s] for s in d_all3},
            "distinct_actions_tried_by_state": {s: len(rows[s]) for s in d_all3},
            "max_distinct_actions_tried": max((len(r) for r in rows.values()),
                                              default=0),
            "unused": action_slots,
        }
        del per_seed[f"seed{seed}"]["unused"]
    return {
        "label": "EVIDENCE DENSITY - how many executions stand behind each "
                 "argmax. Reported so the agreement number is read with its "
                 "sample size, not instead of it.",
        "per_seed": per_seed,
        "note": "the action space is the frozen 12-action MODE12 grid; a state "
                "whose distinct_actions_tried is far below 12 has most of its "
                "Q row still at the shared frozen EXP-002 Q0 value",
    }


def same_seed_comparison(day29: Run, day28: Run) -> dict[str, Any]:
    """Day-28 seed-0 vs Day-29 seed-0: run-to-run variability at FIXED seed.

    CONTEXT ONLY. Both runs carry agent_rng_seed 0. This pair is NOT part of
    M8 and is not a replicate comparison: M8 is a CROSS-SEED measurement over
    seeds {0, 1, 2}.
    """
    g29 = greedy_policy(day29.final_policy or {})
    g28 = greedy_policy(day28.final_policy or {})
    union = sorted(set(g29) | set(g28))
    same = [s for s in union if g29.get(s) == g28.get(s)]
    v29, v28 = visit_counts(day29.episodes), visit_counts(day28.episodes)
    both_visited = [s for s in union if v29.get(s) and v28.get(s)]
    same_visited = [s for s in both_visited if g29.get(s) == g28.get(s)]
    return {
        "label": "CONTEXT ONLY - NOT PART OF M8. Both runs use agent_rng_seed "
                 "0, so this pair measures run-to-run variability at a FIXED "
                 "seed. M8 is the cross-seed measurement over seeds {0,1,2}.",
        "day28_run_id": day28.manifest.get("run_id"),
        "day29_run_id": day29.manifest.get("run_id"),
        "day28_agent_rng_seed": day28.manifest.get("agent_rng_seed"),
        "day29_agent_rng_seed": day29.manifest.get("agent_rng_seed"),
        "day28_episodes": len(day28.episodes),
        "day29_episodes": len(day29.episodes),
        "day28_stop_reason": day28.manifest.get("stop_reason"),
        "day29_stop_reason": day29.manifest.get("stop_reason"),
        "greedy_policies_identical": len(same) == len(union),
        "states_compared": len(union),
        "states_equal": len(same),
        "agreement_over_union": _fraction(len(same), len(union)),
        "states_visited_in_both": len(both_visited),
        "states_equal_over_visited_in_both": len(same_visited),
        "agreement_over_visited_in_both": _fraction(len(same_visited),
                                                    len(both_visited)),
        "per_state": [
            {"state_key": s,
             "day28_greedy_action": g28.get(s),
             "day29_greedy_action": g29.get(s),
             "equal": g29.get(s) == g28.get(s),
             "day28_episodes_in_state": sum(v28.get(s, {}).values()),
             "day29_episodes_in_state": sum(v29.get(s, {}).values())}
            for s in union],
        "note": "the Day-28 seed-0 run stopped early at 42 episodes while the "
                "Day-29 seed-0 replicate ran all 84 planned episodes, so the "
                "two are not the same trajectory and a difference here is not "
                "a defect",
    }


# --- report -------------------------------------------------------------------
def build_report(runs: tuple[Run, ...], day28: Run | None) -> dict[str, Any]:
    """Derive every Day-29 number from the loaded artifacts. Order-independent."""
    seeds = tuple(sorted(r.seed for r in runs))
    # Day-29 protocol: M8 is EXACTLY seeds {0,1,2} - a duplicate or a missing
    # seed must fail loudly, never silently distort the gate.
    if len(set(seeds)) != len(seeds):
        raise AnalysisError(f"duplicate agent seed in the replicate set: "
                            f"{seeds}")
    if set(seeds) != {0, 1, 2}:
        raise AnalysisError(f"replicate seeds {list(seeds)} != frozen set "
                            f"[0, 1, 2] (PLAN line 275)")
    by_seed = {r.seed: r for r in runs}
    greedy = {s: greedy_policy(by_seed[s].final_policy or {}) for s in seeds}
    visits = {s: visit_counts(by_seed[s].episodes) for s in seeds}

    for seed in seeds:
        run = by_seed[seed]
        counted = sum(sum(row.values()) for row in visits[seed].values())
        if counted != len(run.episodes):
            raise AnalysisError(
                f"seed {seed}: visit counts sum to {counted} but the episode "
                f"log has {len(run.episodes)} lines")

    agreement = agreement_block(greedy, visits, seeds)

    return {
        "analysis_schema_version": ANALYSIS_SCHEMA,
        "plan": {
            "line": 275,
            "verbatim": "| 29 | Training replicates | seeds {0,1,2}; policy "
                        "inspection | policies agree >= 70% (M8) |",
        },
        "claims": {
            "learning_demonstrated": False,
            "convergence_demonstrated": False,
            "baseline_comparison": None,
            "note": NO_LEARNING_CLAIM,
        },
        "runs": {f"seed{r.seed}": _run_summary(r)
                 for r in sorted(runs, key=lambda r: r.seed)},
        "greedy_policies": {f"seed{s}": greedy[s] for s in seeds},
        "visit_counts": {
            f"seed{s}": {
                state: {
                    "episodes": sum(visits[s][state].values()),
                    "by_action_index": {str(a): visits[s][state][a]
                                        for a in sorted(visits[s][state])},
                }
                for state in sorted(visits[s])
            } for s in seeds},
        "m8": agreement,
        "evidence_density": evidence_density(
            greedy, visits, seeds, agreement["primary"]["states"]),
        "same_seed_comparison_day28_vs_day29": (
            same_seed_comparison(by_seed[0], day28) if day28 is not None
            else {"available": False,
                  "note": f"{DAY28_SEED0_RUN} not found; the fixed-seed "
                          "comparison point is unavailable (this does not "
                          "affect M8)"}),
    }


# --- rendering ----------------------------------------------------------------
def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_summary(report: dict[str, Any]) -> str:
    m8 = report["m8"]
    verdict = m8["verdict"]
    out: list[str] = []
    w = out.append

    w("=" * 78)
    w("DAY 29 - TRAINING REPLICATES, POLICY INSPECTION AND THE M8 GATE")
    w("=" * 78)
    w("PLAN line 275: " + report["plan"]["verbatim"])
    w("")
    w("The metric was PRE-SPECIFIED in writing BEFORE any policy was")
    w("inspected: PLAN freezes the phrase and no computation. The primary")
    w("denominator is not reconsidered in the light of its result.")

    w("")
    w("-- the three replicate runs -------------------------------------------")
    w(f"{'seed':>4} {'run_id':<32} {'eps':>4} {'epo':>4} {'live':>5} "
      f"{'mean R':>9} {'med R':>9} {'stop_reason':<28}")
    for key in sorted(report["runs"]):
        r = report["runs"][key]
        w(f"{r['agent_rng_seed']:>4} {str(r['run_id']):<32} "
          f"{r['episode_lines_read']:>4} {r['epochs_completed']:>4} "
          f"{r['live_executions']:>5} {_fmt(r['mean_reward']):>9} "
          f"{_fmt(r['median_reward']):>9} {str(r['stop_reason']):<28}")
    for key in sorted(report["runs"]):
        r = report["runs"][key]
        w(f"  seed {r['agent_rng_seed']}: failed episodes "
          f"{r['episodes_failed']}, final epsilon "
          f"{_fmt(r['final_epsilon_used'], 6)}, "
          f"final policy {str(r['final_policy_id'])[:16]} "
          f"({r['states_in_final_policy']} states)")

    w("")
    w("-- greedy policy per seed (argmax of the stored q_table, ties to lowest)")
    w(f"{'state':<32} {'seed0':>6} {'seed1':>6} {'seed2':>6} "
      f"{'visits 0/1/2':>14} {'D_all3':>7} {'agree':>6}")
    for row in m8["per_state"]:
        g = row["greedy_action_by_seed"]
        v = row["episodes_in_state_by_seed"]
        visits = f"{v['seed0']}/{v['seed1']}/{v['seed2']}"
        w(f"{row['state_key']:<32} "
          f"{'a' + str(g['seed0']):>6} {'a' + str(g['seed1']):>6} "
          f"{'a' + str(g['seed2']):>6} {visits:>14} "
          f"{str(row['in_D_all3']):>7} "
          f"{('AGREE' if row['unanimous'] else 'DIFFER'):>6}")
    w("A state no run visited keeps the shared frozen EXP-002 Q0 row, so it")
    w("agrees trivially and carries no evidence; it is excluded from D_all3.")

    w("")
    w("-- M8 (PRIMARY, pre-specified) ----------------------------------------")
    p = m8["primary"]
    w(f"denominator D_all3 = {p['states_total']} state(s) visited by all three "
      f"runs")
    w(f"unanimous greedy action in {p['states_unanimous']} of "
      f"{p['states_total']}")
    w(f"M8 = {_fmt(p['agreement'])}   threshold {_fmt(m8['threshold'], 2)}   "
      f"=> {verdict['status']}")
    if p["disagreeing_states"]:
        w("states that DIFFER: " + ", ".join(p["disagreeing_states"]))

    w("")
    w("-- variants (transparency only, NOT alternative verdicts) --------------")
    v = m8["variants"]
    w(f"V1 D_union_any    {v['V1_D_union_any']['states_unanimous']}/"
      f"{v['V1_D_union_any']['states_total']} = "
      f"{_fmt(v['V1_D_union_any']['agreement'])}")
    w(f"V2 D_visited_any  {v['V2_D_visited_any']['states_unanimous']}/"
      f"{v['V2_D_visited_any']['states_total']} = "
      f"{_fmt(v['V2_D_visited_any']['agreement'])}")
    v3 = v["V3_pairwise_mean_over_D_all3"]
    w("V3 pairwise mean over D_all3 = "
      f"{_fmt(v3['mean_agreement'])}  (" + ", ".join(
          f"{k.replace('seed', '').replace('_vs_', '-')}="
          f"{_fmt(p2['agreement'], 2)}" for k, p2 in v3["pairs"].items()) + ")")
    w(f"V4 union states visited by NO run: "
      f"{v['V4_union_states_visited_by_no_run']['count']} of "
      f"{v['V4_union_states_visited_by_no_run']['of_union_total']} "
      "(trivial agreement)")

    w("")
    w("-- evidence density ---------------------------------------------------")
    ed = report["evidence_density"]
    w(f"{'seed':>4} {'states':>7} {'episodes':>9} {'eps/state':>10} "
      f"{'max distinct actions tried':>28}")
    for key in sorted(ed["per_seed"]):
        d = ed["per_seed"][key]
        w(f"{key.replace('seed', ''):>4} {d['evidence_bearing_states']:>7} "
          f"{d['episodes_in_evidence_bearing_states']:>9} "
          f"{_fmt(d['episodes_per_evidence_bearing_state'], 2):>10} "
          f"{d['max_distinct_actions_tried']:>28}")
    w("The action space is the frozen 12-action grid. Distinct actions tried "
      "per state:")
    for key in sorted(ed["per_seed"]):
        d = ed["per_seed"][key]
        w(f"  {key}: " + ", ".join(
            f"{s.split('|', 1)[-1]}={n}"
            for s, n in d["distinct_actions_tried_by_state"].items()))

    w("")
    w("-- same-seed comparison (CONTEXT ONLY, NOT PART OF M8) ----------------")
    ss = report["same_seed_comparison_day28_vs_day29"]
    if not ss.get("available", True):
        w(str(ss.get("note")))
    else:
        w(f"Day-28 seed-0 {ss['day28_run_id']} ({ss['day28_episodes']} "
          f"episodes, {ss['day28_stop_reason']})")
        w(f"Day-29 seed-0 {ss['day29_run_id']} ({ss['day29_episodes']} "
          f"episodes, {ss['day29_stop_reason']})")
        w(f"greedy policies identical: {ss['greedy_policies_identical']} "
          f"({ss['states_equal']}/{ss['states_compared']} states equal, "
          f"{_fmt(ss['agreement_over_union'])})")
        diff = [r["state_key"] for r in ss["per_state"] if not r["equal"]]
        w("states differing at FIXED seed: " + (", ".join(diff) or "none"))
        w("Both runs carry agent_rng_seed 0, so this pair measures run-to-run")
        w("variability at a fixed seed. It is context for the cross-seed M8")
        w("number and is NOT part of it.")

    w("")
    w("-- VERDICT ------------------------------------------------------------")
    w(f"M8: {verdict['status']}")
    w(verdict["statement"])
    w("")
    w(NO_LEARNING_CLAIM)
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
    # ties go to the LOWEST action index (frozen Day-26 rule)
    assert greedy_policy({"q_table": {"s": [0.1, 0.9, 0.9, 0.2]}}) == {"s": 1}
    assert greedy_policy({"q_table": {"s": [0.5] * 12}}) == {"s": 0}
    assert greedy_policy({"q_table": {"b": [1.0, 0.0], "a": [0.0, 1.0]}}) \
        == {"a": 1, "b": 0}
    eps = ({"state_key_before": "x", "action_index": 3},
           {"state_key_before": "x", "action_index": 3},
           {"state_key_before": "y", "action_index": 1})
    assert visit_counts(eps) == {"x": {3: 2}, "y": {1: 1}}
    assert visit_counts(eps) == visit_counts(tuple(reversed(eps)))

    # the M8 arithmetic, on a hand-built case with a known answer
    greedy = {0: {"a": 1, "b": 2, "c": 5}, 1: {"a": 1, "b": 3, "c": 5},
              2: {"a": 1, "b": 4, "c": 5}}
    visits = {0: {"a": {1: 2}, "b": {2: 1}}, 1: {"a": {1: 1}, "b": {3: 1}},
              2: {"a": {1: 1}, "b": {4: 1}}}          # "c" never visited
    blk = agreement_block(greedy, visits, (0, 1, 2))
    assert blk["primary"]["states"] == ["a", "b"]      # c excluded: unvisited
    assert blk["primary"]["agreement"] == 0.5          # a agrees, b does not
    assert blk["variants"]["V1_D_union_any"]["agreement"] == 2 / 3  # a and c
    assert blk["variants"]["V2_D_visited_any"]["agreement"] == 0.5
    assert blk["variants"]["V4_union_states_visited_by_no_run"]["count"] == 1
    assert blk["variants"]["V3_pairwise_mean_over_D_all3"]["mean_agreement"] \
        == 0.5
    assert blk["verdict"]["passed"] is False
    assert blk["verdict"]["status"] == "FAIL"

    # a genuinely unanimous case must pass, so the verdict is not hard-wired
    g2 = {s: {"a": 1, "b": 2} for s in (0, 1, 2)}
    v2 = {s: {"a": {1: 1}, "b": {2: 1}} for s in (0, 1, 2)}
    blk2 = agreement_block(g2, v2, (0, 1, 2))
    assert blk2["primary"]["agreement"] == 1.0
    assert blk2["verdict"]["passed"] is True and blk2["verdict"]["status"] == "PASS"

    # exactly at the threshold passes (>= 70%), just below does not
    assert _fraction(7, 10) >= M8_THRESHOLD
    assert not _fraction(69, 100) >= M8_THRESHOLD
    assert _mean([0.2, 0.2, 0.4]) == 0.26666666666666666
    assert _median([3.0, 1.0, 2.0]) == 2.0
    assert _median([4.0, 1.0, 3.0, 2.0]) == 2.5
    print("self-check OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Day-29 replicate/policy-agreement analyzer over stored "
                    "training artifacts (no Spark, no training)")
    ap.add_argument("--training-root", default=str(TRAINING_ROOT),
                    help="directory holding the run directories "
                         "(default: results/training)")
    ap.add_argument("--out", default=None,
                    help="output JSON path (default results/training/analysis/"
                         "day29_policy_agreement.json)")
    ap.add_argument("--reverse-input", action="store_true",
                    help="determinism self-check: reverse each episode list "
                         "after loading; the report must be unchanged")
    ap.add_argument("--print-only", action="store_true",
                    help="print the summary without writing any file")
    ap.add_argument("--self-check", action="store_true",
                    help="run the built-in assertions and exit")
    args = ap.parse_args(argv)

    if args.self_check:
        return self_check()

    # resolve() first: run_dir must not embed the spelling of the argument, or
    # the report is not byte-identical across equivalent spellings.
    root = Path(args.training_root).resolve()
    try:
        runs = tuple(load_run(seed, root / run_id,
                              reverse_input=args.reverse_input)
                     for seed, run_id in REPLICATES)
        day28_dir = root / DAY28_SEED0_RUN
        day28 = (load_run(0, day28_dir, reverse_input=args.reverse_input)
                 if day28_dir.is_dir() else None)
        report = build_report(runs, day28)
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
