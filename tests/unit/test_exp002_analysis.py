"""Unit tests for the EXP-002 analysis and sensitivity gate (Day 22).

Every test here runs on controlled synthetic fixture data: the gate logic must be
verifiable without depending on live Spark timing. Two of them are the mandated
end-to-end controls - a synthetic dataset engineered to PASS and one engineered to
FAIL - so the gate is proven to be capable of both verdicts.
"""
from __future__ import annotations

import json

import pytest

from sparkrl.analysis.exp002 import (ANALYSIS_VERSION, GATE_SCHEMA_VERSION,
                                     build_panels, build_report, evaluate_gate,
                                     is_valid_record, partition_observations,
                                     pooled_within_config_cv, relative_spread,
                                     report_json, spearman_rho,
                                     summarize_times,)
from sparkrl.experiments.grid import build_grid
from sparkrl.experiments.spec import ExperimentSpec

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- fixtures
def make_spec(families=("F1_agg", "F2_join"), scales=("small",),
              reps=2, **gate_overrides) -> ExperimentSpec:
    gate = {
        "criterion_id": "H1/SC1",
        "metric": "execution_time_s",
        "statistic": "median",
        "min_relative_spread": 0.10,
        "min_families": 2,
        "scope": "varied_only",
        "family_rule": "any_scale",
        "noise_rule": "spread_must_exceed_pooled_within_config_cv",
        "min_valid_runs_per_config": 1,
        "require_complete_panel": True,
    }
    gate.update(gate_overrides)
    return ExperimentSpec.from_dict({
        "experiment_id": "EXP-002",
        "spec_version": "exp002-spec/v1",
        "families": list(families),
        "scales": list(scales),
        "seeds": [0],
        "repetitions": reps,
        "warmup_runs": 2,
        "aqe_enabled": False,
        "order_seed": 1,
        "timeouts_by_scale": {s: 300.0 for s in scales},
        "base_config_path": "configs/baseline_b0.yaml",
        "result_root": "results/experiments/exp-002",
        "gate": gate,
    })


def make_record(family, scale, config_name, rep, exec_s, *, seed=0,
                usable=True, status=None, error=None, timeout=False,
                event_log_status="COMPLETE", grid_index=0,
                is_reference=False, split="train", applied_mismatches=()):
    """One synthetic stored run record in the exp002-run/v1 shape."""
    if status is None:
        status = "COMPLETED" if usable else "FAILED"
    run_id = (f"exp002-{family}-{scale}-s{seed}-{config_name}-r{rep}"
              .replace("_", "-").lower())
    return {
        "schema_version": "exp002-run/v1",
        "experiment_id": "EXP-002",
        "spec_fingerprint": "spec-fp",
        "grid_fingerprint": "grid-fp",
        "status": status,
        "attempt": 1,
        "run_spec": {
            "run_id": run_id, "experiment_id": "EXP-002", "family": family,
            "scale": scale, "seed": seed, "rep": rep,
            "config_name": config_name, "config_grid_index": grid_index,
            "config_fingerprint": f"fp-{config_name}",
            "config_is_reference": is_reference, "split": split,
            "aqe_enabled": False, "timeout_seconds": 300.0,
            "order_index": 0, "block_id": f"{family}|{scale}|rep{rep}",
            "relative_path": f"{family}/{scale}/seed{seed}/{config_name}/rep{rep}.json",
        },
        "metrics": {
            "schema_version": "run_metrics/v1", "run_id": run_id,
            "family": family, "scale": scale, "seed": seed,
            "execution_time_s": exec_s, "execution_time_source": "runner",
            "usable": usable, "success": usable, "timeout": timeout,
            "error": error, "event_log_status": event_log_status,
            "task_count": 100, "failed_task_count": 0,
            "shuffle_read_bytes": 1000, "shuffle_write_bytes": 1000,
            "total_spill_bytes": 0, "task_duration_cv": 0.5,
            "sysmon_sampled": False, "aqe_enabled": False,
        },
        "provenance": {"code_version": "test",
                       "applied_mismatches": list(applied_mismatches)},
    }


def dataset(spec, times_by_config, *, families=None, scale="small"):
    """Build a full set of records: every configuration x every repetition.

    ``times_by_config`` maps configuration name -> base time; repetition r gets
    ``base * (1 + 0.001 * r)`` so within-configuration noise is tiny but non-zero.
    """
    grid = {p.name: p for p in build_grid()}
    records = []
    for family in (families or spec.families):
        for rep in range(1, spec.repetitions + 1):
            for name, base in times_by_config.items():
                point = grid[name]
                records.append(make_record(
                    family, scale, name, rep, base * (1 + 0.001 * rep),
                    grid_index=point.grid_index or 0,
                    is_reference=point.is_reference))
    return records


