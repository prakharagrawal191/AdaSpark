"""Day-29 M8 agreement tests against scripts/analyze_day29.py (the
authoritative analyzer). Synthetic fixtures only: zero Spark, zero live
executions, zero reads of the real training artifacts.

Covers the Day-29 protocol test list: exact/below/above 70% boundary,
pairwise and aggregate agreement, the pre-specified D_all3 denominator,
unvisited-state handling, Q0-only (trivial-agreement) states, deterministic
lowest-index tie-breaking, reversed-input reproducibility, seed enforcement
(seed mismatch on load, duplicate/missing seeds), and Day-28 artifact
protection (the fixed-seed comparison is descriptive and never enters M8).

No train/validation/test-leakage test is duplicated here: the Q0 builder's
split guard is pinned by tests/unit/test_rl_q0.py and the Day-29 validator
re-checks the stored Q0 provenance of every replicate.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "analyze_day29.py"
_spec = importlib.util.spec_from_file_location("analyze_day29", _SCRIPT)
d29 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("analyze_day29", d29)
_spec.loader.exec_module(d29)

SEEDS = (0, 1, 2)
STATES10 = [f"st{i}" for i in range(10)]


def row(action: int, value: float = 0.95) -> list[float]:
    r = [0.5] * 12
    r[action] = value
    return r


def tie_row(actions: tuple[int, ...]) -> list[float]:
    r = [0.5] * 12
    for a in actions:
        r[a] = 0.9
    return r


def trio(spec: dict[str, tuple[int, ...]]) -> dict[int, dict[str, int]]:
    """greedy per seed from {state: per-seed action}."""
    return {s: {k: v[s] for k, v in spec.items()} for s in SEEDS}


def visits_all(states, action: int = 0) -> dict:
    return {s: {k: {action: 1} for k in states} for s in SEEDS}


def visits_only(seed_states: dict[int, tuple[str, ...]]) -> dict:
    return {s: {k: {0: 1} for k in seed_states[s]} for s in SEEDS}


# --- 1-3: threshold behaviour --------------------------------------------------
def test_exact_70_boundary_passes():
    spec = {k: (3, 3, 3) for k in STATES10[:7]}
    spec.update({"st7": (4, 4, 5), "st8": (4, 5, 4), "st9": (5, 4, 4)})
    blk = d29.agreement_block(trio(spec), visits_all(STATES10), SEEDS)
    assert blk["primary"]["states_total"] == 10
    assert blk["primary"]["states_unanimous"] == 7
    assert blk["primary"]["agreement"] == pytest.approx(0.70)
    assert blk["verdict"]["passed"] is True       # >= threshold is inclusive
    assert blk["verdict"]["status"] == "PASS"


def test_below_70_fails():
    spec = {k: (3, 3, 3) for k in STATES10[:6]}
    spec.update({"st6": (4, 4, 5), "st7": (4, 5, 4),
                 "st8": (5, 4, 4), "st9": (4, 5, 5)})
    blk = d29.agreement_block(trio(spec), visits_all(STATES10), SEEDS)
    assert blk["primary"]["agreement"] == pytest.approx(0.60)
    assert blk["verdict"]["passed"] is False
    assert blk["verdict"]["status"] == "FAIL"


def test_above_70_passes():
    spec = {k: (3, 3, 3) for k in STATES10[:9]}
    spec.update({"st9": (4, 4, 5)})
    blk = d29.agreement_block(trio(spec), visits_all(STATES10), SEEDS)
    assert blk["primary"]["agreement"] == pytest.approx(0.90)
    assert blk["verdict"]["passed"] is True

# --- 4-5: pairwise + aggregate --------------------------------------------------
def test_pairwise_uses_the_same_denominator_and_disagrees_where_told():
    spec = {k: (3, 3, 3) for k in STATES10[:7]}
    spec.update({"st7": (4, 4, 5), "st8": (4, 5, 4), "st9": (5, 4, 4)})
    blk = d29.agreement_block(trio(spec), visits_all(STATES10), SEEDS)
    pw = blk["variants"]["V3_pairwise_mean_over_D_all3"]["pairs"]
    assert pw["seed0_vs_seed1"]["states_equal"] == 8   # + st7
    assert pw["seed0_vs_seed2"]["states_equal"] == 8   # + st8
    assert pw["seed1_vs_seed2"]["states_equal"] == 8   # + st9 (seeds 1,2 tie)
    for rec in pw.values():
        assert rec["states_compared"] == 10            # same denominator


def test_aggregate_counts_only_unanimous_states():
    spec = {k: (3, 3, 3) for k in STATES10[:8]}
    spec.update({"st8": (4, 5, 5), "st9": (5, 5, 5)})
    blk = d29.agreement_block(trio(spec), visits_all(STATES10), SEEDS)
    # st8: only seed 0 differs -> pairwise 1v2 agree but NOT unanimous
    assert blk["primary"]["states_unanimous"] == 9
    assert blk["primary"]["agreement"] == pytest.approx(0.9)
    pw = blk["variants"]["V3_pairwise_mean_over_D_all3"]["pairs"]
    assert pw["seed1_vs_seed2"]["states_equal"] == 10

# --- 6-8: denominator / unvisited / Q0-only --------------------------------------
def test_denominator_is_D_all3_visited_by_every_seed():
    spec = {"a": (1, 1, 1), "b": (2, 2, 3)}
    vis = visits_only({0: ("a", "b"), 1: ("a", "b"), 2: ("a", "b")})
    # "c" exists in every greedy table but nobody ever visited it
    for s in SEEDS:
        spec["c"] = (4, 4, 4)
    blk = d29.agreement_block(trio(spec), vis, SEEDS)
    assert blk["primary"]["states"] == ["a", "b"]       # c excluded
    assert blk["primary"]["agreement"] == pytest.approx(0.5)


def test_unvisited_divergent_state_is_not_counted_as_disagreement():
    spec = {"a": (1, 1, 1), "b": (2, 2, 2), "c": (4, 5, 6)}
    vis = visits_only({0: ("a", "b"), 1: ("a", "b"), 2: ("a", "b")})
    blk = d29.agreement_block(trio(spec), vis, SEEDS)
    assert blk["primary"]["states"] == ["a", "b"]
    assert blk["primary"]["agreement"] == 1.0           # c never counted
    assert blk["variants"]["V1_D_union_any"]["agreement"] == \
        pytest.approx(2 / 3)                            # would differ under V1


def test_q0_only_state_is_flagged_trivial_when_it_agrees():
    spec = {"a": (1, 1, 1), "b": (2, 2, 3), "c": (4, 4, 4)}
    vis = visits_only({0: ("a", "b"), 1: ("a", "b"), 2: ("a", "b")})
    blk = d29.agreement_block(trio(spec), vis, SEEDS)
    rec = {r["state_key"]: r for r in blk["per_state"]}
    assert rec["c"]["agreement_is_trivial"] is True     # unanimous + unvisited
    assert rec["a"]["agreement_is_trivial"] is False
    assert "Q0" in rec["c"]["note"] or "NOT evidence-bearing" in rec["c"]["note"]


def test_empty_denominator_is_a_FAIL_not_a_pass():
    blk = d29.agreement_block(trio({"a": (1, 1, 1)}),
                              visits_only({0: ("a",), 1: (), 2: ()}), SEEDS)
    assert blk["primary"]["states_total"] == 0
    assert blk["primary"]["agreement"] is None
    assert blk["verdict"]["passed"] is False
    assert blk["verdict"]["status"] == "FAIL"

# --- 9-10: ties + reproducibility ------------------------------------------------
def test_greedy_ties_break_to_the_lowest_index():
    art = {"q_table": {"s": tie_row((9, 2))}}
    assert d29.greedy_policy(art) == {"s": 2}
    art4 = {"q_table": {"s": tie_row((3, 9))}}
    assert d29.greedy_policy(art4) == {"s": 3}
    art_det = {"q_table": {"s": row(7)}}
    assert d29.greedy_policy(art_det) == {"s": 7}


def test_reversed_input_order_gives_identical_blocks():
    spec = {k: (3, 3, 3) for k in STATES10[:7]}
    spec.update({"st7": (4, 4, 5), "st8": (4, 5, 4), "st9": (5, 4, 4)})
    g, v = trio(spec), visits_all(STATES10)
    a = d29.agreement_block(g, v, SEEDS)
    b = d29.agreement_block({s: g[s] for s in (2, 1, 0)},
                            {s: v[s] for s in (2, 1, 0)}, SEEDS)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_episode_log_reversal_does_not_change_visits_or_report():
    eps = tuple({"state_key_before": k, "action_index": a,
                 "reward": 0.1, "episode_index": i,
                 "record_schema_version": "rl-training-episode/v1"}
                for i, (k, a) in enumerate(
                    [("a", 1), ("a", 2), ("b", 3)]))
    fwd, rev = d29.visit_counts(eps), d29.visit_counts(tuple(reversed(eps)))
    assert fwd == rev

# --- 11/14/15: seed enforcement ---------------------------------------------------
def _make_run_dir(tmp_path: Path, seed: int, run_id: str) -> Path:
    d = tmp_path / run_id
    (d / "checkpoints").mkdir(parents=True)
    art = {"policy_schema": "policy/v1",
           "q_table": {"state-v1.5|agg|S|le0": row(2)}}
    pol = d / "checkpoints" / "policy-final.json"
    pol.write_text(json.dumps(art), encoding="utf-8")
    manifest = {
        "record_schema_version": "rl-training-run/v1",
        "agent_rng_seed": seed, "dataset_seed": 0,
        "files": {"episode_log": "episodes.jsonl"},
        "final_policy": {"path": "checkpoints\\policy-final.json"},
        "counts": {"episodes_planned": 2, "episodes_completed": 2,
                   "episodes_failed": 0},
        "budget": {"live_executions": 2, "budget_limit_this_run": 500},
    }
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (d / "episodes.jsonl").write_text(
        "\n".join(json.dumps({"record_schema_version":
                              "rl-training-episode/v1",
                              "state_key_before":
                              "state-v1.5|agg|S|le0",
                              "action_index": 2, "reward": 0.2,
                              "epsilon_used": 0.5,
                              "episode_index": i}) for i in (1, 2)),
        encoding="utf-8")
    return d


def test_load_run_rejects_a_seed_mismatch(tmp_path):
    d = _make_run_dir(tmp_path, seed=0, run_id="run-a0")
    with pytest.raises(d29.AnalysisError, match="not the replicate"):
        d29.load_run(1, d)                     # loaded AS seed 1 -> refuse


def test_load_run_rejects_a_wrong_schema(tmp_path):
    d = _make_run_dir(tmp_path, seed=0, run_id="run-b0")
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    m["record_schema_version"] = "something-else/v9"
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(d29.AnalysisError, match="record_schema_version"):
        d29.load_run(0, d)


def test_build_report_rejects_a_duplicate_seed(tmp_path):
    runs = [d29.load_run(0, _make_run_dir(tmp_path, 0, "r0a")),
            d29.load_run(0, _make_run_dir(tmp_path, 0, "r0b")),
            d29.load_run(1, _make_run_dir(tmp_path, 1, "r1"))]
    with pytest.raises(d29.AnalysisError, match="duplicate agent seed"):
        d29.build_report(tuple(runs), None)


def test_build_report_rejects_a_missing_seed(tmp_path):
    runs = [d29.load_run(0, _make_run_dir(tmp_path, 0, "r0")),
            d29.load_run(1, _make_run_dir(tmp_path, 1, "r1"))]
    with pytest.raises(d29.AnalysisError, match="frozen set"):
        d29.build_report(tuple(runs), None)


def test_build_report_visits_must_reconcile_with_the_episode_log(tmp_path):
    # visit_counts skips lines without state_key_before; the reconciliation
    # guard must catch that silently-lost visit as a loud AnalysisError.
    d = _make_run_dir(tmp_path, 0, "r0")
    with (d / "episodes.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("\n" + json.dumps({"record_schema_version":
                                    "rl-training-episode/v1",
                                    "state_key_before": None,
                                    "action_index": 2, "reward": 0.2,
                                    "epsilon_used": 0.5,
                                    "episode_index": 3}))
    runs = [d29.load_run(0, d),
            d29.load_run(1, _make_run_dir(tmp_path, 1, "r1")),
            d29.load_run(2, _make_run_dir(tmp_path, 2, "r2"))]
    with pytest.raises(d29.AnalysisError, match="visit counts"):
        d29.build_report(tuple(runs), None)

# --- 12: Day-28 artifacts are descriptive-only, never part of M8 -----------------
def test_day28_style_run_never_enters_m8(tmp_path):
    runs = [d29.load_run(s, _make_run_dir(tmp_path, s, f"m8-{s}"))
            for s in SEEDS]
    day28 = d29.load_run(0, _make_run_dir(tmp_path, 0, "day28-style"))
    report = d29.build_report(tuple(runs), day28)
    assert report["m8"]["seeds"] == [0, 1, 2]          # M8 stays {0,1,2}
    assert report["m8"]["pre_specification"][
        "fixed_before_any_policy_was_inspected"] is True
    aux = report["same_seed_comparison_day28_vs_day29"]
    assert aux["day28_agent_rng_seed"] == 0            # descriptive block
    assert aux["day29_agent_rng_seed"] == 0
    assert aux["label"].startswith("CONTEXT ONLY")
    # and a report without Day-28 still evaluates M8 identically
    report2 = d29.build_report(tuple(runs), None)
    assert report2["m8"]["primary"] == report["m8"]["primary"]
    assert report2["same_seed_comparison_day28_vs_day29"][
        "available"] is False

# === CHUNK-T5 ===



