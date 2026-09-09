"""Integration: generate micro orders -> Parquet -> Spark read + checksum (Day 13).

Tiny fixture only (2k rows). NOT a research experiment.
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

from sparkrl.datagen.checksums import build_manifest  # noqa: E402
from sparkrl.datagen.generator import GenerationSpec  # noqa: E402
from sparkrl.datagen.rows import orders_row  # noqa: E402
from sparkrl.datagen.schema import column_names  # noqa: E402
from sparkrl.datagen.validate import full_validation  # noqa: E402
from sparkrl.datagen.writer import generate_table  # noqa: E402
from sparkrl.utils.paths import tmp_dir  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    from pyspark.sql import SparkSession

    tdir = tmp_dir(create=True) / "pytest-datagen"
    session = (SparkSession.builder.master("local[2]")
               .appName("sparkrl-pytest-datagen")
               .config("spark.driver.memory", "2g")
               .config("spark.ui.enabled", "false")
               .config("spark.local.dir", str(tdir))
               .getOrCreate())
    yield session
    session.stop()


def test_generate_write_read_validate(spark, tmp_path):
    spec = GenerationSpec(table="orders", scale="micro", rows=2000, seed=7,
                          skew=1.0, key_cardinality=500, chunk_rows=500)
    out = tmp_path / "orders-micro"
    info = generate_table(spark, spec, out)
    assert info["row_count"] == 2000
    assert info["file_count"] == 4  # 2000 / 500
    df = spark.read.parquet(str(out / "data"))
    assert df.count() == 2000
    assert df.columns == column_names("orders")
    assert df.filter("cust_key < 0 OR cust_key >= 500").count() == 0
    manifest = build_manifest("orders-micro-s7", spec, info["checksum"],
                              info["file_count"], info["total_bytes"],
                              code_version="pytest")
    assert full_validation(spec, info["checksum"], manifest) == []
    expect = __import__("sparkrl.datagen.checksums",
                        fromlist=["checksum_rows"]).checksum_rows(
        orders_row(i, spec) for i in range(2000))["fnv1a_hex"]
    assert info["checksum"] == expect
