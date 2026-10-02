"""EXP-013 driver + pre-registered analysis (DEC-053). No Spark is started."""
from __future__ import annotations

import importlib.util
import itertools
import math
from collections import Counter
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


drv = _load("run_exp013")
ana = _load("analyze_exp013")

pytestmark = [pytest.mark.unit]

PLAN_QUEUE_FINGERPRINT = "fe159085330569d577d34285609a6fc3ef232dfa2d81c4e6be175084a16c8d1a"


def _units(*names):
    return [{"unit": n} for n in names]


def _toy():
    cells = [("F1_agg", "large", 3), ("F4_ski", "small", 0), ("F3_rdd", "large", 0)]
    exp005_instances = {cells[0]}
    units_of = {cells[0]: _units("B0", "B1", "B4", "RL", "B0'"),
                cells[1]: _units("B0", "B1", "B4", "RL"),
                cells[2]: _units("B0", "B1", "B4", "RL", "B2")}
    return cells, exp005_instances, units_of


def test_queue_is_deterministic_and_every_block_holds_each_unit_once():
    cells, exp005_instances, units_of = _toy()
    q1 = drv.build_queue(cells, units_of, exp005_instances)
    assert q1 == drv.build_queue(cells, units_of, exp005_instances)
    assert [e["queue_index"] for e in q1] == list(range(1, len(q1) + 1))
    assert len(q1) == drv.REPS * (5 + 4 + 5)
    blocks = Counter((e["family"], e["scale"], e["dataset_seed"], e["rep"]) for e in q1)
    for (f, s, d, _r), n in blocks.items():
        assert n == len(units_of[(f, s, d)])
    stages = [e["stage"] for e in q1]
    assert stages == sorted(stages)                      # stage-major
    assert {e["stage"] for e in q1} == {"A", "B", "D"}


def test_probe_units_lead_the_first_block_of_f3_large_cells_only():
    cells, exp005_instances, units_of = _toy()
    q = drv.build_queue(cells, units_of, exp005_instances)
    f3 = [e for e in q if e["family"] == "F3_rdd" and e["rep"] == 1]
    assert {f3[0]["unit"], f3[1]["unit"]} == set(drv.PROBE_UNITS)
    assert [e["probe"] for e in f3] == [True, True, False, False, False]
    assert not any(e["probe"] for e in q if e["family"] != "F3_rdd" or e["rep"] > 1)


def test_structural_rule_needs_both_probes_failed():
    queue = [{"queue_index": 1, "probe": True, "family": "F3_rdd", "scale": "large",
              "dataset_seed": 0},
             {"queue_index": 2, "probe": True, "family": "F3_rdd", "scale": "large",
              "dataset_seed": 0}]
    row = lambda ok: {"usable": ok, "event_log_status": "COMPLETE" if ok else "FAILED"}
    assert drv.structural_cells({1: row(False)}, queue) == set()
    assert drv.structural_cells({1: row(False), 2: row(True)}, queue) == set()
    assert drv.structural_cells({1: row(False), 2: row(False)}, queue) == {("F3_rdd", "large", 0)}


def test_failed_twice_counts_executed_consecutive_failures_only():
    cell = ("F3_rdd", "large", 0)
    mk = lambda rep, ok, status="FAILED": {"unit": "B1", "family": cell[0], "scale": cell[1],
                                           "seed": cell[2], "rep": rep, "usable": ok,
                                           "event_log_status": status}
    assert drv.failed_twice({1: mk(1, False), 2: mk(2, False)}, cell, "B1", 3)
    assert not drv.failed_twice({1: mk(1, False), 2: mk(2, True)}, cell, "B1", 3)
    assert not drv.failed_twice({1: mk(1, False)}, cell, "B1", 2)


def test_guards_refuse_cells_outside_the_authorization():
    frozen = {("F1_agg", "large", 3)}
    drv.exp013_guard("F1_agg", "large", 3, frozen=frozen)
    with pytest.raises(drv.SplitAuthorization):
        drv.exp013_guard("F1_agg", "large", 1, frozen=frozen)      # TEST, not authorized
    with pytest.raises(Exception):
        drv.exp013_guard("F1_agg", "small", 0, frozen=frozen)      # TRAIN cell
    with pytest.raises(drv.SplitAuthorization):
        drv.b0prime_guard("F1_agg", "large", 3, frozen=frozen, exp005_instances=set())


def test_real_queue_matches_the_preregistered_fingerprint():
    try:
        ctx = drv.setup()
    except (FileNotFoundError, ValueError) as exc:                  # no bulk data root here
        pytest.skip(f"frozen datasets unavailable: {exc}")
    assert ctx["queue_fp"] == PLAN_QUEUE_FINGERPRINT
    assert len(ctx["cells"]) == 42 and len(ctx["queue"]) == 900
    assert Counter(e["stage"] for e in ctx["queue"]) == {"A": 150, "B": 240, "C": 170, "D": 340}
    for c in ctx["cells"]:
        ident = ctx["identity"][c]
        assert ident["B3"] == "B1" and ident["RL-s1"] == ident["RL-s2"] == "RL"


# ---- analysis on synthetic data with a known answer -------------------------------

