"""Integration (real Spark): the Day-27 training loop end to end, 3 episodes.

plan -> episode -> action -> env.step (REAL Spark) -> reward -> agent.update ->
episodes.jsonl line + transition record -> final checkpoint -> manifest.
F1_agg / small / DATASET seed 0 only (T_ref 22.35 s), agent RNG seed 0, budget
exactly 3. Costs 3 live executions of the frozen 500.

NOTE: this test writes to the REAL smoke run root (`configs/rl.yaml`
`training.smoke_run_root` = `results/training/smoke/`), NOT to a pytest
tmp_path, so every invocation adds a run directory and 3 executions to the
cross-run SC6 ledger that `scripts/validate_rl_training.py` check 18 sums.
That is deliberate - decision D4 refuses a ledger that hides real executions -
but it means running the integration suite SPENDS frozen budget. Run it when
you mean to.

This asserts MACHINERY ONLY: record counts, joins, counters, budget accounting,
epsilon threading and checkpoint integrity. It never asserts a reward value, a
trend or an improvement - a smoke run proves the loop executes and proves
nothing about learning, convergence or superiority.
"""
import json
from pathlib import Path

import pytest

from sparkrl.agent.policy_store import load_policy
from sparkrl.spark.config import SparkConfig
from sparkrl.training.loop import (CALIBRATED_DATASET_SEED, EPISODE_SCHEMA,
                                   KIND_SMOKE, LOOP_VERSION, MANIFEST_SCHEMA,
                                   STATUS_COMPLETED, STATUS_TRUNCATED,
                                   STOP_BUDGET, STOP_COMPLETED, STOP_EARLY,
                                   TrainingConfig, build_env_and_agent,
                                   build_plan, run_training)

pytestmark = pytest.mark.integration

SMOKE_CELL = "F1_agg|small"
SMOKE_EPISODES = 3           # minimum that reaches an epoch boundary 3x
PUBLISHED_POLICIES = Path("models/policies")


def _published() -> set[str]:
    return {p.name for p in PUBLISHED_POLICIES.glob("*.json")} \
        if PUBLISHED_POLICIES.exists() else set()


