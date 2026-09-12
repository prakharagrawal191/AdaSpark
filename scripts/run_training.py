#!/usr/bin/env python
"""Day-27 training-loop driver (PLAN line 273).

Runs ONE training run of the frozen tabular Q-learning agent against the frozen
SparkTuningEnv. Hyperparameters come from PLAN section 16 via configs/rl.yaml;
this script exposes NO epsilon / alpha / gamma / checkpoint-interval flag and
there is deliberately no bare ``--seed`` flag - the two seeds have different
meanings and are named separately:

    --agent-seed    PLAN-16 training seed = EXPLORATION replicate (0, 1 or 2)
    --dataset-seed  workload instance seed (only 0 is calibrated for T_ref)

A run of this script records that the machinery executed. It supports NO claim
of learning, convergence, improvement or superiority.

Usage:
    python scripts/run_training.py --agent-seed 0 --episodes 70
    python scripts/run_training.py --agent-seed 0 --smoke
    python scripts/run_training.py --agent-seed 0 --episodes 70 --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.training.loop import (  # noqa: E402
    KIND_SMOKE, KIND_TRAINING, NO_CLAIM, EpisodeOutcome, RunDirExistsError,
    TrainingConfig, TrainingPlanError, build_env_and_agent, build_plan,
    run_training,)

DEFAULT_BASE_CONFIG = PROJECT / "configs" / "baseline_b0.yaml"

# Smoke shape (D2/D4): one cell, a tiny episode count that always exercises
# the epoch boundary, epsilon decay across episodes and the final checkpoint.
# The "stability streak reaching 2" is NOT part of the guaranteed smoke
# coverage (CONFIRMED fix 9): epoch 2 normally inserts a positive-reward
# `gt0` key Q0 lacks, so the greedy snapshot changes and the streak resets.
# Reaching 2 needs four epochs on an unchanging snapshot, not three.
SMOKE_CELLS = ["F1_agg|small"]
SMOKE_EPISODES = 3


def _progress(outcome: EpisodeOutcome) -> None:
    mark = "FAIL" if outcome.failed else "ok  "
    ckpt = (f"  ckpt={outcome.checkpoint_policy_id[:12]}"
            if outcome.checkpoint_policy_id else "")
    print(f"[ep {outcome.episode_index:3d} epoch {outcome.epoch_index:3d}] {mark} "
          f"{outcome.cell.key():<16} a={outcome.action_index:2d} "
          f"({outcome.action_source:<7}) eps={outcome.epsilon_used:.3f} "
          f"r={outcome.reward:+.4f} used={outcome.executions_used_after}{ckpt}",
          flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Day-27 training loop (one run; PLAN line 273)")
    ap.add_argument("--agent-seed", type=int, required=True,
                    help="PLAN-16 training seed = EXPLORATION replicate; "
                         "validated against configs/rl.yaml training_seeds")
    ap.add_argument("--dataset-seed", type=int, default=0,
                    help="workload instance seed (only 0 has a calibrated T_ref)")
    ap.add_argument("--episodes", type=int, default=None,
                    help="required unless --smoke; PLAN freezes no episode count")
    ap.add_argument("--cells", default=None,
                    help="comma list, e.g. 'F1_agg|small,F2_join|small' "
                         "(default: every calibrated TRAIN cell)")
    ap.add_argument("--budget", type=int, default=None,
                    help="may only LOWER the frozen 500 cap")
    ap.add_argument("--smoke", action="store_true",
                    help="F1_agg|small, 3 episodes, budget 3, smoke run root")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan + pre-flight only; no Spark, no run directory")
    ap.add_argument("--run-root", default=None,
                    help="override the run root (default from configs/rl.yaml)")
    ap.add_argument("--policy-dir", default=None,
                    help="default <run_dir>/checkpoints; models/policies is "
                         "reserved for deliberately published policies")
    ap.add_argument("--base-config", default=str(DEFAULT_BASE_CONFIG))
    ap.add_argument("--no-sysmon", action="store_true")
    args = ap.parse_args(argv)

    cfg = TrainingConfig.from_yaml()
    if args.smoke:
        episodes = SMOKE_EPISODES
        cells = list(SMOKE_CELLS)
        budget = SMOKE_EPISODES
        run_kind = KIND_SMOKE
    else:
        if args.episodes is None:
            print("ERROR: --episodes is required unless --smoke (PLAN freezes "
                  "no episode count; Day 28 owns that number)", file=sys.stderr)
            return 2
        episodes = int(args.episodes)
        cells = ([c for c in args.cells.split(",") if c.strip()]
                 if args.cells else None)
        budget = args.budget
        run_kind = KIND_TRAINING
        if budget is not None and budget > cfg.live_execution_cap:
            print(f"ERROR: --budget {budget} may only LOWER the frozen "
                  f"{cfg.live_execution_cap}-execution cap (PLAN section 16/SC6)",
                  file=sys.stderr)
            return 2

    try:
        plan = build_plan(agent_rng_seed=args.agent_seed, episodes=episodes,
                          run_kind=run_kind, dataset_seed=args.dataset_seed,
                          cell_keys=cells, budget_limit=budget, config=cfg,
                          policy_dir=args.policy_dir, run_root=args.run_root)
    except (TrainingPlanError, RunDirExistsError) as exc:
        print(f"PLAN REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(f"run kind               : {plan.run_kind}")
    print(f"run id                 : {plan.run_id}")
    print(f"agent_rng_seed         : {plan.agent_rng_seed}  "
          f"(PLAN-16 training seed = EXPLORATION replicate)")
    print(f"dataset_seed           : {plan.dataset_seed}  "
          f"(workload instance seed; T_ref calibrated for seed 0 only)")
    print(f"T_ref source           : {plan.t_ref_source}")
    for cell in plan.cells:
        print(f"  cell   {cell.key():<16} T_ref={cell.t_ref_s:9.6f}s")
    for exc_cell in plan.excluded:
        print(f"  EXCLUDED {str(exc_cell['cell']):<14} reason="
              f"{exc_cell['reason']} t_ref_s={exc_cell['t_ref_s']}")
    print(f"episodes planned       : {len(plan.episodes)} "
          f"({plan.episodes_per_epoch} per epoch)")
    print(f"budget limit this run  : {plan.budget_limit} "
          f"(frozen cap {cfg.live_execution_cap}; smoke executions COUNT)")
    print(f"run dir                : {plan.run_dir}")
    print(f"policy dir             : {plan.policy_dir}")
    print(f"NO CLAIM               : {NO_CLAIM}")

    if args.dry_run:
        print(json.dumps(plan.to_dict(), indent=1, sort_keys=True))
        return 0

    base = SparkConfig.from_yaml(args.base_config)
    env, agent, q0_provenance = build_env_and_agent(
        plan, base, sysmon_enabled=not args.no_sysmon)
    try:
        result = run_training(plan, env=env, agent=agent,
                              q0_provenance=q0_provenance, config=cfg,
                              on_episode=_progress)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - abort loud, manifest is finalized
        print(f"TRAINING ABORTED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"\nstatus                 : {result.status} / {result.stop_reason}")
    print(f"episodes completed     : {result.episodes_completed} "
          f"({result.episodes_failed} failed)")
    print(f"epochs completed       : {result.epochs_completed} "
          f"(early stop: {result.early_stopped})")
    print(f"live executions        : {result.executions_used}")
    print(f"checkpoints            : {len(result.checkpoints)}")
    print(f"final policy           : {result.final_policy_id}")
    print(f"manifest               : {result.manifest_path}")
    print(f"NO CLAIM               : {NO_CLAIM}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
