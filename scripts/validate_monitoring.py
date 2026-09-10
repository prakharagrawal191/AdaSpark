"""Structural validator for the Day-16 monitoring layer.

Checks repository structure and metadata consistency ONLY: modules exist,
RuntimeMetrics exposes the frozen fields, completeness statuses exist,
fixtures and tests exist, documentation exists. It does NOT prove semantic
correctness of parsed metrics — that is the unit/integration tests' and
later experiments' job.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sparkrl.monitoring.schemas import EventLogStatus, RuntimeMetrics  # noqa: E402

REQUIRED_MODULES = [
    "src/sparkrl/monitoring/__init__.py",
    "src/sparkrl/monitoring/eventlog_parser.py",
    "src/sparkrl/monitoring/metrics.py",
    "src/sparkrl/monitoring/schemas.py",
    "src/sparkrl/monitoring/validate.py",
]
REQUIRED_FIELDS = [
    "run_id", "application_id", "execution_time_s", "execution_time_source",
    "stage_count", "task_count", "failed_task_count",
    "shuffle_read_bytes", "shuffle_write_bytes",
    "memory_spill_bytes", "disk_spill_bytes", "total_spill_bytes",
    "task_duration_mean_s", "task_duration_median_s", "task_duration_std_s",
    "task_duration_cv", "aqe_enabled", "event_log_status",
    "event_log_total_events", "malformed_event_count", "unknown_event_count",
]
REQUIRED_STATUSES = {"COMPLETE", "INCOMPLETE", "MALFORMED", "MISSING"}
REQUIRED_FIXTURES = [
    "valid.jsonl", "failed_tasks.jsonl", "incomplete.jsonl",
    "malformed_line.jsonl", "garbage.jsonl", "empty.jsonl",
]
REQUIRED_DOCS = ["docs/day16_monitoring.md", "docs/monitoring_metrics.md"]
REQUIRED_TESTS = [
    "tests/unit/test_monitoring_parser.py",
    "tests/unit/test_monitoring_metrics.py",
    "tests/integration/test_monitoring_pipeline.py",
]


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_MODULES + REQUIRED_DOCS + REQUIRED_TESTS:
        if not Path(path).exists():
            errors.append(f"missing required file: {path}")

    fields = {f.name for f in dataclasses.fields(RuntimeMetrics)}
    for field_name in REQUIRED_FIELDS:
        if field_name not in fields:
            errors.append(f"RuntimeMetrics missing field: {field_name}")

    statuses = {s.value for s in EventLogStatus}
    if statuses != REQUIRED_STATUSES:
        errors.append(f"EventLogStatus values {statuses} != {REQUIRED_STATUSES}")

    fx = Path("tests/fixtures/eventlogs")
    for name in REQUIRED_FIXTURES:
        if not (fx / name).is_file():
            errors.append(f"missing fixture: tests/fixtures/eventlogs/{name}")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS: monitoring modules, {len(REQUIRED_FIELDS)} RuntimeMetrics "
          f"fields, {len(REQUIRED_STATUSES)} statuses, {len(REQUIRED_FIXTURES)} "
          f"fixtures, tests and documentation present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