ALL_NAMES = [p.name for p in build_grid()]
VARIED_NAMES = [p.name for p in build_grid() if not p.is_reference]


# ---------------------------------------------------------------- primitives
def test_summarize_times_basic_and_empty():
    s = summarize_times([1.0, 2.0, 3.0])
    assert s["n"] == 3 and s["median_s"] == 2.0 and s["mean_s"] == 2.0
    assert s["std_s"] == pytest.approx(1.0)
    assert s["cv"] == pytest.approx(0.5)
    empty = summarize_times([])
    assert empty["n"] == 0 and empty["median_s"] is None and empty["cv"] is None


def test_summarize_times_single_observation_has_no_std_or_cv():
    """n=1 must not fabricate a zero standard deviation."""
    s = summarize_times([4.0])
    assert s["n"] == 1 and s["median_s"] == 4.0
    assert s["std_s"] is None and s["cv"] is None


def test_summarize_times_ignores_none_values():
    assert summarize_times([1.0, None, 3.0])["n"] == 2


def test_relative_spread_maths():
    out = relative_spread({"a": 10.0, "b": 12.0, "c": 11.0})
    assert out["min_s"] == 10.0 and out["max_s"] == 12.0
    assert out["relative"] == pytest.approx(0.2)
    assert out["absolute_s"] == pytest.approx(2.0)
    assert out["argmin"] == "a" and out["argmax"] == "b"


def test_relative_spread_undefined_with_fewer_than_two_configs():
    assert relative_spread({"a": 10.0})["relative"] is None
    assert relative_spread({"a": None, "b": None})["relative"] is None


def test_pooled_within_config_cv_matches_hand_computation():
    # two configs, each with two observations; variances 0.5 and 0.5 -> pooled sd
    # = sqrt((1*0.5 + 1*0.5)/2) = sqrt(0.5); grand mean = 15.5
    data = {"a": [10.0, 11.0], "b": [20.0, 21.0]}
    expected = (0.5 ** 0.5) / 15.5
    # results are rounded to 6 decimal places for byte-stable JSON output
    assert pooled_within_config_cv(data) == pytest.approx(expected, abs=1e-6)


def test_pooled_within_config_cv_none_without_repetitions():
    assert pooled_within_config_cv({"a": [1.0], "b": [2.0]}) is None


