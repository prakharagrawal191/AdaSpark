"""EXP-014 driver queue + pre-registered analysis (DEC-054). No Spark is started."""
from __future__ import annotations

import importlib.util
import itertools
from collections import Counter
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


drv = _load("run_exp014")
ana = _load("analyze_exp014")

pytestmark = [pytest.mark.unit]


def test_queue_blocks_hold_each_condition_once_and_match_rep_counts():
    q = drv.build_queue()
    assert q == drv.build_queue()
    assert len(q) == 3 * sum(drv.REPS_PER_CELL.values()) == 270
    blocks = Counter((e["family"], e["scale"], e["rep"]) for e in q)
    assert set(blocks.values()) == {3}
    for e in q:
        assert sum(1 for x in q if (x["family"], x["scale"], x["rep"]) ==
                   (e["family"], e["scale"], e["rep"]) and x["condition"] == e["condition"]) == 1
    per_cell = Counter((f, s) for f, s, _r in blocks)
    assert dict(per_cell) == drv.REPS_PER_CELL
    assert [e["rep"] for e in q] == sorted(e["rep"] for e in q)          # rep-major
    assert drv.queue_fingerprint(q) == (
        "709d2024a62599466d297c77a6b52178a0f6b238ed787c64852f73d541c13ed9")   # DEC-054 s2


def test_changepoint_screen():
    flat = [1.0 + 0.01 * (-1) ** i for i in range(20)]
    step = flat[:10] + [v + 0.5 for v in flat[10:]]
    assert ana.changepoints(flat) == []
    assert ana.changepoints(step) == [10]
    assert ana.steady_state([2.0] * 3)["status"] == "flat"


def _rows(sysmon_bias: dict[str, float]):
    rows, qi = [], itertools.count(1)
    for (f, s), n in drv.REPS_PER_CELL.items():
        cell = f"{f}|{s}"
        for rep in range(1, n + 1):
            base = 10.0 * (1 + 0.03 * ((rep * 7) % 5))          # common-mode drift
            jitter = 0.002 * (-1) ** rep
            times = {"NO-SYSMON": base, "NEITHER": base * (1 - jitter),
                     "FULL": base * (1 + jitter + sysmon_bias.get(cell, 0.0))}
            for cond, t in times.items():
                rows.append({"queue_index": next(qi), "family": f, "scale": s, "rep": rep,
                             "condition": cond, "timing_valid": True, "execution_time_s": t})
    return rows


def _spec():
    return {"authorized_by": "DEC-054", "artifact_id": "synthetic", "code_sha256": {}}


def test_zero_overhead_passes_everywhere():
    doc = ana.analyze(_spec(), _rows({}), "sha", {})
    assert len(doc["cells"]) == 7
    for c in doc["cells"].values():
        assert c["components"]["sysmon"]["verdict"] == "PASS"
        assert c["components"]["eventlog"]["verdict"] == "PASS"
        # the common-mode drift cancels in the paired statistic
        assert abs(c["components"]["sysmon"]["paired_median_pct"]) < 0.5
    assert doc["predictions"]["Q1_sysmon_overhead_below_5pct_on_6_of_7"] == "AFFIRMED"
    assert doc["predictions"]["Q2_eventlog_overhead_below_5pct_on_6_of_7"] == "AFFIRMED"


def test_a_real_overhead_is_failed_not_hidden():
    doc = ana.analyze(_spec(), _rows({"F2_join|small": 0.10}), "sha", {})
    assert doc["cells"]["F2_join|small"]["components"]["sysmon"]["verdict"] == "FAIL"
    assert doc["predictions"]["Q1_sysmon_overhead_below_5pct_on_6_of_7"] == "REFUTED"
    assert doc["predictions"]["Q2_eventlog_overhead_below_5pct_on_6_of_7"] == "AFFIRMED"
