#!/usr/bin/env python
"""AdaSpark Day-2 backend validation: full Spark smoke matrix (tests A–K).

Validates the frozen backend (DEC-007): Python 3.11 + PySpark 3.5.x + Java 17 +
winutils 3.3.6 shim on native Windows local mode.

Tests: A session creation · B DataFrame creation · C count · D aggregation ·
E Parquet write (small) · F Parquet read (small) · G Parquet round-trip 1M rows ·
H event-log generation · I event-log discovery · J clean shutdown ·
K environment audit (HADOOP_HOME / winutils / bundled Hadoop client).

Results: docs/smoke_matrix_report.md + .json (machine-generated). Exit 0 iff all PASS.
Usage:  python scripts/spark_smoke_matrix.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.utils.paths import eventlog_dir, resolve_data_root, tmp_dir  # noqa: E402

RESULTS: list[dict] = []


def record(tid: str, name: str, status: str, detail: str, seconds: float = 0.0) -> None:
    RESULTS.append({"id": tid, "name": name, "status": status,
                    "detail": detail, "seconds": round(seconds, 3)})
    print(f"[{status:>4}] {tid} {name}: {detail} ({seconds:.2f}s)")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_k_environment_audit() -> dict:
    audit: dict = {}
    hadoop_home = os.environ.get("HADOOP_HOME", "")
    winutils = Path(hadoop_home) / "bin" / "winutils.exe" if hadoop_home else None
    audit["HADOOP_HOME"] = hadoop_home or "<unset>"
    if winutils and winutils.exists():
        audit["winutils_path"] = str(winutils)
        audit["winutils_size"] = winutils.stat().st_size
        audit["winutils_sha256"] = sha256_of(winutils)
        audit["winutils_source"] = "cdarlint/winutils hadoop-3.3.6 (raw.githubusercontent)"
        record("K", "HADOOP_HOME + winutils", "PASS",
               f"{hadoop_home}; winutils {audit['winutils_size']} bytes")
    else:
        record("K", "HADOOP_HOME + winutils", "WARN",
               "HADOOP_HOME unset or winutils.exe missing - Windows local mode will fail")
    try:
        import pyspark
        jars = Path(pyspark.__file__).parent / "jars"
        clients = sorted(p.name for p in jars.glob("hadoop-client-runtime-*.jar"))
        audit["pyspark_version"] = pyspark.__version__
        audit["bundled_hadoop_client"] = clients[0] if clients else "<not found>"
        record("K", "bundled Hadoop client", "PASS",
               f"pyspark {pyspark.__version__}; {audit['bundled_hadoop_client']}")
    except Exception as exc:  # pragma: no cover
        record("K", "bundled Hadoop client", "FAIL", f"{type(exc).__name__}: {exc}")
    audit["java"] = os.environ.get("JAVA_HOME", "<unset>")
    return audit


def build_session(elog: Path):
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    from pyspark.sql import SparkSession

    spark = (SparkSession.builder.master("local[2]")
             .appName("sparkrl-smoke-matrix")
             .config("spark.driver.memory", "2g")
             .config("spark.ui.enabled", "false")
             .config("spark.eventLog.enabled", "true")
             .config("spark.eventLog.compress", "false")   # uncompressed JSON by design
             .config("spark.eventLog.dir", elog.as_uri())
             .config("spark.local.dir", str(tmp_dir(create=True)))
             .getOrCreate())
    return spark


def tests_small(spark) -> None:
    t0 = time.perf_counter()
    ver = spark.version
    record("A", "SparkSession creation", "PASS" if ver else "FAIL",
           f"Spark {ver} local[2], appId={spark.sparkContext.applicationId}",
           time.perf_counter() - t0)

    t0 = time.perf_counter()
    rows = [(i, i % 10, float(i % 1000) / 8.0) for i in range(100)]  # deterministic
    df = spark.createDataFrame(rows, "id long, k long, v double")
    record("B", "DataFrame creation", "PASS" if df.count() >= 0 else "FAIL",
           f"schema={df.schema.simpleString()}", time.perf_counter() - t0)

    t0 = time.perf_counter()
    n = df.count()
    record("C", "count operation", "PASS" if n == 100 else "FAIL",
           f"count={n} (expected 100)", time.perf_counter() - t0)

    t0 = time.perf_counter()
    agg = df.groupBy("k").sum("v").orderBy("k")
    got = agg.count()
    total = df.agg({"v": "sum"}).collect()[0][0]
    agg_total = sum(r[1] for r in agg.collect())
    ok = got == 10 and abs(total - agg_total) < 1e-6
    record("D", "small aggregation", "PASS" if ok else "FAIL",
           f"groups={got}, sum(v)={total:.3f}, sum of group sums={agg_total:.3f}",
           time.perf_counter() - t0)

def tests_parquet(spark) -> dict:
    out = {}
    small = tmp_dir() / "smoke" / "small.parquet"
    t0 = time.perf_counter()
    rows = [(i, i % 10, float(i % 1000) / 8.0) for i in range(100)]
    df = spark.createDataFrame(rows, "id long, k long, v double")
    df.write.mode("overwrite").parquet(str(small))
    record("E", "Parquet write (small)", "PASS", f"{small} ({small.stat().st_size} bytes)",
           time.perf_counter() - t0)

    t0 = time.perf_counter()
    n = spark.read.parquet(str(small)).count()
    record("F", "Parquet read (small)", "PASS" if n == 100 else "FAIL", f"count={n}",
           time.perf_counter() - t0)

    big = tmp_dir() / "smoke" / "big1m.parquet"
    t0 = time.perf_counter()
    src = spark.range(1_000_000).selectExpr("id", "id % 100 as k", "(id % 1000) / 8.0 as v")
    src.write.mode("overwrite").parquet(str(big))
    write_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    back = spark.read.parquet(str(big))
    n2 = back.count()
    sums_src = src.agg({"id": "sum", "v": "sum"}).collect()[0]
    sums_back = back.agg({"id": "sum", "v": "sum"}).collect()[0]
    ok = (n2 == 1_000_000 and sums_src[0] == sums_back[0]
          and abs((sums_src[1] or 0) - (sums_back[1] or 0)) < 1e-6)
    record("G", "Parquet round-trip 1M", "PASS" if ok else "FAIL",
           f"count={n2}, sum(id) src={sums_src[0]} back={sums_back[0]}, "
           f"sum(v) src={sums_src[1]:.1f} back={sums_back[1]:.1f}",
           write_s + (time.perf_counter() - t0))
    out["write_1m_s"] = round(write_s, 3)
    out["read_check_1m_s"] = round(time.perf_counter() - t0, 3)
    return out


def validate_event_log(elog: Path, app_id: str) -> None:
    expected = elog / f"app-{app_id}" if not str(app_id).startswith("app-") else elog / app_id
    completed = expected if expected.exists() else None
    if completed is None:
        cands = [p for p in elog.rglob(f"*{app_id}*") if p.is_file() and not p.name.endswith(".inprogress")]
        completed = cands[0] if cands else None
    if completed is None or completed.stat().st_size == 0:
        record("H", "event-log generation", "FAIL", f"no completed event log for {app_id}")
        record("I", "event-log discovery", "FAIL", "discovery failed")
        return
    record("H", "event-log generation", "PASS",
           f"{completed.name}, {completed.stat().st_size} bytes")
    bad = 0
    n_events = 0
    first_ev = last_ev = "?"
    with open(completed, "r", encoding="utf-8", errors="replace") as fh:
        for ln, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                n_events += 1
                first_ev = first_ev if n_events > 1 else ev.get("Event", "?")
                last_ev = ev.get("Event", "?")
            except json.JSONDecodeError:
                bad += 1
                if bad == 1:
                    record("H", "event-log JSON", "FAIL",
                           f"line {ln} not valid JSON: {line[:80]!r}")
    ok = bad == 0 and n_events > 0
    record("I", "event-log discovery + strict JSON", "PASS" if ok else "FAIL",
           f"{n_events} events parsed, {bad} bad lines; first={first_ev}, last={last_ev}")


def write_report(audit: dict) -> bool:
    all_pass = all(r["status"] == "PASS" for r in RESULTS)
    doc = PROJECT / "docs"
    doc.mkdir(exist_ok=True)
    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "backend": "native Windows + Python 3.11 + PySpark 3.5.9 + winutils 3.3.6 shim (DEC-007)",
               "audit": audit, "tests": RESULTS,
               "verdict": "PASS" if all_pass else "FAIL"}
    (doc / "smoke_matrix_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# AdaSpark Smoke Matrix Report (Day 2)", "",
             f"Generated {payload['generated_utc']} — backend: {payload['backend']}", "",
             "| Test | Name | Status | Detail | Seconds |", "|---|---|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['id']} | {r['name']} | {r['status']} | {r['detail']} | {r['seconds']} |")
    lines += ["", f"**Verdict: {payload['verdict']}**",
              "", "Event log format: uncompressed JSON lines (`spark.eventLog.compress=false`).", ""]
    (doc / "smoke_matrix_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {doc / 'smoke_matrix_report.md'}")
    return all_pass


def main() -> int:
    print("=== AdaSpark Day-2 Spark smoke matrix ===")
    audit = test_k_environment_audit()
    elog = eventlog_dir() / "smoke" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    elog.mkdir(parents=True, exist_ok=True)
    spark = None
    try:
        t0 = time.perf_counter()
        spark = build_session(elog)
        record("A0", "session startup time (info)", "PASS", f"{time.perf_counter() - t0:.2f}s")
        tests_small(spark)
        tests_parquet(spark)
        t0 = time.perf_counter()
        app_id = spark.sparkContext.applicationId
        spark.stop()
        spark = None
        record("J", "clean Spark shutdown", "PASS", f"stopped app {app_id}", time.perf_counter() - t0)
        validate_event_log(elog, app_id)
    except Exception as exc:
        record("X", "unexpected failure", "FAIL", f"{type(exc).__name__}: {exc}")
        if spark is not None:
            try:
                spark.stop()
            except Exception:
                pass
    all_pass = write_report(audit)
    n_fail = sum(1 for r in RESULTS if r["status"] != "PASS")
    print(f"\nOVERALL: {'PASS' if all_pass else 'FAIL'} ({len(RESULTS)} tests, {n_fail} not passing)")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

