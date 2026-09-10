#!/usr/bin/env python
"""Run one frozen workload family through the shared Spark foundation.

Usage:
    python scripts/run_workload.py --family F1_agg --scale small --seed 0

Flow: resolve (family, scale, seed) -> physical dataset (resolver, never
substitutes) -> build session (COMP-SPARK-01/02) -> run with warm-up,
timing, timeout (COMP-SPARK-04 runner, Day-3 harness) -> validate logical
result -> emit manifest JSON (correctness data separate from performance
data). Exit non-zero on failure; never reports success on a failed
validation. AQE is read from the Spark config layer and recorded, never
toggled by the workload.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.spark import config as spark_config  # noqa: E402
from sparkrl.spark import runner as spark_runner  # noqa: E402
from sparkrl.spark import session as spark_session  # noqa: E402
from sparkrl.workloads.registry import REGISTRY, get_workload  # noqa: E402
from sparkrl.workloads.resolver import resolve_dataset  # noqa: E402

REQUIRED_MANIFEST_FIELDS = (
    "workload_id", "family", "scale", "seed", "dataset_id",
    "dataset_fingerprint", "schema_fingerprint", "workload_version",
    "spark_version", "configuration_fingerprint", "aqe_mode", "success",
    "result_signature", "rows_processed", "execution_time_s", "timestamp",
    "code_version",
)

_AQE_FLAG: dict[str, bool] = {"enabled": False}


def build_manifest(workload, resolved, run_result, workload_result,
                   spark_version: str, code_version: str) -> dict:
    """Assemble the manifest (correctness data split from performance)."""
    return {
        "workload_id": workload.workload_id,
        "family": workload.spec.family,
        "scale": workload.spec.scale,
        "seed": workload.spec.seed,
        "dataset_id": resolved.dataset_id,
        "dataset_fingerprint": resolved.dataset_fingerprint,
        "schema_fingerprint": resolved.schema_fingerprint,
        "workload_version": workload.workload_version,
        "spark_version": spark_version,
        "configuration_fingerprint": run_result.config_fingerprint,
        "aqe_mode": "on" if _AQE_FLAG["enabled"] else "off",
        "success": bool(run_result.success and workload_result.success),
        "result_signature": workload_result.result_signature,
        "rows_processed": workload_result.rows_processed,
        "execution_time_s": round(run_result.execution_time, 4),
        "warmup_time_s": round(run_result.warmup_time, 4),
        "total_time_s": round(run_result.total_time, 4),
        "timeout": run_result.timeout,
        "error": run_result.error or workload_result.error,
        "spark_app_id": run_result.spark_app_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code_version": code_version,
        "correctness": {
            "validated": workload.validate(workload_result),
            "columns": list(workload_result.columns),
            "measurements": dict(workload_result.measurements),
        },
        "performance": {
            "execution_time_s": round(run_result.execution_time, 4),
            "warmup_time_s": round(run_result.warmup_time, 4),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run one frozen workload family")
    ap.add_argument("--family", required=True, choices=sorted(REGISTRY))
    ap.add_argument("--scale", required=True,
                    choices=("small", "medium", "large"))
    ap.add_argument("--seed", required=True, type=int,
                    choices=(0, 1, 2, 3, 4))
    ap.add_argument("--config", default=str(PROJECT / "configs" / "spark.yaml"))
    ap.add_argument("--out", default=str(PROJECT / "results" / "workloads"))
    ap.add_argument("--code-version", default="day15")
    ap.add_argument("--print-manifest", action="store_true")
    args = ap.parse_args(argv)

    cfg = spark_config.SparkConfig.from_yaml(args.config)
    _AQE_FLAG["enabled"] = bool(cfg.aqe_enabled)

    try:
        resolved = resolve_dataset(args.family, args.scale, args.seed)
    except (ValueError, FileNotFoundError) as exc:
        print(f"RESOLUTION FAILED: {exc}")
        return 2
    workload = get_workload(args.family, args.scale, args.seed)

    spark = spark_session.build_session(cfg, app_suffix=f"d15-{args.family}")
    try:
        spark_version = spark.version
        run_result = spark_runner.run_workload(spark, workload, cfg)
    finally:
        spark_session.stop_session(spark)

    if not run_result.success:
        print(f"RUN FAILED: {run_result.error} (timeout={run_result.timeout})")
        return 1
    workload_result = run_result.checksum
    if not hasattr(workload_result, "result_signature"):
        print("RUN FAILED: workload returned no WorkloadResult payload")
        return 1
    if not workload.validate(workload_result):
        print("VALIDATION FAILED: logical result did not validate")
        return 1

    manifest = build_manifest(workload, resolved, run_result,
                              workload_result, spark_version,
                              args.code_version)
    out_dir = Path(args.out) / args.family / args.scale / f"seed{args.seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True),
                             encoding="utf-8")
    print(f"family={args.family} scale={args.scale} seed={args.seed} "
          f"dataset={resolved.physical_id} "
          f"signature={workload_result.result_signature} "
          f"exec_s={run_result.execution_time:.3f} manifest={manifest_path}")
    if args.print_manifest:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


