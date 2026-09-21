"""Day-27 training loop (PLAN line 273; hyperparameters frozen by PLAN section 16).

Owns: episode scheduling, the run's append-only JSONL episode log and its run
manifest, the checkpoint cadence, the epoch / early-stop criterion, and the
last_reward thread. Delegates everything else: Spark + reward + T_ref + split
and budget guards -> sparkrl.rl.env.SparkTuningEnv; epsilon schedule + Q update
-> sparkrl.agent.q_learning.QLearningAgent; serialization ->
sparkrl.agent.policy_store; offline Q0 -> sparkrl.agent.q0.

A run of this loop records that the machinery executed. It supports NO claim of
learning, convergence, improvement or superiority.

Seed vocabulary (the bare name "seed" is deliberately absent from this module):
* ``agent_rng_seed``  - PLAN section 16 "3 training seeds {0,1,2}" = the
  EXPLORATION replicate; it reaches QLearningAgent(rng_seed=...) only.
* ``dataset_seed``    - the workload instance seed. T_ref is calibrated for
  dataset seed 0 only, so it is fixed at 0 and reaches exactly one annotated
  ``env.reset`` call site.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

from sparkrl.agent.policy_store import (POLICY_SCHEMA, PolicyCorrupt,
                                        PolicyExistsError,
                                        build_policy_artifact, save_policy)
from sparkrl.agent.q0 import (build_neutral_q0, build_q0_from_exp002,
                              neutral_state_schema)
from sparkrl.agent.q_learning import (AGENT_VERSION, DEFAULT_RL_YAML,
                                      InvalidTransition, QLearningAgent,
                                      RLConfigError, Transition, state_key_of)
from sparkrl.experiments.runner import QueueLock, code_version
from sparkrl.experiments.spec import (TEST_SEEDS, TRAIN, TRAIN_FAMILIES,
                                      TRAIN_SCALES, VALIDATION_SEEDS,
                                      split_of)
from sparkrl.rl.env import (BudgetExhausted, EpisodeDone, SparkTuningEnv,
                            SplitViolation, TRefMissing)
from sparkrl.rl.state import SCHEMA_V15
from sparkrl.rl.tref import DEFAULT_GATE_PATH, TRefStore
from sparkrl.spark.config import SparkConfig
from sparkrl.training.ablation import (ABLATION_EPISODES_PER_SEED,
                                       ABLATION_SEEDS, ABLATION_VARIANTS)

PROJECT = Path(__file__).resolve().parents[3]

LOOP_VERSION = "training-loop/v1"
EPISODE_SCHEMA = "rl-training-episode/v1"
MANIFEST_SCHEMA = "rl-training-run/v1"
EPOCH_DEFINITION = "one_full_pass_over_the_planned_cell_cycle"   # D1
CHECKPOINT_EVERY_EPISODES = 25    # PLAN section 16, verbatim
EARLY_STOP_STABLE_EPOCHS = 2      # PLAN section 16, verbatim
CALIBRATED_DATASET_SEED = 0       # measured: TRefStore calibrates dataset seed 0 only

KIND_TRAINING, KIND_SMOKE = "training", "smoke"

STOP_COMPLETED = "planned_episodes"            # exit 0
STOP_EARLY = "early_stop_policy_stable"        # exit 0
STOP_BUDGET = "budget_exhausted"               # exit 0
STOP_INTERRUPTED = "interrupted"               # exit 130
# abort stop_reasons (exit 1): "tref_missing" | "split_violation" |
# "episode_done" | "invalid_transition" | "policy_exists" | "log_write_failed"

STATUS_RUNNING = "running"
STATUS_COMPLETED, STATUS_TRUNCATED = "completed", "truncated"
STATUS_INTERRUPTED, STATUS_FAILED = "interrupted", "failed"

NO_CLAIM = ("a training run records machinery execution only; no claim of "
            "learning, improvement, convergence or superiority is supported "
            "by this artifact")

SEED_SEMANTICS = (
    "agent_rng_seed = PLAN section 16 training seed (exploration replicate); "
    "dataset_seed = workload instance seed (T_ref calibrated for dataset "
    "seed 0 only)")

STATE_ALIASING_NOTE = (
    "the frozen size binning maps BOTH small and medium to bin S, so "
    "F1_agg|small (T_ref 22.35 s) and F1_agg|medium (T_ref 36.67 s) share one "
    "Q row; same for F2_join and F5_mixed. Reward variance driven by which "
    "cell ran is indistinguishable from within-state noise.")

BUDGET_ENFORCEMENT_NOTE = (
    "in-run only; the env counter is per-process. Cross-run SC6 totals are "
    "the SUM over manifests, REPORTED not enforced (COMP-EXP-11 deferred)")

RECOVERY_PROCEDURE = (
    "a crashed run's consumed live executions are counted from the JSON files "
    "under transitions/; the run is NOT resumed, it is re-planned into a new "
    "run directory")

EARLY_STOP_RULE = "greedy snapshot identical at 3 consecutive epoch boundaries"

# Exception -> stop_reason for the ABORT class (exit 1). BudgetExhausted is a
# CLEAN stop and is deliberately absent.
_ABORT_REASONS: tuple[tuple[type[BaseException], str], ...] = (
    (TRefMissing, "tref_missing"),
    (SplitViolation, "split_violation"),
    (EpisodeDone, "episode_done"),
    (InvalidTransition, "invalid_transition"),
    (PolicyExistsError, "policy_exists"),
    (PolicyCorrupt, "policy_exists"),
    (OSError, "log_write_failed"),
)

# env.step guards that ALL raise BEFORE execute_run (T_ref, split, episode and
# budget). Zero live executions are consumed, so the execution counter is
# exact and such an abort is NOT a mid-step interrupt. Stamping one as
# "interrupted_mid_step" would claim a budget uncertainty that does not exist.
_PRE_EXECUTION_STEP_ABORTS: tuple[type[BaseException], ...] = (
    TRefMissing, SplitViolation, EpisodeDone, BudgetExhausted,
)


# --- errors: exactly three new classes ----------------------------------------
class TrainingPlanError(ValueError):
    """Plan refused BEFORE any Spark: non-TRAIN cell, no calibrated T_ref,
    dataset_seed != 0, no surviving cell, episodes < 1."""


class BudgetPlanError(TrainingPlanError):
    """Planned episodes exceed the budget limit (refused before any Spark)."""


class RunDirExistsError(RuntimeError):
    """Run directory already exists; never append into a prior run's log."""


