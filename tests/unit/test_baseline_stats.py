"""Unit tests for the Day-17 B0 baseline helpers (stats + run-id unicity).

These use pure Python helpers only — no Spark, no datasets — so they run in
the ``unit`` marker set.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_baseline.py"
_spec = importlib.util.spec_from_file_location("run_baseline", _SCRIPT)
assert _spec and _spec.loader
run_baseline = importlib.util.module_from_spec(_spec)
sys.modules["run_baseline"] = run_baseline
_spec.loader.exec_module(run_baseline)


def test_stats_empty():
    s = run_baseline._stats([])
    assert s == {"n": 0, "min": None, "max": None, "mean": None,
                 "median": None, "std": None, "cv": None}


def test_stats_single():
    s = run_baseline._stats([10.0])
    assert s["n"] == 1 and s["mean"] == 10.0 and s["std"] == 0.0 and s["cv"] == 0.0


def test_stats_multi_ddof1():
    # [2,4,4,4,5,5,7,9] -> mean=5.0; ss=32, df=7 -> std=sqrt(32/7)=2.1381, cv=0.4276
    s = run_baseline._stats([2, 4, 4, 4, 5, 5, 7, 9])
    assert s["mean"] == pytest.approx(5.0)
    assert s["median"] == pytest.approx(4.5)
    assert s["std"] == pytest.approx((32 / 7) ** 0.5, abs=1e-3)  # rounded to 4dp
    assert s["cv"] == pytest.approx((32 / 7) ** 0.5 / 5.0, abs=1e-3)
    assert s["min"] == 2.0 and s["max"] == 9.0


def test_stats_zero_mean_cv_none():
    s = run_baseline._stats([0.0, 0.0, 0.0])
    assert s["mean"] == 0.0 and s["cv"] is None


def test_summary_only_usable_runs():
    runs = [
        {"family": "F1_agg", "scale": "small", "seed": 0, "rep": 1, "usable": True,
         "execution_time_s": 1.0, "shuffle_read_bytes": 10, "shuffle_write_bytes": 5,
         "memory_spill_bytes": 1, "disk_spill_bytes": 2, "task_duration_cv": 0.5,
         "stage_count": 4, "task_count": 100},
        {"family": "F1_agg", "scale": "small", "seed": 0, "rep": 2, "usable": True,
         "execution_time_s": 3.0, "shuffle_read_bytes": 10, "shuffle_write_bytes": 5,
         "memory_spill_bytes": 1, "disk_spill_bytes": 2, "task_duration_cv": 0.6,
         "stage_count": 4, "task_count": 100},
        {"family": "F1_agg", "scale": "small", "seed": 0, "rep": 3, "usable": False,
         "execution_time_s": 99.0, "shuffle_read_bytes": 0, "shuffle_write_bytes": 0,
         "memory_spill_bytes": 0, "disk_spill_bytes": 0, "task_duration_cv": None,
         "stage_count": 0, "task_count": 0},
    ]
    s = run_baseline.summarize(runs)
    cond = s["F1_agg|small"]
    assert cond["n"] == 2
    assert cond["execution_time_s"]["median"] == pytest.approx(2.0)
    assert cond["spill_bytes_median"] == pytest.approx(3.0)
    assert cond["task_duration_cv_median"] == pytest.approx(0.55)
    assert cond["seeds"] == [0]