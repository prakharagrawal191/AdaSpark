"""Training loop layer (Day 27): episode schedule, checkpoints, budget guard.

PLAN line 273 only. No execution cache (COMP-EXP-11), no experiment
orchestrator (COMP-EXP-12), no resume/warm start, no DQN/PPO/replay buffer,
no second Spark runner, no reward or T_ref recomputation.

A training run records machinery execution only; it supports no claim of
learning, convergence, improvement or superiority.
"""
from sparkrl.training.loop import (  # noqa: F401
    CHECKPOINT_EVERY_EPISODES,
    EARLY_STOP_STABLE_EPOCHS,
    EPISODE_SCHEMA,
    EPOCH_DEFINITION,
    LOOP_VERSION,
    MANIFEST_SCHEMA,
    BudgetPlanError,
    Cell,
    Episode,
    EpisodeOutcome,
    RunDirExistsError,
    TrainingConfig,
    TrainingPlan,
    TrainingPlanError,
    TrainingResult,
    build_env_and_agent,
    build_plan,
    greedy_snapshot,
    plan_episodes,
    run_training,
)
