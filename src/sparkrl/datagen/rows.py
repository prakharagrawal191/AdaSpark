"""Row-level generation helpers (appended to generator.py by Day-13 assembly)."""
from __future__ import annotations

import random

from sparkrl.datagen.distributions import ZipfSampler


def spec_for_scale(table: str, scale: str, seed: int = 42,
                   skew: float = 1.0,
                   key_cardinality: int | None = None,
                   chunk_rows: int = 100_000):
    """Canonical spec for (table, scale); orders rows = lineitem/4."""
    from sparkrl.datagen.generator import (DEFAULT_PART_CARDINALITY,
                                           GenerationSpec,
                                           LINEITEM_TO_ORDERS,
                                           SCALE_ROWS_LINEITEM,
                                           DEFAULT_CUST_CARDINALITY)
    if scale not in SCALE_ROWS_LINEITEM:
        raise ValueError(
            f"scale must be one of {sorted(SCALE_ROWS_LINEITEM)}, got {scale!r}")
    line_rows = SCALE_ROWS_LINEITEM[scale]
    rows = line_rows if table == "lineitem" else max(1, line_rows // LINEITEM_TO_ORDERS)
    if key_cardinality is None:
        key_cardinality = (DEFAULT_CUST_CARDINALITY if table == "orders"
                           else max(1, line_rows // LINEITEM_TO_ORDERS))
    return GenerationSpec(table=table, scale=scale, rows=rows, seed=seed,
                          skew=skew, key_cardinality=key_cardinality,
                          part_cardinality=DEFAULT_PART_CARDINALITY,
                          chunk_rows=chunk_rows)


def _fresh_to(spec, index: int, draws_per_row: int):
    """Replay the seeded stream, discarding draws before this row's offset."""
    rng = random.Random(spec.seed)
    sampler = ZipfSampler(spec.key_cardinality, spec.skew)
    for _ in range(index * draws_per_row):
        sampler.sample(rng)
    return rng, sampler


def orders_row(index: int, spec, _rng=None, _sampler=None) -> tuple:
    """Canonical orders row: (order_key, cust_key, order_day)."""
    if not 0 <= index < spec.rows:
        raise ValueError(f"index {index} out of range [0, {spec.rows})")
    rng, sampler = _fresh_to(spec, index, draws_per_row=1)
    cust_key = sampler.sample(rng)
    order_day = (index * 2654435761 + spec.seed) % 365
    return (index, cust_key, order_day)


def lineitem_row(index: int, spec, n_orders: int,
                 _rng=None, _sampler=None) -> tuple:
    """Canonical lineitem row: (line_key, order_key, part, qty, price)."""
    if not 0 <= index < spec.rows:
        raise ValueError(f"index {index} out of range [0, {spec.rows})")
    rng, sampler = _fresh_to(spec, index, draws_per_row=3)
    order_key = sampler.sample(rng) % n_orders
    part_key = rng.randrange(spec.part_cardinality)
    quantity = rng.randrange(1, 51)
    extended_price = float(quantity * (10.0 + (part_key % 90)))
    return (index, order_key, part_key, quantity, extended_price)


def iter_chunks(spec) -> object:
    """Yield (start, end) index ranges of <= chunk_rows (streaming slices)."""
    start = 0
    while start < spec.rows:
        end = min(spec.rows, start + spec.chunk_rows)
        yield (start, end)
        start = end
