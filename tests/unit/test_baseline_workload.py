"""Unit tests for the deterministic baseline workload (pure-Python reference)."""
from __future__ import annotations

import pytest

from sparkrl.workloads.baseline import BaselineWorkload

pytestmark = [pytest.mark.unit]


def test_reference_checksum_deterministic():
    a = BaselineWorkload.reference_check(100_000)
    b = BaselineWorkload.reference_check(100_000)
    assert a.checksum_value == b.checksum_value
    assert a.group_count == 1000
    # multiples of 11 in [0, 99999] = (99999 // 11) + 1 = 9091 -> filtered = 90909
    assert a.row_count_filtered == 100_000 - 9091


def test_reference_checksum_known_value():
    # ids 0..9: only id 0 is a multiple of 11 -> filtered ids 1..9, all distinct k,
    # v = (i % 100000) / 7.0
    ref = BaselineWorkload.reference_check(10)
    expected = sum(i / 7.0 for i in range(1, 10))
    assert ref.checksum_value == pytest.approx(expected, rel=1e-9)
    assert ref.group_count == 9


def test_validate_accepts_reference():
    wl = BaselineWorkload(rows=100_000, seed=42)
    ref = wl.reference_check(100_000)
    assert wl.validate(ref, expect_same_as_ref=True)


def test_workload_rejects_bad_rows():
    with pytest.raises(ValueError, match="rows"):
        BaselineWorkload(rows=0)