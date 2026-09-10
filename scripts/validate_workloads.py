"""Structural validator for the Day-15 workload layer.

Checks repository structure and metadata consistency ONLY:
- all five frozen families are registered with stable versions
- unique workload IDs, no missing family
- required documentation exists
- generated smoke-test manifests (if present) contain the required fields

It does NOT prove academic correctness of workload results; that is the
job of the per-family validators and the later experiments.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sparkrl.workloads.registry import REGISTRY  # noqa: E402

EXPECTED_FAMILIES = {"F1_agg", "F2_join", "F3_rdd", "F4_ski", "F5_mixed"}
EXPECTED_VERSIONS = {
    "F1_agg": "F1_agg_v1", "F2_join": "F2_join_v1", "F3_rdd": "F3_rdd_v1",
    "F4_ski": "F4_ski_v1", "F5_mixed": "F5_mixed_v1",
}
REQUIRED_DOCS = [
    "docs/day15_workloads.md", "docs/WORKLOAD_INVENTORY.md",
    "src/sparkrl/workloads/base.py", "src/sparkrl/workloads/resolver.py",
    "src/sparkrl/workloads/families.py", "src/sparkrl/workloads/registry.py",
    "scripts/run_workload.py",
]
REQUIRED_MANIFEST_FIELDS = [
    "workload_id", "family", "scale", "seed", "dataset_id",
    "dataset_fingerprint", "schema_fingerprint", "workload_version",
    "spark_version", "configuration_fingerprint", "aqe_mode", "success",
    "result_signature", "rows_processed", "execution_time_s", "timestamp",
    "code_version", "correctness", "performance",
]


def main() -> int:
    errors: list[str] = []

    # 1. Registry: all five families, unique IDs, stable versions.
    registered = set(REGISTRY.keys())
    missing = EXPECTED_FAMILIES - registered
    extra = registered - EXPECTED_FAMILIES
    if missing:
        errors.append(f"missing families in registry: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected families in registry: {sorted(extra)}")
    ids = [getattr(cls, "workload_id", None) for cls in REGISTRY.values()]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate workload IDs: {ids}")
    for fam, cls in REGISTRY.items():
        if EXPECTED_VERSIONS.get(fam) != getattr(cls, "workload_version", None):
            errors.append(f"{fam}: version {getattr(cls, 'workload_version', None)!r}"
                          f" != expected {EXPECTED_VERSIONS.get(fam)!r}")

    # 2. Required documentation and modules exist.
    for path in REQUIRED_DOCS:
        if not Path(path).exists():
            errors.append(f"missing required file: {path}")

    # 3. Manifests that exist must be structurally complete.
    results = Path("results/workloads")
    n_manifests = 0
    if results.exists():
        for mf in sorted(results.rglob("manifest.json")):
            n_manifests += 1
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                errors.append(f"{mf}: unreadable manifest ({exc})")
                continue
            for field in REQUIRED_MANIFEST_FIELDS:
                if field not in m:
                    errors.append(f"{mf}: missing field {field}")
            if m.get("success") is not True:
                errors.append(f"{mf}: success is not true")
            if m.get("family") not in EXPECTED_FAMILIES:
                errors.append(f"{mf}: invalid family {m.get('family')!r}")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS: 5/5 families registered with stable versions, "
          f"{len(REQUIRED_DOCS)} required files present, "
          f"{n_manifests} manifest(s) structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
