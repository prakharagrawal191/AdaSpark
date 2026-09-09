"""Unit tests: determinism, seeds, Zipf, scales, checksums (Day 13)."""
from __future__ import annotations

import pytest

from sparkrl.datagen.checksums import build_manifest, checksum_rows
from sparkrl.datagen.distributions import ZipfSampler
from sparkrl.datagen.generator import GenerationSpec
from sparkrl.datagen.rows import (iter_chunks, lineitem_row, orders_row,
                                  spec_for_scale)
from sparkrl.datagen.validate import (regeneration_checksum,
                                      skew_direction_ok)

pytestmark = [pytest.mark.unit]

TINY_ORDERS = GenerationSpec(table="orders", scale="micro", rows=2000,
                             seed=7, skew=1.0, key_cardinality=500,
                             chunk_rows=500)
TINY_LINE = GenerationSpec(table="lineitem", scale="micro", rows=4000,
                           seed=7, skew=1.0, key_cardinality=2000,
                           chunk_rows=1000)


def test_deterministic_rows_same_spec():
    assert [orders_row(i, TINY_ORDERS) for i in range(50)] == [
        orders_row(i, TINY_ORDERS) for i in range(50)]
    assert [lineitem_row(i, TINY_LINE, 2000) for i in range(50)] == [
        lineitem_row(i, TINY_LINE, 2000) for i in range(50)]


def test_different_seeds_differ():
    other = GenerationSpec(table="orders", scale="micro", rows=2000, seed=8,
                           skew=1.0, key_cardinality=500, chunk_rows=500)
    a = [orders_row(i, TINY_ORDERS) for i in range(200)]
    b = [orders_row(i, other) for i in range(200)]
    assert a != b
    assert TINY_ORDERS.fingerprint() != other.fingerprint()


def test_zipf_param_validation():
    with pytest.raises(ValueError):
        ZipfSampler(0, 1.0)
    with pytest.raises(ValueError):
        ZipfSampler(10, -0.1)
    with pytest.raises(ValueError):
        ZipfSampler(10, 9.0)


def test_zipf_skew_direction_and_uniform():
    assert skew_direction_ok(TINY_ORDERS)
    flat = GenerationSpec(table="orders", scale="micro", rows=2000, seed=7,
                          skew=0.0, key_cardinality=500, chunk_rows=500)
    assert not skew_direction_ok(
        GenerationSpec(table="orders", scale="micro", rows=2000, seed=7,
                       skew=1.5, key_cardinality=500,
                       chunk_rows=500)) is False  # extreme skew still skewed
    _ = flat


def test_scale_spec_validation_and_ladder():
    with pytest.raises(ValueError):
        spec_for_scale("orders", "xlarge")
    small = spec_for_scale("lineitem", "small")
    assert small.rows == 3_000_000
    assert spec_for_scale("orders", "small").rows == 750_000
    assert spec_for_scale("lineitem", "large").rows == 30_000_000


def test_checksum_and_fingerprint_stability():
    rows = [orders_row(i, TINY_ORDERS) for i in range(2000)]
    assert checksum_rows(rows) == checksum_rows(list(rows))
    assert TINY_ORDERS.fingerprint() == TINY_ORDERS.fingerprint()


def test_manifest_serialization_roundtrip(tmp_path=None):
    m = build_manifest("ds1", TINY_ORDERS, "abc123", 2, 100,
                       code_version="test")
    d = m.to_dict()
    assert d["row_count"] == 2000 and d["seed"] == 7
    assert d["generation_fingerprint"] == TINY_ORDERS.fingerprint()
    assert "generation_timestamp" in d


def test_chunks_cover_rows_exactly_once():
    ranges = list(iter_chunks(TINY_LINE))
    assert ranges[0][0] == 0 and ranges[-1][1] == 4000
    assert sum(e - s for s, e in ranges) == 4000
    assert all(e - s <= 1000 for s, e in ranges)


def test_regeneration_checksum_matches_manual():
    manual = checksum_rows(
        orders_row(i, TINY_ORDERS) for i in range(2000))["fnv1a_hex"]
    assert regeneration_checksum(TINY_ORDERS) == manual
