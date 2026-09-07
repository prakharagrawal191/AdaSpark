"""Unit tests for runner utilities: CV stats, RunResult serialization, timeout."""
from __future__ import annotations

import time

import pytest

from sparkrl.spark.runner import RunResult, run_with_timeout
from sparkrl.utils.stats import timing_stats

pytestmark = [pytest.mark.unit]


def test_cv_calculation():
    st = timing_stats([10.0, 10.0, 10.0])
    assert st["cv"] == 0.0
    st2 = timing_stats([10.0, 11.0, 12.0])
    assert st2["mean_s"] == 11.0
    # sample std (ddof=1) of [10,11,12] is 1.0 -> CV = 1/11, rounded to 4 dp by timing_stats
    assert st2["cv"] == pytest.approx(round(1.0 / 11.0, 4), abs=1e-6)


def test_cv_empty_and_single():
    assert timing_stats([])["cv"] is None
    assert timing_stats([5.0])["cv"] == 0.0


def test_runresult_to_dict_roundtrip():
    r = RunResult(success=True, execution_time=1.5, warmup_time=2.0, total_time=3.5,
                  timeout=False, error=None, spark_app_id="local-1",
                  config_fingerprint="fp", workload_id="wl", timestamp="t",
                  checksum={"g": 100}, measurements={"shuffle_mb": 5})
    d = r.to_dict()
    assert d["success"] is True
    assert d["execution_time_s"] == 1.5
    assert d["checksum"] == {"g": 100}
    assert d["measurements"] == {"shuffle_mb": 5}


def test_run_with_timeout_completes():
    box = run_with_timeout(lambda: "done", timeout_seconds=5.0)
    assert box["timed_out"] is False
    assert box["value"] == "done"
    assert box["error"] is None


def test_run_with_timeout_fires():
    def slow():
        time.sleep(5.0)
        return "late"

    cancelled = {"called": False}

    def cancel():
        cancelled["called"] = True

    box = run_with_timeout(slow, timeout_seconds=0.2, grace_seconds=0.1,
                           cancel_fn=cancel)
    assert box["timed_out"] is True
    assert cancelled["called"] is True
    assert "timed out" in box["error"]


def test_run_with_timeout_captures_exception():
    def boom():
        raise ValueError("boom")

    box = run_with_timeout(boom, timeout_seconds=5.0)
    assert box["timed_out"] is False
    assert "ValueError" in box["error"]