# --- dataclasses ---------------------------------------------------------------
@dataclass(frozen=True)
class TrainingConfig:
    """The additive configs/rl.yaml ``training:`` block (frozen-validated)."""

    loop_version: str
    epoch_definition: str
    checkpoint_every_episodes: int    # frozen-validated == 25
    early_stop_stable_epochs: int     # frozen-validated == 2
    dataset_seed: int                 # frozen-validated == 0
    run_root: str
    smoke_run_root: str
    live_execution_cap: int           # existing top-level key, == 500
    training_seeds: tuple[int, ...]   # existing top-level key, == (0, 1, 2)

    @classmethod
    def from_yaml(cls, path: str | Path = DEFAULT_RL_YAML) -> "TrainingConfig":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        block = raw.get("training")
        if not isinstance(block, dict):
            raise RLConfigError(
                f"{path}: the additive 'training:' block is absent (Day 27)")
        if block.get("checkpoint_every_episodes") != CHECKPOINT_EVERY_EPISODES:
            raise RLConfigError(
                f"checkpoint_every_episodes="
                f"{block.get('checkpoint_every_episodes')!r} disagrees with the "
                f"frozen PLAN-section-16 value {CHECKPOINT_EVERY_EPISODES}")
        if block.get("early_stop_stable_epochs") != EARLY_STOP_STABLE_EPOCHS:
            raise RLConfigError(
                f"early_stop_stable_epochs="
                f"{block.get('early_stop_stable_epochs')!r} disagrees with the "
                f"frozen PLAN-section-16 value {EARLY_STOP_STABLE_EPOCHS}")
        if block.get("dataset_seed") != CALIBRATED_DATASET_SEED:
            raise RLConfigError(
                f"dataset_seed={block.get('dataset_seed')!r}: T_ref is "
                f"calibrated for dataset seed {CALIBRATED_DATASET_SEED} only "
                f"(measured fact, not a tuning choice)")
        if block.get("epoch_definition") != EPOCH_DEFINITION:
            raise RLConfigError(
                f"epoch_definition={block.get('epoch_definition')!r} != "
                f"{EPOCH_DEFINITION!r}")
        cap = raw.get("live_execution_cap")
        if cap != 500:
            raise RLConfigError(
                f"live_execution_cap={cap!r} != 500 (PLAN section 16 / SC6)")
        seeds = raw.get("training_seeds")
        if list(seeds or []) != [0, 1, 2]:
            raise RLConfigError(
                f"training_seeds={seeds!r} != [0, 1, 2] (PLAN section 16)")
        for key in ("run_root", "smoke_run_root"):
            if not isinstance(block.get(key), str) or not block[key]:
                raise RLConfigError(f"training.{key} missing/invalid")
        return cls(loop_version=str(block.get("loop_version", LOOP_VERSION)),
                   epoch_definition=str(block["epoch_definition"]),
                   checkpoint_every_episodes=int(block["checkpoint_every_episodes"]),
                   early_stop_stable_epochs=int(block["early_stop_stable_epochs"]),
                   dataset_seed=int(block["dataset_seed"]),
                   run_root=str(block["run_root"]),
                   smoke_run_root=str(block["smoke_run_root"]),
                   live_execution_cap=int(cap),
                   training_seeds=tuple(int(s) for s in seeds))


@dataclass(frozen=True)
class Cell:
    """One trainable workload cell. ``dataset_seed`` is NEVER an agent seed."""

    family: str
    scale: str
    dataset_seed: int
    t_ref_s: float                 # non-null by construction

    def key(self) -> str:
        return f"{self.family}|{self.scale}"


@dataclass(frozen=True)
class Episode:
    """A PLANNED episode. Carries no results."""

    index: int                     # 1-based, global
    epoch: int                     # 1-based
    rep: int                       # == epoch (D2): unique transition record path
    cell: Cell


@dataclass(frozen=True)
class TrainingPlan:
    run_id: str                    # train-a<A>-d<D>-<YYYYmmddTHHMMSSZ>
    run_kind: str                  # "training" | "smoke"
    agent_rng_seed: int            # PLAN-16 training seed = EXPLORATION replicate
    dataset_seed: int              # workload instance seed, fixed 0
    cells: tuple[Cell, ...]
    excluded: tuple[dict[str, Any], ...]
    episodes: tuple[Episode, ...]
    episodes_per_epoch: int        # DERIVED == len(cells)
    budget_limit: int
    run_dir: Path
    policy_dir: Path
    t_ref_source: str
    variant: str | None = None     # EXP-007 A1/A2 (DEC-023); None = main study
    state_schema: str = SCHEMA_V15  # env encoder schema for this run

    def to_dict(self) -> dict[str, Any]:
        """The --dry-run payload (printed verbatim; no run directory touched)."""
        return {
            "loop_version": LOOP_VERSION,
            "run_id": self.run_id,
            "run_kind": self.run_kind,
            "agent_rng_seed": self.agent_rng_seed,
            "dataset_seed": self.dataset_seed,
            "exp007_variant": self.variant,
            "state_schema": self.state_schema,
            "seed_semantics": SEED_SEMANTICS,
            "schedule": {
                "cells": [{"cell": c.key(), "t_ref_s": c.t_ref_s}
                          for c in self.cells],
                "excluded_cells": [dict(e) for e in self.excluded],
                "order": "fixed_round_robin_over_sorted_cells",
                "epoch_definition": EPOCH_DEFINITION,
                "episodes_per_epoch": self.episodes_per_epoch,
                "episodes_planned": len(self.episodes),
            },
            "episodes": [{"episode_index": e.index, "epoch_index": e.epoch,
                          "rep": e.rep, "cell": e.cell.key()}
                         for e in self.episodes],
            "budget_limit": self.budget_limit,
            "run_dir": str(self.run_dir),
            "policy_dir": str(self.policy_dir),
            "t_ref_source": self.t_ref_source,
            "learning_claim": {"learning_demonstrated": False,
                               "convergence_demonstrated": False,
                               "baseline_comparison": None, "note": NO_CLAIM},
        }


@dataclass(frozen=True)
class EpisodeOutcome:
    """What ``on_episode`` receives; also the episode-log line's source."""

    episode_index: int
    epoch_index: int
    cell: Cell
    action_index: int
    action_source: str             # "explore" | "exploit" (best effort)
    epsilon_used: float
    reward: float
    usable: bool
    failed: bool
    updated: bool
    td_delta: float | None
    epsilon_after: float
    executions_used_after: int
    env_run_id: str
    transition_record_relpath: str
    checkpoint_policy_id: str | None


