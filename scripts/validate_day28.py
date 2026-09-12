#!/usr/bin/env python
"""Day-28 validator: the first full bandit-mode training run (PLAN line 274).

Audits the STORED artifacts of one finished run - results/training/
train-a0-d0-20260912T083120Z - against the frozen contract: PLAN section 16
hyperparameters (alpha 0.2, gamma 0.0, epsilon 1.0 -> 0.05 at 0.95/episode,
optimistic Q0 = +0.5, checkpoint every 25), PLAN section 18 splits, and the
Day-3 runner clock.

Nothing is executed here: no Spark, no training, no integration test. Every
number is READ from the manifest, the episode log, the transition records and
the checkpoint artifacts.

This validator makes NO claim of learning, convergence, improvement or
superiority over any baseline. PLAN freezes no reward-trend threshold for
Day 28, so none is invented; the observed per-epoch trajectory is reported and
the reader judges it. The early stop is a BUDGET-SAVING HEURISTIC - the greedy
argmax stopped changing for the required number of consecutive epochs - and is
NOT evidence of convergence.

PASS/FAIL/SKIP per check; overall PASS requires every applicable check green.
A SKIP is never a PASS and always states why it was skipped.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.policy_store import POLICY_SCHEMA, load_policy  # noqa: E402
from sparkrl.agent.q_learning import AGENT_VERSION  # noqa: E402
from sparkrl.experiments.grid import grid_fingerprint  # noqa: E402
from sparkrl.experiments.spec import TRAIN, split_of  # noqa: E402
from sparkrl.rl.action import MODE12  # noqa: E402
from sparkrl.rl.env import ENV_VERSION  # noqa: E402
from sparkrl.rl.reward import FORMULA_ID  # noqa: E402
from sparkrl.rl.state import STATE_VERSION  # noqa: E402
from sparkrl.training.loop import (CHECKPOINT_EVERY_EPISODES,  # noqa: E402
                                   EARLY_STOP_STABLE_EPOCHS, EPISODE_SCHEMA,
                                   LOOP_VERSION, MANIFEST_SCHEMA)

RUN_ID = "train-a0-d0-20260912T083120Z"
TRAINING_ROOT = PROJECT / "results" / "training"
RUN_DIR = TRAINING_ROOT / RUN_ID
ANALYZER = PROJECT / "scripts" / "analyze_day28.py"
AUDIT = PROJECT / "docs" / "research" / "DAY28_FIRST_FULL_TRAINING_AUDIT.md"
SRC = PROJECT / "src"

TRANSITION_SCHEMA = "rl-transition/v1"
LIVE_EXECUTION_CAP = 500                 # PLAN section 16, frozen
EPSILON_START, EPSILON_MIN, EPSILON_DECAY = 1.0, 0.05, 0.95
ALPHA, GAMMA, Q0_DEFAULT = 0.2, 0.0, 0.5
TOL = 1e-12

# every episode line must carry all of these (the full record contract)
REQUIRED_EPISODE_FIELDS = frozenset({
    "action_index", "action_mode", "action_source", "agent_episodes_after",
    "agent_rng_seed", "agent_updates_after", "budget_remaining_after", "cell",
    "checkpoint_policy_id", "code_version", "config_fingerprint", "config_name",
    "dataset_seed", "env_run_id", "env_version", "episode_index", "episode_key",
    "epoch_index", "epsilon_after", "epsilon_before", "epsilon_used",
    "executed", "executions_used_after", "failed", "feedback_from_failed_episode",
    "feedback_source", "last_reward_in", "loop_version", "position_in_epoch",
    "q_after", "q_before", "record_schema_version", "reward", "reward_source",
    "run_id", "run_kind", "state_key_after", "state_key_before", "state_schema",
    "t_ref_s", "td_delta", "transition_record_relpath", "update_error",
    "updated", "usable", "wall_s", "written_utc"})

# forbidden future components (PLAN: deferred / out of scope for Day 28).
# Matched against CODE ONLY - comments and docstrings are stripped first, so a
# docstring that names a component as deferred is not a violation.
FORBIDDEN_CODE = re.compile(
    r"\b(dqn|ppo|a2c|a3c|sac|td3|actor_critic|actorcritic|policy_gradient"
    r"|policygradient|reinforce|replay_buffer|replaybuffer|replaymemory"
    r"|target_network|targetnetwork|torch|tensorflow|keras|stable_baselines"
    r"|cachekey|cacheentry|cache_hit|cache_lookup|execution_cache"
    r"|executioncache|orchestrator|orchestrate)\b", re.IGNORECASE)

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print(f"{name:<32} {status:<5} {detail}")


@dataclass(frozen=True)
class Run:
    """One finished training run read off disk. Nothing is recomputed."""

    directory: Path
    manifest: dict[str, Any]
    episodes: tuple[dict[str, Any], ...]
    transitions: tuple[tuple[Path, dict[str, Any]], ...]

    @classmethod
    def load(cls, directory: Path) -> "Run":
        manifest_path = directory / "manifest.json"
        log_path = directory / "episodes.jsonl"
        if not manifest_path.exists():
            raise FileNotFoundError(f"missing manifest: {manifest_path}")
        if not log_path.exists():
            raise FileNotFoundError(f"missing episode log: {log_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        episodes = tuple(
            json.loads(line) for line
            in log_path.read_text(encoding="utf-8").splitlines() if line.strip())
        records = sorted((directory / "transitions").rglob("*.json"))
        transitions = tuple(
            (p, json.loads(p.read_text(encoding="utf-8"))) for p in records)
        return cls(directory, manifest, episodes, transitions)

    @property
    def executed(self) -> tuple[dict[str, Any], ...]:
        return tuple(e for e in self.episodes if e.get("executed"))


def _code_only(path: Path) -> str:
    """Source text with comments and string literals (docstrings) removed."""
    text = path.read_text(encoding="utf-8")
    try:
        toks = tokenize.generate_tokens(io.StringIO(text).readline)
        return " ".join(t.string for t in toks
                        if t.type not in (tokenize.COMMENT, tokenize.STRING))
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise RuntimeError(f"cannot tokenize {path}: {exc}") from exc


def _cell_of(episode: dict[str, Any]) -> tuple[str, str, int]:
    cell = episode["cell"]
    return cell["family"], cell["scale"], int(cell["dataset_seed"])


def main() -> int:
    try:
        run = Run.load(RUN_DIR)
    except Exception as exc:  # noqa: BLE001
        check("01 run_artifacts_present", False, f"{RUN_DIR.name}: {exc}")
        return _finish()

    m, eps, trans = run.manifest, run.episodes, run.transitions

    # 1. the run is present and self-describing (schema versions on every layer)
    schema_ok = (m.get("record_schema_version") == MANIFEST_SCHEMA
                 and all(e.get("record_schema_version") == EPISODE_SCHEMA
                         for e in eps)
                 and all(r.get("record_schema_version") == TRANSITION_SCHEMA
                         for _, r in trans)
                 and m.get("run_id") == RUN_ID
                 and m.get("run_kind") == "training"
                 and m.get("status") == "completed"
                 and m.get("loop_version") == LOOP_VERSION)
    check("01 run_self_describing", schema_ok,
          f"{RUN_ID}: manifest {m.get('record_schema_version')}, "
          f"{len(eps)} episode lines {EPISODE_SCHEMA}, "
          f"{len(trans)} transition records {TRANSITION_SCHEMA}")

    # 2. exploration replicate = training seed 0 (NOT the dataset seed)
    # the two names live on the manifest and the episode lines. Transition
    # records carry NEITHER; they carry a bare "seed" (the dataset seed) inside
    # metrics and observation_before, which is why the episode log - not the
    # transition record - is the seed-provenance join point.
    trans_named = sorted(path.name for path, r in trans
                         if "agent_rng_seed" in json.dumps(r)
                         or "dataset_seed" in json.dumps(r))
    trans_bare = [r for _, r in trans
                  if (r.get("metrics") or {}).get("seed") == 0
                  and (r.get("observation_before") or {}).get("seed") == 0]
    seeds_ok = (m.get("agent_rng_seed") == 0
                and m.get("dataset_seed") == 0
                and all(e.get("agent_rng_seed") == 0 for e in eps)
                and all(e.get("dataset_seed") == 0 for e in eps)
                and all("seed" not in e for e in eps)
                and not trans_named and len(trans_bare) == len(trans))
    check("02 agent_rng_seed_zero", seeds_ok,
          f"transition records naming a seed: {trans_named[:3]}" if trans_named
          else "agent_rng_seed == 0 on the manifest and all "
          f"{len(eps)} lines; dataset_seed == 0 recorded separately "
          "(exploration replicate != workload instance seed); no bare 'seed' "
          f"on any episode line. All {len(trans)} transition records carry "
          "NEITHER name and carry a bare seed == 0 under metrics and "
          "observation_before, so the episode log is the join point")

    # 3. bandit mode: gamma == 0.0 and every transition is terminal
    hp = m.get("hyperparameters", {})
    terminal = [not r.get("terminated") for _, r in trans]
    one_record_per_episode = (len(trans) == len(run.executed)
                              and len({e["env_run_id"] for e in run.executed})
                              == len(run.executed))
    bandit_ok = (hp.get("gamma") == GAMMA and not any(terminal)
                 and one_record_per_episode
                 and not any(k in e for e in eps
                             for k in ("step_index", "steps", "n_steps")))
    check("03 bandit_mode", bandit_ok,
          f"gamma={hp.get('gamma')}; all {len(trans)} transitions terminated; "
          "exactly one transition per episode, no multi-step rollout field")

    # 4. only authorized TRAIN cells (asserted through spec.split_of)
    cells = {_cell_of(e) for e in eps}
    non_train = sorted(c for c in cells if split_of(*c) != TRAIN)
    manifest_cells = {c["cell"] for c in m.get("schedule", {}).get("cells", [])}
    log_cells = {f"{f}|{s}" for f, s, _ in cells}
    check("04 train_cells_only", not non_train and log_cells <= manifest_cells,
          str(non_train) or
          f"{len(cells)} distinct cells, split_of() == '{TRAIN}' for every one; "
          f"scheduled set {sorted(manifest_cells)} "
          "(F3_rdd|medium excluded: t_ref_null)")

    # 5. no validation / test leakage anywhere in the recorded artifacts
    leaks: list[str] = []
    for family, scale, seed in cells:
        if seed in (3, 4) or scale == "large" or family == "F4_ski":
            leaks.append(f"episode cell {family}|{scale}|seed{seed}")
    for path, rec in trans:
        met = rec.get("metrics", {})
        obs = rec.get("observation_before", {})
        for src_name, blob in (("metrics", met), ("observation", obs)):
            if (blob.get("seed") in (3, 4) or blob.get("scale") == "large"
                    or blob.get("family") == "F4_ski"):
                leaks.append(f"{path.name} {src_name}")
        rel = path.relative_to(RUN_DIR).as_posix()
        if "seed3" in rel or "seed4" in rel or "/large/" in rel or "F4_ski" in rel:
            leaks.append(f"path {rel}")
    check("05 no_split_leakage", not leaks,
          str(leaks[:5]) or
          "no seed 3, no seed 4, no scale large, no F4_ski in the episode log "
          "or in any transition record (PLAN section 18; TEST frozen to Day 31)")

    # 6. Q0 provenance: source, fingerprint, aggregation, guard, accounting
    q0 = m.get("q0_provenance", {})
    accounting_ok = (q0.get("records_scanned")
                     == (q0.get("records_valid_used", 0)
                         + q0.get("records_invalid_skipped", 0)
                         + q0.get("records_tref_missing_skipped", 0)
                         + q0.get("records_b0_reference", 0)))
    q0_ok = (q0.get("source") == "exp002"
             and q0.get("aggregation") == "median"
             and q0.get("reward_formula") == FORMULA_ID
             and q0.get("state_schema") == STATE_VERSION
             and q0.get("grid_fingerprint") == grid_fingerprint()
             and isinstance(q0.get("spec_fingerprint"), str)
             and len(q0.get("spec_fingerprint", "")) == 64
             and "split_of()!=TRAIN" in q0.get("leakage_guard", "")
             and hp.get("q0_default") == Q0_DEFAULT
             and accounting_ok)
    check("06 q0_provenance", q0_ok,
          f"source={q0.get('source')} agg={q0.get('aggregation')} "
          f"spec_fp={str(q0.get('spec_fingerprint'))[:12]} "
          f"scanned={q0.get('records_scanned')} = valid "
          f"{q0.get('records_valid_used')} + invalid "
          f"{q0.get('records_invalid_skipped')} + t_ref_missing "
          f"{q0.get('records_tref_missing_skipped')} + b0_ref "
          f"{q0.get('records_b0_reference')}; optimistic Q0 "
          f"{hp.get('q0_default')}; leakage guard recorded")

    # 7. epsilon: frozen schedule, decayed exactly ONCE per completed episode
    want = [max(EPSILON_MIN, EPSILON_START * EPSILON_DECAY ** n)
            for n in range(len(eps))]
    got = [e["epsilon_used"] for e in eps]
    chained = all(abs(b["epsilon_used"] - a["epsilon_after"]) < TOL
                  for a, b in zip(eps, eps[1:]))
    stepped = all(abs(e["epsilon_after"]
                      - max(EPSILON_MIN, e["epsilon_used"] * EPSILON_DECAY)) < TOL
                  and abs(e["epsilon_before"] - e["epsilon_used"]) < TOL
                  for e in eps)
    eps_ok = (chained and stepped
              and all(abs(g - w) < TOL for g, w in zip(got, want))
              and hp.get("epsilon_start") == EPSILON_START
              and hp.get("epsilon_min") == EPSILON_MIN
              and hp.get("epsilon_decay") == EPSILON_DECAY)
    check("07 epsilon_schedule", eps_ok,
          f"{len(eps)} episodes: {got[0]:.4f} -> {got[-1]:.6f} "
          f"= 1.0 * 0.95**n (floor {EPSILON_MIN}); epsilon_used[k] == "
          "epsilon_after[k-1] on every line (decayed once per episode)")

    # 8. contract identity recorded on the run and equal to the frozen values
    cv = m.get("contract_versions", {})
    contract_ok = (cv.get("learner_version") == AGENT_VERSION
                   and cv.get("state_schema") == STATE_VERSION
                   and cv.get("grid_fingerprint") == grid_fingerprint()
                   and cv.get("action_mode") == MODE12
                   and cv.get("reward_formula") == FORMULA_ID
                   and hp.get("alpha") == ALPHA
                   and all(e.get("state_schema") == STATE_VERSION
                           and e.get("action_mode") == MODE12 for e in eps))
    check("08 contract_recorded", contract_ok,
          f"learner={cv.get('learner_version')} state={cv.get('state_schema')} "
          f"grid={str(cv.get('grid_fingerprint'))[:12]} "
          f"action={cv.get('action_mode')} reward={cv.get('reward_formula')} "
          f"alpha={hp.get('alpha')}")

    # 9. reward provenance: COPIED from env.step, never recomputed by the loop
    by_rel = {p.relative_to(RUN_DIR).as_posix(): r for p, r in trans}
    mismatched: list[str] = []
    for e in run.executed:
        rec = by_rel.get(e["transition_record_relpath"])
        if rec is None:
            mismatched.append(f"{e['episode_index']}: no record")
        elif rec["reward"]["value"] != e["reward"]:
            mismatched.append(f"{e['episode_index']}: reward differs")
        elif rec["reward"]["formula_id"] != FORMULA_ID:
            mismatched.append(f"{e['episode_index']}: formula "
                              f"{rec['reward']['formula_id']}")
    sources = {e.get("reward_source") for e in run.executed}
    loop_src = _code_only(SRC / "sparkrl" / "training" / "loop.py")
    recomputed = [t for t in ("RewardCalculator", "compute_reward",
                              "reward_from_metrics") if t in loop_src]
    check("09 reward_copied_from_env", not mismatched and not recomputed
          and sources == {"env.step (frozen R3)"},
          str(mismatched[:3] or recomputed) or
          f"all {len(run.executed)} rewards byte-equal to the stored env.step "
          f"value; reward_source == {sorted(sources)[0]!r}; the loop code "
          "constructs no reward calculator")

    # 10. budget accounting for this run + the REPORTED cross-run SC6 ledger
    budget = m.get("budget", {})
    live = budget.get("live_executions")
    this_ok = (live == len(trans) == len(run.executed)
               == m.get("counts", {}).get("episodes_completed")
               and budget.get("live_execution_cap") == LIVE_EXECUTION_CAP
               and live <= budget.get("budget_limit_this_run", 0))
    manifests = sorted(TRAINING_ROOT.glob("**/manifest.json"))
    ledger = sum(int(json.loads(p.read_text(encoding="utf-8"))
                     .get("budget", {}).get("live_executions", 0))
                 for p in manifests)
    all_records = len(list(TRAINING_ROOT.glob("**/transitions/**/*.json")))
    check("10 budget_accounting",
          this_ok and ledger == all_records and ledger <= LIVE_EXECUTION_CAP,
          f"this run: live_executions={live} == {len(trans)} transition "
          f"records == {len(run.executed)} executed episodes; cross-run SC6 "
          f"ledger over {len(manifests)} manifest(s) (smoke included) = "
          f"{ledger} live executions == {all_records} transition records on "
          f"disk (a stale manifest that never flushed would show up here as "
          f"records > ledger) vs cap {LIVE_EXECUTION_CAP} - REPORTED only, "
          "enforcement is per-process (durable cross-process enforcement "
          "COMP-EXP-11 is DEFERRED)")

    # 11. trajectory completeness: contiguous index, full fields, records exist
    indices = [e["episode_index"] for e in eps]
    missing_fields = sorted({f for e in eps
                             for f in REQUIRED_EPISODE_FIELDS - set(e)})
    uniform = len({frozenset(e) for e in eps}) == 1
    missing_records = [e["transition_record_relpath"] for e in run.executed
                       if not (RUN_DIR / e["transition_record_relpath"]).exists()]
    traj_ok = (indices == list(range(1, len(eps) + 1))
               and not missing_fields and uniform and not missing_records
               and len(eps) == m.get("counts", {}).get("episodes_completed"))
    check("11 trajectory_complete", traj_ok,
          str(missing_fields[:5] or missing_records[:3]) or
          f"episode_index 1..{len(eps)} with no gaps; every line carries all "
          f"{len(REQUIRED_EPISODE_FIELDS)} required fields (identical key set) "
          "and joins to an existing transition record on disk")

    # 12. checkpoint provenance: cadence 25 + a final, each artifact verifies
    ckpts = m.get("checkpoints", [])
    ckpt_dir = RUN_DIR / "checkpoints"
    problems: list[str] = []
    for c in ckpts:
        try:
            art = load_policy(c["policy_id"], ckpt_dir)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{c['policy_id'][:12]}: {exc}")
            continue
        if art.get("episodes") != c["episode_index"]:
            problems.append(f"{c['policy_id'][:12]}: episodes "
                            f"{art.get('episodes')} != index {c['episode_index']}")
        if art.get("policy_schema") != POLICY_SCHEMA \
                or art.get("learner_version") != AGENT_VERSION \
                or art.get("rng_seed") != 0:
            problems.append(f"{c['policy_id'][:12]}: contract drift")
    cadence = [c["episode_index"] for c in ckpts]
    completed = m.get("counts", {}).get("episodes_completed")
    final = m.get("final_policy") or {}
    ckpt_ok = (not problems and CHECKPOINT_EVERY_EPISODES == 25
               and all(i % 25 == 0 for i in cadence[:-1])
               and cadence[-1] == completed
               and final.get("policy_id") == ckpts[-1]["policy_id"])
    check("12 checkpoint_provenance", ckpt_ok,
          str(problems[:3]) or
          f"cadence {cadence} (every 25 + one final at {completed}); every "
          "artifact loads and verifies via policy_store.load_policy and its "
          "episodes counter equals its episode_index")

    # 13. identity uniqueness: run ids and transition record paths
    run_ids = [json.loads(p.read_text(encoding="utf-8")).get("run_id")
               for p in manifests]
    dup_runs = sorted({r for r in run_ids if run_ids.count(r) > 1})
    rels = [e["transition_record_relpath"] for e in run.executed]
    dup_paths = sorted({r for r in rels if rels.count(r) > 1})
    check("13 no_duplicate_ids", not dup_runs and not dup_paths,
          str(dup_runs + dup_paths) or
          f"{len(run_ids)} run id(s) under results/training/ all distinct; "
          f"{len(rels)} transition record paths in this run all distinct "
          "(no record was overwritten)")

    # 14. authoritative execution timing: the Day-3 runner clock, unsubstituted
    clocks = {r.get("metrics", {}).get("execution_time_source") for _, r in trans}
    timed = all(isinstance(r.get("metrics", {}).get("execution_time_s"), (int, float))
                for _, r in trans)
    check("14 runner_clock", clocks == {"runner"} and timed,
          f"execution_time_source == {sorted(str(c) for c in clocks)} on all "
          f"{len(trans)} records; no wall-clock or driver clock substituted")

    # 15. early stop consistent with the recorded greedy snapshots
    epochs = m.get("epochs", [])
    early = m.get("early_stop", {})
    required = early.get("stable_epochs_required")
    streak, first_fire = 0, None
    recomputed_streaks = []
    for prev, cur in zip([None] + epochs, epochs):
        if prev is not None and \
                cur["greedy_snapshot_sha256"] == prev["greedy_snapshot_sha256"]:
            streak += 1
        else:
            streak = 0
        recomputed_streaks.append(streak)
        if first_fire is None and streak >= required:
            first_fire = cur["epoch_index"]
    stop_ok = (required == EARLY_STOP_STABLE_EPOCHS
               and recomputed_streaks == [e["stability_streak"] for e in epochs]
               and early.get("triggered") is True
               and first_fire == early.get("at_epoch") == epochs[-1]["epoch_index"]
               and m.get("stop_reason") == "early_stop_policy_stable")
    check("15 early_stop_consistent", stop_ok,
          f"streaks {recomputed_streaks} recomputed from the snapshot hashes "
          f"match the record; fired at epoch {early.get('at_epoch')} after "
          f"{required + 1} identical consecutive greedy snapshots, never "
          "earlier. "
          "BUDGET-SAVING HEURISTIC (the greedy argmax stopped changing), "
          "NOT evidence of convergence")

    # 16. deterministic analysis: the analyzer must be byte-reproducible
    if not ANALYZER.exists():
        check("16 analysis_deterministic", None,
              f"{ANALYZER.name} does not exist yet - determinism cannot be "
              "tested (not a pass)")
    else:
        # written to a scratch directory: results/ is an immutable record and
        # this validator must not write into it
        # the two invocations spell the SAME run directory DIFFERENTLY: the
        # report must not embed the spelling of the --run argument, or a
        # reviewer re-running the documented command gets a different sha256
        # and (without --out) rewrites the pinned artifact under results/.
        spellings = (str(RUN_DIR),
                     RUN_DIR.relative_to(PROJECT).as_posix()
                     .replace("results/", "results/training/../", 1))
        with tempfile.TemporaryDirectory() as td:
            outs, blobs = [], []
            for name, run_arg in zip(("a.json", "b.json"), spellings):
                dest = Path(td) / name
                outs.append(subprocess.run(
                    [sys.executable, str(ANALYZER), "--run", run_arg,
                     "--out", str(dest)], capture_output=True, cwd=PROJECT))
                blobs.append(dest.read_bytes() if dest.exists() else None)
            if any(r.returncode != 0 for r in outs):
                tail = (outs[0].stderr.decode("utf-8", "replace").strip()
                        .splitlines() or ["no stderr"])[-1]
                check("16 analysis_deterministic", False,
                      f"{ANALYZER.name} exited {outs[0].returncode}: {tail}")
            elif blobs[0] is None:
                check("16 analysis_deterministic", None,
                      f"{ANALYZER.name} wrote no JSON to --out - there are no "
                      "bytes to compare (not a pass)")
            else:
                try:
                    json.loads(blobs[0].decode("utf-8"))
                    parsed = True
                except ValueError:
                    parsed = False
                # only the JSON report is compared: the console line names the
                # --out path, which differs between the two scratch files
                same = blobs[0] == blobs[1]
                check("16 analysis_deterministic", same and parsed,
                      f"two runs of {ANALYZER.name} over the run of record, "
                      f"spelled {spellings[0]!r} and {spellings[1]!r}: "
                      f"{len(blobs[0])} JSON bytes, byte-identical={same}, "
                      f"parses as JSON={parsed} (written to a scratch dir; "
                      "results/ untouched)")

    # 17. no prohibited future components in src/ (code only, not docstrings)
    hits = {}
    for path in sorted(SRC.rglob("*.py")):
        found = sorted({mo.group(0).lower()
                        for mo in FORBIDDEN_CODE.finditer(_code_only(path))})
        if found:
            hits[path.relative_to(PROJECT).as_posix()] = found
    check("17 no_future_components", not hits, str(hits) or
          f"{len(list(SRC.rglob('*.py')))} modules scanned with comments and "
          "docstrings stripped: no deep RL (DQN/PPO/actor-critic/policy "
          "gradient/replay/target net/torch/tf/keras), no execution cache "
          "(COMP-EXP-11), no orchestrator (COMP-EXP-12)")

    # 18. EXP-003 / EXP-005 / EXP-005b remain unstarted
    stray = sorted(p.relative_to(PROJECT).as_posix() for p in
                   list((PROJECT / "scripts").glob("*exp00[35]*"))
                   + list((PROJECT / "results" / "experiments").glob("*exp-00[35]*"))
                   + list((PROJECT / "src").rglob("*exp00[35]*")))
    check("18 no_exp003_005", not stray, str(stray) or
          "no EXP-003 / EXP-005 / EXP-005b script or artifact exists")

    # 19. the run's recorded contracts match the CODE as it stands today
    drift = {k: (got_v, want_v) for k, got_v, want_v in (
        ("env_version", cv.get("env_version"), ENV_VERSION),
        ("policy_schema", cv.get("policy_schema"), POLICY_SCHEMA),
        ("learner_version", cv.get("learner_version"), AGENT_VERSION),
        ("state_schema", cv.get("state_schema"), STATE_VERSION),
        ("reward_formula", cv.get("reward_formula"), FORMULA_ID),
        ("action_mode", cv.get("action_mode"), MODE12),
        ("grid_fingerprint", cv.get("grid_fingerprint"), grid_fingerprint()),
        ("loop_version", m.get("loop_version"), LOOP_VERSION),
        ("episode_schema", eps[0].get("record_schema_version"), EPISODE_SCHEMA),
        ("manifest_schema", m.get("record_schema_version"), MANIFEST_SCHEMA),
    ) if got_v != want_v}
    check("19 contract_compatible", not drift, str(drift) or
          "env / agent / loop contract versions recorded in the run are "
          "identical to the current code constants (artifacts still readable)")

    # 20. the audit document and its explicit no-learning-claim sentence
    if not AUDIT.exists():
        check("20 audit_document", None,
              f"{AUDIT.name} not written yet - no-learning-claim sentence "
              "cannot be checked (not a pass)")
    else:
        text = AUDIT.read_text(encoding="utf-8")
        low = text.lower()
        disclaimed = ("no claim of learning" in low
                      or "proves nothing about" in low
                      or "not evidence of convergence" in low)
        check("20 audit_document", disclaimed and "convergence" in low,
              f"{AUDIT.name}: {AUDIT.stat().st_size} bytes; explicit "
              "no-learning-claim sentence present" if disclaimed else
              f"{AUDIT.name} lacks an explicit no-learning-claim sentence")

    # observation only: the per-epoch mean reward trajectory. PLAN freezes NO
    # threshold for Day 28, so nothing here is graded PASS or FAIL.
    per_epoch: dict[int, list[float]] = {}
    for e in run.executed:
        per_epoch.setdefault(e["epoch_index"], []).append(float(e["reward"]))
    traj = ", ".join(f"e{k}={sum(v) / len(v):.4f}"
                     for k, v in sorted(per_epoch.items()))
    print("-" * 72)
    print(f"OBSERVATION (not a check): mean reward per epoch: {traj}")
    print("PLAN freezes no reward-trend threshold for Day 28; this trajectory "
          "is reported, not graded. It supports no claim of learning, "
          "convergence, improvement or superiority over any baseline.")
    return _finish()


def _finish() -> int:
    n_pass = sum(1 for _, s, _ in results if s == "PASS")
    n_fail = sum(1 for _, s, _ in results if s == "FAIL")
    n_skip = sum(1 for _, s, _ in results if s == "SKIP")
    print("-" * 72)
    print(f"OVERALL: {'PASS' if n_fail == 0 else 'FAIL'}  "
          f"({n_pass} passed, {n_skip} skipped, {n_fail} failed of {len(results)})")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
