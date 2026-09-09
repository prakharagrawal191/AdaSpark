"""Chunked Parquet writer: bounded-memory generation (Day 13).

Memory contract: at most one chunk (default <= 100k rows of narrow tuples)
is materialized at a time; chunk -> write -> discard -> next. Peak is
O(chunk_rows), independent of total N. Spark writes each chunk as one
Parquet part-file via createDataFrame (schema-bound, deterministic column
order); content identity comes from the canonical checksum, NOT file bytes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkrl.datagen.checksums import checksum_rows, encode_row
from sparkrl.datagen.generator import GenerationSpec
from sparkrl.datagen.rows import iter_chunks, lineitem_row, orders_row
from sparkrl.datagen.schema import column_names, to_spark_schema


def _row_fn(spec: GenerationSpec, n_orders: int):
    if spec.table == "orders":
        return lambda i: orders_row(i, spec)
    return lambda i: lineitem_row(i, spec, n_orders)


def generate_table(spark, spec: GenerationSpec, out_dir: str | Path,
                   n_orders: int = 0) -> dict[str, Any]:
    """Generate one table in chunks; return {checksum, row_count, files, bytes}.

    Writes part-00000{i}.parquet per chunk under out_dir/data. Caller passes
    n_orders for the lineitem FK domain (orders rows of the same dataset).
    """
    out = Path(out_dir)
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    schema = to_spark_schema(spec.table)
    columns = column_names(spec.table)
    row_fn = _row_fn(spec, n_orders)
    from sparkrl.datagen.checksums import _FNV_OFFSET, _fnv1a_64
    state = _FNV_OFFSET
    count = 0
    first = True
    for chunk_id, (start, end) in enumerate(iter_chunks(spec)):
        rows = [row_fn(i) for i in range(start, end)]
        for row in rows:
            state = _fnv1a_64(encode_row(row), state)
            state = _fnv1a_64(b"\n", state)
        df = spark.createDataFrame(rows, schema=schema)
        mode = "overwrite" if first else "append"
        df.coalesce(1).write.mode(mode).parquet(str(data_dir))
        first = False
        del rows, df
        count += end - start
    part_files = list(data_dir.glob("*.parquet"))
    total_bytes = sum(p.stat().st_size for p in part_files)
    return {"checksum": format(state, "016x"), "row_count": count,
            "file_count": len(part_files), "total_bytes": total_bytes}
