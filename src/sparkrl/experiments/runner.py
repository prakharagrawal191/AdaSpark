"""EXP-002 orchestration: a thin, resumable queue over the existing run pipeline.

This module deliberately owns ONLY experiment-level concerns:

    queue order | resume / skip | atomic immutable manifests | attempt log |
    configuration application + read-back verification | validity bookkeeping

It owns NO measurement semantics. Session creation, warm-up, timed execution and
timeout are ``sparkrl.spark.session`` / ``sparkrl.spark.runner`` (Day 3). Event-log
parsing is ``sparkrl.monitoring.eventlog_parser`` (Day 18). Metric merging and the
``usable`` definition are ``sparkrl.monitoring.merge`` (Day 19). ``execution_time_s``
is the runner clock, warm-up excluded, exactly as frozen on Day 3.

Note on provenance: PLAN days 20-21 (experiment runner v1 + hardening) were never
committed - HEAD is the Day-18 parser commit - so the queue/resume/manifest layer
those days would have delivered is provided here at EXP-002 scope. See
docs/research/EXP002_CONFIGURATION_SENSITIVITY_AUDIT.md, "Dependency deviation".

Validity
--------
A measured observation is VALID iff ``RunMetrics.usable`` is true, i.e. the run
succeeded, an execution time exists, the Spark event log parsed as COMPLETE
(LogStart + ApplicationEnd) and the workload produced a result signature. Every
other outcome is recorded explicitly as FAILED or INCOMPLETE and is never counted
as a normal measurement.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from sparkrl.experiments.grid import assert_b0_unchanged, grid_fingerprint
from sparkrl.experiments.spec import (EXPERIMENT_ID, ExperimentSpec, RunSpec,
                                      assert_train_only,)
from sparkrl.monitoring import (RunMetrics, SamplerConfig, SystemSampler,
                                build_runtime_metrics, find_event_log,
                                merge_run_metrics, parse_event_log,)
from sparkrl.monitoring.schemas import RuntimeMetrics
from sparkrl.spark import runner as spark_runner
from sparkrl.spark import session as spark_session
from sparkrl.utils.paths import eventlog_dir
from sparkrl.workloads.registry import REGISTRY
from sparkrl.workloads.resolver import resolve_dataset

RECORD_SCHEMA_VERSION = "exp002-run/v1"

COMPLETED = "COMPLETED"     # valid measured observation (metrics.usable is true)
INCOMPLETE = "INCOMPLETE"   # ran, but provenance/metrics incomplete -> retryable
FAILED = "FAILED"           # error or timeout -> retryable
SKIPPED = "SKIPPED"         # an immutable COMPLETED record already existed


def _clock() -> str:
    return datetime.now(timezone.utc).isoformat()


def code_version() -> str:
    """Short git description of the working tree (provenance, best effort)."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10)
        if sha.returncode != 0:
            return "unknown"
        tag = sha.stdout.strip()
        return f"{tag}-dirty" if dirty.stdout.strip() else tag
    except Exception:  # noqa: BLE001 - provenance must never fail a run
        return "unknown"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically (temp file + os.replace) so no partial manifest exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append-only attempt log: every attempt is kept, including failures."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def read_record(path: Path) -> dict[str, Any] | None:
    """Read an existing run record, or None if absent/unreadable."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def record_status(record: dict[str, Any] | None) -> str | None:
    return record.get("status") if record else None


def is_completed(record: dict[str, Any] | None) -> bool:
    """A completed record is immutable and must never be re-run or overwritten."""
    if not record:
        return False
    return (record.get("status") == COMPLETED
            and bool((record.get("metrics") or {}).get("usable")))


@dataclass
class RunOutcome:
    """What happened to one planned run in this pass."""

    run_spec: RunSpec
    status: str
    record: dict[str, Any]
    executed: bool

    @property
    def valid(self) -> bool:
        """True when this run is a valid measured observation.

        A SKIPPED run is valid too: it was skipped precisely because an immutable
        COMPLETED record already exists for it.
        """
        if self.status == COMPLETED:
            return True
        return self.status == SKIPPED and is_completed(self.record)


class QueueLock:
    """Exclusive lock over one EXP-002 result root.

    Two runners on one machine would contend for the same cores and silently
    contaminate every timing measured during the overlap - and could race on the
    same manifest path. This is a timing experiment, so that must be impossible
    rather than merely discouraged.
    """

    def __init__(self, result_root: Path) -> None:
        self.path = result_root / ".queue.lock"
        self._fd: int | None = None

    def acquire(self) -> "QueueLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            holder = ""
            try:
                holder = self.path.read_text(encoding="utf-8").strip()
            except OSError:
                pass
            raise RuntimeError(
                f"another EXP-002 runner holds {self.path} ({holder or 'unknown'}). "
                f"Concurrent runs contaminate timing measurements. Wait for it to "
                f"finish, or delete the lock file if it is stale.") from None
        os.write(fd, f"pid={os.getpid()} started={_clock()}".encode("utf-8"))
        self._fd = fd
        return self

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            self.path.unlink()
        except OSError:
            pass

    def __enter__(self) -> "QueueLock":
        return self.acquire()

    def __exit__(self, *exc: Any) -> bool:
        self.release()
        return False


def _failure_metrics(run_id: str, run_result: Any | None,
                     event_log_status: str) -> RuntimeMetrics:
    """Minimal RuntimeMetrics for a failed/incomplete run. Nothing is fabricated."""
    exec_s = None
    source = None
    # A timed-out run's "execution_time" is the timeout ceiling, not a measurement of
    # the workload. Storing it would make a 900 s ceiling look byte-identical to a
    # 900 s observation to any downstream reader, so it is left None.
    timed_out = bool(getattr(run_result, "timeout", False))
    if (run_result is not None and not timed_out
            and getattr(run_result, "execution_time", None)):
        exec_s = float(run_result.execution_time)
        source = "runner"
    return RuntimeMetrics(run_id=run_id,
                          application_id=getattr(run_result, "spark_app_id", None),
                          execution_time_s=exec_s,
                          execution_time_source=source,
                          event_log_status=event_log_status)


def _applied_settings(spark) -> dict[str, Any]:
    """Read the configuration BACK from the live session.

    A sensitivity study is worthless if the configuration silently fails to apply,
    and a silent no-op would look exactly like insensitivity. These values are
    recorded per run and cross-checked against the requested grid point.
    """
    def _get(key: str) -> str | None:
        try:
            return spark.conf.get(key)
        except Exception:  # noqa: BLE001 - unset keys raise in Spark
            return None

    try:
        default_parallelism = int(spark.sparkContext.defaultParallelism)
    except Exception:  # noqa: BLE001
        default_parallelism = None
    return {
        "spark.master": _get("spark.master"),
        "spark.sql.shuffle.partitions": _get("spark.sql.shuffle.partitions"),
        "spark.default.parallelism": _get("spark.default.parallelism"),
        "spark.sql.adaptive.enabled": _get("spark.sql.adaptive.enabled"),
        "spark.driver.memory": _get("spark.driver.memory"),
        "sc.defaultParallelism": default_parallelism,
    }


def verify_applied(run_spec: RunSpec, applied: dict[str, Any]) -> list[str]:
    """Return mismatches between the requested grid point and the live session."""
    problems: list[str] = []
    point = run_spec.config
    if applied.get("spark.master") != point.master:
        problems.append(f"master: requested {point.master!r}, "
                        f"session reports {applied.get('spark.master')!r}")
    want_sp = str(point.shuffle_partitions)
    if applied.get("spark.sql.shuffle.partitions") != want_sp:
        problems.append(
            f"shuffle.partitions: requested {want_sp}, session reports "
            f"{applied.get('spark.sql.shuffle.partitions')!r}")
    got_aqe = str(applied.get("spark.sql.adaptive.enabled")).lower()
    if got_aqe != "false":
        problems.append(f"AQE must be OFF, session reports {got_aqe!r}")
    # Checked for EVERY point, including B0. B0 declares default_parallelism=None
    # ("leave it to Spark"), whose correct local-mode value is N from local[N]; not
    # checking it is what let a stale JVM-level value leak into B0 unnoticed.
    want_dp = str(point.effective_default_parallelism())
    if applied.get("spark.default.parallelism") != want_dp:
        problems.append(
            f"default.parallelism: requires {want_dp}, session reports "
            f"{applied.get('spark.default.parallelism')!r}")
    if str(applied.get("sc.defaultParallelism")) != want_dp:
        problems.append(
            f"sc.defaultParallelism: requires {want_dp}, session reports "
            f"{applied.get('sc.defaultParallelism')!r}")
    return problems


def execute_run(run_spec: RunSpec, base_config, *,
                sysmon_enabled: bool = True,
                version: str | None = None,
                split_guard: Callable[[str, str, int], None] = assert_train_only,
                ) -> tuple[RunMetrics, dict[str, Any]]:
    """Execute exactly one measured observation. Returns (metrics, provenance).

    Raises nothing for workload/Spark failures: those surface as a RunMetrics with
    ``usable=False``. Only programming/environment errors propagate.

    ``split_guard`` is the split authorization applied BEFORE anything runs. It
    defaults to ``assert_train_only``, so every pre-existing caller keeps exactly
    the TRAIN-only behaviour it had; the default is pinned by a unit test. DEC-013
    (Model B) authorizes the EXP-003 calibration stage to pass
    ``sparkrl.evaluation.spec.authorize_validation_cell`` instead, which admits
    VALIDATION cells and nothing else. No guard admits TEST: the test split stays
    sealed behind ``TestSplitSealed`` until EXP-005/006.
    """
    split_guard(run_spec.family, run_spec.scale, run_spec.seed)

    cfg = run_spec.config.apply_to(base_config).with_overrides(
        timeout_seconds=run_spec.timeout_seconds)
    if cfg.aqe_enabled:
        raise RuntimeError("AQE became enabled after config application (PLAN section 7)")

    resolved = resolve_dataset(run_spec.family, run_spec.scale, run_spec.seed)
    workload = REGISTRY[run_spec.family](scale=run_spec.scale, seed=run_spec.seed)

    provenance: dict[str, Any] = {
        "code_version": version or code_version(),
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "workload_version": workload.workload_version,
        "spark_config_fingerprint": cfg.fingerprint(),
        "applied_settings": None,
        "applied_mismatches": [],
        "event_log_path": None,
        "wall_started_utc": _clock(),
    }

    sampler = SystemSampler(SamplerConfig(enabled=sysmon_enabled)).start()
    spark = None
    run_result = None
    spark_version = None
    try:
        spark = spark_session.build_session(
            cfg, app_suffix=f"exp002-{run_spec.run_id}")
        spark_version = spark.version
        applied = _applied_settings(spark)
        provenance["applied_settings"] = applied
        provenance["applied_mismatches"] = verify_applied(run_spec, applied)
        run_result = spark_runner.run_workload(spark, workload, cfg)
    finally:
        spark_session.stop_session(spark)
        sampler.stop()
    provenance["wall_finished_utc"] = _clock()
    system = sampler.summary()

    app_id = run_result.spark_app_id if run_result else None
    runtime: RuntimeMetrics
    if run_result is not None and run_result.success:
        event_log_path = find_event_log(eventlog_dir(), app_id)
        if event_log_path is None:
            runtime = _failure_metrics(run_spec.run_id, run_result, "MISSING")
        else:
            provenance["event_log_path"] = str(event_log_path)
            parsed = parse_event_log(event_log_path)
            try:
                runtime = build_runtime_metrics(run_result, parsed,
                                                run_id=run_spec.run_id)
            except ValueError:
                # INCOMPLETE / MALFORMED: keep diagnostics, never claim validity.
                runtime = build_runtime_metrics(run_result, parsed,
                                                run_id=run_spec.run_id,
                                                include_incomplete=True)
    else:
        status = "MISSING"
        if app_id is not None:
            path = find_event_log(eventlog_dir(), app_id)
            if path is not None:
                provenance["event_log_path"] = str(path)
                status = parse_event_log(path).status.value
        runtime = _failure_metrics(run_spec.run_id, run_result, status)

    metrics = merge_run_metrics(
        run_id=run_spec.run_id, workload=workload, dataset=resolved,
        run_result=run_result, runtime=runtime, system=system,
        code_version=provenance["code_version"], timestamp=_clock())
    metrics.spark_version = spark_version
    metrics.event_log_path = provenance["event_log_path"]
    if runtime.memory_spill_bytes is not None and runtime.disk_spill_bytes is not None:
        metrics.total_spill_bytes = (runtime.memory_spill_bytes
                                     + runtime.disk_spill_bytes)

    provenance["thread_cancelled_late"] = bool(
        getattr(run_result, "thread_cancelled_late", False))

    # A configuration that did not actually apply can never be a valid observation
    # of that configuration, however cleanly the job ran.
    if provenance["applied_mismatches"]:
        metrics.usable = False
        detail = "; ".join(provenance["applied_mismatches"])
        metrics.error = ((metrics.error + " | ") if metrics.error else "") + \
            f"configuration not applied: {detail}"

    # The authoritative timing is the Day-3 runner clock. If a valid-looking run ever
    # carried the event-log wall clock instead, it would silently change what
    # execution_time_s means, so it is refused rather than quietly accepted.
    if metrics.usable and metrics.execution_time_s is not None:
        if metrics.execution_time_source != "runner":
            metrics.usable = False
            metrics.error = ((metrics.error + " | ") if metrics.error else "") + (
                f"execution_time_source is {metrics.execution_time_source!r}, not the "
                f"authoritative runner clock")
    return metrics, provenance


def build_record(spec: ExperimentSpec, run_spec: RunSpec, metrics: RunMetrics,
                 provenance: dict[str, Any], attempt: int) -> dict[str, Any]:
    """Assemble the immutable run record written to disk."""
    if metrics.usable:
        status = COMPLETED
    elif metrics.error or metrics.timeout or not metrics.success:
        status = FAILED
    else:
        status = INCOMPLETE
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "spec_fingerprint": spec.fingerprint(),
        "grid_fingerprint": grid_fingerprint(spec.grid),
        "status": status,
        "attempt": attempt,
        "run_spec": run_spec.to_dict(),
        "metrics": metrics.to_dict(),
        "provenance": provenance,
    }


def run_experiment(spec: ExperimentSpec, base_config, *,
                   result_root: Path,
                   sysmon_enabled: bool = True,
                   limit: int | None = None,
                   on_progress: Callable[[RunOutcome, int, int], None] | None = None,
                   plan: Iterable[RunSpec] | None = None) -> list[RunOutcome]:
    """Execute (or resume) the EXP-002 queue. Completed runs are SKIPPED, never redone."""
    with QueueLock(result_root):
        return _run_experiment_locked(
            spec, base_config, result_root=result_root,
            sysmon_enabled=sysmon_enabled, limit=limit,
            on_progress=on_progress, plan=plan)


def _run_experiment_locked(spec: ExperimentSpec, base_config, *,
                           result_root: Path,
                           sysmon_enabled: bool,
                           limit: int | None,
                           on_progress, plan) -> list[RunOutcome]:
    assert_b0_unchanged(base_config)
    if spec.warmup_runs != base_config.warmup_runs:
        # The pre-registered design declares the warm-up policy; the executed
        # configuration comes from the B0 yaml. If they ever disagree, the recorded
        # design would not describe what actually ran.
        raise ValueError(
            f"spec declares warmup_runs={spec.warmup_runs} but the base configuration "
            f"{spec.base_config_path} uses {base_config.warmup_runs}; refusing to run "
            f"a design that does not match the executed warm-up policy")

    runs = list(plan) if plan is not None else list(spec.plan())
    if limit is not None:
        runs = runs[:limit]

    runs_dir = result_root / "runs"
    attempts_log = result_root / "attempts.jsonl"
    version = code_version()
    spec_fp = spec.fingerprint()
    grid_fp = grid_fingerprint(spec.grid)
    outcomes: list[RunOutcome] = []
    total = len(runs)
    late_cancel_pending = False

    for position, run_spec in enumerate(runs, start=1):
        path = runs_dir / run_spec.relative_path()
        existing = read_record(path)
        if is_completed(existing):
            stale = [
                f"{key}={existing.get(key)!r} != {current!r}"
                for key, current in (("spec_fingerprint", spec_fp),
                                     ("grid_fingerprint", grid_fp))
                if existing.get(key) and existing.get(key) != current]
            if stale:
                raise RuntimeError(
                    f"{path} was produced under a DIFFERENT design ({'; '.join(stale)}). "
                    f"Mixing designs in one result set would make the analysis "
                    f"un-interpretable. Move or delete the old results, or restore the "
                    f"original spec/grid, before resuming.")
            outcome = RunOutcome(run_spec, SKIPPED, existing, executed=False)
            outcomes.append(outcome)
            if on_progress:
                on_progress(outcome, position, total)
            continue

        attempt = int((existing or {}).get("attempt", 0)) + 1
        started = time.perf_counter()
        try:
            metrics, provenance = execute_run(
                run_spec, base_config, sysmon_enabled=sysmon_enabled,
                version=version)
        except Exception as exc:  # noqa: BLE001 - one bad run must not kill the queue
            metrics = RunMetrics(
                run_id=run_spec.run_id, workload_id=None,
                family=run_spec.family, scale=run_spec.scale, seed=run_spec.seed,
                config_fingerprint=run_spec.config.fingerprint(),
                aqe_enabled=run_spec.config.aqe_enabled,
                success=False, usable=False,
                error=f"{type(exc).__name__}: {exc}",
                event_log_status="MISSING", timestamp=_clock(),
                code_version=version)
            provenance = {"code_version": version,
                          "record_schema_version": RECORD_SCHEMA_VERSION,
                          "orchestration_error": f"{type(exc).__name__}: {exc}",
                          "wall_finished_utc": _clock()}

        provenance["queue_wall_s"] = round(time.perf_counter() - started, 4)

        # A timed-out run whose worker thread could not be joined keeps burning cores
        # (documented Windows limitation in the frozen Day-3 runner). The NEXT run's
        # timing is then contaminated, so the condition is carried forward explicitly
        # instead of vanishing.
        provenance["preceded_by_late_cancel"] = late_cancel_pending
        if late_cancel_pending:
            metrics.usable = False
            metrics.error = ((metrics.error + " | ") if metrics.error else "") + (
                "measured immediately after a timed-out run whose worker thread was "
                "still alive; timing is not trustworthy")
        late_cancel_pending = bool(provenance.get("thread_cancelled_late"))

        record = build_record(spec, run_spec, metrics, provenance, attempt)
        _atomic_write_json(path, record)
        _append_jsonl(attempts_log, {
            "timestamp": _clock(), "run_id": run_spec.run_id,
            "attempt": attempt, "status": record["status"],
            "execution_time_s": metrics.execution_time_s,
            "execution_time_source": metrics.execution_time_source,
            "timeout": metrics.timeout,
            "event_log_status": metrics.event_log_status,
            "error": metrics.error,
        })
        outcome = RunOutcome(run_spec, record["status"], record, executed=True)
        outcomes.append(outcome)
        if on_progress:
            on_progress(outcome, position, total)
    return outcomes


def load_records(result_root: Path) -> list[dict[str, Any]]:
    """Load every stored EXP-002 run record, sorted by run id (deterministic)."""
    runs_dir = result_root / "runs"
    records = [rec for path in sorted(runs_dir.rglob("*.json"))
               if (rec := read_record(path)) is not None]
    return sorted(records, key=lambda r: (r.get("run_spec") or {}).get("run_id", ""))
