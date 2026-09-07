"""Integration smoke test: real local-mode Spark (marked ``integration``).

Run explicitly with:  python -m pytest -m integration
Skipped automatically when PySpark is unavailable or SPARKRL_SKIP_SPARK=1.
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

from sparkrl.utils.paths import tmp_dir  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    from pyspark.sql import SparkSession

    tdir = tmp_dir(create=True) / "pytest"
    session = (SparkSession.builder.master("local[2]")
               .appName("sparkrl-pytest")
               .config("spark.driver.memory", "2g")
               .config("spark.ui.enabled", "false")
               .config("spark.local.dir", str(tdir))
               .getOrCreate())
    yield session
    session.stop()


def test_spark_version_is_4_x(spark):
    assert spark.version.startswith("4."), f"unexpected Spark version: {spark.version}"


def test_parquet_roundtrip(spark):
    out = tmp_dir() / "pytest" / "parquet_roundtrip"
    spark.range(50_000).write.mode("overwrite").parquet(str(out))
    assert spark.read.parquet(str(out)).count() == 50_000
