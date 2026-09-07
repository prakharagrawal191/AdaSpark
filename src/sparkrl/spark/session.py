"""Spark session creation for AdaSpark.

Responsibilities (plan: M1/M5, DEC-007): build a config-driven local-mode SparkSession,
verify the Spark version matches the frozen backend, attach event-log + local-dir
configuration from path utilities, and stop cleanly. No experiment-specific logic lives
here — this is purely the session layer.
"""
from __future__ import annotations

import logging
import os
import sys
import time

from sparkrl.spark.config import SparkConfig
from sparkrl.utils.paths import eventlog_dir, tmp_dir

logger = logging.getLogger(__name__)


def ensure_pyspark_env() -> None:
    """Point PySpark's driver/worker Python at the current interpreter.

    Required on Windows so local-mode Spark spawns the same venv interpreter.
    """
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


def build_session(config: SparkConfig | None = None,
                  app_suffix: str = "",
                  verify_version: bool = True):
    """Create a SparkSession from a SparkConfig.

    Args:
        config: SparkConfig; defaults to SparkConfig() with built-in defaults.
        app_suffix: optional string appended to the app name (per-instance runs).
        verify_version: assert the running Spark major.minor matches the frozen backend.

    Returns:
        A started SparkSession. Caller is responsible for ``.stop()``.

    Raises:
        RuntimeError: if the Spark version does not match the expected prefix, or if
            session creation fails (e.g. the Windows hadoop/winutils layer is missing).
    """
    cfg = config if config is not None else SparkConfig()
    ensure_pyspark_env()

    from pyspark.sql import SparkSession

    builder = SparkSession.builder
    for key, value in cfg.to_spark_settings().items():
        builder = builder.config(key, value)

    # Event log + local dirs resolve through paths.py (external data root, no literals).
    if cfg.event_log_enabled:
        elog = cfg.event_log_dir if cfg.event_log_dir else str(eventlog_dir(create=True))
        builder = (builder
                   .config("spark.eventLog.enabled", "true")
                   .config("spark.eventLog.dir", elog)
                   .config("spark.eventLog.compress", "false"))
    else:
        builder = builder.config("spark.eventLog.enabled", "false")

    local_dir = cfg.local_dir if cfg.local_dir else str(tmp_dir(create=True))
    builder = builder.config("spark.local.dir", local_dir)

    app_name = cfg.app_name + (f"-{app_suffix}" if app_suffix else "")
    t0 = time.perf_counter()
    spark = builder.appName(app_name).getOrCreate()
    logger.info("SparkSession %s started in %.1fs (appId=%s)",
                spark.version, time.perf_counter() - t0, spark.sparkContext.applicationId)

    if verify_version:
        actual = spark.version
        expected = cfg.expected_spark_version_prefix
        if not actual.startswith(expected):
            spark.stop()
            raise RuntimeError(
                f"Spark version mismatch: running {actual}, expected prefix {expected} "
                f"(frozen backend DEC-007)")

    # Optional micro-job to soak JVM/JIT/class-loading cost (kept out of measurements).
    if cfg.warmup_micro_job:
        spark.range(10).count()

    return spark


def stop_session(spark) -> None:
    """Stop a SparkSession defensively (idempotent, tolerates partial teardown)."""
    if spark is None:
        return
    try:
        spark.stop()
        logger.info("SparkSession stopped (file locks released)")
    except Exception as exc:  # pragma: no cover - best-effort teardown
        logger.warning("SparkSession stop raised %s: %s", type(exc).__name__, exc)