#!/usr/bin/env python
"""Where do the frozen RL policy's TEST-time choices come from? (0 Spark executions)

QUESTION. EXP-013 evaluated the frozen RL arm greedily, with no feedback history.
Does any of its TEST-time configuration choices come from an online Q-update made
during training, or are they all the offline initialization Q0 (built from the
EXP-002 TRAIN records) or the agent's tie-break default for a state with no row?

METHOD (descriptive and exploratory; not a pre-registered test, decides nothing):
  * Q0 is rebuilt with the frozen builder ``sparkrl.agent.q0.build_q0_from_exp002``.
  * Every TEST cell of ``results/evaluation/test_freeze.json`` is resolved with the
    EXP-005 driver's own frozen code (``scripts/run_exp005.py::resolve_rl_arm``),
    the path EXP-013 used (DEC-053 s1(c)): last_reward=None, epsilon 0.
  * A "Q0-only" agent - the same frozen learner holding Q0 and no update - is
    resolved on the same states.
  * For every state the evaluation reaches, each frozen policy row is compared
    with Q0 entry by entry.

Reads the frozen policies, the TEST identity, the EXP-002 run records, T_ref and
the dataset manifests (the generated-data index must be present). Writes nothing
unless --out is given.

    python scripts/analyze_q0_provenance.py
    python scripts/analyze_q0_provenance.py --out docs/decisions/evidence/q0_provenance.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.policy_store import agent_from_artifact, load_policy  # noqa: E402
from sparkrl.agent.q0 import build_q0_from_exp002  # noqa: E402
from sparkrl.agent.q_learning import state_key_of  # noqa: E402
from sparkrl.experiments.grid import build_grid  # noqa: E402
from sparkrl.rl.state import StateEncoder  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

ANALYSIS_VERSION = "q0-provenance/v1"
POLICY_DIR = PROJECT / "models" / "policies"
ARMS_PATH = POLICY_DIR / "exp005_rl_arms.json"
FREEZE_PATH = PROJECT / "results" / "evaluation" / "test_freeze.json"


def _frozen_driver():
    """Import the EXP-005 driver so its frozen resolve_rl_arm is reused, not re-implemented."""
    spec = importlib.util.spec_from_file_location("run_exp005", PROJECT / "scripts" / "run_exp005.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _greedy(row: list[float]) -> int:
    """The agent's frozen exploitation rule: highest value, ties to the lowest index."""
    return max(range(len(row)), key=lambda a: (row[a], -a))


