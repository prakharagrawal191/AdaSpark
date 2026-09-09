"""Day-13 dataset generator CLI: validate -> generate -> Parquet -> manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sparkrl.datagen.checksums import build_manifest  # noqa: E402
from sparkrl.datagen.rows import spec_for_scale  # noqa: E402
from sparkrl.datagen.validate import full_validation  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402
from sparkrl.spark.session import build_session, stop_session  # noqa: E402


def parse_args(argv=None):
    """CLI args: table/scale/seed/skew/out; research scales need confirm."""
    parser = argparse.ArgumentParser(description="Generate a Day-13 dataset")
    parser.add_argument("--table", choices=["orders", "lineitem"],
                        default="orders")
    parser.add_argument("--scale", default="micro",
                        choices=["micro", "small", "medium", "large"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skew", type=float, default=1.0)
    parser.add_argument("--key-cardinality", type=int, default=None)
    parser.add_argument("--chunk-rows", type=int, default=100_000)
    parser.add_argument("--out", required=True,
                        help="output dataset directory ( NOT in Git)")
    parser.add_argument("--allow-large", action="store_true",
                        help="required for small/medium/large scales")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Validate args, generate, checksum, manifest, print summary."""
    args = parse_args(argv)
    if args.scale in ("small", "medium", "large") and not args.allow_large:
        print(f"refusing {args.scale} without --allow-large "
              f"(Day-13: validate micro first)", file=sys.stderr)
        return 2
    if args.seed < 0 or not 0 <= args.skew <= 5.0:
        print("seed must be >= 0 and skew in [0, 5]", file=sys.stderr)
        return 2
    spec = spec_for_scale(args.table, args.scale, seed=args.seed,
                          skew=args.skew, key_cardinality=args.key_cardinality,
                          chunk_rows=args.chunk_rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    spark = build_session(SparkConfig(), app_suffix="datagen")
    try:
        from sparkrl.datagen.writer import generate_table
        n_orders = (spec.rows if spec.table == "orders"
                    else max(1, spec.rows // 4))
        info = generate_table(spark, spec, out, n_orders=n_orders)
    finally:
        stop_session(spark)
    manifest = build_manifest(f"{args.table}-{args.scale}-s{args.seed}",
                              spec, info["checksum"], info["file_count"],
                              info["total_bytes"], code_version="cli")
    errors = full_validation(spec, info["checksum"], manifest,
                             n_orders=n_orders)
    if errors:
        print("validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    (out / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    print(json.dumps({"dataset": manifest.dataset_id,
                      "rows": info["row_count"],
                      "files": info["file_count"],
                      "bytes": info["total_bytes"],
                      "checksum": info["checksum"],
                      "fingerprint": spec.fingerprint(),
                      "manifest": str(out / "manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
