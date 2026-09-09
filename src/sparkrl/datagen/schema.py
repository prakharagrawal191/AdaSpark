"""Canonical synthetic-data schema for AdaSpark (Day 13).

One reusable schema (NOT per-workload schemas): two tables, ORDERS and
LINEITEM, from which later workload families derive views (PLAN Day-14+).

Day-13 implementation conventions (NOT frozen research decisions — the
frozen plan fixes only: Parquet storage, seeded RNG, Zipf skew mix,
0.3-3 GB ladder, S/M/L naming):
- schema_version "datagen-v1"; fingerprint = SHA-256 over canonical DDL.
- orders.cust_key and lineitem.order_key are the skew-relevant keys drawn
  from the seeded Zipf stream; all other columns are pure functions of
  (row_index, seed) so they are chunking-independent.
- Draw order per row is part of the spec (schema version covers it):
  orders row draws [cust_key]; lineitem row draws [order_key, part_key,
  quantity] in that order from a single random.Random(seed) stream.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

SCHEMA_VERSION = "datagen-v1"
GENERATOR_VERSION = "datagen-v1"


@dataclass(frozen=True)
class Field:
    """One canonical field: name, logical type, meaning, nullability, domain, rule."""

    name: str
    dtype: str  # one of: long, int, double, string
    meaning: str
    nullable: bool
    domain: str
    rule: str


ORDERS_FIELDS: tuple[Field, ...] = (
    Field("order_key", "long", "Primary key, dense 0..N-1", False,
          "[0, N_orders)", "rule=id (row index)"),
    Field("cust_key", "long", "Customer key, Zipf-skewed (skew driver)",
          False, "[0, K_cust)", "draw=zipf(s, K_cust) from seeded stream"),
    Field("order_day", "int", "Order date as day-of-year", False,
          "[0, 365)", "rule=(order_key * 2654435761 + seed) % 365"),
)

LINEITEM_FIELDS: tuple[Field, ...] = (
    Field("line_key", "long", "Primary key, dense 0..N-1", False,
          "[0, N_lineitem)", "rule=id (row index)"),
    Field("order_key", "long", "FK into orders (join-skew driver)", False,
          "[0, N_orders)", "draw=zipf(s, N_orders) from seeded stream"),
    Field("part_key", "long", "Part key, uniform (non-skewed contrast)",
          False, "[0, P_part)", "draw=uniform int [0, P_part) from stream"),
    Field("quantity", "int", "Line quantity", False,
          "[1, 50]", "draw=uniform int [1, 50] from stream"),
    Field("extended_price", "double", "Line price, derived deterministically",
          False, "> 0", "rule=quantity * (10.0 + (part_key % 90))"),
)

TABLES: dict[str, tuple[Field, ...]] = {
    "orders": ORDERS_FIELDS,
    "lineitem": LINEITEM_FIELDS,
}

_SPARK_TYPE = {"long": "LongType()", "int": "IntegerType()",
               "double": "DoubleType()", "string": "StringType()"}


def canonical_ddl(table: str) -> str:
    """Canonical DDL string; the exact bytes fingerprinted for provenance."""
    fields = require_table(table)
    cols = ", ".join(f"{f.name}:{f.dtype}"
                     + ("" if not f.nullable else "?") for f in fields)
    return f"{table}({cols})@{SCHEMA_VERSION}"


def schema_fingerprint(table: str) -> str:
    """Stable SHA-256 over the canonical DDL (schema identity for manifests)."""
    return hashlib.sha256(canonical_ddl(table).encode("utf-8")).hexdigest()


def require_table(table: str) -> tuple[Field, ...]:
    """Return field tuple or raise ValueError on unknown table."""
    try:
        return TABLES[table]
    except KeyError:
        raise ValueError(
            f"unknown table {table!r}; expected one of {sorted(TABLES)}") from None


def column_names(table: str) -> list[str]:
    """Column names in canonical order."""
    return [f.name for f in require_table(table)]


def validate_row(table: str, row: tuple) -> list[str]:
    """Check nullability/domain/range of a canonical-order row tuple."""
    fields = require_table(table)
    errors: list[str] = []
    if len(row) != len(fields):
        return [f"expected {len(fields)} columns, got {len(row)}"]
    for value, field in zip(row, fields):
        if value is None:
            if not field.nullable:
                errors.append(f"{field.name}: null violates NOT NULL")
            continue
        if field.dtype in ("long", "int") and not isinstance(value, int):
            errors.append(f"{field.name}: expected int, got {type(value).__name__}")
        elif field.dtype == "double" and not isinstance(value, (int, float)):
            errors.append(f"{field.name}: expected float, got {type(value).__name__}")
        if field.name == "quantity" and isinstance(value, int):
            if not 1 <= value <= 50:
                errors.append(f"quantity out of range: {value}")
        if field.name == "order_day" and isinstance(value, int):
            if not 0 <= value < 365:
                errors.append(f"order_day out of range: {value}")
        if field.name == "extended_price" and isinstance(value, (int, float)):
            if value <= 0:
                errors.append(f"extended_price not positive: {value}")
    return errors


def to_spark_schema(table: str):
    """Build a pyspark StructType (lazy import: unit env stays Spark-free)."""
    from pyspark.sql.types import (DoubleType, IntegerType, LongType,
                                   StringType, StructField, StructType)
    mapping = {"long": LongType(), "int": IntegerType(),
               "double": DoubleType(), "string": StringType()}
    return StructType([StructField(f.name, mapping[f.dtype], f.nullable)
                       for f in require_table(table)])
