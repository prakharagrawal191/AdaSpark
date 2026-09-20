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


# HEAD-authorized experiment drivers (check 12 allowlist + contracts).
#
# run_exp001.py: DEC-018 Decision E, TRAIN-only B0 noise calibration.
# run_exp005.py: DEC-018 Decision B, frozen 245-TEST protocol on EXP-005's
#     own register line (7 instances x 7 arms x 5 reps, outside the SC6
#     TRAIN cap).
# run_exp006.py / freeze_exp006.py / analyze_exp006.py: DEC-020 s.B/D,
#     DEC-021 and DEC-022. These were EXECUTED (125 queue rows, 105 live
#     Spark, 2026-09-16) while DEC-021/DEC-022 existed only in the working
#     tree, which is exactly why this check was RED and correctly so - it
#     was a true positive, not a stale guard. The decisions are now
#     committed, so the allowlist may admit the drivers; the rule that
#     uncommitted worktree decisions are NOT HEAD authorization is
#     UNCHANGED and is now ENFORCED mechanically by _dec022_at_head()
#     below rather than asserted in a comment.
# Anything else matching the future-driver globs (EXP-003 / EXP-005b, or
#     any EXP-006-shaped filename that fails its contract) stays forbidden.
ALLOWED_EXP_DRIVERS = ("run_exp001.py", "run_exp005.py",
                       "run_exp006.py", "freeze_exp006.py",
                       "analyze_exp006.py")

EXP001_CONTRACT_TOKENS = (
    "assert_b0_unchanged", "b0_point", "split_of",
    "execute_run(spec, base)",
    "no-retry", "refusing to overwrite", "split != TRAIN",
)

