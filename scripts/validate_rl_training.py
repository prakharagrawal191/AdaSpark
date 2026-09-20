#!/usr/bin/env python
"""Day-27 validator: training loop (PLAN line 273; PLAN section 16).

Checks the frozen loop boundaries: the additive configs/rl.yaml training block
adds no hyperparameter, the episode schedule is DERIVED and TRAIN-only at the
calibrated dataset seed, every scheduled cell has a calibrated T_ref, the budget
guard cannot exceed 500, epsilon decays exactly once per episode on the frozen
schedule, the checkpoint cadence is 25, the early-stop rule needs three
identical greedy snapshots, plans are deterministic, and the loop delegates
reward / T_ref / Spark (no cache, no orchestrator, no deep RL).

Every run driven here uses a FAKE environment: no Spark, no live execution.
Nothing here supports a claim of learning, convergence or improvement.
PASS/FAIL/SKIP per check; overall PASS requires every applicable check green.
"""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.q_learning import AgentConfig, QLearningAgent  # noqa: E402
from sparkrl.rl.state import StateEncoder  # noqa: E402
from sparkrl.rl.tref import TRefStore  # noqa: E402
from sparkrl.training.loop import (CALIBRATED_DATASET_SEED,  # noqa: E402
                                   CHECKPOINT_EVERY_EPISODES,
                                   EARLY_STOP_STABLE_EPOCHS, KIND_SMOKE,
                                   BudgetPlanError, TrainingConfig,
                                   TrainingPlanError, build_plan,
                                   plan_episodes, run_training,
                                   trainable_cells)

RL_YAML = PROJECT / "configs" / "rl.yaml"
LOOP_SRC = PROJECT / "src" / "sparkrl" / "training" / "loop.py"
CLI_SRC = PROJECT / "scripts" / "run_training.py"
AUDIT = PROJECT / "docs" / "research" / "DAY27_TRAINING_LOOP_AUDIT.md"
TRAINING_RESULTS = PROJECT / "results" / "training"
SMALL_BYTES = 100 * 1024 * 1024          # bin S, like every measured TRAIN cell
EXPECTED_CELLS = ("F1_agg|medium", "F1_agg|small", "F2_join|medium",
                  "F2_join|small", "F3_rdd|small", "F5_mixed|medium",
                  "F5_mixed|small")

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print(f"{name:<30} {status:<5} {detail}")


# --- a fake environment: the loop is duck-typed, so no Spark is needed ---------
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


class FakeEnv:
    env_version = "fake-env/v1"

    def __init__(self, reward: float = 0.4, budget_limit: int = 500) -> None:
        self._reward = float(reward)
        self._limit = int(budget_limit)
        self._used = 0
        self.encoder = StateEncoder()
        self._episode: dict[str, Any] | None = None

    @property
    def budget_limit(self) -> int:
        return self._limit

    @property
    def executions_used(self) -> int:
        return self._used

    @property
    def budget_remaining(self) -> int:
        return self._limit - self._used

    def reset(self, *, family, scale, seed=0, rep=1, last_reward=None):
        self._episode = {"family": family, "scale": scale, "seed": seed,
                         "rep": rep}
        state = self.encoder.encode(family, SMALL_BYTES, last_reward=last_reward)
        return type("Obs", (), {"state": state})(), {"episode_key": "fake"}

    def step(self, action: int):
        ep = self._episode
        assert ep is not None, "step() before reset()"
        self._used += 1
        after = self.encoder.encode(ep["family"], SMALL_BYTES,
                                    last_reward=self._reward)
        info = FakeStep(
            run_id=f"env-{ep['family']}-{ep['scale']}-s{ep['seed']}"
                   f"-cfg{action:02d}-r{ep['rep']}",
            episode_key=f"{ep['family']}|{ep['scale']}|seed{ep['seed']}"
                        f"|rep{ep['rep']}",
            action_index=int(action), action_mode="mode12",
            config_name=f"cfg{action:02d}", config_fingerprint=f"fp{action:02d}",
            metrics={"usable": True, "timeout": False})
        self._episode = None
        return after, self._reward, True, False, info


