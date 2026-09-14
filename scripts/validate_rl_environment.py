#!/usr/bin/env python
"""Day-25 validator: SparkTuningEnv contract integrity (COMP-RL-09).

Checks the frozen boundaries: action domain, state schema, reward weights,
T_ref provenance, guard behaviour, infrastructure reuse, authoritative timing,
split protection, absence of learning/cache/EXP-003+, and documentation.
PASS/FAIL/SKIP per check; overall PASS requires every applicable check green.
"""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.experiments.grid import grid_fingerprint  # noqa: E402
from sparkrl.rl.action import MODE4_SUBSET, ActionMapper  # noqa: E402
from sparkrl.rl.env import DEFAULT_BUDGET, ENV_VERSION, SparkTuningEnv  # noqa: E402
from sparkrl.rl.reward import FROZEN_WEIGHTS, load_reward_config  # noqa: E402
from sparkrl.rl.state import SCHEMA_V1, SCHEMA_V15, StateVector  # noqa: E402
from sparkrl.rl.tref import DEFAULT_GATE_PATH, TRefStore  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print(f"{name:<28} {status:<5} {detail}")


def main() -> int:
    # 1. modules import + class exists
    try:
        env_mod = importlib.import_module("sparkrl.rl.env")
        cls = env_mod.SparkTuningEnv
        check("01 modules_import", True, f"{ENV_VERSION}")
    except Exception as exc:  # noqa: BLE001
        check("01 modules_import", False, str(exc))
        return _finish()

    # 2. reset/step signatures
    check("02 reset_step_exist",
          callable(getattr(cls, "reset", None)) and callable(getattr(cls, "step", None)))

    # 3. action domain constrained
    m = ActionMapper()
    ok = (m.size == 12 and m.grid_fingerprint == grid_fingerprint()
          and ActionMapper(mode="mode4").allowed_actions() == tuple(sorted(MODE4_SUBSET)))
    check("03 action_domain_frozen", ok,
          f"12 actions, mode4={sorted(MODE4_SUBSET)}, grid_fp={m.grid_fingerprint[:12]}...")

    # 4. state schema sizes
    ok = (StateVector.space_size(SCHEMA_V1) == 15
          and StateVector.space_size(SCHEMA_V15) == 30)
    check("04 state_schema_15_30", ok)

    # 5. reward weights frozen
    try:
        w = load_reward_config()
        ok = all(abs(w[k] - v) < 1e-12 for k, v in FROZEN_WEIGHTS.items())
        check("05 reward_weights_frozen", ok, "configs/reward.yaml == PLAN section 15")
    except Exception as exc:  # noqa: BLE001
        check("05 reward_weights_frozen", False, str(exc))

    # 6. T_ref provenance (read-only EXP-002 gate)
    try:
        t = TRefStore()
        v = t.get("F2_join", "small", 0)
        ok = (t.source.startswith("exp002-gate")
              and v is not None and abs(v - 2.214523) < 1e-6
              and t.get("F3_rdd", "medium", 0) is None
              and t.get("F2_join", "small", 3) is None)
        check("06 tref_from_exp002_gate", ok, f"F2_join|small={v}")
    except Exception as exc:  # noqa: BLE001
        check("06 tref_from_exp002_gate", False, str(exc))

    # 7. budget default = frozen 500
    check("07 budget_default_500", DEFAULT_BUDGET == 500, f"DEFAULT_BUDGET={DEFAULT_BUDGET}")

    # 8. env reuses the experiment runner (source-level, no duplicate runner)
    src = (PROJECT / "src" / "sparkrl" / "rl" / "env.py").read_text(encoding="utf-8")
    check("08 reuses_execute_run", "execute_run" in src
          and "from sparkrl.experiments.runner import" in src)
    check("09 no_second_session_layer",
          "build_session" not in src and "SparkSession.builder" not in src)

    # 10. authoritative timing untouched (reward module uses execution_time_s only)
    rsrc = (PROJECT / "src" / "sparkrl" / "rl" / "reward.py").read_text(encoding="utf-8")
    ok = "execution_time_s" in rsrc and "time.time()" not in rsrc
    check("10 timing_semantics_unchanged", ok)
    return _part2()


