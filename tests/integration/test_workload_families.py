"""Integration: all five families on small/seed-0 via the shared harness.

Requires the frozen backend (DEC-007) + Day-14 datasets. One module-scoped
Spark session; each family resolves its own dataset, runs through the
Day-3 runner (warm-up + timing + timeout), validates, and checks the
manifest-relevant fields (family/scale/seed/fingerprints/signature).
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
from sparkrl.workloads.registry import REGISTRY, get_workload  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

BASE = SparkConfig.from_dict({
    "runtime": {"master": "local[2]", "driver_memory": "2g",
                "expected_spark_version_prefix": "3.5", "ui_enabled": False},
    "execution": {"warmup_micro_job": False, "warmup_runs": 1,
                  "timeout_seconds": 600.0},
    "workload": {"baseline_rows": 100_000, "baseline_scale": "small",
                 "seed": 1},
})


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    s = spark_session.build_session(BASE, app_suffix="day15-pytest")
    yield s
    spark_session.stop_session(s)


@pytest.mark.parametrize("family", sorted(REGISTRY))
def test_family_small_seed0_end_to_end(spark, family):
    resolved = resolve_dataset(family, "small", 0)
    workload = get_workload(family, "small", 0)
    assert resolved.family == family
    if family == "F4_ski":
        assert abs(resolved.skew - 1.5) < 1e-12
    else:
        assert abs(resolved.skew - 1.0) < 1e-12
    run_result = run_workload(spark, workload, BASE)
    assert run_result.success is True, run_result.error
    assert run_result.timeout is False
    payload = run_result.checksum
    assert hasattr(payload, "result_signature")
    assert payload.family == family
    assert payload.scale == "small" and payload.seed == 0
    assert payload.dataset_id == resolved.physical_id
    assert payload.dataset_fingerprint == resolved.dataset_fingerprint
    assert payload.schema_fingerprint == resolved.schema_fingerprint
    assert len(payload.result_signature) == 16
    assert workload.validate(payload) is True
