#!/usr/bin/env python
"""AdaSpark Day-2 backend benchmark — VALIDATION ONLY, not research data (EXP-001 is the
calibrated noise study, Day 22). Runs 3 repetitions of a deterministic 1M-row workload:
session start → count → aggregation → Parquet write → Parquet read → clean shutdown,
sampling peak RSS (python + JVM children) with psutil.

Results: docs/backend_benchmark.md + .json. Usage: python scripts/spark_benchmark.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.utils.paths import tmp_dir  # noqa: E402

REPS = 3


class PeakSampler(threading.Thread):
    """Samples peak RSS of this process + all children (JVM) every 200 ms."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.peak = 0
        # NOTE: must NOT be named `_stop` — threading.Thread uses that attribute
        # internally (called by join()); shadowing it breaks Thread.join().
        self._halt = threading.Event()
        try:
            import psutil

            self.proc = psutil.Process()
        except ImportError:
            self.proc = None

    def run(self) -> None:
        while not self._halt.is_set():
            if self.proc is not None:
                try:
                    total = self.proc.memory_info().rss
                    for child in self.proc.children(recursive=True):
                        try:
                            total += child.memory_info().rss
                        except Exception:
                            pass
                    self.peak = max(self.peak, total)
                except Exception:
                    pass
            self._halt.wait(0.2)

    def stop(self) -> None:
        self._halt.set()


def one_rep(rep: int) -> dict:
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    from pyspark.sql import SparkSession

    r: dict = {"rep": rep}
    sampler = PeakSampler()
    sampler.start()
    t0 = time.perf_counter()
    spark = (SparkSession.builder.master("local[2]")
             .appName(f"sparkrl-benchmark-{rep}")
             .config("spark.driver.memory", "2g")
             .config("spark.ui.enabled", "false")
             .config("spark.local.dir", str(tmp_dir(create=True)))
             .getOrCreate())
    r["session_start_s"] = round(time.perf_counter() - t0, 3)

    df = spark.range(1_000_000).selectExpr("id", "id % 100 as k", "(id % 1000) / 8.0 as v")
    t0 = time.perf_counter()
    n = df.count()
    r["count_1m_s"] = round(time.perf_counter() - t0, 3)

    t0 = time.perf_counter()
    groups = df.groupBy("k").sum("v").count()
    r["agg_1m_groups_s"] = round(time.perf_counter() - t0, 3)

    pq = tmp_dir() / "benchmark" / f"rep{rep}.parquet"
    t0 = time.perf_counter()
    df.write.mode("overwrite").parquet(str(pq))
    r["parquet_write_1m_s"] = round(time.perf_counter() - t0, 3)

    t0 = time.perf_counter()
    n2 = spark.read.parquet(str(pq)).count()
    r["parquet_read_1m_s"] = round(time.perf_counter() - t0, 3)

    t0 = time.perf_counter()
    spark.stop()
    r["shutdown_s"] = round(time.perf_counter() - t0, 3)

    sampler.stop()
    sampler.join(timeout=1)
    r["peak_rss_GB"] = round(sampler.peak / 1024**3, 2)
    r["ok"] = (n == 1_000_000 and groups == 100 and n2 == 1_000_000)
    return r


def main() -> int:
    reps = [one_rep(i) for i in range(1, REPS + 1)]

    def median(key: str):
        vals = sorted(r[key] for r in reps)
        return vals[len(vals) // 2]

    keys = ("session_start_s", "count_1m_s", "agg_1m_groups_s",
            "parquet_write_1m_s", "parquet_read_1m_s", "shutdown_s")
    summary = {k: median(k) for k in keys}
    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "note": "backend validation benchmark — NOT research experiment data",
               "reps": reps, "median": summary,
               "all_ok": all(r["ok"] for r in reps)}
    doc = PROJECT / "docs"
    doc.mkdir(exist_ok=True)
    (doc / "backend_benchmark.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# AdaSpark Backend Benchmark (Day 2 — validation only)", "",
             f"Generated {payload['generated_utc']}; {REPS} repetitions of a deterministic 1M-row workload.", "",
             "| Metric | Median |", "|---|---|"]
    for k, v in summary.items():
        lines.append(f"| {k} | {v} s |")
    lines += ["", f"| peak_rss_GB | {median('peak_rss_GB')} GB |",
              "", f"**All repetitions OK: {payload['all_ok']}**", ""]
    (doc / "backend_benchmark.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report: {doc / 'backend_benchmark.md'}")
    return 0 if payload["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