def _synthetic():
    """12 cells: 4 F1 (RL == B1 config), 6 F4 (RL 60% slower), 2 F5 (RL ~ B1).
    B0 is 3x slower than B1 everywhere; B4 == B1 within +/-1%."""
    fams = [("F1_agg", "large", s) for s in range(4)] + \
           [("F4_ski", "medium", s) for s in range(3)] + [("F4_ski", "small", s) for s in range(3)] + \
           [("F5_mixed", "large", s) for s in range(2)]
    spec = {"stages": ["A"], "cells": [], "units": {}, "identity_map": {}, "queue": [],
            "authorized_by": "DEC-053", "artifact_id": "synthetic", "code_sha256": {}}
    rows, qi = [], itertools.count(1)
    for idx, (f, sc, sd) in enumerate(fams):
        cell = "%s|%s|s%d" % (f, sc, sd)
        rl_cfg = {"F1_agg": "cfgB1", "F4_ski": "cfgP2", "F5_mixed": "cfgSP32"}[f]
        spec["cells"].append({"cell": cell, "stage": "A"})
        spec["units"][cell] = [{"unit": "B0", "config_fingerprint": "cfgB0"},
                               {"unit": "B1", "config_fingerprint": "cfgB1"},
                               {"unit": "B4", "config_fingerprint": "cfgB1"},
                               {"unit": "RL", "config_fingerprint": rl_cfg}]
        spec["identity_map"][cell] = {"B0": "B0", "B1": "B1", "B3": "B1", "B4": "B4",
                                      "RL-s0": "RL", "RL-s1": "RL", "RL-s2": "RL",
                                      "B2": "UNDEFINED"}
        base = 2.0 + sd
        factor = {"B0": 3.0, "B1": 1.0, "B4": math.exp(0.01 if idx % 2 else -0.01),
                  "RL": 1.6 if f == "F4_ski" else (1.0 if f == "F1_agg" else 0.98)}
        for unit, k in factor.items():
            for rep in range(1, 6):
                i = next(qi)
                spec["queue"].append({"queue_index": i, "stage": "A", "probe": False})
                rows.append({"queue_index": i, "stage": "A", "unit": unit, "family": f,
                             "scale": sc, "seed": sd, "rep": rep, "usable": True,
                             "execution_time_s": base * k * (1 + 0.002 * rep),
                             "event_log_status": "COMPLETE", "error": None})
    return spec, rows


def test_analysis_recovers_the_known_answer():
    spec, rows = _synthetic()
    doc = ana.analyze(spec, rows, "sha", {})
    v = doc["hypotheses"]["verdicts"]
    assert doc["stages_complete"] == ["A"] and doc["n_cells_analysed"] == 12
    assert {a: v[a]["analysed_as"] for a in ana.RL_ARMS} == dict.fromkeys(ana.RL_ARMS, "RL-s0")
    assert all(v[a]["H2"] == "ACCEPTED" for a in ana.RL_ARMS)
    assert all(v[a]["H3"] == "REJECTED" for a in ana.RL_ARMS)
    p = doc["predictions"]
    assert p["P1_H2_accepted_all_RL"] == "AFFIRMED"
    assert p["P2_RL_did_not_beat_static"] == "AFFIRMED"
    assert p["P3_F4_parallelism_pattern"] == "AFFIRMED"
    assert p["P5_AA_identical_configs_within_noise"] == "AFFIRMED"
    assert p["P4_RL_competitive_with_random_search"] != "AFFIRMED"   # F4 deficit is real here
    assert p["P6_F3_large_structural_all_seeds"] == "UNDECIDABLE"     # no probe cells
    t2 = doc["hypotheses"]["tests"]["T2|RL-s0|B3"]
    assert len(t2["cells_a_worse_outside_noise"]) == 6
    assert doc["aa_control"]["B4_vs_B1"]["n"] == 12


def test_analysis_excludes_incomplete_stages_and_short_cells():
    spec, rows = _synthetic()
    spec["stages"] = ["A", "B"]
    spec["queue"].append({"queue_index": 10_000, "stage": "B", "probe": False})
    doc = ana.analyze(spec, rows, "sha", {})
    assert doc["stages_complete"] == ["A"]
    spec2, rows2 = _synthetic()
    for r in rows2:                       # a failed run is a row with usable=false
        if r["unit"] == "RL" and r["family"] == "F4_ski" and r["rep"] == 5:
            r.update(usable=False, execution_time_s=None, event_log_status="FAILED")
    doc2 = ana.analyze(spec2, rows2, "sha", {})
    assert doc2["hypotheses"]["tests"]["T1|RL-s0|B0"]["n_cells"] == 6   # F4 RL incomplete


def test_analysis_flags_code_deviation():
    spec, rows = _synthetic()
    spec["code_sha256"] = {"scripts/analyze_exp013.py": "frozen"}
    doc = ana.analyze(spec, rows, "sha", {"scripts/analyze_exp013.py": "edited"})
    assert doc["analysis_code_deviation"] == {"scripts/analyze_exp013.py": "edited"}
    assert not math.isnan(doc["hypotheses"]["tests"]["T1|RL-s0|B0"]["gmr"]["gmr"])