def test_spearman_rho_perfect_and_reversed_and_tied():
    assert spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman_rho([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    assert spearman_rho([1, 1, 1], [1, 2, 3]) is None      # zero variance in ranks
    assert spearman_rho([1.0], [2.0]) is None              # too few points


# ---------------------------------------------------------------- validity
def test_is_valid_record_requires_both_usable_and_completed_status():
    ok = make_record("F1_agg", "small", "B0", 1, 5.0, is_reference=True)
    assert is_valid_record(ok)

    not_usable = make_record("F1_agg", "small", "B0", 1, 5.0, usable=False,
                             error="boom")
    assert not is_valid_record(not_usable)

    # A record claiming COMPLETED while its metrics say unusable must NOT count.
    lying = make_record("F1_agg", "small", "B0", 1, 5.0, usable=False,
                        status="COMPLETED")
    assert not is_valid_record(lying)


def test_invalid_runs_are_excluded_from_stats_but_still_reported():
    spec = make_spec()
    records = dataset(spec, {n: 10.0 for n in ALL_NAMES})
    records.append(make_record("F1_agg", "small", "G-p2-sp16", 9, None,
                               usable=False, error="PermissionError WinError 32",
                               event_log_status="INCOMPLETE"))
    valid, invalid = partition_observations(records)
    assert len(invalid) == 1
    assert all(o["usable"] for o in valid)

    report = build_report(records, spec, generated_utc="T", code_version="v")
    assert report["execution"]["invalid"] == 1
    assert report["execution"]["valid"] == len(valid)
    only = report["execution"]["invalid_runs"][0]
    assert "WinError 32" in only["error"]
    # the invalid observation must not have moved any median
    panel = next(p for p in report["panels"] if p["family"] == "F1_agg")
    cfg = next(c for c in panel["configs"] if c["name"] == "G-p2-sp16")
    assert cfg["n_valid"] == spec.repetitions


def test_missing_metric_is_preserved_as_none_not_zero():
    spec = make_spec()
    records = dataset(spec, {n: 10.0 for n in ALL_NAMES})
    report = build_report(records, spec, generated_utc="T", code_version="v")
    panel = next(p for p in report["panels"] if p["family"] == "F1_agg")
    # a configuration with no observations keeps None everywhere, never 0.0
    empty_spec = make_spec()
    sparse = [r for r in records if r["run_spec"]["config_name"] != "G-p8-sp128"]
    sparse_report = build_report(sparse, empty_spec, generated_utc="T",
                                 code_version="v")
    sparse_panel = next(p for p in sparse_report["panels"]
                        if p["family"] == "F1_agg")
    missing = next(c for c in sparse_panel["configs"] if c["name"] == "G-p8-sp128")
    assert missing["n_valid"] == 0
    assert missing["median_s"] is None and missing["mean_s"] is None
    assert missing["rel_diff_from_b0"] is None
    assert panel["complete"] is True and sparse_panel["complete"] is False


# ---------------------------------------------------------------- B0-relative
def test_b0_relative_difference_calculation():
    spec = make_spec()
    times = {n: 20.0 for n in ALL_NAMES}
    times["B0"] = 20.0
    times["G-p8-sp16"] = 10.0     # 50% faster than B0
    times["G-p2-sp16"] = 25.0     # 25% slower than B0
    report = build_report(dataset(spec, times), spec, generated_utc="T",
                          code_version="v")
    panel = next(p for p in report["panels"] if p["family"] == "F1_agg")
    by_name = {c["name"]: c for c in panel["configs"]}
    assert by_name["B0"]["rel_diff_from_b0"] == pytest.approx(0.0, abs=1e-9)
    assert by_name["G-p8-sp16"]["rel_diff_from_b0"] == pytest.approx(-0.5, rel=1e-6)
    assert by_name["G-p2-sp16"]["rel_diff_from_b0"] == pytest.approx(0.25, rel=1e-6)
    # absolute difference is consistent with the panel's own medians
    assert by_name["G-p8-sp16"]["abs_diff_from_b0_s"] == pytest.approx(
        by_name["G-p8-sp16"]["median_s"] - panel["b0_median_s"], abs=1e-6)
    assert by_name["G-p8-sp16"]["abs_diff_from_b0_s"] == pytest.approx(-10.0, abs=0.05)
    # T_ref is the B0 median, per PLAN sections 15/33
    assert panel["t_ref_s"] == panel["b0_median_s"]


def test_gate_scope_excludes_the_b0_reference():
    """B0 is the reference, not a candidate: it must not drive the gate statistic."""
    spec = make_spec()
    times = {n: 10.0 for n in VARIED_NAMES}      # varied configs perfectly flat
    times["B0"] = 100.0                          # reference far away
    report = build_report(dataset(spec, times), spec, generated_utc="T",
                          code_version="v")
    panel = next(p for p in report["panels"] if p["family"] == "F1_agg")
    assert panel["spread"]["varied_only"]["relative"] == pytest.approx(0.0, abs=1e-6)
    assert panel["spread"]["including_reference"]["relative"] > 8.0
    assert panel["observed_spread"] == panel["spread"]["varied_only"]["relative"]
    assert panel["sensitive"] is False


# ---------------------------------------------------------------- the gate
def test_gate_pass_on_controlled_synthetic_data():
    """Engineered PASS: a large, repeatable spread on both families."""
    spec = make_spec()
    times = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        times[name] = 10.0 + 2.0 * i          # 10 s .. 32 s -> 220% spread
    report = build_report(dataset(spec, times), spec, generated_utc="T",
                          code_version="v")
    gate = report["gate"]
    assert gate["result"] == "PASS"
    assert gate["n_families_sensitive"] == 2
    assert sorted(gate["families_sensitive"]) == ["F1_agg", "F2_join"]
    for panel in report["panels"]:
        assert panel["complete"] is True
        assert panel["sensitive"] is True
        assert panel["observed_spread"] > 0.10
        assert panel["observed_spread"] > panel["pooled_within_config_cv"]


def test_gate_fail_on_controlled_synthetic_data():
    """Engineered FAIL: configurations are flat, so there is nothing to adapt to."""
    spec = make_spec()
    times = {n: 10.0 for n in ALL_NAMES}
    for i, name in enumerate(VARIED_NAMES):
        times[name] = 10.0 + 0.02 * i         # <0.25% spread, far below 10%
    report = build_report(dataset(spec, times), spec, generated_utc="T",
                          code_version="v")
    gate = report["gate"]
    assert gate["result"] == "FAIL"
    assert gate["n_families_sensitive"] == 0
    assert any("< required" in r for p in report["panels"] for r in p["reasons"])


def test_gate_fails_when_spread_does_not_exceed_noise():
    """A 12% spread buried in 30% run-to-run noise is not evidence of an effect."""
    spec = make_spec()
    grid = {p.name: p for p in build_grid()}
    records = []
    for family in spec.families:
        for name in ALL_NAMES:
            point = grid[name]
            base = 10.0 if name != "G-p8-sp128" else 11.2   # 12% spread
            # huge within-configuration swing between the two repetitions
            for rep, factor in ((1, 0.7), (2, 1.3)):
                records.append(make_record(
                    family, "small", name, rep, base * factor,
                    grid_index=point.grid_index or 0,
                    is_reference=point.is_reference))
    report = build_report(records, spec, generated_utc="T", code_version="v")
    panel = next(p for p in report["panels"] if p["family"] == "F1_agg")
    assert panel["pooled_within_config_cv"] > panel["observed_spread"]
    assert panel["sensitive"] is False
    assert report["gate"]["result"] == "FAIL"
    assert any("noise" in r for r in panel["reasons"])


def test_gate_fails_when_only_one_family_is_sensitive():
    """min_families=2: a single sensitive family is not enough."""
    spec = make_spec()
    flat = {n: 10.0 for n in ALL_NAMES}
    wide = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        wide[name] = 10.0 + 2.0 * i
    records = (dataset(spec, wide, families=["F1_agg"])
               + dataset(spec, flat, families=["F2_join"]))
    report = build_report(records, spec, generated_utc="T", code_version="v")
    assert report["gate"]["n_families_sensitive"] == 1
    assert report["gate"]["result"] == "FAIL"


def test_incomplete_panel_cannot_be_declared_sensitive():
    """A huge spread measured on a partial grid must not pass the gate."""
    spec = make_spec()
    wide = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        wide[name] = 10.0 + 2.0 * i
    records = dataset(spec, wide)
    # drop every observation of one configuration on both families
    records = [r for r in records
               if r["run_spec"]["config_name"] != "G-p4-sp64"]
    report = build_report(records, spec, generated_utc="T", code_version="v")
    for panel in report["panels"]:
        assert panel["complete"] is False
        assert panel["sensitive"] is False
        assert any("incomplete" in r for r in panel["reasons"])
    assert report["gate"]["result"] == "FAIL"


def test_gate_criteria_are_echoed_from_the_spec_not_hardcoded():
    spec = make_spec(min_relative_spread=0.25, min_families=1)
    times = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        times[name] = 10.0 + 0.15 * i      # ~16% spread: passes 10% but not 25%
    report = build_report(dataset(spec, times), spec, generated_utc="T",
                          code_version="v")
    crit = report["gate"]["criteria"]
    assert crit["min_relative_spread"] == 0.25
    assert crit["min_families"] == 1
    assert report["gate"]["result"] == "FAIL"


# ---------------------------------------------------------------- determinism
def test_gate_result_is_deterministic():
    spec = make_spec()
    times = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        times[name] = 10.0 + 2.0 * i
    records = dataset(spec, times)
    a = report_json(build_report(records, spec, generated_utc="T", code_version="v"))
    b = report_json(build_report(list(reversed(records)), spec,
                                 generated_utc="T", code_version="v"))
    assert a == b
    assert json.loads(a)["gate"]["result"] == "PASS"


def test_report_carries_schema_and_provenance_fields():
    spec = make_spec()
    report = build_report(dataset(spec, {n: 10.0 for n in ALL_NAMES}), spec,
                          generated_utc="T", code_version="abc123")
    assert report["schema_version"] == GATE_SCHEMA_VERSION
    assert report["analysis_version"] == ANALYSIS_VERSION
    assert report["experiment_id"] == "EXP-002"
    assert report["code_version"] == "abc123"
    assert report["metric"] == "execution_time_s"
    assert report["aqe_enabled"] is False
    assert report["spec_fingerprint"] == spec.fingerprint()
    for key in ("planned_runs", "records_found", "valid", "invalid", "missing"):
        assert key in report["execution"]


def test_report_counts_missing_planned_runs():
    spec = make_spec()
    records = dataset(spec, {n: 10.0 for n in ALL_NAMES})
    report = build_report(records, spec, generated_utc="T", code_version="v")
    assert report["execution"]["planned_runs"] == spec.planned_run_count()
    assert report["execution"]["missing"] == 0
    trimmed = build_report(records[:5], spec, generated_utc="T", code_version="v")
    assert trimmed["execution"]["missing"] == spec.planned_run_count() - 5


def test_repeatability_fields_are_populated():
    spec = make_spec()
    times = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        times[name] = 10.0 + 2.0 * i
    report = build_report(dataset(spec, times), spec, generated_utc="T",
                          code_version="v")
    panel = next(p for p in report["panels"] if p["family"] == "F1_agg")
    assert set(panel["per_rep_spread"]) == {"1", "2"}
    # the ordering is identical in both repetitions by construction
    assert panel["rep_rank_agreement_spearman"] == pytest.approx(1.0)
    assert panel["pooled_within_config_cv"] is not None
    assert panel["median_within_config_cv"] is not None


def test_evaluate_gate_is_pure_given_panels():
    spec = make_spec()
    times = {"B0": 20.0}
    for i, name in enumerate(VARIED_NAMES):
        times[name] = 10.0 + 2.0 * i
    valid, invalid = partition_observations(dataset(spec, times))
    panels = build_panels(valid, invalid, spec)
    assert evaluate_gate(panels, spec) == evaluate_gate(panels, spec)
