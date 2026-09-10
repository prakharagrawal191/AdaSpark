"""Integration: Spark run -> event log -> parser -> RuntimeMetrics (Day 16).

Runs one tiny deterministic Spark job through the frozen session layer with
event logging enabled, then parses the produced event log and asserts the
Step-19 checklist. No large workloads, no tuning, no reward.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sparkrl.monitoring import (build_runtime_metrics, find_event_log,
                                parse_event_log, validate_metrics,)
from sparkrl.spark.config import SparkConfig
from sparkrl.spark.session import build_session, stop_session

pytestmark = pytest.mark.integration


def _tiny_workload(spark):
    """Small deterministic job with a real shuffle (groupBy)."""
    from pyspark.sql import functions as F
    df = spark.range(0, 20_000).withColumn(
        "k", (F.col("id") * 37 + 59) % 50)
    out = df.groupBy("k").agg(F.count("*").alias("n"))
    rows = out.orderBy("k").collect()
    assert len(rows) == 50
    assert sum(r["n"] for r in rows) == 20_000
    return [r["k"] for r in rows]


def test_spark_run_to_runtime_metrics():
    from sparkrl.utils.paths import eventlog_dir  # frozen default location

    with tempfile.TemporaryDirectory(prefix="sparkrl-elog-") as tmp:
        cfg = SparkConfig(event_log_dir=tmp, warmup_micro_job=False)
        spark = build_session(cfg, app_suffix="monitoring-int")
        try:
            app_id = spark.sparkContext.applicationId
            keys = _tiny_workload(spark)
            assert keys == sorted(keys)
        finally:
            stop_session(spark)

        log_path = find_event_log(tmp, app_id)
        assert log_path is not None, "event log for the app not found"

        parsed = parse_event_log(log_path)
        assert parsed.status.value == "COMPLETE"
        assert parsed.application_id == app_id

        metrics = build_runtime_metrics(None, parsed, run_id="monitoring-int")
        assert metrics.event_log_status == "COMPLETE"
        assert metrics.execution_time_source == "event_log"
        assert metrics.execution_time_s is not None and metrics.execution_time_s > 0
        assert metrics.stage_count and metrics.stage_count > 0
        assert metrics.task_count and metrics.task_count > 0
        assert metrics.failed_task_count == 0
        # shuffle happened (groupBy) -> write bytes > 0; spill not required
        assert metrics.shuffle_write_bytes > 0
        assert metrics.task_duration_mean_s is not None
        assert metrics.task_duration_cv is not None  # defined (mean > 0)
        assert validate_metrics(metrics) == []
        # serialization round-trip
        from sparkrl.monitoring.schemas import RuntimeMetrics
        assert RuntimeMetrics.from_dict(metrics.to_dict()) == metrics