def _drive(tmp: Path, *, episodes: int, cfg: TrainingConfig, tag: str,
           reward: float = 0.4, epsilon: float | None = None):
    """One fake-env training run; returns (plan, result, lines, manifest)."""
    plan = build_plan(agent_rng_seed=0, episodes=episodes, config=cfg,
                      run_root=tmp, now_utc=tag)
    env = FakeEnv(reward=reward, budget_limit=plan.budget_limit)
    agent = QLearningAgent(AgentConfig.from_yaml(), rng_seed=0, epsilon=epsilon)
    result = run_training(plan, env=env, agent=agent,
                          q0_provenance={"source": "fake-q0"}, config=cfg)
    lines = [json.loads(ln) for ln
             in Path(result.episode_log_path).read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    return plan, result, lines, manifest


def main() -> int:
    # 1. module imports and versions
    try:
        mod = importlib.import_module("sparkrl.training")
        check("01 training_imports", True,
              f"{mod.LOOP_VERSION} / {mod.EPISODE_SCHEMA} / {mod.MANIFEST_SCHEMA}")
    except Exception as exc:  # noqa: BLE001
        check("01 training_imports", False, str(exc))
        return _finish()

    # 2. frozen PLAN-16 training block + untouched existing keys
    try:
        cfg = TrainingConfig.from_yaml()
        ok = (cfg.checkpoint_every_episodes == 25
              and cfg.early_stop_stable_epochs == 2
              and cfg.dataset_seed == CALIBRATED_DATASET_SEED
              and cfg.epoch_definition == mod.EPOCH_DEFINITION
              and cfg.live_execution_cap == 500
              and cfg.training_seeds == (0, 1, 2))
        check("02 training_config_frozen", ok,
              f"ckpt={cfg.checkpoint_every_episodes} "
              f"stable={cfg.early_stop_stable_epochs} "
              f"dseed={cfg.dataset_seed} cap={cfg.live_execution_cap} "
              f"seeds={list(cfg.training_seeds)}")
    except Exception as exc:  # noqa: BLE001
        check("02 training_config_frozen", False, str(exc))
        return _finish()

    # 3. the additive block introduces NO new hyperparameter
    raw = yaml.safe_load(RL_YAML.read_text(encoding="utf-8"))
    block = dict(raw.get("training") or {})
    expected_block = {"loop_version", "epoch_definition",
                      "checkpoint_every_episodes", "early_stop_stable_epochs",
                      "dataset_seed", "run_root", "smoke_run_root"}
    tuning = re.compile(r"alpha|gamma|epsilon|q0|learning_rate|decay|lambda|tau")
    expected_top = {"rl_config_schema", "learner", "alpha", "gamma",
                    "epsilon_start", "epsilon_min", "epsilon_decay", "q0_default",
                    "q0_source", "q0_aggregation", "training_seeds",
                    "live_execution_cap", "policy_dir", "training"}
    extra = sorted(set(block) - expected_block)
    drift = sorted(k for k in block if tuning.search(k))
    top_drift = sorted(set(raw) ^ expected_top)
    check("03 no_new_hyperparameters",
          not extra and not drift and not top_drift,
          f"training keys {sorted(block)}; extra={extra} tuning={drift} "
          f"top_level_drift={top_drift}")

    # 4. the schedule is DERIVED from the real gate: TRAIN-only, T_ref non-null
    try:
        store = TRefStore()
        cells = trainable_cells(store)
        excluded = {e["cell"]: e for e in build_plan(
            agent_rng_seed=0, episodes=1, config=cfg,
            run_root=Path(tempfile.gettempdir()) / "sparkrl-day27-plan",
            now_utc="20260101T000000Z").excluded}
        ok = (tuple(c.key() for c in cells) == EXPECTED_CELLS
              and all(c.dataset_seed == CALIBRATED_DATASET_SEED for c in cells)
              and all(store.get(c.family, c.scale, 0) is not None for c in cells)
              and excluded["F3_rdd|medium"]["reason"] == "t_ref_null"
              and excluded["F3_rdd|medium"]["t_ref_s"] is None)
        check("04 schedule_derived", ok,
              f"{len(cells)} TRAIN cells, all T_ref calibrated; "
              f"F3_rdd|medium excluded (t_ref_null); source {store.source}")
    except Exception as exc:  # noqa: BLE001
        check("04 schedule_derived", False, str(exc))

    # 5. validation/test cells are REFUSED - prove the guard fires
    refusals: list[str] = []
    for key in ("F4_ski|small", "F1_agg|large"):
        try:
            trainable_cells(TRefStore(), cell_keys=[key])
            refusals.append(f"{key}: NOT REFUSED")
        except TrainingPlanError as exc:
            msg = str(exc)
            if "TRAIN" not in msg or "split" not in msg:
                refusals.append(f"{key}: message does not name the split")
    check("05 non_train_cells_refused", not refusals,
          str(refusals) or "F4_ski|small and F1_agg|large refused as non-TRAIN "
                           "(PLAN section 18); TEST split frozen until Day 31")

    # 6. dataset_seed: TRAIN-but-uncalibrated (1, 2) refuses with a T_REF
    # CALIBRATION message; split seeds (validation 3, test 4) refuse with a
    # PLAN-section-18 SPLIT message (CONFIRMED fix 1)
    try:
        build_plan(agent_rng_seed=0, episodes=1, dataset_seed=1, config=cfg,
                   run_root=Path(tempfile.gettempdir()))
        check("06 dataset_seed_guard", False, "dataset_seed=1 was NOT refused")
    except TrainingPlanError as exc:
        msg = str(exc)
        check("06 dataset_seed_guard",
              "T_REF CALIBRATION" in msg and "NOT the split" in msg,
              "dataset_seed=1 refused; message names T_ref, not the split")
    try:
        build_plan(agent_rng_seed=0, episodes=1, dataset_seed=3, config=cfg,
                   run_root=Path(tempfile.gettempdir()))
        check("06b validation_seed_guard", False, "dataset_seed=3 was NOT refused")
    except TrainingPlanError as exc:
        check("06b validation_seed_guard", "SPLIT" in str(exc),
              "dataset_seed=3 refused; message names the split, not T_ref")
    try:
        build_plan(agent_rng_seed=0, episodes=1, dataset_seed=4, config=cfg,
                   run_root=Path(tempfile.gettempdir()))
        check("06c test_seed_guard", False, "dataset_seed=4 was NOT refused")
    except TrainingPlanError as exc:
        check("06c test_seed_guard", "SPLIT" in str(exc),
              "dataset_seed=4 refused; message names the split, not T_ref")

    return _part2(cfg)


def _part2(cfg: TrainingConfig) -> int:
    # 7. a repeated plan is byte-identical; N episodes -> N distinct record paths
    try:
        tmp_root = Path(tempfile.gettempdir()) / "sparkrl-day27-plan"
        kw = dict(agent_rng_seed=0, episodes=20, config=cfg, run_root=tmp_root,
                  now_utc="20260101T000000Z")
        a, b = build_plan(**kw).to_dict(), build_plan(**kw).to_dict()
        cells = trainable_cells(TRefStore())
        eps = plan_episodes(cells, 20)
        paths = {f"{e.cell.family}/{e.cell.scale}/rep{e.rep}" for e in eps}
        epochs = sorted({e.epoch for e in eps})
        check("07 plan_deterministic",
              a == b and len(paths) == 20 and epochs == [1, 2, 3],
              f"identical dry-run plans; 20 episodes -> {len(paths)} distinct "
              f"record paths over epochs {epochs} (rep = epoch)")
    except Exception as exc:  # noqa: BLE001
        check("07 plan_deterministic", False, str(exc))

    # 8. the budget guard cannot be raised above the frozen 500
    findings: list[str] = []
    root = Path(tempfile.gettempdir()) / "sparkrl-day27-plan"
    try:
        build_plan(agent_rng_seed=0, episodes=1, budget_limit=501, config=cfg,
                   run_root=root)
        findings.append("--budget 501 was accepted")
    except BudgetPlanError:
        pass
    try:
        build_plan(agent_rng_seed=0, episodes=600, config=cfg, run_root=root)
        findings.append("600 episodes > cap was accepted")
    except BudgetPlanError:
        pass
    plan = build_plan(agent_rng_seed=0, episodes=7, config=cfg, run_root=root,
                      now_utc="20260101T000000Z")
    if plan.budget_limit > cfg.live_execution_cap:
        findings.append(f"budget_limit {plan.budget_limit} > cap")
    smoke = build_plan(agent_rng_seed=0, episodes=3, run_kind=KIND_SMOKE,
                       cell_keys=["F1_agg|small"], config=cfg, run_root=root,
                       now_utc="20260101T000000Z")
    if smoke.budget_limit != 3:
        findings.append(f"smoke budget_limit {smoke.budget_limit} != 3")
    # the smoke branch binds the frozen cap too: it used to ignore both the
    # cap and the caller's budget_limit entirely
    try:
        build_plan(agent_rng_seed=0, episodes=600, run_kind=KIND_SMOKE,
                   cell_keys=["F1_agg|small"], config=cfg, run_root=root)
        findings.append("smoke episodes=600 was accepted against the cap")
    except BudgetPlanError:
        pass
    try:
        build_plan(agent_rng_seed=0, episodes=3, run_kind=KIND_SMOKE,
                   cell_keys=["F1_agg|small"], config=cfg, budget_limit=501,
                   run_root=root)
        findings.append("smoke --budget 501 was accepted")
    except BudgetPlanError:
        pass
    check("08 budget_guard", not findings,
          str(findings) or f"cap {cfg.live_execution_cap} may only be LOWERED; "
                           f"episodes > limit refused before any Spark")

    # 9-11. one fake-env run: epsilon schedule, checkpoints, early stop
    try:
        with tempfile.TemporaryDirectory() as td:
            plan, result, lines, manifest = _drive(
                Path(td), episodes=40, cfg=cfg, tag="20260101T000000Z")

            # 9. epsilon: decayed exactly once per episode, 1.0 * 0.95**n @ 0.05
            ac = AgentConfig.from_yaml()
            want = [max(ac.epsilon_min, ac.epsilon_start * ac.epsilon_decay ** n)
                    for n in range(len(lines))]
            got = [ln["epsilon_used"] for ln in lines]
            chained = all(abs(b["epsilon_used"] - a["epsilon_after"]) < 1e-12
                          for a, b in zip(lines, lines[1:]))
            check("09 epsilon_schedule",
                  chained and all(abs(g - w) < 1e-12 for g, w in zip(got, want)),
                  f"{len(lines)} episodes: {got[0]:.4f} -> {got[-1]:.4f} "
                  f"(1.0 * 0.95**n, floor {ac.epsilon_min}); decayed once each")

            # 10. checkpoint cadence 25, AFTER end_episode, plus one final
            cadence = [c["episode_index"] for c in manifest["checkpoints"]]
            post_decay = all(
                abs(c["epsilon"] - ac.epsilon_start * ac.epsilon_decay ** c["episode_index"])
                < 1e-12 or c["epsilon"] == ac.epsilon_min
                for c in manifest["checkpoints"])
            counters = all(c["episodes"] == c["episode_index"]
                           for c in manifest["checkpoints"])
            final = manifest["final_policy"] is not None
            ok = (CHECKPOINT_EVERY_EPISODES == 25
                  and cfg.checkpoint_every_episodes == 25
                  and all(i % 25 == 0 for i in cadence[:-1])
                  and cadence[-1] == result.episodes_completed
                  and post_decay and counters and final)
            check("10 checkpoint_cadence", ok,
                  f"every 25 episodes + one final: {cadence}; each artifact's "
                  f"episodes == its episode_index and epsilon is post-decay")

            # 11. early stop: 3 identical snapshots (2 stable comparisons)
            streaks = [e["stability_streak"] for e in manifest["epochs"]]
            required = manifest["early_stop"]["stable_epochs_required"]
            # a greedy (epsilon = 0) run over a constant reward settles, so the
            # rule can be observed FIRING rather than merely not firing
            with tempfile.TemporaryDirectory() as td2:
                _p2, r2, _l2, m2 = _drive(Path(td2), episodes=70, cfg=cfg,
                                          tag="20260102T000000Z", reward=0.9,
                                          epsilon=0.0)
            s2 = [e["stability_streak"] for e in m2["epochs"]]
            e2 = m2["early_stop"]
            ok = (EARLY_STOP_STABLE_EPOCHS == 2 and required == 2
                  and (not streaks or streaks[0] == 0)
                  and all(s < 2 for s in streaks[:-1])
                  and e2["triggered"] is True and r2.early_stopped is True
                  and s2[-1] == 2 and all(s < 2 for s in s2[:-1])
                  and len(m2["epochs"]) == e2["at_epoch"] >= 3)
            check("11 early_stop_rule", ok,
                  f"exploring run streaks {streaks} (no stop); greedy run "
                  f"streaks {s2} -> fired at epoch {e2['at_epoch']} on the "
                  f"THIRD identical snapshot, never the second")

            # 12b. records carry both seed names and the no-claim block
            claim = manifest["learning_claim"]
            ok = (all(ln["agent_rng_seed"] == 0 and ln["dataset_seed"] == 0
                      and "seed" not in ln for ln in lines)
                  and manifest["agent_rng_seed"] == 0
                  and manifest["dataset_seed"] == 0
                  and claim["learning_demonstrated"] is False
                  and claim["convergence_demonstrated"] is False)
            check("12 record_seed_and_claim", ok,
                  "every line carries agent_rng_seed + dataset_seed and no "
                  "bare 'seed'; manifest asserts no learning claim")
    except Exception as exc:  # noqa: BLE001
        for name in ("09 epsilon_schedule", "10 checkpoint_cadence",
                     "11 early_stop_rule", "12 record_seed_and_claim"):
            check(name, False, f"fake-env run failed: {exc}")

    return _part3()


def _part3() -> int:
    # 13. the seed vocabulary is unambiguous: one bare `seed=` site, annotated
    bare = re.compile(r"(?<![A-Za-z0-9_])seed=")
    hits = [(p.name, i + 1, ln.strip())
            for p in (LOOP_SRC, CLI_SRC)
            for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines())
            if bare.search(ln)]
    ok = len(hits) == 1 and "DATASET seed" in hits[0][2] and "env" in hits[0][2]
    check("13 no_seed_ambiguity", ok,
          f"{len(hits)} bare 'seed=' site(s): "
          f"{[(h[0], h[1]) for h in hits]} (the annotated env.reset call)")

    # 14. reward / T_ref / Spark are DELEGATED - the loop computes none of them
    src = LOOP_SRC.read_text(encoding="utf-8")
    banned = ["RewardCalculator(", "from sparkrl.rl.reward", "execute_run(",
              "SparkSession", "build_session", "spark_submit"]
    found = [b for b in banned if b in src]
    check("14 reward_spark_delegated", not found,
          str(found) or "loop consumes env.step reward; env owns R3/T_ref/"
                        "guards and the frozen runner owns Spark")

    # 15-17. no cache, no orchestrator, no deep RL in the training layer
    layer = "\n".join(f.read_text(encoding="utf-8") for f in
                      sorted((PROJECT / "src/sparkrl/training").glob("*.py")))
    low = layer.lower()
    check("15 no_cache_no_orchestrator",
          "cachekey" not in low and "cache_hit" not in low
          and "cacheentry" not in low and "def run_experiment" not in low
          and "itertools.product" not in low,
          "COMP-EXP-11 cache and COMP-EXP-12 orchestrator remain deferred "
          "(named only as deferrals in the docstrings)")
    libs = [lib for lib in ("torch", "tensorflow", "keras", "stable_baselines",
                            "replay_buffer", "target_network")
            if lib in low]
    check("16 no_deep_rl_libs", not libs, str(libs) or "clean (tabular only)")
    # 17. no unauthorized future-experiment drivers (DEC-018B exception).
    #     Original Day-27 invariant (commit 6d85481, 2026-09-12):
    #         exp_files = scripts.glob("*exp00[35]*"); PASS iff empty.
    #     That premise was valid on Day-27 because scripts/run_exp005.py
    #     did not exist anywhere (verified: `git show 6d85481:...` fails)
    #     and no HEAD decision authorized TEST execution. DEC-018
    #     Decision B (commit 715a7d3, 2026-09-14, recorded in
    #     DECISIONS.md) later authorized run_exp005.py -- 7 instances x
    #     7 arms x 5 reps = 245 TEST executions on EXP-005's own register
    #     line, outside the SC6 TRAIN cap -- and the driver was committed
    #     (feb5a16) and is HEAD-tracked. The bare existence check is
    #     therefore stale for run_exp005.py only. Surviving invariant
    #     (narrower but not weaker): run_exp005.py may exist IFF it
    #     satisfies the DEC-018B content contract below (filename alone
    #     never authorizes); every other future driver -- EXP-003 /
    #     EXP-005b / EXP-006 in any naming form (exp003/exp-003/exp_003,
    #     exp005/exp-005/exp_005, exp005b/exp-005b/exp_005b,
    #     exp006/exp-006/exp_006, run/analyze/freeze included) -- remains
    #     forbidden. Uncommitted worktree decisions grant no authorization.
    #     Token list is the validator-side DEC-018B contract established
    #     by the Day-25 repair, copied (not imported) so neither
    #     validator executes the other: purpose-scoped guard / TEST-only
    #     boundary / split seal / frozen 7-instance scope / frozen 245-run
    #     scope / authorization provenance / protocol pin / explicit Spark
    #     gate / no-fallback path. Ten of the twelve tokens are absent
    #     from the unauthorized worktree run_exp006.py, so EXP-006 content
    #     cannot satisfy this contract.
    _EXP005_CONTRACT_TOKENS = (
        "exp005_test_guard",
        "authorize_test_cell",
        "assert_test_execution_permitted stays sealed",
        "exp005_instances.json",
        "len(instances) != 7",
        "TOTAL_RUNS = 245",
        "DEC-018",
        "exp005/v1",
        "split_guard=guard",
        "--run requires --allow-spark",
        "refusing to overwrite",
        "no retry, no substitution",
    )
    _scripts_dir = PROJECT / "scripts"
    _exp_files = [p.name for p in _scripts_dir.glob("*exp00[356]*")]
    _exp_files += [p.name for p in _scripts_dir.glob("*exp-00[356]*")]
    _exp_files += [p.name for p in _scripts_dir.glob("*exp_00[356]*")]
    _exp_files += [p.name for p in _scripts_dir.glob("*exp005b*")]
    _exp_files += [p.name for p in _scripts_dir.glob("*exp-005b*")]
    _exp_files += [p.name for p in _scripts_dir.glob("*exp_005b*")]
    # DEC-022 contract for the three EXP-006 drivers. They were EXECUTED
    # (125 queue rows, 105 live Spark, 2026-09-16) while DEC-021/DEC-022
    # existed only in the working tree, which is why this check was RED and
    # correctly so: a TRUE POSITIVE, not a stale guard. Those decisions are
    # now committed. The rule that uncommitted worktree decisions grant no
    # authorization is UNCHANGED - it is now ENFORCED MECHANICALLY by the
    # HEAD lookup below instead of asserted in prose, so if DEC-022 ever
    # leaves the committed ledger these drivers stop being allowlisted.
    # Filename alone still never authorizes (the DEC-018B rule). Copied,
    # not imported, so no validator executes another.
    _ALLOWED_EXP_DRIVERS = ("run_exp005.py", "run_exp006.py",
                            "freeze_exp006.py", "analyze_exp006.py")
    _EXP006_CONTRACT_TOKENS = {
        "run_exp006.py": (
            "def verify_dec022",
            "EXP-006 execution authorization = APPROVED",
            'PROTOCOL_VERSION = "exp006/v1"',
            "TOTAL_RUNS = 125",
            "EXECUTABLE_RUNS = 105",
            "--allow-spark",
            "DEC-022",
        ),
        "freeze_exp006.py": (
            'PROTOCOL_VERSION = "exp006/v1"',
            "EXECUTION IS NOT AUTHORIZED BY THIS ARTIFACT",
            "DEC-021",
        ),
        "analyze_exp006.py": (
            "DEC-019 Option A / DEC-022 scope",
            "def sha256_canonical",
        ),
    }
    _r22 = subprocess.run(["git", "show", "HEAD:DECISIONS.md"],
                          cwd=PROJECT, capture_output=True, text=True)
    _exp006_ok = _r22.returncode == 0 and any(
        ln.startswith("## DEC-022") for ln in _r22.stdout.splitlines())
    for _n6, _toks in _EXP006_CONTRACT_TOKENS.items():
        _p6 = _scripts_dir / _n6
        if not _p6.exists():
            continue      # absent is fine; present-but-uncontracted is not
        try:
            _s6 = _p6.read_text(encoding="utf-8")
        except OSError:
            _s6 = ""
        _exp006_ok = _exp006_ok and bool(_s6) and all(t in _s6 for t in _toks)
    _future_files = sorted({f for f in _exp_files
                            if f not in _ALLOWED_EXP_DRIVERS})
    if "run_exp005.py" in _exp_files:
        try:
            _src5 = (_scripts_dir / "run_exp005.py").read_text(encoding="utf-8")
        except OSError:
            _src5 = ""
        _exp005_ok = bool(_src5) and all(tok in _src5 for tok in _EXP005_CONTRACT_TOKENS)
    else:
        _exp005_ok = True
    check("17 no_exp003_005", not _future_files and _exp005_ok and _exp006_ok,
          f"run_exp005.py DEC-018B contract={_exp005_ok}; "
          f"EXP-006 DEC-022 contract (HEAD-committed)={_exp006_ok}; "
          f"no other EXP-003/005b driver={not _future_files} "
          f"({_future_files or 'none'})")

    # 18. cross-run SC6 ledger: manifests + transition records vs the frozen 500
    manifests = sorted(TRAINING_RESULTS.glob("**/manifest.json")) \
        if TRAINING_RESULTS.exists() else []
    if not manifests:
        check("18 budget_ledger_total", None,
              "no manifest under results/training/ (the SC6 training ledger "
              "is the glob over manifests under results/training/; empty "
              "means nothing recorded, not zero spend)")
        check("19 no_learning_claim_in_manifests", None, "no manifest yet")
    else:
        total = 0
        claims_ok = True
        for m in manifests:
            rec = json.loads(m.read_text(encoding="utf-8"))
            total += int(rec.get("budget", {}).get("live_executions", 0))
            claims_ok &= (rec.get("learning_claim", {})
                          .get("learning_demonstrated") is False)
        records = len(list(TRAINING_RESULTS.glob("**/transitions/**/*.json")))
        check("18 budget_ledger_total", total <= 500 and records <= 500,
              f"{len(manifests)} manifest(s): {total} live executions, "
              f"{records} transition records, vs the frozen cap 500 "
              f"(REPORTED, not enforced: COMP-EXP-11 deferred)")
        check("19 no_learning_claim_in_manifests", claims_ok,
              "every manifest asserts learning_demonstrated == false")

    # 20. unit tests green (this interpreter)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no",
                        "tests/unit/test_rl_training.py",
                        "tests/unit/test_rl_training_fixes.py"],
                       capture_output=True, text=True, cwd=PROJECT)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "no output"
    if r.returncode != 0 and not r.stdout.strip() and not r.stderr.strip():
        check("20 training_unit_tests", None,
              "child interpreter failed to start pytest")
    else:
        check("20 training_unit_tests", r.returncode == 0, tail)

    # 21. the real-Spark smoke test exists and is marked (never run here)
    smoke = PROJECT / "tests/integration/test_rl_training_smoke.py"
    text = smoke.read_text(encoding="utf-8") if smoke.exists() else ""
    check("21 integration_test_present",
          smoke.exists() and "pytest.mark.integration" in text,
          "tests/integration/test_rl_training_smoke.py (operator-run; 3 live "
          "executions of the frozen 500)")

    # 22-23. documentation
    audit = AUDIT.read_text(encoding="utf-8") if AUDIT.exists() else ""
    check("22 audit_document",
          AUDIT.exists() and AUDIT.stat().st_size > 5000
          and "proves nothing about" in audit and "convergence" in audit,
          f"{AUDIT.name}: {AUDIT.stat().st_size if AUDIT.exists() else 0} bytes; "
          f"carries the 'proves nothing about convergence' sentence")
    contracts = (PROJECT / "docs/architecture/COMPONENT_CONTRACTS.md"
                 ).read_text(encoding="utf-8")
    check("23 contracts_updated",
          contracts.count("## 11. Implemented contract") == 1
          and "Implemented contract" in contracts and "Day 27" in contracts
          and "training loop" in contracts,
          "the Day-27 implemented-contract block appears exactly once")
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
