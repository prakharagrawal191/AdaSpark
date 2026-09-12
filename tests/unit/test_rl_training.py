"""Unit tests: Day-27 training loop (PLAN line 273) - fakes only, NO Spark.

Every test drives ``run_training`` against a FakeEnv that returns scripted
rewards and a REAL QLearningAgent, so the frozen epsilon schedule, the frozen
update rule and the real policy store are exercised. Nothing here asserts a
reward threshold, a trend or an improvement: a training run records machinery
execution only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from sparkrl.agent.policy_store import PolicyExistsError, load_policy
from sparkrl.agent.q_learning import (AgentConfig, InvalidTransition,
                                      QLearningAgent, RLConfigError,
                                      Transition)
from sparkrl.rl.env import BudgetExhausted, EpisodeDone, SplitViolation, TRefMissing
from sparkrl.rl.state import StateEncoder
from sparkrl.rl.tref import TRefStore
from sparkrl.training.loop import (CALIBRATED_DATASET_SEED,
                                   CHECKPOINT_EVERY_EPISODES,
                                   EARLY_STOP_STABLE_EPOCHS, EPOCH_DEFINITION,
                                   KIND_SMOKE, STATUS_COMPLETED,
                                   STATUS_FAILED, STATUS_INTERRUPTED,
                                   STATUS_TRUNCATED, STOP_BUDGET, STOP_EARLY,
                                   BudgetPlanError, Cell, RunDirExistsError,
                                   TrainingConfig, TrainingPlanError,
                                   build_plan, greedy_snapshot, plan_episodes,
                                   run_training, trainable_cells)

pytestmark = [pytest.mark.unit]

# The measured EXP-002 calibration (results/experiments/exp-002/analysis/
# gate.json): F3_rdd|medium is null, everything else is a calibrated TRAIN cell.
GATE = {
    "F1_agg|medium": 36.669743,
    "F1_agg|small": 22.347372,
    "F2_join|medium": 16.126881,
    "F2_join|small": 2.214523,
    "F3_rdd|medium": None,
    "F3_rdd|small": 25.109380,
    "F5_mixed|medium": 32.759411,
    "F5_mixed|small": 3.903756,
}
EXPECTED_CELLS = ("F1_agg|medium", "F1_agg|small", "F2_join|medium",
                  "F2_join|small", "F3_rdd|small", "F5_mixed|medium",
                  "F5_mixed|small")

SMALL_BYTES = 100 * 1024 * 1024      # bin S, like every measured TRAIN cell


def store() -> TRefStore:
    return TRefStore(mapping=GATE)


def cfg() -> TrainingConfig:
    return TrainingConfig.from_yaml()


# --- fakes ---------------------------------------------------------------------
@dataclass(frozen=True)
class FakeStep:
    run_id: str
    episode_key: str
    action_index: int
    action_mode: str
    config_name: str
    config_fingerprint: str
    metrics: dict[str, Any]
    env_version: str = "fake-env/v1"


@dataclass(frozen=True)
class FakeObs:
    state: Any


class FakeEnv:
    """Duck-typed stand-in for SparkTuningEnv: reset / step / budget counters."""

    env_version = "fake-env/v1"

    def __init__(self, rewards, *, budget_limit: int = 500,
                 failures: frozenset[int] = frozenset(),
                 step_raises: dict[int, BaseException] | None = None,
                 reset_raises: dict[int, BaseException] | None = None) -> None:
        self._rewards = rewards
        self._budget_limit = int(budget_limit)
        self._used = 0
        self._failures = set(failures)
        self._step_raises = dict(step_raises or {})
        self._reset_raises = dict(reset_raises or {})
        self.encoder = StateEncoder()
        self.resets: list[dict[str, Any]] = []
        self._episode: dict[str, Any] | None = None
        self._n = 0

    # -- introspection the loop reads --------------------------------------
    @property
    def budget_limit(self) -> int:
        return self._budget_limit

    @property
    def executions_used(self) -> int:
        return self._used

    @property
    def budget_remaining(self) -> int:
        return self._budget_limit - self._used

    # -- API ----------------------------------------------------------------
    def reset(self, *, family, scale, seed=0, rep=1, last_reward=None):
        self._n += 1
        if self._n in self._reset_raises:
            raise self._reset_raises[self._n]
        if self.budget_remaining <= 0:
            raise BudgetExhausted(f"fake budget exhausted at {self._used}")
        self.resets.append({"family": family, "scale": scale,
                            "dataset_seed": seed, "rep": rep,
                            "last_reward": last_reward})
        state = self.encoder.encode(family, SMALL_BYTES, last_reward=last_reward)
        self._episode = {"family": family, "scale": scale, "seed": seed,
                         "rep": rep, "n": self._n}
        return FakeObs(state=state), {"episode_key": "fake"}

    def _reward_for(self, n: int) -> float:
        if callable(self._rewards):
            return float(self._rewards(n))
        return float(self._rewards[(n - 1) % len(self._rewards)])

    def step(self, action: int):
        assert self._episode is not None, "step() before reset()"
        ep = self._episode
        n = ep["n"]
        if n in self._step_raises:
            raise self._step_raises[n]
        reward = self._reward_for(n)
        self._used += 1
        usable = n not in self._failures
        state_after = self.encoder.encode(ep["family"], SMALL_BYTES,
                                          last_reward=reward)
        info = FakeStep(
            run_id=f"env-{ep['family']}-{ep['scale']}-s{ep['seed']}"
                   f"-cfg{action:02d}-r{ep['rep']}",
            episode_key=f"{ep['family']}|{ep['scale']}|seed{ep['seed']}"
                        f"|rep{ep['rep']}",
            action_index=int(action), action_mode="mode12",
            config_name=f"cfg{action:02d}", config_fingerprint=f"fp{action:02d}",
            metrics={"usable": usable, "timeout": False})
        self._episode = None
        return state_after, reward, True, False, info


def make_agent(*, epsilon: float | None = None, rng_seed: int = 0) -> QLearningAgent:
    return QLearningAgent(AgentConfig.from_yaml(), rng_seed=rng_seed,
                          epsilon=epsilon)


def drive(tmp_path: Path, *, episodes: int, rewards, cell_keys=None,
          agent_epsilon=None, agent_rng_seed=0, budget_limit=None,
          run_kind="training", failures=frozenset(), step_raises=None,
          reset_raises=None, env_budget=None, policy_dir=None,
          on_episode=None, now_utc="20260101T000000Z"):
    """Build a plan, a FakeEnv and a real agent, and run one training run."""
    plan = build_plan(agent_rng_seed=agent_rng_seed, episodes=episodes,
                      run_kind=run_kind, cell_keys=cell_keys,
                      budget_limit=budget_limit, config=cfg(),
                      tref_store=store(), run_root=tmp_path,
                      policy_dir=policy_dir, now_utc=now_utc)
    env = FakeEnv(rewards,
                  budget_limit=(plan.budget_limit if env_budget is None
                                else env_budget),
                  failures=failures, step_raises=step_raises,
                  reset_raises=reset_raises)
    agent = make_agent(epsilon=agent_epsilon, rng_seed=agent_rng_seed)
    result = run_training(plan, env=env, agent=agent,
                          q0_provenance={"source": "fake-q0"}, config=cfg(),
                          on_episode=on_episode)
    return plan, env, agent, result


def read_lines(result) -> list[dict[str, Any]]:
    text = Path(result.episode_log_path).read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def read_manifest(result) -> dict[str, Any]:
    return json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))


# --- 1-2: derived cell set ------------------------------------------------------
def test_trainable_cells_are_derived_train_cells_with_calibrated_tref():
    cells = trainable_cells(store())
    assert tuple(c.key() for c in cells) == EXPECTED_CELLS
    assert all(c.dataset_seed == CALIBRATED_DATASET_SEED for c in cells)
    assert all(c.t_ref_s == GATE[c.key()] for c in cells)
    assert "F3_rdd|medium" not in {c.key() for c in cells}


def test_f3_medium_lands_in_the_exclusion_list_with_a_reason(tmp_path):
    plan = build_plan(agent_rng_seed=0, episodes=7, config=cfg(),
                      tref_store=store(), run_root=tmp_path)
    assert {"cell": "F3_rdd|medium", "reason": "t_ref_null",
            "t_ref_s": None} in [dict(e) for e in plan.excluded]


def test_dataset_seed_one_is_refused_for_tref_not_for_the_split():
    with pytest.raises(TrainingPlanError) as exc:
        trainable_cells(store(), dataset_seed=1)
    msg = str(exc.value)
    assert "T_REF CALIBRATION" in msg
    assert "split" in msg.lower() and "NOT the split" in msg
    assert "SplitViolation" not in msg


def test_build_plan_refuses_dataset_seed_one_with_a_tref_message(tmp_path):
    with pytest.raises(TrainingPlanError) as exc:
        build_plan(agent_rng_seed=0, episodes=3, dataset_seed=1, config=cfg(),
                   tref_store=store(), run_root=tmp_path)
    assert "T_REF CALIBRATION" in str(exc.value)


def test_requesting_a_non_train_cell_names_the_split_not_tref():
    with pytest.raises(TrainingPlanError) as exc:
        trainable_cells(store(), cell_keys=["F4_ski|small"])
    assert "split=" in str(exc.value)


def test_requesting_an_uncalibrated_cell_names_tref_not_the_split():
    with pytest.raises(TrainingPlanError) as exc:
        trainable_cells(store(), cell_keys=["F3_rdd|medium"])
    assert "NO CALIBRATED T_REF" in str(exc.value)


# --- 3-4: the pure schedule -----------------------------------------------------
def test_plan_episodes_is_pure_and_round_robin():
    cells = trainable_cells(store())
    plan_a = plan_episodes(cells, 20)
    plan_b = plan_episodes(cells, 20)
    assert plan_a == plan_b
    assert [(e.index, e.epoch, e.rep, e.cell.key()) for e in plan_a[:9]] == [
        (1, 1, 1, "F1_agg|medium"), (2, 1, 1, "F1_agg|small"),
        (3, 1, 1, "F2_join|medium"), (4, 1, 1, "F2_join|small"),
        (5, 1, 1, "F3_rdd|small"), (6, 1, 1, "F5_mixed|medium"),
        (7, 1, 1, "F5_mixed|small"), (8, 2, 2, "F1_agg|medium"),
        (9, 2, 2, "F1_agg|small")]
    # every cell exactly once per COMPLETE epoch
    first_epoch = [e.cell.key() for e in plan_a if e.epoch == 1]
    assert sorted(first_epoch) == sorted(EXPECTED_CELLS)
    assert [e.rep for e in plan_a] == [e.epoch for e in plan_a]


def test_duplicate_cells_are_refused_because_record_paths_would_collide():
    c = Cell("F1_agg", "small", 0, 22.3)
    with pytest.raises(TrainingPlanError):
        plan_episodes([c, c], 2)


def test_n_episodes_produce_n_distinct_transition_record_paths(tmp_path):
    # the rep = epoch regression test: a fixed rep would make the env
    # os.replace() one episode's immutable record with another's.
    plan, env, _, result = drive(tmp_path, episodes=21, rewards=[0.5])
    paths = [ln["transition_record_relpath"] for ln in read_lines(result)]
    assert len(paths) == 21
    assert len(set(paths)) == 21
    # the relpath above is rebuilt by the loop from ep.rep, so it stays
    # self-consistent even if the ENV was told a different rep. Pin the value
    # the env actually received - that is what names the file on disk.
    assert [r["rep"] for r in env.resets] == [e.epoch for e in plan.episodes]


# --- 5-7: pre-flight refusals ---------------------------------------------------
def test_episodes_over_budget_is_refused_before_any_spark(tmp_path):
    with pytest.raises(BudgetPlanError):
        build_plan(agent_rng_seed=0, episodes=11, budget_limit=10, config=cfg(),
                   tref_store=store(), run_root=tmp_path)


def test_budget_above_the_frozen_cap_is_refused_at_plan_level(tmp_path):
    with pytest.raises(BudgetPlanError) as exc:
        build_plan(agent_rng_seed=0, episodes=7, budget_limit=501, config=cfg(),
                   tref_store=store(), run_root=tmp_path)
    assert "only LOWER" in str(exc.value)


def test_existing_run_dir_is_refused(tmp_path):
    plan = build_plan(agent_rng_seed=0, episodes=7, config=cfg(),
                      tref_store=store(), run_root=tmp_path,
                      now_utc="20260101T000000Z")
    plan.run_dir.mkdir(parents=True)
    with pytest.raises(RunDirExistsError):
        build_plan(agent_rng_seed=0, episodes=7, config=cfg(),
                   tref_store=store(), run_root=tmp_path,
                   now_utc="20260101T000000Z")


def test_unknown_agent_seed_and_zero_episodes_are_refused(tmp_path):
    with pytest.raises(TrainingPlanError):
        build_plan(agent_rng_seed=7, episodes=3, config=cfg(),
                   tref_store=store(), run_root=tmp_path)
    with pytest.raises(TrainingPlanError):
        build_plan(agent_rng_seed=0, episodes=0, config=cfg(),
                   tref_store=store(), run_root=tmp_path)


def test_smoke_plan_shape(tmp_path):
    plan = build_plan(agent_rng_seed=0, episodes=3, run_kind=KIND_SMOKE,
                      cell_keys=["F1_agg|small"], config=cfg(),
                      tref_store=store(), run_root=tmp_path / "smoke")
    assert [c.key() for c in plan.cells] == ["F1_agg|small"]
    assert len(plan.episodes) == 3 and plan.episodes_per_epoch == 1
    assert plan.budget_limit == 3          # exactly the planned episode count
    assert plan.run_dir.parent == tmp_path / "smoke"
    assert plan.policy_dir == plan.run_dir / "checkpoints"


# --- 8: greedy snapshot has no side effects -------------------------------------
def test_greedy_snapshot_touches_neither_rng_nor_n_states():
    probe = make_agent()
    reference = make_agent()
    state = StateEncoder().encode("F1_agg", SMALL_BYTES, last_reward=None)
    # seed one row WITHOUT touching the RNG, so the snapshot is non-empty
    for agent in (probe, reference):
        agent.update(Transition(state, 3, reward=0.9, next_state=None,
                                terminated=True))
    before_states, before_table = probe.n_states, probe.q_table()

    snap = greedy_snapshot(probe)

    assert snap == {"state-v1.5|agg|S|le0": 3}
    assert probe.n_states == before_states
    assert probe.q_table() == before_table
    # the exploration stream must be untouched: both agents agree afterwards
    assert ([probe.select_action(state) for _ in range(12)]
            == [reference.select_action(state) for _ in range(12)])


# --- 9: epoch / early stop ------------------------------------------------------
def test_early_stop_needs_three_identical_snapshots_not_two(tmp_path):
    # reward == q0_default makes every update a zero-delta no-op, so the greedy
    # snapshot changes only when a new state key appears.
    _, _, _, result = drive(tmp_path, episodes=10, rewards=[0.5],
                            cell_keys=["F1_agg|small"])
    man = read_manifest(result)
    epochs = man["epochs"]
    assert [e["stability_streak"] for e in epochs] == [0, 0, 1, 2]
    # epochs 2 and 3 were already identical (two identical snapshots) and the
    # run did NOT stop there; it stopped only at the third.
    hashes = [e["greedy_snapshot_sha256"] for e in epochs]
    assert hashes[1] == hashes[2] == hashes[3]
    assert result.stop_reason == STOP_EARLY and result.status == STATUS_COMPLETED
    assert result.exit_code == 0 and result.early_stopped
    assert result.episodes_completed == 4
    assert man["early_stop"]["at_epoch"] == 4
    assert man["early_stop"]["stable_epochs_required"] == EARLY_STOP_STABLE_EPOCHS


def test_a_changed_argmax_resets_the_stability_streak(tmp_path):
    # epsilon 0 + rng_seed 0: the first 35 draws all exceed the 0.05 floor, so
    # every action below is the greedy one (asserted).
    rewards = [0.5, 0.5, 0.5, -1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    _, _, _, result = drive(tmp_path, episodes=10, rewards=rewards,
                            cell_keys=["F1_agg|small"], agent_epsilon=0.0)
    lines = read_lines(result)
    assert [ln["action_index"] for ln in lines] == [0, 0, 0, 0, 0, 1]
    man = read_manifest(result)
    assert [e["stability_streak"] for e in man["epochs"]] == [0, 0, 1, 0, 1, 2]
    assert man["early_stop"]["at_epoch"] == 6
    assert result.episodes_completed == 6


def test_episodes_per_epoch_is_derived_from_the_cell_count(tmp_path):
    plan = build_plan(agent_rng_seed=0, episodes=14, config=cfg(),
                      tref_store=store(), run_root=tmp_path)
    assert plan.episodes_per_epoch == len(plan.cells) == 7
    assert cfg().epoch_definition == EPOCH_DEFINITION


# --- 10: epsilon threading ------------------------------------------------------
def test_epsilon_is_decayed_exactly_once_per_episode(tmp_path):
    # 7 cells => one epoch boundary in 12 episodes, so no early stop is possible
    _, _, agent, result = drive(tmp_path, episodes=12, rewards=[-1.0])
    lines = read_lines(result)
    assert len(lines) == 12
    expected = [max(0.05, 1.0 * 0.95 ** n) for n in range(1, 13)]
    assert [ln["epsilon_after"] for ln in lines] == pytest.approx(expected)
    assert lines[0]["epsilon_used"] == pytest.approx(1.0)
    for prev, cur in zip(lines, lines[1:]):
        assert cur["epsilon_used"] == pytest.approx(prev["epsilon_after"])
    assert agent.episodes == 12


# --- 11-12: last_reward threading and failed episodes ---------------------------
def test_last_reward_chain_is_global_and_chronological(tmp_path):
    rewards = [0.4, -1.0, 0.7, 0.2, 0.9, -0.3, 0.1]
    _, env, _, result = drive(tmp_path, episodes=7, rewards=rewards,
                              failures=frozenset({2}))
    lines = read_lines(result)
    assert lines[0]["last_reward_in"] is None
    assert lines[0]["feedback_source"] == "no_history_convention"
    assert [ln["last_reward_in"] for ln in lines[1:]] == rewards[:-1]
    assert all(ln["feedback_source"] == "previous_episode" for ln in lines[1:])
    # the chain is chronological, NOT per-cell: the cells all differ
    assert len({ln["cell"]["family"] + ln["cell"]["scale"] for ln in lines}) == 7
    # the env received exactly what the log records
    assert [r["last_reward"] for r in env.resets] == [None] + rewards[:-1]
    # a failed episode's -1.0 IS threaded
    assert lines[2]["last_reward_in"] == -1.0
    assert lines[2]["feedback_from_failed_episode"] is True
    assert lines[1]["feedback_from_failed_episode"] is False


def test_failed_episode_is_recorded_updated_and_the_run_continues(tmp_path):
    _, _, agent, result = drive(tmp_path, episodes=7,
                                rewards=[0.4, -1.0, 0.7, 0.2, 0.9, 0.3, 0.1],
                                failures=frozenset({2}))
    lines = read_lines(result)
    bad = lines[1]
    assert bad["failed"] is True and bad["usable"] is False
    assert bad["reward"] == -1.0 and bad["updated"] is True
    assert bad["td_delta"] is not None and bad["q_after"] != bad["q_before"]
    assert result.episodes_failed == 1 and result.episodes_completed == 7
    assert agent.updates == 7
    assert read_manifest(result)["counts"]["episodes_failed"] == 1


# --- 13-14: checkpoints ---------------------------------------------------------
def test_checkpoint_at_25_is_written_after_end_episode(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=25, rewards=[-1.0])
    lines = read_lines(result)
    assert len(lines) == 25
    assert [ln["episode_index"] for ln in lines
            if ln["checkpoint_policy_id"]] == [CHECKPOINT_EVERY_EPISODES]
    ckpt = result.checkpoints[0]
    assert ckpt["episode_index"] == 25
    assert ckpt["episodes"] == 25            # counter == the line above it
    assert ckpt["epsilon"] == pytest.approx(lines[24]["epsilon_after"])
    assert ckpt["epsilon"] != pytest.approx(lines[24]["epsilon_used"])
    artifact = load_policy(ckpt["policy_id"], result.run_dir / "checkpoints")
    assert artifact["episodes"] == 25
    assert artifact["epsilon"] == pytest.approx(ckpt["epsilon"])


def test_final_checkpoint_exists_on_a_short_clean_run(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=3, rewards=[0.5],
                            cell_keys=["F1_agg|small"], run_kind=KIND_SMOKE)
    assert result.status == STATUS_COMPLETED
    assert result.final_policy_id is not None
    assert result.checkpoints and result.checkpoints[-1]["episode_index"] == 3
    load_policy(result.final_policy_id, result.run_dir / "checkpoints")
    man = read_manifest(result)
    assert man["final_policy"]["policy_id"] == result.final_policy_id
    assert man["run_kind"] == KIND_SMOKE
    # checkpoints live in the run dir, never in the published policy store
    assert (result.run_dir / "checkpoints").is_dir()


def test_checkpoints_are_never_written_to_models_policies(tmp_path):
    plan, _, _, result = drive(tmp_path, episodes=3, rewards=[0.5],
                               cell_keys=["F1_agg|small"], run_kind=KIND_SMOKE)
    assert plan.policy_dir == plan.run_dir / "checkpoints"
    assert "models" not in plan.policy_dir.parts


# --- 15: budget ------------------------------------------------------------------
def test_budget_exhausted_from_reset_is_a_clean_truncated_stop(tmp_path):
    _, env, _, result = drive(tmp_path, episodes=7, rewards=[0.5], env_budget=3)
    assert result.status == STATUS_TRUNCATED
    assert result.stop_reason == STOP_BUDGET and result.exit_code == 0
    assert result.episodes_completed == 3 and env.executions_used == 3
    assert result.final_policy_id is not None          # final checkpoint present
    man = read_manifest(result)
    assert man["status"] == STATUS_TRUNCATED
    assert man["budget"]["live_executions"] == 3
    assert man["counts"]["episodes_planned"] == 7


def test_budget_exhausted_raised_by_reset_mid_run_is_caught(tmp_path):
    # defence in depth: the env raises even though budget_remaining looked fine
    boom = {3: BudgetExhausted("env guard")}
    _, _, _, result = drive(tmp_path, episodes=7, rewards=[0.5],
                            reset_raises=boom)
    assert result.status == STATUS_TRUNCATED
    assert result.stop_reason == STOP_BUDGET and result.exit_code == 0
    assert result.episodes_completed == 2
    assert result.final_policy_id is not None


def test_smoke_executions_count_against_the_frozen_cap(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=3, rewards=[0.5],
                            cell_keys=["F1_agg|small"], run_kind=KIND_SMOKE)
    budget = read_manifest(result)["budget"]
    assert budget["live_execution_cap"] == 500
    assert budget["live_executions"] == 3
    assert "COUNT" not in json.dumps(budget)           # no escape-hatch field
    assert "counts_against_sc6" not in json.dumps(read_manifest(result))


# --- 16-17: the failure table ----------------------------------------------------
def test_invalid_transition_writes_the_line_then_aborts(tmp_path):
    with pytest.raises(InvalidTransition):
        drive(tmp_path, episodes=5, rewards=[0.5, float("nan"), 0.5])
    run_dir = next((tmp_path).glob("train-*"))
    lines = [json.loads(ln) for ln
             in (run_dir / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    assert len(lines) == 2
    bad = lines[-1]
    assert bad["updated"] is False and bad["update_error"]
    assert bad["episode_index"] == 2
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert man["status"] == STATUS_FAILED
    assert man["stop_reason"] == "invalid_transition"
    assert man["exit_code"] == 1


@pytest.mark.parametrize("exc,reason", [
    (TRefMissing("no T_ref"), "tref_missing"),
    (SplitViolation("test cell"), "split_violation"),
    (EpisodeDone("no episode"), "episode_done"),
])
def test_env_exceptions_abort_with_the_right_stop_reason(tmp_path, exc, reason):
    with pytest.raises(type(exc)):
        drive(tmp_path, episodes=5, rewards=[0.5], step_raises={2: exc})
    run_dir = next((tmp_path).glob("train-*"))
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert man["status"] == STATUS_FAILED and man["stop_reason"] == reason
    assert man["exit_code"] == 1
    lines = (run_dir / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2                 # the in-flight line is forensic record
    assert json.loads(lines[-1])["executed"] is False
    assert "abort_error" in json.loads(lines[-1])


def test_policy_exists_error_aborts(tmp_path):
    shared = tmp_path / "shared_policies"
    _, _, _, first = drive(tmp_path / "a", episodes=3, rewards=[0.5],
                           cell_keys=["F1_agg|small"], policy_dir=shared)
    pid = first.final_policy_id
    path = shared / f"policy-{pid[:16]}.json"
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["q_table"] = {"state-v1.5|agg|S|le0": [9.0] * 12}   # same id, new body
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(PolicyExistsError):
        drive(tmp_path / "b", episodes=3, rewards=[0.5],
              cell_keys=["F1_agg|small"], policy_dir=shared)
    run_dir = next((tmp_path / "b").glob("train-*"))
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert man["stop_reason"] == "policy_exists" and man["status"] == STATUS_FAILED


def test_interrupt_at_an_episode_boundary_checkpoints(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=5, rewards=[0.5],
                            reset_raises={3: KeyboardInterrupt()})
    assert result.status == STATUS_INTERRUPTED and result.exit_code == 130
    assert result.episodes_completed == 2
    assert result.final_policy_id is not None
    man = read_manifest(result)
    assert "interrupted_mid_step" not in man


def test_interrupt_during_step_writes_no_checkpoint(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=5, rewards=[0.5],
                            step_raises={3: KeyboardInterrupt()})
    assert result.status == STATUS_INTERRUPTED and result.exit_code == 130
    assert result.checkpoints == () and result.final_policy_id is None
    man = read_manifest(result)
    assert man["interrupted_mid_step"] is True
    assert man["in_flight_episode"] == 3
    assert "uncertain" in man["budget_accounting"]


# --- 18-20: records --------------------------------------------------------------
def test_every_line_carries_both_seed_names_and_no_bare_seed(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=7, rewards=[0.5],
                            agent_rng_seed=1)
    for line in read_lines(result):
        assert line["agent_rng_seed"] == 1
        assert line["dataset_seed"] == CALIBRATED_DATASET_SEED
        assert "seed" not in line
        assert set(line["cell"]) == {"family", "scale", "dataset_seed", "rep"}
    man = read_manifest(result)
    assert man["agent_rng_seed"] == 1 and man["dataset_seed"] == 0
    assert "seed" not in man
    assert "exploration replicate" in man["seed_semantics"]


def test_manifest_makes_no_learning_claim(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=7, rewards=[0.5])
    claim = read_manifest(result)["learning_claim"]
    assert claim["learning_demonstrated"] is False
    assert claim["convergence_demonstrated"] is False
    assert claim["baseline_comparison"] is None
    assert "no claim of learning" in claim["note"]


def test_manifest_is_valid_json_at_every_rewrite_point(tmp_path):
    seen: list[str] = []

    def watch(outcome):
        run_dir = next((tmp_path).glob("train-*"))
        man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        seen.append(man["status"])
        assert man["record_schema_version"] == "rl-training-run/v1"

    _, _, _, result = drive(tmp_path, episodes=25, rewards=[-1.0],
                            on_episode=watch)
    assert len(seen) == 25 and set(seen) == {"running"}
    man = read_manifest(result)
    assert man["status"] == STATUS_COMPLETED
    assert len(man["epochs"]) == 3 and len(man["checkpoints"]) == 2
    assert man["epochs"][0]["visited_state_keys"]



def test_visited_state_keys_are_scoped_to_their_own_epoch(tmp_path):
    # The reward sign flips after epoch 1, so the feedback bin - and therefore
    # the state keys - differ between epoch 1 and epoch 2. If the per-epoch
    # `visited` reset were dropped, epoch 2 would inherit epoch 1's keys and
    # this comparison would fail.
    _, _, _, result = drive(tmp_path, episodes=21,
                            rewards=lambda n: 0.5 if n <= 7 else -0.5)
    lines = read_lines(result)
    man = read_manifest(result)
    assert len(man["epochs"]) == 3
    for i, epoch in enumerate(man["epochs"]):
        own = lines[i * 7:(i + 1) * 7]
        assert epoch["visited_state_keys"] == sorted(
            {ln["state_key_before"] for ln in own})
    assert man["epochs"][0]["visited_state_keys"] !=         man["epochs"][1]["visited_state_keys"]


def test_episode_line_joins_to_the_env_transition_record(tmp_path):
    _, _, _, result = drive(tmp_path, episodes=3, rewards=[0.5])
    for line in read_lines(result):
        cell, rep = line["cell"], line["cell"]["rep"]
        assert line["transition_record_relpath"] == (
            f"transitions/{cell['family']}/{cell['scale']}"
            f"/seed{cell['dataset_seed']}/{line['config_name']}/rep{rep}.json")
        assert line["env_run_id"].endswith(f"-r{rep}")
        assert line["reward_source"] == "env.step (frozen R3)"
        assert "execution_time_s" not in line    # the runner clock stays sole
        assert "metrics" not in line


def test_run_is_reproducible_for_the_same_seeds(tmp_path):
    volatile = {"wall_s", "written_utc", "run_id", "code_version"}

    def strip(lines):
        return [{k: v for k, v in ln.items() if k not in volatile} for ln in lines]

    _, _, _, a = drive(tmp_path / "a", episodes=14, rewards=[0.3, -1.0, 0.8])
    _, _, _, b = drive(tmp_path / "b", episodes=14, rewards=[0.3, -1.0, 0.8])
    assert strip(read_lines(a)) == strip(read_lines(b))
    assert ([c["policy_id"] for c in a.checkpoints]
            == [c["policy_id"] for c in b.checkpoints])
    ma, mb = read_manifest(a), read_manifest(b)
    assert ma["epochs"] == mb["epochs"]


def test_a_different_agent_seed_changes_only_exploration(tmp_path):
    plan_a = build_plan(agent_rng_seed=0, episodes=14, config=cfg(),
                        tref_store=store(), run_root=tmp_path,
                        now_utc="20260101T000000Z")
    plan_b = build_plan(agent_rng_seed=2, episodes=14, config=cfg(),
                        tref_store=store(), run_root=tmp_path,
                        now_utc="20260101T000000Z")
    assert ([(e.index, e.epoch, e.rep, e.cell.key()) for e in plan_a.episodes]
            == [(e.index, e.epoch, e.rep, e.cell.key()) for e in plan_b.episodes])
    assert plan_a.run_id != plan_b.run_id


# --- config ---------------------------------------------------------------------
def test_training_config_matches_the_frozen_values():
    c = cfg()
    assert c.checkpoint_every_episodes == CHECKPOINT_EVERY_EPISODES == 25
    assert c.early_stop_stable_epochs == EARLY_STOP_STABLE_EPOCHS == 2
    assert c.dataset_seed == CALIBRATED_DATASET_SEED == 0
    assert c.epoch_definition == EPOCH_DEFINITION
    assert c.live_execution_cap == 500
    assert c.training_seeds == (0, 1, 2)
    assert c.run_root == "results/training"
    assert c.smoke_run_root == "results/training/smoke"


@pytest.mark.parametrize("mutation", [
    {"training": {"checkpoint_every_episodes": 10}},
    {"training": {"early_stop_stable_epochs": 1}},
    {"training": {"dataset_seed": 1}},
    {"training": {"epoch_definition": "every_25_episodes"}},
    {"live_execution_cap": 1000},
    {"training_seeds": [0, 1, 2, 3]},
])
def test_training_config_hard_errors_on_drift(tmp_path, mutation):
    import yaml
    from sparkrl.agent.q_learning import DEFAULT_RL_YAML
    raw = yaml.safe_load(Path(DEFAULT_RL_YAML).read_text(encoding="utf-8"))
    for key, value in mutation.items():
        if isinstance(value, dict):
            raw[key].update(value)
        else:
            raw[key] = value
    path = tmp_path / "rl.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(RLConfigError):
        TrainingConfig.from_yaml(path)


def test_training_block_absent_is_a_hard_error(tmp_path):
    import yaml
    from sparkrl.agent.q_learning import DEFAULT_RL_YAML
    raw = yaml.safe_load(Path(DEFAULT_RL_YAML).read_text(encoding="utf-8"))
    raw.pop("training")
    path = tmp_path / "rl.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(RLConfigError):
        TrainingConfig.from_yaml(path)
