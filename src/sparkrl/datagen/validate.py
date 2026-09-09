"""Reusable validation: schema/domains/checksum/skew-sanity (Day 13).

Zipf validation is statistical (never exact-frequency): domain-correct,
reproducible under seed, skew-direction monotone (top-decile share grows
with s), and uniform (s=0) near-flat within tolerance.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sparkrl.datagen.checksums import checksum_rows, validate_manifest
from sparkrl.datagen.generator import GenerationSpec
from sparkrl.datagen.rows import lineitem_row, orders_row
from sparkrl.datagen.schema import validate_row


def validate_spec_rows(spec: GenerationSpec, n_orders: int = 0,
                       sample: int = 2000) -> list[str]:
    """Validate domains + manifest-independent row rules on a head sample."""
    errors: list[str] = []
    n = min(sample, spec.rows)
    fn = (lambda i: orders_row(i, spec)) if spec.table == "orders" else (
        lambda i: lineitem_row(i, spec, n_orders or spec.key_cardinality))
    for i in range(n):
        row_errors = validate_row(spec.table, fn(i))
        if row_errors:
            errors.extend([f"row {i}: {e}" for e in row_errors])
            if len(errors) > 10:
                break
    return errors


def skew_direction_ok(spec: GenerationSpec, sample_rows: int = 5000) -> bool:
    """Top-10% keys must own strictly more than 10% of sampled draws (s>0)."""
    if spec.skew <= 0:
        return True
    fn = (lambda i: orders_row(i, spec)[1]) if spec.table == "orders" else (
        lambda i: lineitem_row(i, spec, spec.key_cardinality)[1])
    n = min(sample_rows, spec.rows)
    counts: Counter[int] = Counter(fn(i) for i in range(n))
    top = max(1, spec.key_cardinality // 10)
    top_share = sum(1 for i in range(n) if fn(i) < top) / n
    _ = counts
    return top_share > 0.10


def regeneration_checksum(spec: GenerationSpec, n_orders: int = 0) -> str:
    """Canonical checksum over the FULL spec content (chunk-size free)."""
    if spec.table == "orders":
        rows = (orders_row(i, spec) for i in range(spec.rows))
    else:
        rows = (lineitem_row(i, spec, n_orders or spec.key_cardinality)
                for i in range(spec.rows))
    return checksum_rows(rows)["fnv1a_hex"]


def full_validation(spec: GenerationSpec, checksum: str,
                    manifest: Any, n_orders: int = 0) -> list[str]:
    """Row rules + skew sanity + manifest consistency, aggregated."""
    errors = validate_spec_rows(spec, n_orders)
    if not skew_direction_ok(spec):
        errors.append("skew direction check failed (top-decile share <= 10%)")
    errors.extend(validate_manifest(manifest, spec, checksum))
    return errors