def grid_comparison(arms: list[dict], q0_greedy: dict[str, int]) -> list[dict]:
    """DESCRIPTIVE ONLY: EXP-002 grid medians for the Q0 choice and for each policy's
    learned positive-feedback (gt0) choice, on the training cells the grid measured.

    Each median is over the completed, usable EXP-002 runs of one configuration on
    one cell (two repetitions by design, fewer where a run failed), so a difference
    here is a pointer, not a test.
    """
    names = {p.grid_index: p.name for p in build_grid(include_b0=True) if p.grid_index is not None}
    runs = PROJECT / "results" / "experiments" / "exp-002" / "runs"
    times: dict[tuple[str, str], dict[str, list[float]]] = {}
    for path in sorted(runs.glob("*/*/seed0/G-*/rep*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        metrics = rec.get("metrics") or {}
        if rec.get("status") != "COMPLETED" or not metrics.get("usable"):
            continue
        family, scale, cfg = path.parts[-5], path.parts[-4], path.parts[-2]
        times.setdefault((family, scale), {}).setdefault(cfg, []).append(float(metrics["execution_time_s"]))
    tables = {arm["arm"]: load_policy(arm["policy_id"], POLICY_DIR)["q_table"] for arm in arms}
    rows = []
    for (family, scale), per_cfg in sorted(times.items()):
        medians = {cfg: statistics.median(v) for cfg, v in per_cfg.items()}
        cls = StateEncoder().encode(family, 1, last_reward=None).key()[1]
        q0_cfg = names[q0_greedy[f"state-v1.5|{cls}|S|le0"]]
        learned = {arm: names[_greedy([float(x) for x in table[f"state-v1.5|{cls}|S|gt0"]])]
                   for arm, table in tables.items()}
        best = min(medians, key=medians.get)
        rows.append({"cell": f"{family}|{scale}|s0", "q0_choice": q0_cfg,
                     "q0_choice_median_s": medians.get(q0_cfg),
                     "learned_gt0_choice": learned,
                     "learned_gt0_median_s": {a: medians.get(c) for a, c in learned.items()},
                     "grid_best": best, "grid_best_median_s": medians[best],
                     "runs_per_configuration": sorted({len(v) for v in per_cfg.values()})})
    return rows


def analyze() -> dict:
    driver = _frozen_driver()
    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    arms = json.loads(ARMS_PATH.read_text(encoding="utf-8"))["arms"]
    cells = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))["cells"]

    q0 = build_q0_from_exp002()
    template = load_policy(arms[0]["policy_id"], POLICY_DIR)
    q0_agent = agent_from_artifact({**template, "q_table": q0.q_table})
    default = q0_agent.config.q0_default
    encoder = StateEncoder()

    per_cell, states = [], {}
    for c in cells:
        fam, scale, seed = c["family"], c["scale"], int(c["seed"])
        res = resolve_dataset(fam, scale, seed)
        input_bytes = int(res.orders_manifest["total_bytes"]) + int(res.lineitem_manifest["total_bytes"])
        state = encoder.encode(fam, input_bytes, last_reward=None)
        key = state_key_of(state)
        q0_action = q0_agent.select_action(state, epsilon=0.0)
        row = {"cell": f"{fam}|{scale}|s{seed}", "state": key, "q0_only_action": q0_action, "rl": {}}
        for arm in arms:
            point, action, state_key, _, _ = driver.resolve_rl_arm(arm, fam, scale, seed, base)
            assert "|".join(map(str, state_key)) == key, (state_key, key)
            row["rl"][arm["arm"]] = {"action": action, "config": point.name}
        row["identical_to_q0_only"] = all(v["action"] == q0_action for v in row["rl"].values())
        per_cell.append(row)
        states.setdefault(key, set()).add(row["cell"])

    q0_rows = {k: [default if v is None else float(v) for v in vals] for k, vals in q0.q_table.items()}
    per_state = []
    for key in sorted(states):
        q0_row = q0_rows.get(key)
        entry = {"state": key, "test_cells": len(states[key]),
                 "q0_row_present": q0_row is not None,
                 "q0_greedy": _greedy(q0_row) if q0_row else _greedy([default] * 12),
                 "policies": {}}
        for arm in arms:
            table = load_policy(arm["policy_id"], POLICY_DIR)["q_table"]
            prow = table.get(key)
            if prow is None:
                entry["policies"][arm["arm"]] = {"row_present": False, "greedy": _greedy([default] * 12),
                                                 "entries_changed_from_q0": 0}
                continue
            prow = [float(v) for v in prow]
            ref = q0_row or [default] * 12
            changed = [a for a in range(12) if abs(prow[a] - ref[a]) > 1e-12]
            entry["policies"][arm["arm"]] = {
                "row_present": True, "greedy": _greedy(prow), "entries_changed_from_q0": len(changed),
                "changed_actions": changed, "greedy_entry_changed": _greedy(prow) in changed}
        if not entry["q0_row_present"] and not any(p["row_present"] for p in entry["policies"].values()):
            entry["source"] = "tie-break default (no row in Q0 or in any policy)"
        elif all(p["greedy"] == entry["q0_greedy"] and not p.get("greedy_entry_changed")
                 for p in entry["policies"].values()):
            entry["source"] = "offline Q0 (greedy entry never updated online)"
        else:
            entry["source"] = "online update changed the greedy choice"
        per_state.append(entry)

    trained_rows = {}
    for arm in arms:
        table = load_policy(arm["policy_id"], POLICY_DIR)["q_table"]
        for key, vals in table.items():
            ref = q0_rows.get(key, [default] * 12)
            n = sum(1 for a in range(12) if abs(float(vals[a]) - ref[a]) > 1e-12)
            trained_rows.setdefault(key, {})[arm["arm"]] = n

    identical = sum(1 for r in per_cell if r["identical_to_q0_only"])
    provenance = dict(q0.provenance)
    root = Path(provenance.get("result_root", ""))
    if root.is_absolute():  # keep machine paths out of a published record
        provenance["result_root"] = root.relative_to(PROJECT).as_posix()
    return {
        "analysis": ANALYSIS_VERSION,
        "spark_executions": 0,
        "kind": "descriptive, exploratory (not pre-registered; decides no hypothesis)",
        "inputs": {"policies": [a["policy_id"] for a in arms], "test_freeze": "results/evaluation/test_freeze.json",
                   "q0_provenance": provenance},
        "n_test_cells": len(per_cell),
        "n_cells_rl_identical_to_q0_only_all_seeds": identical,
        "distinct_test_states": len(per_state),
        "per_state": per_state,
        "per_cell": per_cell,
        "entries_changed_by_training_per_row": trained_rows,
        "gt0_choices_vs_exp002_grid": grid_comparison(
            arms, {key: _greedy(row) for key, row in q0_rows.items()}),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None, help="write the JSON result here")
    a = ap.parse_args(argv)
    result = analyze()
    for s in result["per_state"]:
        acts = {k: v["greedy"] for k, v in s["policies"].items()}
        print(f"{s['state']:28} cells={s['test_cells']:2}  Q0-only={s['q0_greedy']:2}  RL={acts}  -> {s['source']}")
    print(f"TEST cells where RL-s0/s1/s2 all choose the Q0-only action: "
          f"{result['n_cells_rl_identical_to_q0_only_all_seeds']} of {result['n_test_cells']}")
    print("Descriptive, EXP-002 grid medians on training cells (about 2 runs per configuration):")
    for r in result["gt0_choices_vs_exp002_grid"]:
        learned = "  ".join(f"{a}:{c}" for a, c in r["learned_gt0_choice"].items())
        print(f"  {r['cell']:20} Q0 {r['q0_choice']}={r['q0_choice_median_s']}  learned gt0 {learned}  "
              f"grid-best {r['grid_best']}={r['grid_best_median_s']:.2f}")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
