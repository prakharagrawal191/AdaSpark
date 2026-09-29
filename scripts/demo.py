#!/usr/bin/env python
"""AdaSpark live + backup demo (EXP-012, PLAN section 36).

Live (``--mode live --allow-spark``, <10 min, deterministic): fixed-seed F5-mixed S-scale
workload (F5_mixed/small/seed 0, TRAIN, T_ref calibrated) -> B0 run -> B3 run (G-p8-sp16) ->
frozen RL-s0 policy for 3 episodes with printed state/action/reward trace -> comparison
table. All printed numbers originate from logged manifests written to
results/experiments/x-demo/observations.jsonl (own register line, disclosed TRAIN-split
spend; needs DEC-051 before --allow-spark).

Backup (``--mode backup``): replays stored manifests, regenerates the identical table
without Spark. ``--mode plan`` runs 0 Spark and 0 writes.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.policy_store import (agent_from_artifact, load_policy)  # noqa: E402
from sparkrl.evaluation.strategies import resolve as resolve_strategy  # noqa: E402
from sparkrl.experiments.grid import b0_point  # noqa: E402
from sparkrl.experiments.runner import execute_run  # noqa: E402
from sparkrl.experiments.spec import RunSpec, split_of  # noqa: E402
from sparkrl.rl.env import SparkTuningEnv  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

PROTOCOL_VERSION = "demo/v1"
EXPERIMENT_ID = "EXP-012"
AUTHORIZED_BY = "DEC-051"
FAM, SCALE, SEED = "F5_mixed", "small", 0
OUT_DIR = PROJECT / "results" / "experiments" / "x-demo"
OBS_PATH = OUT_DIR / "observations.jsonl"
SPEC_PATH = OUT_DIR / "spec.json"
RL_POLICY_ID = "b801f4a7df200b04c630978f0476c29245da9a9336802f26bff4c2e5b8a7d033"


def queue_plan() -> list[dict]:
    return ([{"run": "B0"}, {"run": "B3 (G-p8-sp16)"}] +
            [{"run": f"RL-s0 episode {i} (frozen policy, trace)"} for i in (1, 2, 3)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("plan", "live", "backup"), default="plan")
    ap.add_argument("--allow-spark", action="store_true")
    a = ap.parse_args()

    if a.mode == "plan":
        print("EXP-012 demo plan (0 Spark, 0 writes):")
        for q in queue_plan():
            print("  -", q["run"])
        print("cell: F5_mixed|small|seed0 (TRAIN, T_ref calibrated); 5 TRAIN-split runs;")
        print("needs DEC-051 signed + --allow-spark for live. Backup replays x-demo/observations.jsonl.")
        return 0

    if a.mode == "backup":
        if not OBS_PATH.exists():
            raise SystemExit("refusing: no packaged demo manifest (run --mode live once, then backup replays it)")
        rows = [json.loads(l) for l in OBS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
        print_table(rows)
        print(f"backup replay: {len(rows)} logged rows, 0 Spark executions.")
        return 0

    if not a.allow_spark:
        raise SystemExit("refusing: live needs --allow-spark (and signed DEC-051)")
    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    assert not base.aqe_enabled
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OBS_PATH.exists():
        raise SystemExit("refusing: demo manifest exists; replay with --mode backup (no overwrite)")
    SPEC_PATH.write_text(json.dumps({
        "experiment_id": EXPERIMENT_ID, "protocol_version": PROTOCOL_VERSION,
        "authorized_by": AUTHORIZED_BY, "cell": f"{FAM}|{SCALE}|seed{SEED}",
        "runs": 5, "sc6_note": "5 TRAIN-split executions on the demo register line (disclosed, not hidden)",
        "policy": RL_POLICY_ID}, indent=1), encoding="utf-8")

    rows: list[dict] = []

    def do_static(label: str, point) -> None:
        rs = RunSpec(run_id=f"demo-{label}-r1".lower(), family=FAM, scale=SCALE, seed=SEED,
                     rep=1, config=point, split=split_of(FAM, SCALE, SEED),
                     timeout_seconds=float(base.timeout_seconds), order_index=len(rows),
                     block_id="demo")
        metrics, _ = execute_run(rs, base)
        row = {"run_id": rs.run_id, "arm": label, "config_name": point.name,
               "execution_time_s": metrics.execution_time_s, "usable": bool(metrics.usable),
               "error": metrics.error}
        rows.append(row)
        print(f"[{label}] t={metrics.execution_time_s} usable={metrics.usable}", flush=True)

    do_static("B0", b0_point())
    b3 = resolve_strategy("B3", family=FAM, scale=SCALE, dataset_seed=SEED)
    from sparkrl.experiments.grid import build_grid
    grid = {p.name: p for p in build_grid(include_b0=True)}
    do_static("B3", grid[b3.config_name])

    art = load_policy(RL_POLICY_ID, PROJECT / "models" / "policies")
    agent = agent_from_artifact(art)
    env = SparkTuningEnv(base, result_root=None)
    last_r = None
    for i in (1, 2, 3):
        obs, _ = env.reset(family=FAM, scale=SCALE, seed=SEED, rep=i, last_reward=last_r)
        action = agent.select_action(obs.state, epsilon=0.0)
        state_after, reward, _, _, info = env.step(action)
        last_r = reward
        row = {"run_id": info.run_id, "arm": f"RL-s0-ep{i}", "config_name": info.config_name,
               "state": obs.state.key(), "action": int(action),
               "execution_time_s": info.metrics.get("execution_time_s"),
               "reward": reward, "usable": bool(info.metrics.get("usable", True))}
        rows.append(row)
        print(f"[RL-s0 ep{i}] state={obs.state.key()} action={action} "
              f"config={info.config_name} t={row['execution_time_s']} r={reward:.4f}", flush=True)

    with OBS_PATH.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print_table(rows)
    return 0


def print_table(rows: list[dict]) -> None:
    print(f"{'arm':12} {'config':10} {'time_s':>10} {'reward':>8} usable")
    for r in rows:
        print(f"{r['arm']:12} {r.get('config_name', '?'):10} "
              f"{str(round(r['execution_time_s'], 3)) if r['execution_time_s'] is not None else 'FAILED':>10} "
              f"{round(r['reward'], 4) if 'reward' in r else '-':>8} {r['usable']}")


if __name__ == "__main__":
    raise SystemExit(main())