@dataclass(frozen=True)
class TrainingResult:
    run_id: str
    run_dir: Path
    status: str                    # completed | truncated | interrupted | failed
    stop_reason: str
    exit_code: int
    episodes_completed: int
    episodes_failed: int
    epochs_completed: int
    executions_used: int
    early_stopped: bool
    checkpoints: tuple[dict[str, Any], ...]
    final_policy_id: str | None
    manifest_path: Path
    episode_log_path: Path


def _dataset_seed_probe_seed(seed: int) -> str:
    """Classify one DATASET seed on a canonical TRAIN cell (PLAN section 18).

    "F1_agg|small" is TRAIN for every trainable seed, so ``split_of`` on it
    isolates the seed axis: the result answers "what split is this DATASET
    seed?" without a cell universe walk.
    """
    return split_of(TRAIN_FAMILIES[0], TRAIN_SCALES[0], int(seed))


def _dataset_seed_refusal(seed: int) -> str:
    """The true refusal reason for one DATASET seed (CONFIRMED fix 1).

    TRAIN-but-uncalibrated seeds (1, 2) are refused for T_REF CALIBRATION;
    split seeds (validation 3, test 4) are refused because they are NOT
    TRAIN (PLAN section 18). The old text blamed calibration for every
    seed, which names the one condition expected to CHANGE (broader T_ref
    calibration) and denies the one that never does (the Day-31 test
    freeze) for the TEST seed.
    """
    if _dataset_seed_probe_seed(seed) != TRAIN:
        split = _dataset_seed_probe_seed(seed)
        return (f"dataset_seed={seed} refused: PLAN section 18 SPLIT. "
                f"dataset_seed {seed} holds split={split!r}; training "
                f"consumes TRAIN data only, at the calibrated dataset "
                f"seed {CALIBRATED_DATASET_SEED} (the Day-31 test freeze "
                f"never changes).")
    return (f"dataset_seed={seed} refused: T_REF CALIBRATION. EXP-002 "
            f"calibrated dataset seed {CALIBRATED_DATASET_SEED} only, "
            f"so env.step would raise TRefMissing before executing. This "
            f"is NOT the split - dataset seeds 1 and 2 are "
            f"legitimately TRAIN.")


def trainable_cells(tref_store: TRefStore | None = None, *,
                    dataset_seed: int = CALIBRATED_DATASET_SEED,
                    cell_keys: Sequence[str] | None = None) -> tuple[Cell, ...]:
    """DERIVED, never hard-coded: calibrated T_ref keys intersected with TRAIN.

    An empty result raises ``TrainingPlanError`` naming the true reason
    (``_dataset_seed_refusal``): a split seed refuses by PLAN section 18 SPLIT,
    a TRAIN-but-uncalibrated seed by T_REF CALIBRATION (dataset seeds 1 and 2
    ARE legitimately TRAIN; ``env.step`` would raise ``TRefMissing``).
    """
    store = tref_store if tref_store is not None else TRefStore()
    cells: list[Cell] = []
    for key in store.calibrated_keys():
        family, _, scale = key.partition("|")
        try:
            if split_of(family, scale, dataset_seed) != TRAIN:
                continue
        except ValueError as exc:
            raise TrainingPlanError(str(exc)) from None
        t_ref = store.get(family, scale, dataset_seed)
        if t_ref is None:
            continue                   # T_REF CALIBRATION, not a split decision
        cells.append(Cell(family=family, scale=scale, dataset_seed=dataset_seed,
                          t_ref_s=float(t_ref)))
    cells.sort(key=lambda c: c.key())
    if cell_keys is not None:
        available = {c.key(): c for c in cells}
        chosen: list[Cell] = []
        for raw in cell_keys:
            key = str(raw).strip()
            if key in available:
                if key in {c.key() for c in chosen}:
                    raise TrainingPlanError(f"cell {key!r} requested twice")
                chosen.append(available[key])
                continue
            family, _, scale = key.partition("|")
            try:
                split = split_of(family, scale, dataset_seed)
            except ValueError as exc:
                raise TrainingPlanError(f"cell {key!r}: {exc}") from None
            if split != TRAIN:
                raise TrainingPlanError(
                    f"cell {key!r} is split={split!r}: training accepts TRAIN "
                    f"cells only (PLAN section 18)")
            raise TrainingPlanError(
                f"cell {key!r} has NO CALIBRATED T_REF at dataset seed "
                f"{dataset_seed} (T_REF CALIBRATION: EXP-002 calibrated dataset "
                f"seed 0 only and F3_rdd|medium is null); env.step would raise "
                f"TRefMissing before executing")
        cells = chosen
    if not cells:
        # A split seed holds no trainable cell BY SPLIT; a TRAIN seed may be
        # merely uncalibrated. Name the true reason (CONFIRMED fix 1).
        raise TrainingPlanError(_dataset_seed_refusal(dataset_seed) +
                                f" No trainable cell survives at that seed. "
                                f"T_ref source: {store.source}")
    return tuple(cells)


def _excluded_cells(store: TRefStore, dataset_seed: int,
                    kept: Sequence[Cell]) -> tuple[dict[str, Any], ...]:
    """Every TRAIN-universe cell NOT in the plan, with its reason. Never silent."""
    kept_keys = {c.key() for c in kept}
    out: list[dict[str, Any]] = []
    for family in TRAIN_FAMILIES:
        for scale in TRAIN_SCALES:
            key = f"{family}|{scale}"
            if key in kept_keys:
                continue
            t_ref = store.get(family, scale, dataset_seed)
            if split_of(family, scale, dataset_seed) != TRAIN:
                reason = "not_train"
            elif t_ref is None:
                reason = "t_ref_null"
            else:
                reason = "not_selected"
            out.append({"cell": key, "reason": reason, "t_ref_s": t_ref})
    out.sort(key=lambda e: str(e["cell"]))
    return tuple(out)


