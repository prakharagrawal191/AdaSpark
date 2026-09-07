"""Integration tests (Day 3): session module + baseline workload via the runner.

Requires the frozen backend (DEC-007): pyspark 3.5.9 / Java 17 / winutils on native
Windows. Run with:  python -m pytest -m integration
"""
from __future__ import annotations

import os
import sys

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("SPARKRL_SKIP_SPARK") == "1",
                       reason="SPARKRL_SKIP_SPARK=1"),
]
pytest.importorskip("pyspark", reason="PySpark not installed")

from sparkrl.spark import session as spark_session  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.spark.runner import run_workload  # noqa: E402
from sparkrl.workloads.baseline import BaselineWorkload  # noqa: E402

BASE = SparkConfig.from_dict({
    "runtime": {"master": "local[2]", "driver_memory": "2g",
                "expected_spark_version_prefix": "3.5", "ui_enabled": False},
    "execution": {"warmup_micro_job": False, "warmup_runs": 1,
                  "timeout_seconds": 120.0},
    "workload": {"baseline_rows": 100_000, "baseline_scale": "micro", "seed": 1},
})


@pytest.fixture(scope="module")
def session():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    s = spark_session.build_session(BASE, app_suffix="day03-pytest")
    yield s
    spark_session.stop_session(s)


def test_session_version_and_config_applied(session):
    assert session.version.startswith("3.5.")
    applied = session.conf.get("spark.sql.shuffle.partitions")
    assert applied == "200"


def test_baseline_workload_matches_reference(session):
    wl = BaselineWorkload(rows=50_000, seed=7)
    result = wl.run(session, BASE)
    ref = wl.reference_check(50_000)
    assert result.group_count == ref.group_count == 1000
    assert abs(result.checksum_value - ref.checksum_value) < 1e-6


def test_runner_executes_workload(session):
    wl = BaselineWorkload(rows=50_000, seed=7)
    r = run_workload(session, wl, BASE)
    assert r.success is True
    assert r.timeout is False
    assert r.execution_time > 0
    assert r.warmup_time > 0            # warmup_runs=1 was set
    assert r.total_time >= r.execution_time
    assert r.spark_app_id.startswith("local-")
    assert len(r.config_fingerprint) == 64
    assert r.workload_id == "baseline_agg_v1"
    assert r.checksum["group_count"] == 1000