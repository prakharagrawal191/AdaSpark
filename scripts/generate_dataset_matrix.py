#!/usr/bin/env python
"""Day-14 batch dataset matrix generator (idempotent, resumable).

Approved substrate (docs/PLAN.md sections 11/16/18):
  logical families : F1_agg F2_join F3_rdd F4_ski F5_mixed
  scales           : small medium large (lineitem rows 3/10/30 M)
  seeds            : {0, 1, 2, 3, 4}
  skews            : 1.0 (F1,F2,F3,F5), 1.5 (F4)

Physical matrix = 2 skews x 3 scales x 5 seeds = 30 datasets.
Logical matrix  = 5 families x 3 scales x 5 seeds = 75 entries
                  (F1/F2/F3/F5 share the skew=1.0 physical data; F4 uses 1.5).

Layout (outside Git; SPARKRL_DATA_ROOT or ./data):
  <root>/generated/datasets/skew<skew>_<scale>_s<seed>/
      orders/    data/*.parquet  manifest.json
      lineitem/  data/*.parquet  manifest.json
  <root>/generated/index.json
  <root>/generated/summary.json

Idempotent: a dataset with BOTH valid manifests (matching generation
fingerprint + row count) and at least one parquet file per table is SKIPPED.
Missing/failed tables are regenerated; corrupt output is quarantined first.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.datagen.checksums import DatasetManifest, build_manifest  # noqa: E402
from sparkrl.datagen.rows import spec_for_scale  # noqa: E402
from sparkrl.datagen.validate import full_validation  # noqa: E402
from sparkrl.datagen.writer import generate_table  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.spark.session import build_session, stop_session  # noqa: E402

DATA_ROOT = Path(os.environ.get("SPARKRL_DATA_ROOT", "data")).expanduser().resolve()
GENERATED_DIR = DATA_ROOT / "generated"
DATASETS_DIR = GENERATED_DIR / "datasets"
INDEX_PATH = GENERATED_DIR / "index.json"
SUMMARY_PATH = GENERATED_DIR / "summary.json"

FAMILIES = ["F1_agg", "F2_join", "F3_rdd", "F4_ski", "F5_mixed"]
SCALES = ["small", "medium", "large"]
SEEDS = [0, 1, 2, 3, 4]
SKEWS = [1.0, 1.5]
FAMILY_SKEW = {"F1_agg": 1.0, "F2_join": 1.0, "F3_rdd": 1.0,
               "F4_ski": 1.5, "F5_mixed": 1.0}
SCALE_LINE_ROWS = {"small": 3_000_000, "medium": 10_000_000, "large": 30_000_000}
LINEITEM_TO_ORDERS = 4
DEFAULT_CHUNK_ROWS = 100_000
def ordered_matrix() -> list[tuple[float, str, int]]:
    """All (skew, scale, seed) triples in a deterministic order."""
    return [(sk, sc, sd) for sk in SKEWS for sc in SCALES for sd in SEEDS]


def phys_id(skew: float, scale: str, seed: int) -> str:
    return f"skew{skew:g}_{scale}_s{seed}"


def phys_dir(skew: float, scale: str, seed: int) -> Path:
    return DATASETS_DIR / phys_id(skew, scale, seed)


def expected_spec(table: str, scale: str, seed: int, skew: float,
                  chunk_rows: int = DEFAULT_CHUNK_ROWS):
    """Canonical GenerationSpec for one table of one physical dataset."""
    return spec_for_scale(table, scale, seed=seed, skew=skew,
                          key_cardinality=None, chunk_rows=chunk_rows)


def disk_requirement_bytes(todo: list[tuple[float, str, int]]) -> int:
    """Free bytes a run needs for the REQUESTED datasets: estimate + margin.

    The estimate is the uncompressed size of the requested tables at 60 bytes
    per row (Parquet output is 3-10x smaller). The margin, for Spark's
    temporary files, equals the estimate clamped to 1-10 GiB. One small
    dataset therefore needs about 1.2 GiB free; the full 30-dataset matrix
    needs the same 40 GiB as the original full-matrix check.
    """
    rows = sum(SCALE_LINE_ROWS[sc] + SCALE_LINE_ROWS[sc] // LINEITEM_TO_ORDERS
               for _, sc, _ in todo)
    estimate = rows * 60
    return estimate + min(10 * 1024**3, max(1024**3, estimate))


def _disk_preflight(todo: list[tuple[float, str, int]]) -> float:
    free_gb = shutil.disk_usage(str(DATA_ROOT)).free / 1024**3
    need_gb = disk_requirement_bytes(todo) / 1024**3
    print(f"[PREF] data_root={DATA_ROOT}")
    print(f"[PREF] free={free_gb:.1f} GiB need={need_gb:.1f} GiB for "
          f"{len(todo)} dataset(s) (uncompressed estimate + Spark temp margin)")
    if free_gb < need_gb:
        print("[FATAL] free disk below the requirement; stopping",
              file=sys.stderr)
        sys.exit(2)
    return free_gb


def _spark_session():
    if os.environ.get("SPARKRL_SKIP_SPARK", "").strip().lower() in ("1", "true", "yes"):
        print("[FATAL] SPARKRL_SKIP_SPARK set; cannot generate datasets",
              file=sys.stderr)
        sys.exit(2)
    cfg = SparkConfig(event_log_enabled=False, aqe_enabled=False,
                      warmup_micro_job=False)
    spark = build_session(cfg, app_suffix="datagen-batch-d14")
    print("[SPARK] session ready for batch generation")
    return spark


def read_manifest(tdir: Path):
    """Load a per-table manifest; None if absent or malformed."""
    mp = tdir / "manifest.json"
    if not mp.exists():
        return None
    try:
        return DatasetManifest(**json.loads(mp.read_text(encoding="utf-8")))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def table_valid(tdir: Path, spec) -> dict[str, Any]:
    """Check an existing table dir: manifest + fingerprint + row + files."""
    result: dict[str, Any] = {"ok": False, "errors": [], "manifest": None}
    man = read_manifest(tdir)
    if man is None:
        result["errors"].append("manifest missing/invalid")
        return result
    result["manifest"] = man
    if man.generation_fingerprint != spec.fingerprint():
        result["errors"].append("generation_fingerprint mismatch")
    if man.row_count != spec.rows:
        result["errors"].append(f"row_count {man.row_count} != expected {spec.rows}")
    data = tdir / "data"
    parts = list(data.glob("*.parquet")) if data.exists() else []
    if not parts:
        result["errors"].append("no parquet files")
    result["ok"] = not result["errors"]
    return result
def _generate_table(spark, table: str, scale: str, seed: int, skew: float,
                    pdir: Path, chunk_rows: int) -> bool:
    """Generate one table fully (chunked) with validation; True on success."""
    tdir = pdir / table
    tdir.mkdir(parents=True, exist_ok=True)
    spec = expected_spec(table, scale, seed, skew, chunk_rows)
    n_orders = spec.rows if table == "orders" else max(1, spec.rows // LINEITEM_TO_ORDERS)
    print(f"  gen {table:9s} rows={spec.rows:>9,} chunk={chunk_rows:,} ...",
          end=" ", flush=True)
    t0 = time.time()
    info = generate_table(spark, spec, tdir, n_orders=n_orders)
    dt = time.time() - t0
    manifest = build_manifest(
        dataset_id=f"{table}-{phys_id(skew, scale, seed)}", spec=spec,
        checksum=info["checksum"], file_count=info["file_count"],
        total_bytes=info["total_bytes"], code_version="matrix-d14")
    errors = full_validation(spec, info["checksum"], manifest, n_orders=n_orders)
    if errors:
        print("FAIL validation")
        for e in errors:
            print(f"    - {e}")
        return False
    (tdir / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    print(f"OK files={info['file_count']} bytes={info['total_bytes']:,} "
          f"dt={dt:.1f}s checksum={manifest.checksum[:10]}...")
    return True


def gen_physical(spark, skew: float, scale: str, seed: int,
                 chunk_rows: int, force: bool = False) -> bool:
    """Ensure one physical dataset is present and valid; True when VALID."""
    pid = phys_id(skew, scale, seed)
    pdir = phys_dir(skew, scale, seed)
    pdir.mkdir(parents=True, exist_ok=True)
    status_ok = True
    for table in ("orders", "lineitem"):
        spec = expected_spec(table, scale, seed, skew, chunk_rows)
        tdir = pdir / table
        if not force:
            check = table_valid(tdir, spec)
            if check["ok"]:
                continue  # already valid -> SKIP
            print(f"[CORRUPT] {pid} {table}: {check['errors']}")
            quar = pdir / f".quarantine_{table}_{int(time.time())}"
            if tdir.exists():
                tdir.rename(quar)
            tdir.mkdir(parents=True, exist_ok=True)
        if not _generate_table(spark, table, scale, seed, skew, pdir, chunk_rows):
            status_ok = False
    print(f"[DONE] {pid}")
    return status_ok


def _collect_physical() -> list[dict[str, Any]]:
    """Read manifests + sizes for every expected physical dataset."""
    entries: list[dict[str, Any]] = []
    for skew, scale, seed in ordered_matrix():
        pdir = phys_dir(skew, scale, seed)
        entry = {"id": phys_id(skew, scale, seed), "skew": skew,
                 "scale": scale, "seed": seed, "status": "MISSING",
                 "tables": {}}
        all_ok = True
        any_table = False
        for table in ("orders", "lineitem"):
            spec = expected_spec(table, scale, seed, skew)
            check = table_valid(pdir / table, spec)
            entry["tables"][table] = {}
            if not check["ok"]:
                all_ok = False
                entry["tables"][table]["errors"] = check["errors"]
                continue
            any_table = True
            man = check["manifest"]
            entry["tables"][table] = {
                "row_count": man.row_count, "seed": man.seed,
                "zipf_parameter": man.zipf_parameter,
                "key_cardinality": man.key_cardinality,
                "file_count": man.file_count, "total_bytes": man.total_bytes,
                "checksum": man.checksum,
                "generation_fingerprint": man.generation_fingerprint,
            }
        if all_ok and any_table:
            entry["status"] = "VALID"
        entries.append(entry)
    return entries
def build_index(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Machine-readable inventory: physical + logical views, relative paths."""
    logical: list[dict[str, Any]] = []
    for fam in FAMILIES:
        for sc in SCALES:
            for sd in SEEDS:
                sk = FAMILY_SKEW[fam]
                logical.append({"family": fam, "scale": sc, "seed": sd,
                                "skew": sk, "physical_id": phys_id(sk, sc, sd),
                                "status": "MAPPED"})
    return {
        "doc": "AdaSpark Day-14 dataset inventory; paths relative to "
               "SPARKRL_DATA_ROOT (never machine-specific)",
        "generator_version": "datagen-v1", "schema_version": "datagen-v1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "data_root_env": "SPARKRL_DATA_ROOT",
        "families": FAMILIES, "scales": SCALES, "seeds": SEEDS,
        "lineitem_to_orders": LINEITEM_TO_ORDERS,
        "physical": entries, "logical": logical,
    }


