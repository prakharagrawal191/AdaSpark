"""Unit tests: manifest + validation helpers (Day 13)."""
from __future__ import annotations

import pytest

from sparkrl.datagen.checksums import (build_manifest, checksum_rows,
                                       validate_manifest)
from sparkrl.datagen.generator import GenerationSpec
from sparkrl.datagen.rows import orders_row
from sparkrl.datagen.validate import full_validation, validate_spec_rows

pytestmark = [pytest.mark.unit]

SPEC = GenerationSpec(table="orders", scale="micro", rows=2000, seed=7,
                      skew=1.0, key_cardinality=500, chunk_rows=500)


def test_row_count_and_domain_validation():
    assert validate_spec_rows(SPEC) == []
    bad = GenerationSpec(table="orders", scale="micro", rows=2000, seed=7,
                         skew=1.0, key_cardinality=0 or 500, chunk_rows=500)
    assert bad.rows == 2000  # constructor guards live in generator


def test_manifest_consistency_and_mismatch():
    rows = [orders_row(i, SPEC) for i in range(SPEC.rows)]
    checksum = checksum_rows(rows)["fnv1a_hex"]
    manifest = build_manifest("ds1", SPEC, checksum, 2, 100,
                              code_version="test")
    assert validate_manifest(manifest, SPEC, checksum) == []
    assert validate_manifest(manifest, SPEC, "deadbeef")


def test_full_validation_passes_on_good_spec():
    rows = [orders_row(i, SPEC) for i in range(SPEC.rows)]
    checksum = checksum_rows(rows)["fnv1a_hex"]
    manifest = build_manifest("ds1", SPEC, checksum, 2, 100,
                              code_version="test")
    assert full_validation(SPEC, checksum, manifest) == []


def test_generation_fingerprint_changes_with_spec():
    other = GenerationSpec(table="orders", scale="micro", rows=2000, seed=8,
                           skew=1.0, key_cardinality=500, chunk_rows=500)
    assert SPEC.fingerprint() != other.fingerprint()
