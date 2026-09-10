"""Structural/data-integrity validator for the Day-17 B0 baseline.

Checks repository structure and metadata consistency ONLY:
- B0 config exists and pins AQE off
- every expected workload is represented
- per-run manifests exist and contain the required fields
- result signatures present, config fingerprint consistent across all runs
- AQE mode consistent (off)
- event-log status COMPLETE for usable runs
- no duplicate run IDs
- summary agrees with per-run manifests (counts + fingerprints)

It does NOT decide whether the baseline is "good" or whether configuration
sensitivity exists (that is EXP-002).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REQUIRED_MANIFEST_FIELDS = (
    "calibration_id", "baseline_id", "run_id", "family", "scale", "seed",
    "workload_id", "workload_version", "spark_version",
    "dataset_id", "dataset_fingerprint", "schema_fingerprint",
    "configuration_fingerprint", "aqe_mode", "warmup_runs",
    "execution_time_s", "stage_count", "task_count",
    "shuffle_read_bytes", "shuffle_write_bytes",
    "memory_spill_bytes", "disk_spill_bytes", "total_spill_bytes",
    "task_duration_cv", "result_signature", "success", "usable",
    "event_log_status", "application_id", "timestamp", "code_version",
)
EXPECTED_FAMILIES = {"F1_agg", "F2_join", "F3_rdd", "F4_ski", "F5_mixed"}


def main() -> int:
    errors: list[str] = []
    config = PROJECT / "configs" / "baseline_b0.yaml"
    if not config.exists():
        errors.append("missing configs/baseline_b0.yaml")

    results = PROJECT / "results" / "baseline"
    if not (results / "runs.json").exists():
        errors.append("missing results/baseline/runs.json")
        print("FAIL: baseline results absent (run scripts/run_baseline.py first)")
        return 1

    runs = json.loads((results / "runs.json").read_text(encoding="utf-8"))
    if not runs:
        errors.append("runs.json is empty")
    families = {r["family"] for r in runs}
    missing = EXPECTED_FAMILIES - families
    if missing:
        errors.append(f"no baseline runs for: {sorted(missing)}")

    run_ids = [r["run_id"] for r in runs if r.get("run_id")]
    if len(run_ids) != len(set(run_ids)):
        errors.append("duplicate run IDs in runs.json")

    cfgs = {r.get("configuration_fingerprint") for r in runs if r.get("run_id")}
    if len(cfgs) > 1:
        errors.append(f"inconsistent config fingerprints across B0 runs: {sorted(cfgs)}")
    aqe = {r.get("aqe_mode") for r in runs if r.get("run_id")}
    if aqe != {"off"}:
        errors.append(f"B0 runs reported aqe_mode != 'off': {aqe}")

    # Per-run manifest files on disk
    n_manifest = 0
    for r in runs:
        rid = r.get("run_id")
        if not rid:
            continue
        rep = r.get("rep")
        path = (results / r["family"] / r["scale"]
                / f"seed{r['seed']}" / f"run-{rep}.json")
        if not path.is_file():
            errors.append(f"missing manifest file: {path}")
            continue
        n_manifest += 1
        m = json.loads(path.read_text(encoding="utf-8"))
        for field in REQUIRED_MANIFEST_FIELDS:
            if field not in m:
                errors.append(f"{path}: missing field {field}")
        if m["run_id"] != rid:
            errors.append(f"{path}: run_id mismatch with registry")
        if m.get("usable") and m.get("event_log_status") != "COMPLETE":
            errors.append(f"{path}: usable=True but status={m.get('event_log_status')}")
        if m.get("usable") and not m.get("result_signature"):
            errors.append(f"{path}: usable but no result_signature")

    # Summary agrees with per-run manifests
    summary_path = results / "b0_summary.json"
    if not summary_path.exists():
        errors.append("missing results/baseline/b0_summary.json")
    else:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        usable_families = {r["family"] for r in runs if r.get("usable")}
        if not usable_families == EXPECTED_FAMILIES:
            errors.append(
                f"usable-family set {sorted(usable_families)} != {sorted(EXPECTED_FAMILIES)}")
        summary_families = {v["family"] for k, v in summary.items()}
        if summary_families != EXPECTED_FAMILIES:
            errors.append(f"summary families {sorted(summary_families)} "
                          f"!= {sorted(EXPECTED_FAMILIES)}")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS: B0 config present, {len(runs)} registered runs "
          f"({n_manifest} manifests), 5/5 families usable, config fingerprint "
          f"consistent, AQE off, summaries agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())