def write_inventory(index: dict[str, Any]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, sort_keys=True, indent=2),
                          encoding="utf-8")
    print(f"[IDX] wrote {INDEX_PATH}")


def write_summary(index: dict[str, Any]) -> dict[str, Any]:
    """Actual sizes by family/scale/seed from manifests (not estimates)."""
    phys = index["physical"]
    aggregate = {
        "total_physical": len(phys), "total_logical": len(index["logical"]),
        "valid_physical": sum(1 for e in phys if e["status"] == "VALID"),
        "missing_physical": sum(1 for e in phys if e["status"] == "MISSING"),
        "total_rows": sum(t.get("row_count", 0)
                          for e in phys for t in e["tables"].values()
                          if isinstance(t, dict) and "row_count" in t),
        "total_bytes": sum(t.get("total_bytes", 0)
                           for e in phys for t in e["tables"].values()
                           if isinstance(t, dict) and "total_bytes" in t),
    }
    aggregate["total_gib"] = round(aggregate["total_bytes"] / 1024**3, 4)
    by_scale: dict[str, int] = {}
    by_family: dict[str, int] = {}
    by_seed: dict[str, int] = {}
    for e in phys:
        line_bytes = (e["tables"].get("lineitem") or {}).get("total_bytes", 0)
        table_bytes = sum((t or {}).get("total_bytes", 0)
                          for t in e["tables"].values())
        by_scale[e["scale"]] = by_scale.get(e["scale"], 0) + table_bytes
        by_seed[str(e["seed"])] = by_seed.get(str(e["seed"]), 0) + table_bytes
        for fam, fam_skew in FAMILY_SKEW.items():
            if abs(fam_skew - e["skew"]) < 1e-12:
                by_family[fam] = by_family.get(fam, 0) + line_bytes
    aggregate["bytes_by_scale"] = by_scale
    aggregate["bytes_by_seed"] = by_seed
    aggregate["lineitem_bytes_by_family"] = by_family
    SUMMARY_PATH.write_text(json.dumps(aggregate, sort_keys=True, indent=2),
                            encoding="utf-8")
    print(f"[SUM] wrote {SUMMARY_PATH}")
    return aggregate
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scale", choices=SCALES, default=None)
    ap.add_argument("--seed", type=int, choices=SEEDS, default=None)
    ap.add_argument("--skew", type=float, choices=SKEWS, default=None)
    ap.add_argument("--chunk-rows", type=int, default=DEFAULT_CHUNK_ROWS)
    ap.add_argument("--force", action="store_true",
                    help="regenerate even if existing manifests look valid")
    ap.add_argument("--plan-only", action="store_true",
                    help="print planned matrix and exit")
    args = ap.parse_args(argv)

    print("=== Planned matrix: family x scale x seed -> physical ===\n")
    for fam in FAMILIES:
        for sc in SCALES:
            for sd in SEEDS:
                print(f"  {fam} x {sc:6s} x s{sd}  ->  "
                      f"{phys_id(FAMILY_SKEW[fam], sc, sd)}")
    print(f"\n  LOGICAL={len(FAMILIES) * len(SCALES) * len(SEEDS)}  "
          f"PHYSICAL={len(ordered_matrix())}")
    if args.plan_only:
        return 0

    todo = [(sk, sc, sd) for sk, sc, sd in ordered_matrix()
            if (args.scale is None or sc == args.scale)
            and (args.seed is None or sd == args.seed)
            and (args.skew is None or sk == args.skew)]
    if not todo:
        print("no matrix rows match the provided filters")
        return 2

    DATASETS_DIR.mkdir(parents=True, exist_ok=True)  # also creates a new data root
    _disk_preflight(todo)

    spark = _spark_session()
    try:
        for skew, scale, seed in todo:
            if not gen_physical(spark, skew, scale, seed, args.chunk_rows,
                                force=args.force):
                print(f"[ABORT] generation failed at "
                      f"{phys_id(skew, scale, seed)}")
                return 1
    finally:
        stop_session(spark)

    entries = _collect_physical()
    index = build_index(entries)
    write_inventory(index)
    summary = write_summary(index)
    requested = {phys_id(sk, sc, sd) for sk, sc, sd in todo}
    valid = sum(1 for e in entries if e["id"] in requested and e["status"] == "VALID")
    print(f"\n[RESULT] requested {valid}/{len(requested)} VALID; matrix "
          f"{summary['valid_physical']}/{summary['total_physical']} physical "
          f"datasets VALID; missing={summary['missing_physical']} "
          f"total_rows={summary['total_rows']:,} total_gib="
          f"{summary['total_gib']}")
    # A filtered run succeeds when everything it was asked for is valid; an
    # unfiltered run asks for the whole matrix, as before.
    return 0 if valid == len(requested) else 1


if __name__ == "__main__":
    raise SystemExit(main())