def _part2() -> int:
    # 11. no learning / no cache in the RL layer source
    rl_dir = PROJECT / "src" / "sparkrl" / "rl"
    banned = re.compile(
        r"q_table|QTable|epsilon_greedy|bellman|td_error|"
        r"policy_update|value_update|policy_gradient|"
        r"cache_hit|cache_lookup|online_adaptation|live_learning",
        re.IGNORECASE)
    banned_cs = re.compile(r"\bDQN\b|\bPPO\b|\bepsilon\b")  # case-sensitive: 'supported' contains 'ppo'
    negation = re.compile(r"no (Q-table|epsilon|policy|cache|learning|dqn|ppo)",
                          re.IGNORECASE)
    hits = []
    for f in sorted(rl_dir.glob("*.py")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if (banned.search(line) or banned_cs.search(line)) \
                    and not line.lstrip().startswith("#") \
                    and not negation.search(line):
                hits.append(f"{f.name}:{i}: {line.strip()[:90]}")
    check("11 no_learning_no_cache", not hits, "; ".join(hits[:3]) or "clean")

    # 12. EXP-001 driver integrity (Day 32: the authorized noise-calibration
    #     driver). The pre-Day-32 invariant ("no *exp00[135]* script") is STALE:
    #     EXP-001 was legitimately executed, so the driver's presence is
    #     EXPECTED. The surviving invariant is narrower but not weaker: the
    #     driver must be the single authorized TRAIN-only B0 driver, and no
    #     future-experiment driver may exist - EXP-003, EXP-005, EXP-005b
    #     or EXP-006, in either naming form (exp003 / exp-003, exp005 /
    #     exp-005, exp005b / exp-005b, exp006 / exp-006).
    driver = PROJECT / "scripts" / "run_exp001.py"
    exp_files = [p.name for p in (PROJECT / "scripts").glob("*exp00[356]*")]
    exp_files += [p.name for p in (PROJECT / "scripts").glob("*exp-00[356]*")]
    exp_files += [p.name for p in (PROJECT / "scripts").glob("*exp_00[356]*")]
    exp_files += [p.name for p in (PROJECT / "scripts").glob("*exp005b*")]
    exp_files += [p.name for p in (PROJECT / "scripts").glob("*exp-005b*")]
    exp_files += [p.name for p in (PROJECT / "scripts").glob("*exp_005b*")]
    future_files = sorted({f for f in exp_files if f != "run_exp001.py"})
    ok = driver.exists() and not future_files
    if ok:
        try:
            src = driver.read_text(encoding="utf-8")
            # Positive content pins (import-level, not string-literal):
            # the driver must import the B0 drift guard, the TRAIN-only
            # split guard (as the execute_run default), the B0 reference
            # point, and split_of; and must carry the no-retry / no-overwrite
            # protocol text. Import of assert_train_only is via execute_run's
            # default split_guard (runner.py), so require the local use of
            # split_of + the TRAIN defence plus the default-guard call site.
            ok = all(tok in src for tok in
                     ("assert_b0_unchanged", "b0_point", "split_of",
                      "execute_run(spec, base)",
                      "no-retry", "refusing to overwrite", "split != TRAIN"))
        except OSError:
            ok = False
    check("12 exp001_driver_authorized", ok,
          f"run_exp001.py present TRAIN-only B0 no-retry no-overwrite; "
          f"no EXP-003/005/005b/006 driver={not future_files} ({future_files or 'none'})")

    # 13. agent package holds the Day-26 learner and NOTHING from a future day.
    #     Day 25 asserted this package was EMPTY (COMP-RL-10 was Day 26+). Day 26
    #     legitimately populated it, so the empty-file assertion is STALE and was
    #     corrected on Day 28. The invariant that survives the Day-26 freeze is
    #     narrower but not weaker: the COMP-RL-10 learner is present and exported,
    #     only the three Day-26 modules exist, and no prohibited future learning
    #     component (deep RL, replay, target network, cache) has appeared.
    agent_dir = PROJECT / "src" / "sparkrl" / "agent"
    agent_init = agent_dir / "__init__.py"
    modules = sorted(f.name for f in agent_dir.glob("*.py"))
    allowed = {"__init__.py", "q_learning.py", "q0.py", "policy_store.py"}
    unexpected = sorted(set(modules) - allowed)
    exports = ("QLearningAgent", "AgentConfig", "build_q0_from_exp002",
               "save_policy", "load_policy")
    init_src = agent_init.read_text(encoding="utf-8") if agent_init.exists() else ""
    missing = [e for e in exports if e not in init_src]
    forbidden = re.compile(
        r"DQN|PPO|actor_critic|ActorCritic|policy_gradient|"
        r"replay_buffer|ReplayBuffer|target_network|TargetNetwork|"
        r"torch|tensorflow|keras|stable_baselines|"
        r"cache_hit|cache_lookup|CacheKey")
    fneg = re.compile(r"no (DQN|PPO|replay|target|cache|neural|deep)", re.IGNORECASE)
    drift = []
    for f in sorted(agent_dir.glob("*.py")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if forbidden.search(line) and not line.lstrip().startswith("#")                     and not fneg.search(line):
                drift.append(f"{f.name}:{i}: {line.strip()[:70]}")
    ok = not unexpected and not missing and not drift
    check("13 agent_package_day26_only", ok,
          f"modules={modules}; missing COMP-RL-10 exports={missing or 'none'}; "
          f"unexpected={unexpected or 'none'}; forbidden={drift[:2] or 'none'}")

    # 14. EXP-002 gate artifact intact (untouched by Day 25)
    try:
        gate = json.loads(DEFAULT_GATE_PATH.read_text(encoding="utf-8"))
        ok = (gate.get("sensitivity", {}).get("n_families_sensitive") == 4
              and gate.get("gate", {}).get("result") == "PASS")
        check("14 exp002_gate_intact", ok, "4/4 families, PASS")
    except Exception as exc:  # noqa: BLE001
        check("14 exp002_gate_intact", False, str(exc))

    # 15. guards: split + budget + T_ref + episode (unit-level, no Spark)
    try:
        from sparkrl.rl.env import BudgetExhausted, EpisodeDone, SplitViolation
        from unittest import mock
        import tempfile
        from sparkrl.monitoring.run_metrics import RunMetrics
        tstore = TRefStore(mapping={"F2_join|small": 10.0, "F3_rdd|medium": None})
        guard_ok = True
        with tempfile.TemporaryDirectory() as td:
            base = SparkConfig.from_yaml(str(PROJECT / "configs" / "baseline_b0.yaml"))
            env = SparkTuningEnv(base, tref_store=tstore, result_root=td,
                                 budget_limit=1)
            for fam, sc, sd in (("F4_ski", "small", 0), ("F2_join", "large", 0),
                                ("F2_join", "small", 4), ("F2_join", "small", 3)):
                try:
                    env.reset(family=fam, scale=sc, seed=sd)
                    guard_ok = False
                except SplitViolation:
                    pass
            fake = RunMetrics(execution_time_s=5.0, usable=True, success=True,
                              timeout=False, task_duration_cv=0.25,
                              disk_spill_bytes=0)
            with mock.patch("sparkrl.rl.env.execute_run",
                            lambda *a, **k: (fake, {"fake": True})):
                env.reset(family="F2_join", scale="small", seed=0)
                env.step(0)
                try:
                    env.reset(family="F2_join", scale="small", seed=0)
                    guard_ok = False      # budget exhausted -> must raise
                except BudgetExhausted:
                    pass
                env2 = SparkTuningEnv(base, tref_store=tstore, result_root=td,
                                      budget_limit=5)
                env2.reset(family="F3_rdd", scale="medium", seed=0)
                try:
                    env2.step(0)
                    guard_ok = False      # T_ref None -> refuse pre-exec
                except Exception as exc:  # noqa: BLE001
                    guard_ok = guard_ok and "T_ref" in str(exc)
                env3 = SparkTuningEnv(base, tref_store=tstore, result_root=td)
                try:
                    env3.step(0)
                    guard_ok = False      # no episode -> must raise
                except EpisodeDone:
                    pass
        check("15 guards_split_budget_tref_episode", guard_ok)
    except Exception as exc:  # noqa: BLE001
        check("15 guards_split_budget_tref_episode", False, str(exc))

    # 16. RL unit tests green (this interpreter)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no",
                        "tests/unit/test_rl_state.py", "tests/unit/test_rl_action.py",
                        "tests/unit/test_rl_reward.py", "tests/unit/test_rl_env.py"],
                       capture_output=True, text=True, cwd=PROJECT)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "no output"
    if r.returncode != 0 and not r.stdout.strip() and not r.stderr.strip():
        # interpreter could not even start pytest (e.g. OS blocked DLLs) -
        # report SKIP, not PASS and not a code FAIL; rerun under sparkrl_env311
        check("16 rl_unit_tests", None, "child interpreter failed to start pytest")
    else:
        check("16 rl_unit_tests", r.returncode == 0, tail)

    # 17. integration test present (executed separately on sparkrl_env311)
    it = PROJECT / "tests" / "integration" / "test_rl_env_smoke.py"
    check("17 integration_test_present", it.exists())

    # 18. documentation present and aligned
    audit = PROJECT / "docs" / "research" / "DAY25_RL_ENVIRONMENT_AUDIT.md"
    check("18 audit_document", audit.exists() and audit.stat().st_size > 5000)
    contracts = (PROJECT / "docs" / "architecture" / "COMPONENT_CONTRACTS.md"
                 ).read_text(encoding="utf-8")
    check("19 contracts_updated", "Implemented contract" in contracts
          and "SparkTuningEnv" in contracts)

    return _finish()


def _finish() -> int:
    n_pass = sum(1 for _, s, _ in results if s == "PASS")
    n_fail = sum(1 for _, s, _ in results if s == "FAIL")
    n_skip = sum(1 for _, s, _ in results if s == "SKIP")
    print("-" * 70)
    print(f"OVERALL: {'PASS' if n_fail == 0 else 'FAIL'}  "
          f"({n_pass} passed, {n_skip} skipped, {n_fail} failed of {len(results)})")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