def plan_episodes(cells: Sequence[Cell], n_episodes: int) -> tuple[Episode, ...]:
    """Pure, RNG-free, machine-independent round-robin (D2).

    ``rep = epoch`` is load-bearing: ``SparkTuningEnv._record_path`` is
    ``<result_root>/<family>/<scale>/seed<N>/<config_name>/rep<R>.json`` and the
    env ``os.replace``s that file, so two visits to one cell that select the
    same action would silently destroy each other's immutable transition record
    under a fixed rep. Round-robin visits each cell exactly once per cycle, so
    rep = epoch is unique per (cell, visit).
    """
    if not cells:
        raise TrainingPlanError("no cells to schedule")
    keys = [c.key() for c in cells]
    if len(set(keys)) != len(keys):
        raise TrainingPlanError(
            f"cells must be unique (transition record paths would collide): {keys}")
    if int(n_episodes) < 1:
        raise TrainingPlanError(f"episodes must be >= 1, got {n_episodes}")
    n = len(cells)
    return tuple(Episode(index=i, epoch=1 + (i - 1) // n, rep=1 + (i - 1) // n,
                         cell=cells[(i - 1) % n])
                 for i in range(1, int(n_episodes) + 1))


def build_plan(*, agent_rng_seed: int, episodes: int,
               run_kind: str = KIND_TRAINING,
               dataset_seed: int = CALIBRATED_DATASET_SEED,
               cell_keys: Sequence[str] | None = None,
               budget_limit: int | None = None,
               config: TrainingConfig | None = None,
               tref_store: TRefStore | None = None,
               policy_dir: str | Path | None = None,
               run_root: str | Path | None = None,
               now_utc: str | None = None,
               variant: str | None = None) -> TrainingPlan:
    """All pre-flight happens here, BEFORE any Spark session exists.

    ``variant`` (EXP-007, DEC-023 as amended by DEC-025): ``"A1"`` / ``"A2"``
    selects the frozen ablation arm. A variant plan enforces the amended
    scope: agent seeds {0, 1} only (seed 2 is NOT used), at most 35 planned
    episodes per seed (5 complete epochs x 7 TRAIN cells, 35 = 5 x 7), and a
    run budget defaulting to exactly the planned episode count so a variant
    run can never execute beyond its plan.
    The TRAIN cell set, split guards, T_ref gating and dataset seed 0 are the
    SAME machinery as the main study (control parity).
    """
    cfg = config if config is not None else TrainingConfig.from_yaml()
    if run_kind not in (KIND_TRAINING, KIND_SMOKE):
        raise TrainingPlanError(
            f"unknown run_kind {run_kind!r}; expected {KIND_TRAINING!r} or "
            f"{KIND_SMOKE!r}")
    if int(dataset_seed) != CALIBRATED_DATASET_SEED:
        # Split seeds (3/4) are out for a SPLIT reason; TRAIN-but-uncalibrated
        # seeds (1/2) are out for calibration. Say which (CONFIRMED fix 1).
        raise TrainingPlanError(_dataset_seed_refusal(int(dataset_seed)))
    if int(agent_rng_seed) not in cfg.training_seeds:
        raise TrainingPlanError(
            f"agent_rng_seed={agent_rng_seed} is not one of the frozen "
            f"PLAN-section-16 training seeds {list(cfg.training_seeds)} (these "
            f"are EXPLORATION replicates, not dataset seeds)")
    if int(episodes) < 1:
        raise TrainingPlanError(f"episodes must be >= 1, got {episodes}")

    # EXP-007 ablation scope (DEC-023 sections 6-8), BEFORE anything is built.
    if variant is not None:
        if variant not in ABLATION_VARIANTS:
            raise TrainingPlanError(
                f"unknown EXP-007 ablation variant {variant!r}; DEC-023 "
                f"freezes exactly {list(ABLATION_VARIANTS)} and no third arm")
        if int(agent_rng_seed) not in ABLATION_SEEDS:
            raise TrainingPlanError(
                f"EXP-007 variant {variant} accepts agent_rng_seed in "
                f"{list(ABLATION_SEEDS)} only (DEC-023 section 7); seed "
                f"{agent_rng_seed} is NOT used and must not leak from the "
                f"main study into the ablation")
        if int(episodes) > ABLATION_EPISODES_PER_SEED:
            raise BudgetPlanError(
                f"EXP-007 variant {variant} plans at most "
                f"{ABLATION_EPISODES_PER_SEED} episodes per seed "
                f"(DEC-023 section 6 as amended by DEC-025 sections 3-4: "
                f"5 complete epochs x 7 TRAIN cells, 35 = 5 x 7); "
                f"got {episodes}")

    store = tref_store if tref_store is not None else TRefStore()
    cells = trainable_cells(store, dataset_seed=int(dataset_seed),
                            cell_keys=cell_keys)
    excluded = _excluded_cells(store, int(dataset_seed), cells)

    cap = cfg.live_execution_cap
    if run_kind == KIND_SMOKE or variant is not None:
        # Smoke plans default their budget to exactly the planned episode
        # count, and may only LOWER it; the frozen cap binds both branches
        # (CONFIRMED fix 8 - the smoke branch used to ignore the cap and
        # the caller's budget_limit entirely, so --episodes 600 on a smoke
        # plan authorized 600 live executions through the env). An EXP-007
        # variant plan uses the SAME discipline (DEC-023 section 8): its
        # budget defaults to the planned episode count, so a variant run can
        # never execute beyond its own plan (planned max 35 per seed).
        limit = int(episodes) if budget_limit is None else int(budget_limit)
    else:
        limit = cap if budget_limit is None else int(budget_limit)
    if limit > cap:
        raise BudgetPlanError(
            f"budget_limit={limit} exceeds the frozen live_execution_cap "
            f"{cap} (PLAN section 16 / SC6); --budget may only LOWER the cap")
    if limit < 1:
        raise BudgetPlanError(f"budget_limit must be >= 1, got {limit}")
    if int(episodes) > limit:
        raise BudgetPlanError(
            f"{episodes} planned episodes exceed the budget limit {limit}; "
            f"refused before any Spark session exists (an overrun must be "
            f"impossible-by-plan, never discovered mid-run)")

    stamp = now_utc if now_utc is not None else time.strftime(
        "%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = f"train-a{int(agent_rng_seed)}-d{int(dataset_seed)}-{stamp}"
    if run_root is not None:
        root = Path(run_root)
    else:
        root = PROJECT / (cfg.smoke_run_root if run_kind == KIND_SMOKE
                          else cfg.run_root)
    run_dir = root / run_id
    if run_dir.exists():
        raise RunDirExistsError(
            f"run directory {run_dir} already exists; the loop never appends "
            f"into a prior run's episode log (resume is deferred to Day 28+)")
    pdir = Path(policy_dir) if policy_dir is not None else run_dir / "checkpoints"
    return TrainingPlan(
        run_id=run_id, run_kind=run_kind, agent_rng_seed=int(agent_rng_seed),
        dataset_seed=int(dataset_seed), cells=cells, excluded=excluded,
        episodes=plan_episodes(cells, int(episodes)),
        episodes_per_epoch=len(cells), budget_limit=limit, run_dir=run_dir,
        policy_dir=pdir, t_ref_source=store.source,
        variant=variant,
        state_schema=(neutral_state_schema(variant) if variant is not None
                      else SCHEMA_V15))


# --- greedy snapshot (side-effect free) ----------------------------------------
def greedy_snapshot(agent: QLearningAgent) -> dict[str, int]:
    """{q_key: argmax over ``agent.allowed_actions()``, lowest-index tie-break}.

    Computed ONLY from ``agent.q_table()`` (a deep copy), over every key present.

    NEVER ``select_action(state, epsilon=0.0)``: ``QLearningAgent.select_action``
    calls ``self._rng.random()`` BEFORE comparing to epsilon, so a greedy probe
    advances the exploration stream and makes the run irreproducible.
    NEVER ``q_values(state)``: it routes through ``_row()``, which INSERTS an
    optimistic default row for an unseen key, changing n_states and hence the
    checkpoint policy_id.
    """
    allowed = agent.allowed_actions()
    return {key: max(allowed, key=lambda a: (row[a], -a))
            for key, row in agent.q_table().items()}


def snapshot_hash(snapshot: Mapping[str, int]) -> str:
    """sha256 over the snapshot with sorted keys (stable across processes)."""
    canonical = json.dumps({k: int(v) for k, v in sorted(snapshot.items())},
                           sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _greedy_action(agent: QLearningAgent, state: Any) -> int:
    """Best-effort greedy label, without touching the RNG or inserting a row."""
    allowed = agent.allowed_actions()
    row = agent.q_table().get(state_key_of(state))
    if row is None:
        row = [agent.config.q0_default] * 12
    return max(allowed, key=lambda a: (row[a], -a))


# --- construction ---------------------------------------------------------------
def build_env_and_agent(plan: TrainingPlan, base_config: SparkConfig, *,
                        sysmon_enabled: bool = True,
                        ) -> tuple[SparkTuningEnv, QLearningAgent, dict[str, Any]]:
    """Offline Q0 -> agent; plan -> env. No Spark session is created here.

    EXP-007 (DEC-023 sections 2-4): a variant plan selects its frozen state
    encoder (A1 = state-v1, A2 = state-v2 feedback-only) and the NEUTRAL Q0
    (q0_default = 0.5 for every valid state x action). The main-study path
    (variant None) is UNCHANGED: full v1.5 states and the EXP-002-derived Q0.
    The learner, epsilon schedule, reward, T_ref and budget machinery are
    identical for all three conditions (control parity).
    """
    if plan.variant is not None:
        q0 = build_neutral_q0(plan.variant)
    else:
        q0 = build_q0_from_exp002()
    agent = QLearningAgent(q_table=q0.q_table, rng_seed=plan.agent_rng_seed)
    env = SparkTuningEnv(base_config,
                         state_schema=plan.state_schema,
                         result_root=plan.run_dir / "transitions",
                         budget_limit=plan.budget_limit,
                         sysmon_enabled=sysmon_enabled)
    return env, agent, dict(q0.provenance)


# --- io helpers -----------------------------------------------------------------
def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_CODE_VERSION: str | None = None


def _code_version() -> str:
    """One git description per process: the tree cannot change mid-run, and
    the frozen helper shells out twice per call."""
    global _CODE_VERSION
    if _CODE_VERSION is None:
        _CODE_VERSION = code_version()
    return _CODE_VERSION


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _sha256_file_lf(path: Path) -> str | None:
    """sha256 of `path` with line endings normalised to LF (DEC-037 s4).

    ``_sha256_file`` above hashes RAW BYTES and KEEPS THAT MEANING FOREVER -
    it is not changed here and must not be. Its digest, however, depends on
    checkout line endings for any file governed by ``* text=auto`` in
    .gitattributes under ``core.autocrlf=true``, so it can never be stable
    across clones. That is the direct cause of the Day-29 check 05/06
    provenance failures: ``configs/rl.yaml`` produced ``4bb71750...`` when
    the Day-29 runs recorded it and ``8ca70d6d...`` today, from the SAME
    committed content in two checkout representations. It bears on SC8,
    "repo reproducible from fresh clone" (PLAN line 45).

    DEC-037 s4 resolves this ADDITIVELY and only for FUTURE runs: the raw
    field keeps its meaning, no recorded manifest hash is edited, and runs
    additionally record this normalised digest in a sibling field. Changing
    ``_sha256_file`` in place would instead silently redefine
    ``t_ref_gate_sha256`` as well and make every future ``rl_yaml_sha256``
    incomparable to every recorded one. An added field is the only shape in
    which no field ever means two things.

    Normalisation collapses CRLF and lone CR to LF, so all three checkout
    representations of one content agree. Returns None on an unreadable
    path, exactly like the raw sibling, so a missing file is never a crash.
    """
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return None
    normalised = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalised).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)          # atomic on the same volume


