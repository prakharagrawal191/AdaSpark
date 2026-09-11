"""Bounded optional psutil sampler (Day 19).

Measures the *current (orchestrator/driver) process* plus coarse system
counters around one Spark execution. This is process-level monitoring of the
process that actually exists in the single-node architecture — it is NOT
executor-level CPU/RSS coverage and must never be presented as such.

Rules (frozen Day-19 contract):
- sampling is strictly optional: any failure degrades to ``sampled=False``
  with the reason recorded; it must NEVER fail the experiment;
- bounded: ``max_samples`` caps the retained samples (oldest dropped);
- no busy-spin: a daemon thread sleeps ``interval_s`` between samples;
- ``psutil.cpu_percent(interval=None)`` is non-blocking; a priming call at
  ``start()`` discards the meaningless first reading;
- missing vs zero are distinguished: a metric the OS did not provide stays
  ``None``, it is never fabricated as 0.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

try:  # psutil is a pinned core dependency, but sampling stays optional
    import psutil as _psutil
except Exception:  # noqa: BLE001 - degraded mode, never fatal
    _psutil = None


@dataclass(frozen=True)
class SamplerConfig:
    """Sampling policy (plain data, safe to put in manifests)."""

    enabled: bool = True
    interval_s: float = 1.0
    max_samples: int = 600  # at 1 s interval -> 10 min of execution covered


@dataclass
class SystemSummary:
    """Aggregated psutil summary for one execution window."""

    sampled: bool = False
    reason: str | None = None          # why unavailable, when sampled=False
    sample_count: int = 0
    window_s: float | None = None      # start->stop wall time
    # process-level (current process), peak/mean over samples
    rss_bytes_max: int | None = None
    rss_bytes_mean: int | None = None
    proc_cpu_time_s: float | None = None      # user+system at stop (cumulative)
    proc_cpu_percent_mean: float | None = None
    # system-level
    sys_cpu_percent_mean: float | None = None
    sys_mem_available_bytes_min: int | None = None
    sys_mem_percent_max: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sampled": self.sampled,
            "reason": self.reason,
            "sample_count": self.sample_count,
            "window_s": self.window_s,
            "rss_bytes_max": self.rss_bytes_max,
            "rss_bytes_mean": self.rss_bytes_mean,
            "proc_cpu_time_s": self.proc_cpu_time_s,
            "proc_cpu_percent_mean": self.proc_cpu_percent_mean,
            "sys_cpu_percent_mean": self.sys_cpu_percent_mean,
            "sys_mem_available_bytes_min": self.sys_mem_available_bytes_min,
            "sys_mem_percent_max": self.sys_mem_percent_max,
        }

    @classmethod
    def unavailable(cls, reason: str) -> "SystemSummary":
        return cls(sampled=False, reason=reason)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None

class SystemSampler:
    """Thread-based bounded sampler. Use as ``with SystemSampler(cfg) as s: ...``.

    ``summary()`` is safe to call at any time (including after failures) and
    never raises.
    """

    def __init__(self, config: SamplerConfig | None = None) -> None:
        self.config = config or SamplerConfig()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._rss: list[int] = []
        self._proc_cpu: list[float] = []
        self._sys_cpu: list[float] = []
        self._mem_avail: list[int] = []
        self._mem_pct: list[float] = []
        self._start_t: float | None = None
        self._end_t: float | None = None
        self._proc = None
        self._error: str | None = None
        if _psutil is None:
            self._error = "psutil not importable"

    # -- lifecycle ------------------------------------------------------
    def start(self) -> "SystemSampler":
        self._start_t = time.perf_counter()
        if not self.config.enabled:
            self._error = "disabled by config"
            return self
        if _psutil is None:
            return self
        try:
            self._proc = _psutil.Process()
            # Prime non-blocking cpu_percent readings (first call is 0.0).
            self._proc.cpu_percent(interval=None)
            _psutil.cpu_percent(interval=None)
        except Exception as exc:  # noqa: BLE001 - degrade, never fail
            self._error = f"prime failed: {type(exc).__name__}: {exc}"
            return self
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="sparkrl-sysmon",
                                        daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        try:
            while not self._stop_event.wait(self.config.interval_s):
                self._take_sample()
        except Exception as exc:  # noqa: BLE001 - sampler must never crash run
            with self._lock:
                if self._error is None:
                    self._error = f"loop failed: {type(exc).__name__}: {exc}"

    def _take_sample(self) -> None:
        try:
            assert _psutil is not None and self._proc is not None
            mem = self._proc.memory_info()
            rss = int(mem.rss)
            proc_cpu = float(self._proc.cpu_percent(interval=None))
            sys_cpu = float(_psutil.cpu_percent(interval=None))
            vm = _psutil.virtual_memory()
        except Exception:  # noqa: BLE001 - skip bad samples, keep going
            return
        with self._lock:
            cap = max(1, self.config.max_samples)
            for buf, val in ((self._rss, rss), (self._proc_cpu, proc_cpu),
                             (self._sys_cpu, sys_cpu),
                             (self._mem_avail, int(vm.available)),
                             (self._mem_pct, float(vm.percent))):
                buf.append(val)
                while len(buf) > cap:
                    buf.pop(0)

    def stop(self) -> "SystemSampler":
        self._end_t = time.perf_counter()
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.config.interval_s * 2))
            self._thread = None
        return self

    def __enter__(self) -> "SystemSampler":
        return self.start()

    def __exit__(self, *exc: Any) -> bool:
        self.stop()
    # -- result ----------------------------------------------------------
    def summary(self) -> SystemSummary:
        """Aggregate retained samples. Never raises."""
        try:
            with self._lock:
                rss = list(self._rss)
                proc_cpu = list(self._proc_cpu)
                sys_cpu = list(self._sys_cpu)
                mem_avail = list(self._mem_avail)
                mem_pct = list(self._mem_pct)
                error = self._error
            if error is not None or not rss:
                reason = error or "no samples collected"
                return SystemSummary.unavailable(reason)
            cpu_time = None
            try:
                if self._proc is not None and _psutil is not None:
                    t = self._proc.cpu_times()
                    cpu_time = float(t.user + t.system)
            except Exception:  # noqa: BLE001 - cumulative time is best-effort
                cpu_time = None
            window = None
            if self._start_t is not None and self._end_t is not None:
                window = self._end_t - self._start_t
            return SystemSummary(
                sampled=True,
                reason=None,
                sample_count=len(rss),
                window_s=window,
                rss_bytes_max=max(rss),
                rss_bytes_mean=int(sum(rss) / len(rss)),
                proc_cpu_time_s=cpu_time,
                proc_cpu_percent_mean=_mean(proc_cpu),
                sys_cpu_percent_mean=_mean(sys_cpu),
                sys_mem_available_bytes_min=min(mem_avail) if mem_avail else None,
                sys_mem_percent_max=max(mem_pct) if mem_pct else None,
            )
        except Exception as exc:  # noqa: BLE001 - summary itself never fails
            return SystemSummary.unavailable(f"summary failed: {type(exc).__name__}")
        return False  # never swallow caller exceptions