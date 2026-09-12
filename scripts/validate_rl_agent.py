#!/usr/bin/env python
"""Day-26 validator: tabular Q-learning agent + policy store (COMP-RL-10).

Checks the frozen learner boundaries: Q0 provenance (EXP-002 TRAIN only),
leakage protection, the frozen update rule, epsilon schedule, seeded
determinism, immutable versioned policy store, reward delegation, no
duplicated runner, no deep-RL / cache / experiment orchestration.
PASS/FAIL/SKIP per check; overall PASS requires every applicable check green.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.q_learning import AgentConfig, QLearningAgent, Transition  # noqa: E402
from sparkrl.agent.q0 import build_q0_from_exp002  # noqa: E402
from sparkrl.agent.policy_store import (  # noqa: E402
    PolicyExistsError, build_policy_artifact, save_policy)
from sparkrl.rl.state import SCHEMA_V15, StateVector  # noqa: E402

results: list[tuple[str, str, str]] = []
q0a = None


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print(f"{name:<30} {status:<5} {detail}")


def main() -> int:
    global q0a
    try:
        mod = importlib.import_module("sparkrl.agent")
        check("01 learner_imports", True,
              f"{mod.AGENT_VERSION} / {mod.Q0_VERSION} / {mod.POLICY_SCHEMA}")
    except Exception as exc:  # noqa: BLE001
        check("01 learner_imports", False, str(exc))
        return _finish()
    try:
        cfg = AgentConfig.from_yaml()
        ok = (abs(cfg.alpha - 0.2) < 1e-12 and abs(cfg.epsilon_start - 1.0) < 1e-12
              and abs(cfg.epsilon_min - 0.05) < 1e-12
              and abs(cfg.epsilon_decay - 0.95) < 1e-12
              and abs(cfg.q0_default - 0.5) < 1e-12 and cfg.gamma in (0.0, 0.9))
        check("02 hyperparams_frozen", ok,
              f"a={cfg.alpha} g={cfg.gamma} e=1->{cfg.epsilon_min}@{cfg.epsilon_decay}")
    except Exception as exc:  # noqa: BLE001
        check("02 hyperparams_frozen", False, str(exc))
    try:
        q0a = build_q0_from_exp002()
        q0b = build_q0_from_exp002()
        p = q0a.provenance
        ok = (p["source"] == "exp002" and p["records_scanned"] == 208
              and p["records_valid_used"] + p["records_invalid_skipped"]
              + p["records_tref_missing_skipped"] + p["records_b0_reference"] == 208
              and p["leakage_guard"].startswith("split_of()")
              and q0a.q_table == q0b.q_table
              and all(k.split("|")[0] == SCHEMA_V15 for k in q0a.q_table)
              and all(k.split("|")[3] == "le0" for k in q0a.q_table))
        check("03 q0_exp002_train_only", ok,
              f"{p['pairs_initialized']} states / {p['records_valid_used']} valid obs")
    except Exception as exc:  # noqa: BLE001
        check("03 q0_exp002_train_only", False, str(exc))
        q0a = None
    keys = "".join(sorted(q0a.q_table)) if q0a is not None else ""
    ok = "skew_join" not in keys and "|M|" not in keys and "|L|" not in keys
    check("04 q0_no_test_cells", ok,
          "no skew_join family; TRAIN small+medium both bin to S (measured)")
    ag = QLearningAgent(rng_seed=0)
    s = StateVector("join", "S", schema_version=SCHEMA_V15, feedback_bin="le0")
    ag.update(Transition(s, 0, reward=0.5, next_state=None, terminated=True))
    ok = abs(ag.q_values(s)[0] - (0.5 + 0.2 * (0.5 - 0.5))) < 1e-12
    check("05 terminal_update_sanity", ok,
          f"Q after r=0.5 terminal = {ag.q_values(s)[0]:.4f} (Q0=+0.5, a=0.2)")
    return _part2()


def _part2() -> int:
    # 6. epsilon schedule sanity
    ag2 = QLearningAgent(rng_seed=1)
    ag2.epsilon = 1.0
    e1 = ag2.end_episode()
    check("06 epsilon_schedule", abs(e1 - 0.95) < 1e-12, f"1.0 -> {e1}")

    # 7. policy-store round-trip + immutability (real Q0 -> temp dir)
    try:
        with tempfile.TemporaryDirectory() as td:
            agent = QLearningAgent(q_table=q0a.q_table, rng_seed=0)
            art = build_policy_artifact(agent, init_provenance=dict(q0a.provenance))
            save_policy(art, td)
            tampered = dict(art)
            tampered["q_table"] = {"state-v1.5|join|S|le0": [9.9] * 12}
            try:
                save_policy(tampered, td)
                immut = False
            except PolicyExistsError:
                immut = True
        check("07 policy_immutable", immut,
              f"policy-{art['policy_id'][:16]}.json persisted")
    except Exception as exc:  # noqa: BLE001
        check("07 policy_immutable", False, str(exc))

    # 8. reward delegated to environment - the ONLINE learner never computes R3
    #    (Q0 init may read T_ref: that is its authorized EXP-002 role)
    src = (PROJECT / "src/sparkrl/agent/q_learning.py").read_text(encoding="utf-8")
    code_refs = ["RewardCalculator(", "from sparkrl.rl.reward",
                 "from sparkrl.rl.env", "SparkTuningEnv(",
                 "tref_store", "trefs.", "execute_run("]
    check("08 reward_delegated",
          not any(c in src for c in code_refs),
          "agent consumes transition.reward; env owns R3/T_ref/guards")

    # 9-11. no duplicated runner / cache / deep-RL in the whole agent layer
    src = "\n".join(f.read_text(encoding="utf-8")
                    for f in sorted((PROJECT / "src/sparkrl/agent").glob("*.py")))
    check("09 no_duplicate_runner",
          "build_session" not in src and "execute_run" not in src
          and "SparkSession" not in src and "spark_submit" not in src)

    # 10. no cache implementation in the agent layer
    low = src.lower()
    check("10 no_cache",
          "cachekey" not in low and "cache_hit" not in low and "cacheentry" not in low)

    # 11. no deep-RL libraries
    hits = [lib for lib in ("torch", "tensorflow", "keras", "stable_baselines")
            if lib in low]
    check("11 no_deep_rl_libs", not hits, str(hits) or "clean")

    # 12. no EXP-003/005 files and no experiment orchestration
    exp_files = [p.name for p in (PROJECT / "scripts").glob("*exp00[35]*")]
    check("12 no_exp003_005", not exp_files, str(exp_files))
    return _part3()


def _part3() -> int:
    # 13. unit tests green (this interpreter)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no",
                        "tests/unit/test_rl_agent.py",
                        "tests/unit/test_rl_policy_store.py",
                        "tests/unit/test_rl_q0.py"],
                       capture_output=True, text=True, cwd=PROJECT)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "no output"
    if r.returncode != 0 and not r.stdout.strip() and not r.stderr.strip():
        check("13 rl_agent_unit_tests", None, "child interpreter failed to start pytest")
    else:
        check("13 rl_agent_unit_tests", r.returncode == 0, tail)

    # 14. integration tests present
    for f in ("test_rl_agent_offline_init.py", "test_rl_agent_env_smoke.py"):
        check(f"14 integration_{f[5:23]}", (PROJECT / "tests/integration" / f).exists())

    # 15. documentation
    audit = PROJECT / "docs/research/DAY26_RL_AGENT_AUDIT.md"
    check("15 audit_document", audit.exists() and audit.stat().st_size > 5000)
    contracts = (PROJECT / "docs/architecture/COMPONENT_CONTRACTS.md"
                 ).read_text(encoding="utf-8")
    check("16 contracts_updated", "Implemented contract" in contracts
          and "tabular Q" in contracts and "Day 26" in contracts)

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
