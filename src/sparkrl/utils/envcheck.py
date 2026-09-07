"""Environment probing and machine-generated reporting for AdaSpark.

Every value written to the report is measured at run time; nothing is hard-coded
or assumed (approved planning rule: "inspect, do not assume").

Regenerate the report at any time with:  python scripts/env_check.py
Outputs: docs/ENVIRONMENT_REPORT.md (human) + docs/environment_report.json (machine).
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is pinned in requirements.txt
    psutil = None  # type: ignore[assignment]

from sparkrl.utils.paths import eventlog_dir, project_root, resolve_data_root, tmp_dir

CHECKS: list[dict[str, str]] = []


def _record(name: str, status: str, detail: str) -> None:
    CHECKS.append({"name": name, "status": status, "detail": detail})
    print(f"[{status:>4}] {name}: {detail}")


def _short(exc: BaseException, limit: int = 240) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def check_python() -> None:
    ok = sys.version_info >= (3, 12)
    _record("Python", "PASS" if ok else "FAIL",
            f"{platform.python_version()} at {sys.executable} (require >= 3.12)")


def check_platform() -> dict[str, Any]:
    info: dict[str, Any] = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_model": platform.processor() or "unknown",
        "cpu_logical_cores": os.cpu_count(),
        "ram_total_GB": None,
        "ram_available_GB": None,
    }
    if psutil is not None:
        vm = psutil.virtual_memory()
        info["ram_total_GB"] = round(vm.total / 1024**3, 1)
        info["ram_available_GB"] = round(vm.available / 1024**3, 1)
    _record("Platform", "PASS", f"{info['os']}; {info['cpu_logical_cores']} logical cores")
    return info


def check_gpu() -> str:
    smi = shutil.which("nvidia-smi")
    if smi is None:
        _record("GPU", "WARN", "not detected (acceptable: GPU not required by the approved architecture)")
        return "not detected"
    try:
        out = subprocess.run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=15)
        first = out.stdout.strip().splitlines()[0] if out.stdout.strip() else "unknown"
        _record("GPU", "PASS", f"{first} (detected; NOT used by this project)")
        return first
    except Exception as exc:
        _record("GPU", "WARN", f"nvidia-smi present but query failed: {_short(exc)}")
        return "query failed"


def check_disk() -> dict[str, Any]:
    data_root = resolve_data_root(create=True)
    free_project = shutil.disk_usage(project_root()).free / 1024**3
    free_data = shutil.disk_usage(data_root).free / 1024**3
    _record("Disk", "PASS" if free_data > 20 else "WARN",
            f"project volume {free_project:.1f} GB free; data root {data_root} {free_data:.1f} GB free")
    return {"project_free_GB": round(free_project, 1), "data_free_GB": round(free_data, 1),
            "data_root": str(data_root)}


def check_java() -> str | None:
    java_home = os.environ.get("JAVA_HOME", "<unset>")
    try:
        out = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=30)
        first = (out.stderr or out.stdout).strip().splitlines()[0]
        _record("Java", "PASS", f"{first}; JAVA_HOME={java_home}")
        return first
    except Exception as exc:
        _record("Java", "FAIL", f"java not runnable: {_short(exc)}; JAVA_HOME={java_home}")
        return None


def check_git() -> bool:
    git = shutil.which("git")
    if git is None:
        _record("Git", "FAIL", "git executable not found on PATH")
        return False
    try:
        ver = subprocess.run([git, "--version"], capture_output=True, text=True, timeout=15).stdout.strip()
        inside = subprocess.run([git, "-C", str(project_root()), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True, timeout=15).stdout.strip() == "true"
        _record("Git", "PASS" if inside else "WARN", f"{ver}; inside work tree: {inside}")
        return inside
    except Exception as exc:
        _record("Git", "WARN", _short(exc))
        return False


def check_filesystem() -> bool:
    try:
        probe = tmp_dir(create=True) / "envcheck_probe.txt"
        probe.write_text("sparkrl-probe", encoding="utf-8")
        ok = probe.read_text(encoding="utf-8") == "sparkrl-probe"
        probe.unlink()
        _record("Filesystem", "PASS" if ok else "FAIL",
                f"write/read/delete OK under {resolve_data_root(create=False)}")
        return ok
    except Exception as exc:
        _record("Filesystem", "FAIL", _short(exc))
        return False


def check_pyspark_import() -> str | None:
    try:
        import pyspark

        _record("PySpark import", "PASS", f"pyspark {pyspark.__version__}")
        return str(pyspark.__version__)
    except Exception as exc:
        _record("PySpark import", "FAIL", _short(exc))
        return None


def check_spark_smoke() -> dict[str, Any]:
    """Start local[2] Spark, run a count + Parquet roundtrip, verify the event log."""
    out: dict[str, Any] = {}
    try:
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        from pyspark.sql import SparkSession
    except Exception as exc:
        _record("Spark smoke", "FAIL", f"cannot import SparkSession: {_short(exc)}")
        return out

    elog = eventlog_dir(create=True)
    spark = None
    t0 = time.perf_counter()
    try:
        spark = (SparkSession.builder.master("local[2]")
                 .appName("sparkrl-env-check")
                 .config("spark.driver.memory", "2g")
                 .config("spark.ui.enabled", "false")
                 .config("spark.eventLog.enabled", "true")
                 .config("spark.eventLog.dir", elog.as_uri())
                 .config("spark.local.dir", str(tmp_dir(create=True)))
                 .getOrCreate())
        startup_s = round(time.perf_counter() - t0, 1)
        _record("SparkSession", "PASS", f"Spark {spark.version} local[2] started in {startup_s}s")
        out["spark_version"] = spark.version
        out["session_startup_s"] = startup_s

        n = spark.range(1_000_000).count()
        out["count_result"] = n
        _record("Spark job (count)", "PASS", f"range(1,000,000).count() = {n}")

        pq = tmp_dir() / "envcheck_parquet"
        spark.range(100_000).write.mode("overwrite").parquet(str(pq))
        n2 = spark.read.parquet(str(pq)).count()
        out["parquet_roundtrip_count"] = n2
        _record("Parquet roundtrip", "PASS", f"write + read back, count={n2}")
    except Exception as exc:
        _record("Spark smoke", "FAIL", _short(exc))
    finally:
        if spark is not None:
            spark.stop()
            _record("SparkSession stop", "PASS", "session stopped (Windows file locks released)")

    try:
        files = sorted((p for p in elog.rglob("*") if p.is_file() and p.stat().st_size > 0),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            _record("Event log", "WARN", "no event-log file found after the run")
            return out
        newest = files[0]
        with open(newest, "r", encoding="utf-8", errors="replace") as fh:
            first = json.loads(fh.readline())
        n_lines = sum(1 for _ in open(newest, "r", encoding="utf-8", errors="replace"))
        _record("Event log", "PASS",
                f"{newest.name}: {n_lines} JSON events; first='{first.get('Event', '?')}'")
        out["eventlog_file"] = newest.name
        out["eventlog_events"] = n_lines
    except Exception as exc:
        _record("Event log", "WARN", _short(exc))
    return out


def run_all(write_report: bool = True) -> dict[str, Any]:
    """Run every check, print results, optionally write the report files."""
    CHECKS.clear()
    started = datetime.now(timezone.utc)
    platform_info = check_platform()
    gpu = check_gpu()
    disk = check_disk()
    check_python()
    java_line = check_java()
    check_git()
    check_filesystem()
    pyspark_version = check_pyspark_import()
    spark_info = check_spark_smoke()

    failed = [c for c in CHECKS if c["status"] == "FAIL"]
    warned = [c for c in CHECKS if c["status"] == "WARN"]
    verdict = "BLOCKED" if failed else ("PASS" if not warned else "PASS_WITH_WARNINGS")
    report = {"generated_utc": started.isoformat(), "verdict": verdict,
              "project_root": str(project_root()), "platform": platform_info, "gpu": gpu,
              "disk": disk, "java": java_line, "pyspark": pyspark_version,
              "spark": spark_info, "checks": CHECKS}
    if write_report:
        _write_markdown(report)
        (project_root() / "docs" / "environment_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport written: {project_root() / 'docs' / 'ENVIRONMENT_REPORT.md'}")
    print(f"\nOVERALL: {verdict} ({len(CHECKS)} checks, {len(failed)} failed, {len(warned)} warnings)")
    return report


def _write_markdown(rep: dict[str, Any]) -> None:
    docs = project_root() / "docs"
    docs.mkdir(exist_ok=True)
    n_fail = sum(1 for c in rep["checks"] if c["status"] == "FAIL")
    n_warn = sum(1 for c in rep["checks"] if c["status"] == "WARN")
    lines = [
        "# AdaSpark Environment Report",
        "",
        f"Machine-generated by `scripts/env_check.py` on {rep['generated_utc']} — values are measured, not assumed.",
        "",
        "## Detected environment",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| OS | {rep['platform']['os']} |",
        f"| CPU | {rep['platform']['cpu_model']} ({rep['platform']['cpu_logical_cores']} logical cores) |",
        f"| RAM | {rep['platform']['ram_total_GB']} GB total / {rep['platform']['ram_available_GB']} GB available at check time |",
        f"| GPU | {rep['gpu']} (not used by this project) |",
        f"| Python | {rep['platform']['python']} |",
        f"| Java | {rep['java'] or 'NOT RUNNABLE'} |",
        f"| PySpark (installed) | {rep['pyspark'] or 'NOT INSTALLED'} |",
        f"| Spark (runtime) | {rep['spark'].get('spark_version', 'not started')} |",
        f"| Data root | `{rep['disk']['data_root']}` (override with SPARKRL_DATA_ROOT) |",
        f"| Disk free | project {rep['disk']['project_free_GB']} GB / data {rep['disk']['data_free_GB']} GB |",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for c in rep["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | {c['detail']} |")
    lines += [
        "",
        "## Verdict",
        "",
        f"**{rep['verdict']}** — {len(rep['checks'])} checks, {n_fail} failed, {n_warn} warnings.",
        "",
        "## Notes",
        "",
        "- Provisional execution backend: **native Windows local-mode Spark**; final confirmation in the Day-2 smoke-test matrix (see `docs/DECISIONS.md`, DEC-005).",
        "- Fallback chain if native Windows fails: WSL2 Ubuntu → Docker (approved plan §39).",
        "- Regenerate at any time with: `python scripts/env_check.py`",
        "",
    ]
    (docs / "ENVIRONMENT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
