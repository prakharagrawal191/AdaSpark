"""Reusable Spark execution runner with warm-up, timing, and timeout enforcement.

Conceptual flow (plan §11, §21):
    prepare → warm-up → execute → measure → timeout? → cleanup → RunResult

Design decisions:
- Timed measurement covers ONLY the workload execution (``run()`` call), never session
  startup or warm-up. This separates startup variability from job variability (Day-3 §10).
- Warm-up runs are executed and discarded (their results are materialized so the query is
  really executed, not just planned).
- Timeout is enforced with a daemon thread plus Spark's job-group cancellation, which is
  SAFE (cancels only this job group) and does not kill unrelated processes (Day-3 §6).

Windows timeout limitation (documented): a stuck Python thread cannot be forcibly killed
on Windows. After ``cancelJobGroup`` we wait ``grace_seconds``; if the thread still runs we
report ``thread_cancelled_late=True`` and leave it as a daemon thread (does not block exit).
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

ExecutionFn = Callable[[], Any]


@dataclass
class RunResult:
    """Structured result of one timed workload execution."""

    success: bool
    execution_time: float            # seconds, workload.run() only (warm-up excluded)
    warmup_time: float               # seconds aggregated across warm-up runs
    total_time: float                # seconds, warm-up + execution + cleanup
    timeout: bool
    error: str | None
    spark_app_id: str | None
    config_fingerprint: str
    workload_id: str
    timestamp: str
    checksum: Any | None = None
    thread_cancelled_late: bool = False
    measurements: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable manifest row (used by scripts + future experiment runner)."""
        return {
            "success": self.success,
            "execution_time_s": round(self.execution_time, 4),
            "warmup_time_s": round(self.warmup_time, 4),
            "total_time_s": round(self.total_time, 4),
            "timeout": self.timeout,
            "error": self.error,
            "spark_app_id": self.spark_app_id,
            "config_fingerprint": self.config_fingerprint,
            "workload_id": self.workload_id,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
            "thread_cancelled_late": self.thread_cancelled_late,
            "measurements": self.measurements,
        }
def run_with_timeout(fn: ExecutionFn, timeout_seconds: float,
                     grace_seconds: float = 10.0,
                     cancel_fn: Callable[[], None] | None = None) -> dict[str, Any]:
    """Execute ``fn`` with a wall-clock timeout using a daemon thread.

    Returns a dict: ``{"value": ..., "timed_out": bool, "error": ..., "late": bool}``.
    On timeout, ``cancel_fn()`` (typically ``cancelJobGroup``) is invoked and the thread is
    given ``grace_seconds`` to finish before we give up on joining it.
    """
    box: dict[str, Any] = {"value": None, "error": None, "timed_out": False, "late": False}

    def _target() -> None:
        try:
            box["value"] = fn()
        except Exception as exc:  # noqa: BLE001 - captured for the caller
            box["error"] = f"{type(exc).__name__}: {exc}"

    worker = threading.Thread(target=_target, name="sparkrl-timed-run", daemon=True)
    worker.start()
    worker.join(timeout_seconds)

    if worker.is_alive():
        box["timed_out"] = True
        if cancel_fn is not None:
            try:
                cancel_fn()
            except Exception as exc:  # pragma: no cover
                logger.warning("cancel_fn raised %s: %s", type(exc).__name__, exc)
        worker.join(grace_seconds)
        box["late"] = worker.is_alive()
        box["error"] = f"execution timed out after {timeout_seconds:.1f}s"
    return box


def run_workload(spark, workload, config) -> RunResult:
    """Execute a workload through the common harness.

    ``spark``: an active SparkSession.
    ``workload``: object exposing ``.workload_id`` and ``.run(spark, config)``.
    ``config``: the SparkConfig used for this run (fingerprint + timeout + warm-up policy).
    """
    start = time.perf_counter()
    app_id = spark.sparkContext.applicationId
    job_group = f"{workload.workload_id}-{app_id}-{time.time_ns()}"

    # --- warm-up (discarded, materialized) ------------------------------------
    warmup_t0 = time.perf_counter()
    for i in range(config.warmup_runs):
        spark.sparkContext.setJobGroup(f"{job_group}-warm{i}",
                                       f"warm-up {i} of {workload.workload_id}",
                                       interruptOnCancel=True)
        try:
            workload.run(spark, config)
        except Exception as exc:  # noqa: BLE001
            logger.warning("warm-up run %d failed (%s); continuing to timed run", i, exc)
    warmup_s = time.perf_counter() - warmup_t0

    # --- timed execution (with timeout) --------------------------------------
    spark.sparkContext.setJobGroup(f"{job_group}-timed", workload.workload_id,
                                   interruptOnCancel=True)
    exec_t0 = time.perf_counter()

    def _run() -> Any:
        return workload.run(spark, config)

    timeout_box = run_with_timeout(
        _run,
        timeout_seconds=config.timeout_seconds,
        grace_seconds=config.timeout_grace_seconds,
        cancel_fn=lambda: spark.sparkContext.cancelJobGroup(f"{job_group}-timed"),
    )
    exec_s = time.perf_counter() - exec_t0

    if timeout_box["timed_out"]:
        return RunResult(
            success=False, execution_time=exec_s, warmup_time=warmup_s,
            total_time=time.perf_counter() - start, timeout=True,
            error=timeout_box["error"], spark_app_id=app_id,
            config_fingerprint=config.fingerprint(), workload_id=workload.workload_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            thread_cancelled_late=timeout_box["late"])

    if timeout_box["error"] is not None:
        return RunResult(
            success=False, execution_time=exec_s, warmup_time=warmup_s,
            total_time=time.perf_counter() - start, timeout=False,
            error=timeout_box["error"], spark_app_id=app_id,
            config_fingerprint=config.fingerprint(), workload_id=workload.workload_id,
            timestamp=datetime.now(timezone.utc).isoformat())

    checksum, measurements = _extract(workload, timeout_box["value"])
    return RunResult(
        success=True, execution_time=exec_s, warmup_time=warmup_s,
        total_time=time.perf_counter() - start, timeout=False, error=None,
        spark_app_id=app_id, config_fingerprint=config.fingerprint(),
        workload_id=workload.workload_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checksum=checksum, measurements=measurements)


def _extract(workload, value: Any) -> tuple[Any, dict[str, Any]]:
    """Extract (checksum, measurements) from a workload return value.

    Supports workloads returning a small dataclass-like object with ``checksum`` and/or
    ``measurements`` attributes, or a plain value (used as checksum directly).
    """
    if value is None:
        return None, {}
    checksum = getattr(value, "checksum", value)
    measurements = getattr(value, "measurements", None) or {}
    return checksum, dict(measurements)