def _append_jsonl(path: Path, line: Mapping[str, Any]) -> None:
    """Durable append - NOT POSIX-atomic.

    A crash mid-write can leave a partial trailing line. Readers must tolerate
    exactly ONE malformed FINAL line and hard-fail on a malformed non-final one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _contract_versions(env: Any, agent: QLearningAgent) -> dict[str, Any]:
    """Contract fingerprints read off the duck-typed env (never recomputed)."""
    mapper = getattr(env, "action_mapper", None)
    encoder = getattr(env, "encoder", None)
    calc = getattr(env, "reward_calculator", None)
    base = getattr(env, "base_config", None)
    return {
        "env_version": getattr(env, "env_version", None),
        "state_schema": getattr(encoder, "schema_version", None),
        "action_mode": getattr(mapper, "mode", None),
        "grid_fingerprint": getattr(mapper, "grid_fingerprint", None),
        "reward_formula": getattr(calc, "formula_id", None),
        "learner_version": AGENT_VERSION,
        "policy_schema": POLICY_SCHEMA,
        "base_config_fingerprint": (base.fingerprint()
                                    if hasattr(base, "fingerprint") else None),
    }


# --- the loop --------------------------------------------------------------------
def run_training(plan: TrainingPlan, *, env: Any, agent: QLearningAgent,
                 q0_provenance: Mapping[str, Any],
                 config: TrainingConfig | None = None,
                 on_episode: Callable[[EpisodeOutcome], None] | None = None,
                 ) -> TrainingResult:
    """Run one training run.

    ``env`` is DUCK-TYPED (``SparkTuningEnv``, or a unit-test fake exposing
    reset / step / budget_limit / executions_used / budget_remaining /
    env_version) - no Protocol, no ABC, no adapter. A ``QueueLock`` guards
    this run's own directory against accidental re-entry into the same run
    (double execution of one ``TrainingPlan``); it does NOT serialize two
    different trainings - run directories are unique per run, so a lock per
    run directory cannot collide across runs (CONFIRMED fixes 2/5: the old
    sentence claimed core-contention exclusion that this lock cannot
    deliver). Serializing two training runs is operator discipline
    (DAY27_TRAINING_LOOP_AUDIT.md, Limitation 4).

    The loop keeps NO budget counter of its own, NEVER computes a reward, and
    NEVER touches epsilon arithmetic.

    ``state_after`` from ``env.step`` is used ONLY as ``Transition.next_state``.
    It is the env's WITHIN-episode successor (the same context re-encoded with
    this episode's reward), not the next episode's start state. That is harmless
    only because every bandit episode is terminal and never bootstraps; a Day-30
    multi-step gate would make it a wrong bootstrap target.
    """
    cfg = config if config is not None else TrainingConfig.from_yaml()
    run_dir = Path(plan.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "episodes.jsonl"
    manifest_path = run_dir / "manifest.json"

    started = _utc()
    checkpoints: list[dict[str, Any]] = []
    epochs: list[dict[str, Any]] = []
    counts = {"completed": 0, "failed": 0, "updated": 0}
    flags: dict[str, Any] = {"early_stopped": False, "at_epoch": None,
                             "mid_step": False, "in_flight": None}
    last_reward: float | None = None       # D8: assigned only from env.step
    prev_snapshot: dict[str, int] | None = None
    streak = 0
    visited: list[str] = []
    last_failed: bool = False          # CONFIRMED fix 6: the predecessor's
                                       # authoritative `failed` boolean
                                       # (the sentinel `reward == -1.0` lies
                                       # for clipped usable runs)
    pending: dict[str, Any] | None = None  # the in-flight episode's line

    def _manifest(status: str, stop_reason: str, exit_code: int,
                  finished: str | None = None) -> None:
        payload: dict[str, Any] = {
            "record_schema_version": MANIFEST_SCHEMA,
            "loop_version": LOOP_VERSION,
            "run_id": plan.run_id, "run_kind": plan.run_kind,
            "status": status, "stop_reason": stop_reason, "exit_code": exit_code,
            "started_utc": started, "finished_utc": finished,
            "exp007_variant": plan.variant,
            "state_schema": plan.state_schema,
            "code_version": _code_version(),
            "agent_rng_seed": plan.agent_rng_seed,
            "dataset_seed": plan.dataset_seed,
            "seed_semantics": SEED_SEMANTICS,
            "policy_rng_seed_is_agent_rng_seed": True,
            "schedule": {
                "cells": [{"cell": c.key(), "t_ref_s": c.t_ref_s}
                          for c in plan.cells],
                "excluded_cells": [dict(e) for e in plan.excluded],
                "order": "fixed_round_robin_over_sorted_cells",
                "epoch_definition": EPOCH_DEFINITION,
                "episodes_per_epoch": plan.episodes_per_epoch,
                "episodes_planned": len(plan.episodes),
            },
            "t_ref_source": plan.t_ref_source,
            # Raw-byte digest: UNCHANGED meaning, forever (DEC-037 s4).
            "t_ref_gate_sha256": _sha256_file(DEFAULT_GATE_PATH),
            # Additive LF-normalised sibling, FUTURE runs only. DEC-037 s7
            # left the timing of this one to the implementer ("immediately
            # or later"); it is added now, in the same shape s4 authorized
            # for rl_yaml_sha256, because both share _sha256_file and the
            # identical `text=auto` exposure.
            "t_ref_gate_sha256_lf": _sha256_file_lf(DEFAULT_GATE_PATH),
            "hyperparameters": {
                "alpha": agent.config.alpha, "gamma": agent.config.gamma,
                "epsilon_start": agent.config.epsilon_start,
                "epsilon_min": agent.config.epsilon_min,
                "epsilon_decay": agent.config.epsilon_decay,
                "q0_default": agent.config.q0_default,
                "source": "configs/rl.yaml + PLAN section 16",
            },
            # Raw-byte digest: UNCHANGED meaning, forever. Every recorded
            # manifest hash stays comparable to it, and the CITED historical
            # constant DAY29_RECORDED_RL_YAML_SHA256 is never touched.
            "rl_yaml_sha256": _sha256_file(Path(DEFAULT_RL_YAML)),
            # Additive LF-normalised sibling, FUTURE runs only (DEC-037 s4):
            # stable across clones and autocrlf settings, so provenance
            # becomes assertable for new runs without redefining any field.
            "rl_yaml_sha256_lf": _sha256_file_lf(Path(DEFAULT_RL_YAML)),
            "contract_versions": _contract_versions(env, agent),
            "q0_provenance": dict(q0_provenance),
            "budget": {
                "live_execution_cap": cfg.live_execution_cap,
                "budget_limit_this_run": plan.budget_limit,
                "live_executions": int(getattr(env, "executions_used", 0)),
                "budget_remaining": int(getattr(env, "budget_remaining", 0)),
                "enforcement": BUDGET_ENFORCEMENT_NOTE,
            },
            "counts": {
                "episodes_planned": len(plan.episodes),
                "episodes_completed": counts["completed"],
                "episodes_failed": counts["failed"],
                "episodes_updated": counts["updated"],
            },
            "early_stop": {
                "rule": EARLY_STOP_RULE,
                "stable_epochs_required": cfg.early_stop_stable_epochs,
                "triggered": flags["early_stopped"],
                "at_epoch": flags["at_epoch"],
            },
            "epochs": [dict(e) for e in epochs],
            "checkpoints": [dict(c) for c in checkpoints],
            "final_policy": ({"policy_id": checkpoints[-1]["policy_id"],
                              "path": checkpoints[-1]["path"]}
                             if checkpoints else None),
            "resume": {"implemented": False, "deferred_to": "Day 28+",
                       "recovery_procedure": RECOVERY_PROCEDURE},
            "feedback_chain_origin": "run_start_no_history",
            "state_aliasing_note": STATE_ALIASING_NOTE,
            "files": {"episode_log": "episodes.jsonl",
                      "transitions_root": "transitions",
                      "checkpoints_dir": _checkpoints_rel()},
            "learning_claim": {"learning_demonstrated": False,
                               "convergence_demonstrated": False,
                               "baseline_comparison": None, "note": NO_CLAIM},
        }
        if flags["mid_step"]:
            payload["interrupted_mid_step"] = True
            payload["in_flight_episode"] = flags["in_flight"]
            payload["budget_accounting"] = (
                "uncertain: the in-flight execution may or may not have "
                "completed; count records under transitions/ to reconcile")
        _atomic_write_json(manifest_path, payload)

    def _checkpoints_rel() -> str:
        try:
            return str(Path(plan.policy_dir).relative_to(run_dir))
        except ValueError:
            return str(plan.policy_dir)

    def _relpath(path: Path) -> str:
        try:
            return str(Path(path).relative_to(run_dir))
        except ValueError:
            return str(path)

    def _checkpoint(episode_index: int) -> str:
        # init_provenance stays PURE Q0 provenance: no run context is injected,
        # so checkpoint identity remains content-addressed and a repeated
        # policy_id across checkpoints is correct, not a bug.
        artifact = build_policy_artifact(agent, init_provenance=dict(q0_provenance),
                                         created_utc=_utc())
        path = save_policy(artifact, plan.policy_dir)
        checkpoints.append({"episode_index": episode_index,
                            "policy_id": artifact["policy_id"],
                            "path": _relpath(path),
                            "epsilon": agent.epsilon, "updates": agent.updates,
                            "episodes": agent.episodes})
        return str(artifact["policy_id"])

    def _result(status: str, stop_reason: str, exit_code: int) -> TrainingResult:
        return TrainingResult(
            run_id=plan.run_id, run_dir=run_dir, status=status,
            stop_reason=stop_reason, exit_code=exit_code,
            episodes_completed=counts["completed"],
            episodes_failed=counts["failed"], epochs_completed=len(epochs),
            executions_used=int(getattr(env, "executions_used", 0)),
            early_stopped=bool(flags["early_stopped"]),
            checkpoints=tuple(checkpoints),
            final_policy_id=(checkpoints[-1]["policy_id"] if checkpoints else None),
            manifest_path=manifest_path, episode_log_path=log_path)

    status, stop_reason, exit_code = STATUS_COMPLETED, STOP_COMPLETED, 0
    lock = QueueLock(run_dir).acquire()
    try:
        _manifest(STATUS_RUNNING, "in_progress", 0)
        for ep in plan.episodes:
            k = ep.index
            if int(getattr(env, "budget_remaining", 1)) <= 0:
                status, stop_reason = STATUS_TRUNCATED, STOP_BUDGET
                print(f"BUDGET EXHAUSTED before episode {k}: "
                      f"{len(plan.episodes) - k + 1} planned episodes will NOT "
                      f"run", file=sys.stderr, flush=True)
                break
            t0 = time.perf_counter()
            try:
                obs, _info = env.reset(
                    family=ep.cell.family, scale=ep.cell.scale,
                    seed=plan.dataset_seed,   # env's `seed` is the DATASET seed
                    rep=ep.rep, last_reward=last_reward)
            except BudgetExhausted:
                status, stop_reason = STATUS_TRUNCATED, STOP_BUDGET
                print(f"BUDGET EXHAUSTED at episode {k} (env guard): "
                      f"{len(plan.episodes) - k + 1} planned episodes will NOT "
                      f"run", file=sys.stderr, flush=True)
                break

            eps_used = float(agent.epsilon)
            greedy_a = _greedy_action(agent, obs.state)
            action = agent.select_action(obs.state)
            key_before = state_key_of(obs.state)
            line: dict[str, Any] = {
                "record_schema_version": EPISODE_SCHEMA,
                "loop_version": LOOP_VERSION,
                "run_id": plan.run_id, "run_kind": plan.run_kind,
                "episode_index": k, "epoch_index": ep.epoch,
                "position_in_epoch": 1 + (k - 1) % plan.episodes_per_epoch,
                "agent_rng_seed": plan.agent_rng_seed,
                "dataset_seed": plan.dataset_seed,
                "cell": {"family": ep.cell.family, "scale": ep.cell.scale,
                         "dataset_seed": plan.dataset_seed, "rep": ep.rep},
                "episode_key": f"{ep.cell.family}|{ep.cell.scale}"
                               f"|seed{plan.dataset_seed}|rep{ep.rep}",
                "last_reward_in": last_reward,
                "feedback_source": ("no_history_convention" if last_reward is None
                                    else "previous_episode"),
                # The predecessor's authoritative failure boolean, threaded
                # episode to episode (CONFIRMED fix 6). The old text inferred
                # failure from last_reward == -1.0, which lies whenever a
                # USABLE run clips to exactly -1.0 (T >= 2*T_ref on a cell
                # whose other terms are zero).
                "feedback_from_failed_episode": bool(
                    last_reward is not None and last_failed),
                "state_key_before": key_before,
                "state_key_after": None,
                "action_index": int(action),
                # Best effort: an exploration draw can coincide with the greedy
                # action, so "exploit" here means "equals the greedy action",
                # not "was produced by the exploitation branch".
                "action_source": "exploit" if action == greedy_a else "explore",
                "epsilon_used": eps_used, "epsilon_before": eps_used,
                "executed": False,
                "t_ref_s": ep.cell.t_ref_s,
                "reward_source": "env.step (frozen R3)",
                "updated": False, "update_error": None, "td_delta": None,
                "checkpoint_policy_id": None,
                "code_version": _code_version(),
            }
            pending = line
            flags["mid_step"] = True
            flags["in_flight"] = k
            try:
                s2, reward, terminated, _truncated, step = env.step(action)
            except KeyboardInterrupt:
                # A genuine mid-step interrupt: Spark may or may not have
                # completed, so the flag STAYS True and the manifest keeps
                # its uncertain-budget stamp.
                flags["mid_step"] = True
                raise
            except _PRE_EXECUTION_STEP_ABORTS:
                # A planned env guard fired before execute_run: the counter
                # is exact, so this abort carries no budget uncertainty.
                flags["mid_step"] = False
                raise
            flags["mid_step"] = False

            metrics = dict(getattr(step, "metrics", {}) or {})
            usable = bool(metrics.get("usable", True))
            failed = (not usable) or bool(metrics.get("timeout", False))
            q_row = agent.q_table().get(key_before)
            q_before = (float(q_row[action]) if q_row is not None
                        else float(agent.config.q0_default))
            line.update({
                "executed": True,
                "state_key_after": state_key_of(s2),
                "config_name": step.config_name,
                "config_fingerprint": step.config_fingerprint,
                "reward": float(reward),          # COPIED, never recomputed
                "usable": usable, "failed": failed,
                "env_run_id": step.run_id,
                "transition_record_relpath":
                    f"transitions/{ep.cell.family}/{ep.cell.scale}"
                    f"/seed{plan.dataset_seed}/{step.config_name}"
                    f"/rep{ep.rep}.json",
                "env_version": getattr(step, "env_version", None),
                "state_schema": getattr(s2, "schema_version", None),
                "action_mode": getattr(step, "action_mode", None),
                "q_before": q_before,
            })
            try:
                delta = agent.update(Transition(
                    state=obs.state, action=action, reward=float(reward),
                    next_state=s2, terminated=bool(terminated),
                    info={"run_id": step.run_id,
                          "episode_key": step.episode_key}))
                line["updated"], line["td_delta"] = True, float(delta)
                counts["updated"] += 1
            except InvalidTransition as exc:
                line["updated"], line["update_error"] = False, str(exc)
                raise                     # COMP-RL-10: Q untouched + abort

            q_row = agent.q_table().get(key_before)
            line["q_after"] = (float(q_row[action]) if q_row is not None
                               else float(agent.config.q0_default))
            last_reward = float(reward)           # D8: the step float only
            last_failed = failed                # CONFIRMED fix 6: thread the
                                                # authoritative flag with the
                                                # reward for the next line
            eps_after = agent.end_episode()       # the frozen epsilon decay
            line.update({
                "epsilon_after": float(eps_after),
                "agent_updates_after": agent.updates,
                "agent_episodes_after": agent.episodes,
                "executions_used_after": int(getattr(env, "executions_used", 0)),
                "budget_remaining_after": int(getattr(env, "budget_remaining", 0)),
                "wall_s": round(time.perf_counter() - t0, 3),
                "written_utc": _utc(),
            })
            if k % cfg.checkpoint_every_episodes == 0:
                # AFTER end_episode: a checkpoint's epsilon is always the
                # post-decay value and its episodes counter always equals the
                # episode_index of the line above it.
                line["checkpoint_policy_id"] = _checkpoint(k)
            _append_jsonl(log_path, line)
            pending = None
            counts["completed"] += 1
            visited.append(key_before)
            if failed:
                counts["failed"] += 1
                print(f"EPISODE {k} FAILED on {ep.cell.key()} "
                      f"(usable={usable}): reward {reward} recorded, Q updated, "
                      f"feedback threaded; the run continues (no retry)",
                      file=sys.stderr, flush=True)
            if line["checkpoint_policy_id"] is not None:
                _manifest(STATUS_RUNNING, "in_progress", 0)
            if on_episode is not None:
                on_episode(EpisodeOutcome(
                    episode_index=k, epoch_index=ep.epoch, cell=ep.cell,
                    action_index=int(action),
                    action_source=str(line["action_source"]),
                    epsilon_used=eps_used, reward=float(reward), usable=usable,
                    failed=failed, updated=bool(line["updated"]),
                    td_delta=line["td_delta"], epsilon_after=float(eps_after),
                    executions_used_after=int(line["executions_used_after"]),
                    env_run_id=str(step.run_id),
                    transition_record_relpath=str(line["transition_record_relpath"]),
                    checkpoint_policy_id=line["checkpoint_policy_id"]))

            if k % plan.episodes_per_epoch == 0:
                snap = greedy_snapshot(agent)
                stable = prev_snapshot is not None and snap == prev_snapshot
                streak = streak + 1 if stable else 0
                epochs.append({
                    "epoch_index": ep.epoch,
                    "episodes": plan.episodes_per_epoch,
                    "visited_state_keys": sorted(set(visited)),
                    "greedy_snapshot_sha256": snapshot_hash(snap),
                    "stable_vs_previous": bool(stable),
                    "stability_streak": streak,
                })
                prev_snapshot = snap
                visited = []          # per-epoch scope: an epoch's
                                      # visited_state_keys must describe THAT
                                      # epoch, or a vacuously stable snapshot
                                      # looks better evidenced than it is
                _manifest(STATUS_RUNNING, "in_progress", 0)
                if streak >= cfg.early_stop_stable_epochs:
                    flags["early_stopped"] = True
                    flags["at_epoch"] = ep.epoch
                    status, stop_reason = STATUS_COMPLETED, STOP_EARLY
                    break
        if not flags["mid_step"]:
            _checkpoint(counts["completed"])   # one FINAL clean-stop checkpoint
        _manifest(status, stop_reason, exit_code, finished=_utc())
    except KeyboardInterrupt:
        status, stop_reason, exit_code = STATUS_INTERRUPTED, STOP_INTERRUPTED, 130
        if pending is None:
            _checkpoint(counts["completed"])   # clean episode-boundary interrupt
        else:
            flags["in_flight"] = pending.get("episode_index")
            flags["mid_step"] = True           # mid-step: NO checkpoint
        _manifest(status, stop_reason, exit_code, finished=_utc())
        lock.release()
        return _result(status, stop_reason, exit_code)
    except BaseException as exc:               # noqa: BLE001 - abort loud
        reason = "aborted"
        for kind, name in _ABORT_REASONS:
            if isinstance(exc, kind):
                reason = name
                break
        if pending is not None:
            # A live execution costs ~20-90 s of the frozen 500; this line is
            # its only forensic record, so it is written BEFORE the re-raise.
            pending.setdefault("written_utc", _utc())
            pending["abort_error"] = f"{type(exc).__name__}: {exc}"
            try:
                _append_jsonl(log_path, pending)
            except OSError:
                pass
        print(f"ABORT ({reason}): {type(exc).__name__}: {exc}",
              file=sys.stderr, flush=True)
        _manifest(STATUS_FAILED, reason, 1, finished=_utc())
        lock.release()
        raise

    lock.release()
    return _result(status, stop_reason, exit_code)