def test_training_loop_three_real_episodes():
    before_published = _published()
    # CONFIRMED fix 3: the integration smoke's 3 live executions are a REAL
    # spend of the frozen 500, so they must land in the operator-visible
    # SC6 ledger (`results/training/**/manifest.json`). A pytest tmp dir is
    # garbage-collected and would leave the spend unrecorded (the ledger
    # would report 3 while Day 28 was sized at 500-3-after-6). The
    # configured smoke root writes there; run dirs stay unique per second.
    smoke_root = Path(TrainingConfig.from_yaml().smoke_run_root)
    if not smoke_root.is_absolute():
        smoke_root = Path(__file__).resolve().parents[2] / smoke_root

    plan = build_plan(agent_rng_seed=0, episodes=SMOKE_EPISODES,
                      run_kind=KIND_SMOKE,
                      dataset_seed=CALIBRATED_DATASET_SEED,
                      cell_keys=[SMOKE_CELL], run_root=smoke_root)
    assert [c.key() for c in plan.cells] == [SMOKE_CELL]
    assert plan.cells[0].t_ref_s == pytest.approx(22.347372)   # EXP-002 gate
    assert plan.budget_limit == SMOKE_EPISODES        # smoke cannot overrun
    assert plan.episodes_per_epoch == 1
    assert [(e.index, e.epoch, e.rep) for e in plan.episodes] == [
        (1, 1, 1), (2, 2, 2), (3, 3, 3)]

    env, agent, q0_provenance = build_env_and_agent(
        plan, SparkConfig.from_yaml("configs/baseline_b0.yaml"))
    assert env.budget_limit == SMOKE_EPISODES

    result = run_training(plan, env=env, agent=agent,
                          q0_provenance=q0_provenance)

    # --- run outcome: a clean stop, every planned episode executed ------------
    assert result.status in (STATUS_COMPLETED, STATUS_TRUNCATED)
    assert result.stop_reason in (STOP_COMPLETED, STOP_EARLY, STOP_BUDGET)
    assert result.exit_code == 0
    assert result.episodes_completed == SMOKE_EPISODES
    assert result.epochs_completed == SMOKE_EPISODES     # 1 cell => 1 ep/epoch

    # --- budget accounting is the env's, and it is exhausted exactly ----------
    assert env.executions_used == SMOKE_EPISODES
    assert env.budget_remaining == 0
    assert result.executions_used == SMOKE_EPISODES

    # --- episode log: one line per completed episode --------------------------
    lines = [json.loads(ln) for ln in
             result.episode_log_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == SMOKE_EPISODES
    assert [ln["episode_index"] for ln in lines] == [1, 2, 3]
    assert [ln["epoch_index"] for ln in lines] == [1, 2, 3]
    for ln in lines:
        assert ln["record_schema_version"] == EPISODE_SCHEMA
        assert ln["loop_version"] == LOOP_VERSION
        assert ln["run_id"] == plan.run_id and ln["run_kind"] == KIND_SMOKE
        assert ln["agent_rng_seed"] == 0 and ln["dataset_seed"] == 0
        assert "seed" not in ln                 # the bare name is ambiguous
        assert ln["executed"] is True and ln["updated"] is True
        assert ln["cell"]["family"] == "F1_agg" and ln["cell"]["scale"] == "small"
        assert ln["t_ref_s"] == pytest.approx(22.347372)
        # reward is COPIED from env.step (frozen R3), never recomputed here
        assert ln["reward_source"] == "env.step (frozen R3)"
        assert -1.0 <= ln["reward"] <= 2.0
        assert isinstance(ln["td_delta"], float)
        assert ln["q_after"] == pytest.approx(
            ln["q_before"] + 0.2 * (ln["reward"] - ln["q_before"]))   # alpha=0.2

    # --- three distinct transition records, each joining back to its line -----
    relpaths = [ln["transition_record_relpath"] for ln in lines]
    assert len(set(relpaths)) == SMOKE_EPISODES      # the rep = epoch guarantee
    written = sorted((result.run_dir / "transitions").rglob("*.json"))
    assert len(written) == SMOKE_EPISODES
    for ln, rep in zip(lines, (1, 2, 3)):
        rec_path = result.run_dir / ln["transition_record_relpath"]
        assert rec_path.exists()
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        assert rec["run_id"] == ln["env_run_id"]
        assert rec["episode_key"] == ln["episode_key"]
        assert rec["episode_key"].endswith(f"|seed0|rep{rep}")
        assert rec["action_index"] == ln["action_index"]
        assert rec["reward"]["value"] == pytest.approx(ln["reward"])
        assert rec["reward"]["formula_id"] == "R3"

    # --- epsilon and feedback threading (frozen schedule, decay once/episode) -
    assert [ln["epsilon_used"] for ln in lines] == [
        pytest.approx(1.0), pytest.approx(0.95), pytest.approx(0.9025)]
    for prev, cur in zip(lines, lines[1:]):
        assert cur["epsilon_used"] == pytest.approx(prev["epsilon_after"])
        assert cur["last_reward_in"] == pytest.approx(prev["reward"])
        assert cur["feedback_source"] == "previous_episode"
    assert lines[0]["last_reward_in"] is None
    assert lines[0]["feedback_source"] == "no_history_convention"
    assert agent.episodes == SMOKE_EPISODES and agent.updates == SMOKE_EPISODES
    assert agent.epsilon == pytest.approx(lines[-1]["epsilon_after"])

    # --- one final checkpoint, inside the run dir, and it verifies ------------
    assert len(result.checkpoints) == 1              # 3 < 25: final only
    ckpt = result.checkpoints[0]
    assert ckpt["episode_index"] == SMOKE_EPISODES
    assert ckpt["episodes"] == SMOKE_EPISODES and ckpt["updates"] == SMOKE_EPISODES
    assert ckpt["epsilon"] == pytest.approx(lines[-1]["epsilon_after"])
    assert (result.run_dir / ckpt["path"]).exists()
    artifact = load_policy(result.final_policy_id, plan.policy_dir)
    assert artifact["q_table"] == agent.q_table()
    assert artifact["contract_versions"]["reward_formula"] == "R3"

    # published policies are for deliberate publication; the loop never writes there
    assert _published() == before_published

    # --- manifest: derived, honest, and claims nothing ------------------------
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["record_schema_version"] == MANIFEST_SCHEMA
    assert manifest["status"] == result.status
    assert manifest["stop_reason"] == result.stop_reason
    assert manifest["run_kind"] == KIND_SMOKE
    assert manifest["agent_rng_seed"] == 0 and manifest["dataset_seed"] == 0
    assert manifest["budget"]["live_executions"] == SMOKE_EPISODES
    assert manifest["budget"]["budget_limit_this_run"] == SMOKE_EPISODES
    assert manifest["budget"]["live_execution_cap"] == 500
    counts = manifest["counts"]
    assert counts["episodes_planned"] == SMOKE_EPISODES
    assert counts["episodes_completed"] == SMOKE_EPISODES
    assert counts["episodes_updated"] == SMOKE_EPISODES
    assert counts["episodes_failed"] == sum(1 for ln in lines if ln["failed"])
    assert len(manifest["epochs"]) == SMOKE_EPISODES
    assert manifest["final_policy"]["policy_id"] == result.final_policy_id
    assert manifest["resume"]["implemented"] is False
    assert manifest["q0_provenance"]["source"] == "exp002"
    assert manifest["contract_versions"]["reward_formula"] == "R3"
    claim = manifest["learning_claim"]
    assert claim["learning_demonstrated"] is False
    assert claim["convergence_demonstrated"] is False
    assert claim["baseline_comparison"] is None
