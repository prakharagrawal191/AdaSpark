"""Offline Q0 initialization from EXP-002 TRAIN records (Day 26 requirement).

Frozen elements combined here (no new freedom):
* SOURCE: only the EXP-002 stored run records (``results/experiments/exp-002``),
  and only TRAIN cells (PLAN section 18). The builder HARD-FAILS on any record
  whose (family, scale, seed) is not TRAIN - validation seed 3, test family
  F4_ski, test scale large, and test seed 4 can never enter Q0.
* VALUE: the per-observation FROZEN R3 reward (``sparkrl.rl.reward``), using
  T_ref from the EXP-002 gate artifact (B0 median, seed 0) and input_bytes
  from the dataset manifests. Reward is NEVER recomputed differently here.
* ACTION: the record's frozen ``config_grid_index`` (0..11). B0 records
  (grid_index None) contribute NOTHING to Q - B0 is the reference condition,
  and its role is T_ref.
* AGGREGATION: median over the per-observation rewards (PLAN section 22
  primary statistic). No cherry-picking: every valid observation counts,
  invalid observations are counted and skipped, never used.
* DEFAULT: pairs without evidence receive the frozen optimistic init
  Q0 = +0.5 (PLAN section 16). This is applied by ``QLearningAgent`` itself,
  not fabricated here.
* STATE: the frozen v1.5 encoder with no history (feedback_bin = le0, the
  documented Day-25 no-history convention).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkrl.experiments.runner import load_records
from sparkrl.experiments.spec import (EXPERIMENT_ID, TRAIN, ExperimentSpec,
                                      split_of)
from sparkrl.agent.q_learning import AGENT_VERSION, state_key_of
from sparkrl.rl.reward import RewardCalculator
from sparkrl.rl.state import SCHEMA_V15, StateEncoder
from sparkrl.rl.tref import TRefStore
from sparkrl.workloads.resolver import resolve_dataset

PROJECT = Path(__file__).resolve().parents[3]
EXP002_RESULT_ROOT = PROJECT / "results" / "experiments" / "exp-002"
DEFAULT_SPEC_PATH = PROJECT / "experiments" / "exp002.yaml"

Q0_VERSION = "q0-exp002/v1"


class LeakageError(RuntimeError):
    """A protected (validation/test) record attempted to enter Q0."""


class Q0SourceError(RuntimeError):
    """EXP-002 source artifacts missing or inconsistent with the spec."""


@dataclass
class Q0Result:
    q_table: dict[str, list[float]]          # key -> 12 frozen-action values
    provenance: dict[str, Any] = field(default_factory=dict)


def build_q0_from_exp002(*, result_root: Path = EXP002_RESULT_ROOT,
                         spec_path: Path = DEFAULT_SPEC_PATH,
                         encoder: StateEncoder | None = None,
                         reward_calculator: RewardCalculator | None = None,
                         tref_store: TRefStore | None = None) -> Q0Result:
    """Derive Q0 from authorized EXP-002 TRAIN observations (deterministic)."""
    spec = ExperimentSpec.from_yaml(spec_path)
    records = load_records(result_root)
    if not records:
        raise Q0SourceError(f"no EXP-002 records under {result_root}")
    encoder = encoder or StateEncoder(schema_version=SCHEMA_V15)
    calculator = reward_calculator or RewardCalculator()
    trefs = tref_store or TRefStore()

    rewards: dict[tuple[str, int], list[float]] = {}
    n_scanned = n_valid = n_invalid = n_b0 = n_tref_missing = 0
    spec_fps: set[str] = set()
    grid_fps: set[str] = set()
    tref_missing_cells: set[str] = set()
    input_bytes_cache: dict[tuple[str, str], int] = {}

    for rec in records:
        n_scanned += 1
        rs = rec.get("run_spec") or {}
        family, scale, seed = rs.get("family"), rs.get("scale"), rs.get("seed")
        split = split_of(family, scale, seed)
        if split != TRAIN:
            raise LeakageError(
                f"record {rs.get('run_id')!r} is split={split!r}; Q0 accepts "
                f"TRAIN cells only (PLAN section 18)")
        if rec.get("experiment_id") != EXPERIMENT_ID:
            raise Q0SourceError(
                f"record {rs.get('run_id')!r} is {rec.get('experiment_id')!r}, "
                f"not {EXPERIMENT_ID}")
        spec_fps.add(rec.get("spec_fingerprint"))
        grid_fps.add(rec.get("grid_fingerprint"))

        action = rs.get("config_grid_index")
        if action is None:
            n_b0 += 1                    # B0 = reference; T_ref role only
            continue
        metrics = rec.get("metrics") or {}
        if rec.get("status") != "COMPLETED" or not metrics.get("usable"):
            n_invalid += 1               # counted, never used
            continue

        t_ref = trefs.get(family, scale, seed)
        if t_ref is None:
            # T_ref pending (e.g. F3_rdd|medium: invalid EXP-002 B0 panel;
            # EXP-003 calibrates). The frozen reward is UNDEFINED without it,
            # so the observation is counted and skipped - never fabricated.
            n_tref_missing += 1
            tref_missing_cells.add(f"{family}|{scale}")
            continue
        n_valid += 1

        cache_key = (family, scale)
        if cache_key not in input_bytes_cache:
            resolved = resolve_dataset(family, scale, seed)
            input_bytes_cache[cache_key] = (
                int(resolved.orders_manifest.get("total_bytes") or 0)
                + int(resolved.lineitem_manifest.get("total_bytes") or 0))
        input_bytes = input_bytes_cache[cache_key]

        reward = calculator.compute(metrics, t_ref, input_bytes,
                                    failed=False).value
        state = encoder.encode(family, input_bytes, last_reward=None)
        rewards.setdefault((state_key_of(state), int(action)), []).append(reward)

    if spec.fingerprint() not in spec_fps:
        raise Q0SourceError(
            "stored records do not match the current EXP-002 spec fingerprint "
            f"{spec.fingerprint()}; refusing to initialize from unknown data")

    return _assemble(rewards, n_scanned, n_valid, n_invalid, n_b0,
                     n_tref_missing, sorted(tref_missing_cells),
                     sorted(grid_fps), spec, encoder, calculator, trefs,
                     result_root)


def _assemble(rewards: dict[tuple[str, int], list[float]], n_scanned: int,
              n_valid: int, n_invalid: int, n_b0: int, n_tref_missing: int,
              tref_missing_cells: list[str], grid_fps: list[str],
              spec: ExperimentSpec, encoder: StateEncoder,
              calculator: RewardCalculator, trefs: TRefStore,
              result_root: Path) -> Q0Result:
    # Rows hold ONLY evidence: unobserved actions stay None and the AGENT
    # fills the frozen optimistic default (+0.5, PLAN section 16) at access
    # time. A row is kept only when it has at least one observation.
    q_table: dict[str, list[float | None]] = {}
    pair_counts: dict[str, int] = {}
    for (key, action), values in sorted(rewards.items()):
        row = q_table.setdefault(key, [None] * 12)
        row[action] = statistics.median(values)     # frozen aggregation
        pair_counts[f"{key}#{action}"] = len(values)
    q_table_typed: dict[str, list[float]] = {
        k: [float(v) if v is not None else float("nan") for v in row]
        for k, row in q_table.items()}
    # A NaN in serialized Q0 data would corrupt downstream agents; replace
    # evidence-free action slots with None so the agent applies its default.
    q_table_typed = {
        k: [None if math.isnan(v) else v for v in row]
        for k, row in q_table_typed.items()}  # type: ignore[list-item]

    provenance: dict[str, Any] = {
        "q0_version": Q0_VERSION,
        "learner_version": AGENT_VERSION,
        "source": "exp002",
        "result_root": str(result_root),
        "spec_fingerprint": spec.fingerprint(),
        "grid_fingerprint": grid_fps[0] if len(grid_fps) == 1 else grid_fps,
        "t_ref_source": trefs.source,
        "state_schema": encoder.schema_version,
        "reward_formula": calculator.formula_id,
        "aggregation": "median",
        "records_scanned": n_scanned,
        "records_valid_used": n_valid,
        "records_invalid_skipped": n_invalid,
        "records_b0_reference": n_b0,
        "records_tref_missing_skipped": n_tref_missing,
        "tref_missing_cells": sorted(tref_missing_cells),
        "pairs_initialized": len(q_table_typed),
        "pair_observation_counts": pair_counts,
        "leakage_guard": "split_of()!=TRAIN -> hard error; none encountered",
    }
    return Q0Result(q_table=q_table_typed, provenance=provenance)

