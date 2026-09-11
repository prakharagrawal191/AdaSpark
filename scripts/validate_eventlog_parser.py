"""Structural validator for the Day-16/18 event-log parser.

Checks repository structure and fixture/metadata consistency ONLY:
modules exist, RuntimeMetrics exposes the frozen fields, completeness
statuses exist, hand-checked fixtures + expected values exist, relevant
tests and documentation exist. It does NOT prove semantic correctness of
parsed metrics — that is the job of the hand-checked fixtures and tests.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

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
    "valid.jsonl", "valid.expected.json", "failed_tasks.jsonl",
    "incomplete.jsonl", "incomplete_nostart.jsonl", "malformed_line.jsonl",
    "garbage.jsonl", "empty.jsonl", "unknown_event.jsonl",
    "wallclock_vs_executor.jsonl",
]
REQUIRED_DOCS = ["docs/day16_monitoring.md", "docs/monitoring_metrics.md",
                 "docs/research/DAY18_EVENTLOG_AUDIT.md"]
REQUIRED_TESTS = [
    "tests/unit/test_monitoring_parser.py",
    "tests/unit/test_monitoring_metrics.py",
    "tests/integration/test_monitoring_pipeline.py",
]


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_MODULES + REQUIRED_DOCS + REQUIRED_TESTS:
        if not (PROJECT / path).exists():
            errors.append(f"missing required file: {path}")

    fields = {f.name for f in dataclasses.fields(RuntimeMetrics)}
    for field_name in REQUIRED_FIELDS:
        if field_name not in fields:
            errors.append(f"RuntimeMetrics missing field: {field_name}")

    statuses = {s.value for s in EventLogStatus}
    if statuses != REQUIRED_STATUSES:
        errors.append(f"EventLogStatus values {statuses} != {REQUIRED_STATUSES}")

    fx = PROJECT / "tests" / "fixtures" / "eventlogs"
    for name in REQUIRED_FIXTURES:
        if not (fx / name).is_file():
            errors.append(f"missing fixture: tests/fixtures/eventlogs/{name}")

    try:
        expected = json.loads((fx / "valid.expected.json").read_text())["expected"]
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"valid.expected.json unreadable: {exc}")
        expected = {}
    for key in ("stage_count", "task_count", "shuffle_read_bytes",
                "shuffle_write_bytes", "memory_spill_bytes",
                "disk_spill_bytes", "total_spill_bytes"):
        if key not in expected:
            errors.append(f"valid.expected.json missing hand-check key: {key}")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: event-log parser modules, 21 RuntimeMetrics fields, 4 statuses, "
          f"{len(REQUIRED_FIXTURES)} fixtures + hand-checked expectations, "
          "tests and documentation present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())