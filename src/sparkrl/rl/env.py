"""SparkTuningEnv: the RL-facing environment contract (COMP-RL-09).

Frozen source: PLAN section 12 (RL formulation), DEC-009, ARCHITECTURE_FREEZE
COMP-RL-09: "Gymnasium-style reset/step with guards; inputs (seeds, split,
budget, cache); outputs (state, cached_flag, done); guards: test-access ->
abort; budget-hit -> done."

Day-25 scope (bandit mode): one decision per episode.

    reset(family, scale, seed, rep, last_reward)
        -> (Observation, info)          # pure bookkeeping; NO Spark execution;
                                        # consumes NO budget
    step(action)
        -> (obs_next, reward, terminated=True, truncated=False, info)
        # resolves action -> frozen configuration (pre-exec rejection),
        # raises TRefMissing BEFORE executing if no T_ref is calibrated,
        # delegates execution to the existing experiment runner
        # (sparkrl.experiments.runner.execute_run), computes the frozen R3
        # reward from the returned RunMetrics, and records the transition.

Guards implemented here (COMP-RL-09):
* SPLIT: TRAIN cells only (PLAN section 18). TEST (F4_ski / large / seed 4)
  and VALIDATION (seed 3) accesses raise ``SplitViolation`` before anything
  runs; the executor re-checks independently (defense in depth).
* BUDGET: live executions are counted; ``budget_limit`` defaults to the
  frozen <=500 cap (PLAN section 16 / SC6). When the budget is exhausted,
  ``reset`` raises ``BudgetExhausted`` - the episode-boundary form of the
  frozen "budget-hit -> done" guard. Cache hits do NOT consume budget; the
  cache itself is COMP-EXP-11 (deferred, Day 26+), so every Day-25 step is a
  live execution and ``info["cached"]`` is always False.

The environment owns NO learning: no Q-table, no epsilon schedule, no policy
update, no value function. Reward = the frozen R3 formula via COMP-RL-08
(``sparkrl.rl.reward.RewardCalculator``); the agent (COMP-RL-10, Day 26+) is
the only future consumer of transitions.

Authoritative timing is untouched: reward and records use
``RunMetrics.execution_time_s`` (the frozen Day-3 runner clock). Runner
wall time, parse time, and manifest time are never substituted.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkrl.experiments.runner import code_version, execute_run
from sparkrl.experiments.spec import TRAIN, RunSpec, split_of
from sparkrl.rl.action import MODE12, ActionMapper, InvalidAction
from sparkrl.rl.reward import Reward, RewardCalculator, TRefMissing
from sparkrl.rl.state import SCHEMA_V15, StateEncoder, StateVector
from sparkrl.rl.tref import TRefStore
from sparkrl.spark.config import SparkConfig
from sparkrl.workloads.resolver import resolve_dataset

ENV_VERSION = "spark-tuning-env/v1"
DEFAULT_BUDGET = 500  # frozen live-execution cap (PLAN section 16 / SC6)


class SplitViolation(RuntimeError):
    """A non-TRAIN cell was requested (test/validation guard, COMP-RL-09)."""


class BudgetExhausted(RuntimeError):
    """The live-execution budget is spent (budget-hit guard, COMP-RL-09)."""


class EpisodeDone(RuntimeError):
    """step() called on a finished episode (bandit mode: one decision)."""


@dataclass(frozen=True)
class Observation:
    """What the agent sees at decision time (pre-execution facts only)."""

    state: StateVector
    family: str
    scale: str
    seed: int
    rep: int
    episode_key: str
    dataset_id: str
    dataset_fingerprint: str
    input_bytes: int
    t_ref_s: float | None
    budget_remaining: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "family": self.family,
            "scale": self.scale,
            "seed": self.seed,
            "rep": self.rep,
            "episode_key": self.episode_key,
            "dataset_id": self.dataset_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "input_bytes": self.input_bytes,
            "t_ref_s": self.t_ref_s,
            "budget_remaining": self.budget_remaining,
        }


@dataclass(frozen=True)
class StepInfo:
    """Full transition provenance (the record an agent would learn from)."""

    run_id: str
    episode_key: str
    action_index: int
    action_mode: str
    config_name: str
    config_fingerprint: str
    state_before: StateVector
    state_after: StateVector
    reward: Reward
    metrics: dict[str, Any]
    provenance: dict[str, Any]
    env_version: str = ENV_VERSION
    cached: bool = False   # stable interface boundary; cache is COMP-EXP-11
    terminated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "episode_key": self.episode_key,
            "action_index": self.action_index,
            "action_mode": self.action_mode,
            "config_name": self.config_name,
            "config_fingerprint": self.config_fingerprint,
            "state_before": self.state_before.to_dict(),
            "state_after": self.state_after.to_dict(),
            "reward": self.reward.to_dict(),
            "metrics": dict(self.metrics),
            "provenance": dict(self.provenance),
            "env_version": self.env_version,
            "cached": self.cached,
            "terminated": self.terminated,
        }


class SparkTuningEnv:
    """Gymnasium-style single-node Spark configuration environment.

    The environment is an RL-facing ORCHESTRATION LAYER over the existing
    infrastructure; it embeds no second Spark runner, no timing code, and no
    monitoring code.
    """

    def __init__(self, base_config: SparkConfig, *,
                 action_mode: str = MODE12,
                 state_schema: str = SCHEMA_V15,
                 tref_store: TRefStore | None = None,
                 reward_calculator: RewardCalculator | None = None,
                 result_root: str | Path | None = None,
                 sysmon_enabled: bool = True,
                 budget_limit: int = DEFAULT_BUDGET) -> None:
        if not isinstance(budget_limit, int) or isinstance(budget_limit, bool) \
                or budget_limit < 1:
            raise ValueError(f"budget_limit must be a positive int, got {budget_limit!r}")
        self.base_config = base_config
        self.action_mapper = ActionMapper(mode=action_mode)
        self.encoder = StateEncoder(schema_version=state_schema)
        self.tref_store = tref_store if tref_store is not None else TRefStore()
        self.reward_calculator = reward_calculator if reward_calculator is not None \
            else RewardCalculator()
        self.result_root = Path(result_root) if result_root is not None else None
        self.sysmon_enabled = bool(sysmon_enabled)
        self._budget_limit = budget_limit
        self._executions_used = 0
        self._episode: dict[str, Any] | None = None

    # -- introspection -------------------------------------------------------
    @property
    def env_version(self) -> str:
        return ENV_VERSION

    @property
    def action_space_size(self) -> int:
        return self.action_mapper.size

    @property
    def observation_space_size(self) -> int:
        return StateVector.space_size(self.encoder.schema_version)

    @property
    def budget_limit(self) -> int:
        return self._budget_limit

    @property
    def executions_used(self) -> int:
        return self._executions_used

    @property
    def budget_remaining(self) -> int:
        return self._budget_limit - self._executions_used

    # -- guards ---------------------------------------------------------------
    @staticmethod
    def _assert_train(family: str, scale: str, seed: int) -> None:
        split = split_of(family, scale, seed)
        if split != TRAIN:
            raise SplitViolation(
                f"{family}/{scale}/seed{seed} is split={split!r}; the environment "
                f"accepts TRAIN cells only (test split frozen until Day 31, "
                f"PLAN section 18; validation belongs to EXP-003)")

    def _assert_budget(self) -> None:
        if self.budget_remaining <= 0:
            raise BudgetExhausted(
                f"live-execution budget exhausted: {self._executions_used}/"
                f"{self._budget_limit} (frozen <=500 cap, PLAN section 16/SC6)")

    # -- API ------------------------------------------------------------------
    def reset(self, *, family: str, scale: str, seed: int = 0, rep: int = 1,
              last_reward: float | None = None) -> tuple[Observation, dict[str, Any]]:
        """Begin one episode. Pure bookkeeping: NO Spark execution, NO budget.

        ``last_reward`` (optional) is the PREVIOUS episode's realized reward
        for v1.5 feedback binning; ``None`` maps to the documented pessimistic
        default (see sparkrl.rl.state).
        """
        self._assert_train(family, scale, seed)
        self._assert_budget()
        resolved = resolve_dataset(family, scale, seed)
        input_bytes = (int(resolved.orders_manifest.get("total_bytes") or 0)
                       + int(resolved.lineitem_manifest.get("total_bytes") or 0))
        state = self.encoder.encode(family, input_bytes, last_reward=last_reward)
        t_ref = self.tref_store.get(family, scale, seed)
        episode_key = f"{family}|{scale}|seed{seed}|rep{rep}"
        self._episode = {
            "family": family, "scale": scale, "seed": seed, "rep": rep,
            "state": state, "input_bytes": input_bytes,
            "t_ref": t_ref, "episode_key": episode_key,
            "dataset_id": resolved.dataset_id,
            "dataset_fingerprint": resolved.dataset_fingerprint,
        }
        obs = Observation(
            state=state, family=family, scale=scale, seed=seed, rep=rep,
            episode_key=episode_key, dataset_id=resolved.dataset_id,
            dataset_fingerprint=resolved.dataset_fingerprint,
            input_bytes=input_bytes, t_ref_s=t_ref,
            budget_remaining=self.budget_remaining)
        info = {
            "episode_key": episode_key,
            "t_ref_available": t_ref is not None,
            "t_ref_source": self.tref_store.source,
            "state_schema": self.encoder.schema_version,
            "action_space_size": self.action_space_size,
            "observation_space_size": self.observation_space_size,
            "budget_remaining": self.budget_remaining,
        }
        return obs, info

    def step(self, action: int) -> tuple[StateVector, float, bool, bool, StepInfo]:
        """Execute ONE controlled workload transition (bandit mode)."""
        if self._episode is None:
            raise EpisodeDone("no active episode; call reset() first "
                              "(bandit mode: one decision per episode)")
        ep = self._episode
        # 1. action domain guard - pre-execution rejection (COMP-RL-07)
        cfg, point, cfg_fp = self.action_mapper.to_config(action, self.base_config)
        # 2. T_ref guard - BEFORE executing Spark (COMP-RL-08 hard error)
        t_ref = ep["t_ref"]
        if t_ref is None:
            raise TRefMissing(
                f"no T_ref calibrated for {ep['family']}|{ep['scale']} seed "
                f"{ep['seed']}; refusing to execute (EXP-002/003 calibration)")
        # 3. budget guard
        self._assert_budget()
        # 4. delegate execution to the existing experiment runner
        run_id = (f"env-{ep['family']}-{ep['scale']}-s{ep['seed']}"
                  f"-{point.name}-r{ep['rep']}")
        run_spec = RunSpec(
            run_id=run_id, family=ep["family"], scale=ep["scale"], seed=ep["seed"],
            rep=ep["rep"], config=point, split=TRAIN,
            timeout_seconds=float(self.base_config.timeout_seconds),
            order_index=0, block_id=f"env-{ep['episode_key']}")
        metrics, provenance = execute_run(run_spec, self.base_config,
                                          sysmon_enabled=self.sysmon_enabled)
        self._executions_used += 1  # live execution; a future cache hit would not
        # 5. frozen reward (COMP-RL-08)
        failed = (not metrics.usable) or bool(metrics.timeout)
        reward = self.reward_calculator.compute(
            metrics.to_dict(), t_ref, ep["input_bytes"], failed=failed)
        # 6. next observation (v1.5: feedback bin from the realized reward)
        state_after = self.encoder.encode(ep["family"], ep["input_bytes"],
                                          last_reward=reward.value)
        info = StepInfo(
            run_id=run_id, episode_key=ep["episode_key"], action_index=int(action),
            action_mode=self.action_mapper.mode, config_name=point.name,
            config_fingerprint=cfg_fp, state_before=ep["state"],
            state_after=state_after, reward=reward,
            metrics=metrics.to_dict(), provenance=dict(provenance))
        if self.result_root is not None:
            self._write_record(info, ep)
        self._episode = None  # bandit mode: episode terminates
        return state_after, reward.value, True, False, info

    # -- persistence ----------------------------------------------------------
    def _record_path(self, ep: dict[str, Any], info: StepInfo) -> Path:
        """Deterministic on-disk location (independent of traversal order)."""
        assert self.result_root is not None
        return (self.result_root / ep["family"] / ep["scale"]
                / f"seed{ep['seed']}" / info.config_name / f"rep{ep['rep']}.json")

    def _write_record(self, info: StepInfo, ep: dict[str, Any]) -> None:
        """Atomic, immutable per-step transition record (provenance)."""
        path = self._record_path(ep, info)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "record_schema_version": "rl-transition/v1",
            "env_version": ENV_VERSION,
            "env_config": {
                "action_mode": self.action_mapper.mode,
                "grid_fingerprint": self.action_mapper.grid_fingerprint,
                "state_schema": self.encoder.schema_version,
                "budget_limit": self._budget_limit,
                "t_ref_source": self.tref_store.source,
                "base_config_fingerprint": self.base_config.fingerprint(),
            },
            "observation_before": {
                "family": ep["family"], "scale": ep["scale"],
                "seed": ep["seed"], "rep": ep["rep"],
                "dataset_id": ep["dataset_id"],
                "dataset_fingerprint": ep["dataset_fingerprint"],
                "input_bytes": ep["input_bytes"],
                "t_ref_s": ep["t_ref"],
            },
            **info.to_dict(),
            "code_version": code_version(),
            "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=1, sort_keys=True),
                       encoding="utf-8")
        os.replace(tmp, path)  # atomic on same volume