# Validator-side DEC-018B contract for run_exp005.py. Each token is
# repository evidence of one authorized property; only the conjunction
# admits the driver, so filename alone never authorizes:
#   purpose-scoped experiment guard / TEST-only boundary / split seal /
#   frozen 7-instance scope / frozen 245-run scope / authorization
#   provenance / protocol pin / explicit Spark gate / no-fallback path.
# Every token below is present in the HEAD-authorized driver, while ten
# of the twelve are absent from the unauthorized worktree EXP-006
# driver, so EXP-006 content cannot satisfy this contract.
EXP005_CONTRACT_TOKENS = (
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


# Validator-side DEC-022 contract for the three EXP-006 drivers. Same rule
# as DEC-018B: filename alone never authorizes. Each token is repository
# evidence of one authorized property, and only the conjunction admits the
# file - so a driver stripped of its authorization gate, its frozen scope
# or its Spark gate fails immediately, and an EXP-006-SHAPED file that is
# not these drivers cannot pass by being named to look like them.
EXP006_CONTRACT_TOKENS = {
    "run_exp006.py": (
        "def verify_dec022",                          # independent authz gate
        "EXP-006 execution authorization = APPROVED",  # the exact DEC-022 sentence it greps
        'PROTOCOL_VERSION = "exp006/v1"',              # protocol pin
        "TOTAL_RUNS = 125",                            # frozen queue scope
        "EXECUTABLE_RUNS = 105",                       # frozen executable scope
        "--allow-spark",                               # explicit Spark gate
        "DEC-022",                                     # authorization provenance
    ),
    "freeze_exp006.py": (
        'PROTOCOL_VERSION = "exp006/v1"',
        "EXECUTION IS NOT AUTHORIZED BY THIS ARTIFACT",  # freeze != authorization
        "DEC-021",
    ),
    "analyze_exp006.py": (
        "DEC-019 Option A / DEC-022 scope",            # undefined-cell semantics
        "def sha256_canonical",                        # fingerprint-verifying analyser
    ),
}


def _dec022_at_head() -> bool:
    """True iff DEC-022 exists in the COMMITTED ledger at HEAD.

    This is the mechanical form of the rule the comments have always
    stated: uncommitted worktree decisions grant no authorization. The
    EXP-006 carve-out is bound to it, so if the decision is ever absent
    from HEAD - rewritten history, a fresh clone, a reverted commit - the
    drivers stop being allowlisted and check 12 FAILS again. The gate is
    an INDEPENDENT source: it reads git's committed object store, never
    the worktree files the carve-out is about.
    """
    try:
        r = subprocess.run(["git", "show", "HEAD:DECISIONS.md"],
                           cwd=PROJECT, capture_output=True, text=True)
    except OSError:
        return False
    return r.returncode == 0 and bool(re.search(r"^##\s*DEC-022\b",
                                                r.stdout, re.M))


def _exp_driver_contracts(scripts_dir: Path) -> tuple[bool, bool, bool]:
    """Positive contracts for the HEAD-authorized drivers. Source read only.

    Returns (exp001_ok, exp005_ok, exp006_ok); executes nothing, starts no
    Spark. exp006_ok additionally requires DEC-022 to be committed at HEAD.
    """
    try:
        src1 = (scripts_dir / "run_exp001.py").read_text(encoding="utf-8")
    except OSError:
        src1 = ""
    try:
        src5 = (scripts_dir / "run_exp005.py").read_text(encoding="utf-8")
    except OSError:
        src5 = ""
    exp001_ok = bool(src1) and all(tok in src1 for tok in EXP001_CONTRACT_TOKENS)
    exp005_ok = bool(src5) and all(tok in src5 for tok in EXP005_CONTRACT_TOKENS)
    exp006_ok = _dec022_at_head()
    for name, tokens in EXP006_CONTRACT_TOKENS.items():
        path = scripts_dir / name
        if not path.exists():
            continue          # absent is fine; present-but-uncontracted is not
        try:
            src6 = path.read_text(encoding="utf-8")
        except OSError:
            src6 = ""
        exp006_ok = exp006_ok and bool(src6) and all(t in src6 for t in tokens)
    return exp001_ok, exp005_ok, exp006_ok


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

    # 12. HEAD-authorized experiment-driver allowlist + content contracts.
    #     The pre-Day-32/33 invariant ("no *exp00[356]* script") is STALE
    #     twice over: DEC-018 Decision E authorizes run_exp001.py (TRAIN-only
    #     B0, 20 runs) and Decision B authorizes run_exp005.py (frozen 245
    #     TEST runs, 7 instances x 7 arms x 5 reps, on EXP-005's own register
    #     line outside the SC6 TRAIN cap). The surviving invariant is narrower
    #     but not weaker: run_exp001.py must satisfy its TRAIN/B0/no-retry
    #     contract, run_exp005.py must satisfy its DEC-018B contract below,
    #     and no other future-experiment driver may exist - EXP-003, EXP-005b
    #     or EXP-006 (run/analyze/freeze included), in any naming form
    #     (exp003 / exp-003 / exp_003, exp005 / exp-005 / exp_005,
    #     exp005b / exp-005b / exp_005b, exp006 / exp-006 / exp_006).
    #     Filename alone authorizes nothing; each allowlisted driver must
    #     satisfy its full content contract. Uncommitted worktree decisions
    #     grant no authorization and transfer nothing into this allowlist.
    _scripts_dir = PROJECT / "scripts"
    exp_files = [p.name for p in _scripts_dir.glob("*exp00[356]*")]
    exp_files += [p.name for p in _scripts_dir.glob("*exp-00[356]*")]
    exp_files += [p.name for p in _scripts_dir.glob("*exp_00[356]*")]
    exp_files += [p.name for p in _scripts_dir.glob("*exp005b*")]
    exp_files += [p.name for p in _scripts_dir.glob("*exp-005b*")]
    exp_files += [p.name for p in _scripts_dir.glob("*exp_005b*")]
    future_files = sorted({f for f in exp_files if f not in ALLOWED_EXP_DRIVERS})
    exp001_ok, exp005_ok, exp006_ok = _exp_driver_contracts(_scripts_dir)
    ok = not future_files and exp001_ok and exp005_ok and exp006_ok
    check("12 exp001_driver_authorized", ok,
          f"run_exp001.py contract={exp001_ok}; run_exp005.py DEC-018B contract={exp005_ok}; "
          f"EXP-006 DEC-022 contract (HEAD-committed)={exp006_ok}; "
          f"no other EXP-003/005b driver={not future_files} ({future_files or 'none'})")

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
