"""Unit tests: schema + fingerprint (Day 13)."""
from __future__ import annotations

import pytest

from sparkrl.datagen.schema import (column_names, require_table,
                                    schema_fingerprint, validate_row)

pytestmark = [pytest.mark.unit]


def test_tables_have_expected_columns():
    assert column_names("orders") == ["order_key", "cust_key", "order_day"]
    assert column_names("lineitem") == ["line_key", "order_key", "part_key",
                                        "quantity", "extended_price"]


def test_schema_fingerprint_stable():
    assert schema_fingerprint("orders") == schema_fingerprint("orders")
    assert schema_fingerprint("orders") != schema_fingerprint("lineitem")
    assert len(schema_fingerprint("orders")) == 64


def test_require_table_rejects_unknown():
    with pytest.raises(ValueError):
        require_table("customers")


def test_validate_row_accepts_good_orders_row():
    assert validate_row("orders", (7, 3, 100)) == []


def test_validate_row_flags_bad_quantity_and_day():
    assert validate_row("lineitem", (0, 1, 2, 0, 5.0))
    assert validate_row("orders", (0, 1, 999))
    assert validate_row("orders", (0, 1))
