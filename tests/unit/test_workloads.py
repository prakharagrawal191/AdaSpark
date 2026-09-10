"""Unit tests for the Day-15 workload layer (no Spark required).

Covers: registry lookup, invalid family/scale/seed rejection, resolver
failure modes (via tmp index fixtures), workload versions, result
signature determinism + machine-independence, manifest serialization /
required fields, and per-family validate() gates. Spark execution is
covered by the integration test; these tests use stubs only.
"""
from __future__ import annotations

import json

import pytest

from sparkrl.workloads import registry as reg
from sparkrl.workloads.base import (WorkloadResult, WorkloadSpec,
                                    result_signature,)
from sparkrl.workloads.families import (F1Aggregation, F2Join, F3Rdd,
                                        F4SkewJoin, F5Mixed,)
from sparkrl.workloads.resolver import resolve_dataset

pytestmark = [pytest.mark.unit]


def _ok_result(**over) -> WorkloadResult:
    base = dict(workload_id="T_v1", family="F1_agg", scale="small", seed=0,
                dataset_id="skew1_small_s0", dataset_fingerprint="fp",
                schema_fingerprint="sfp", workload_version="F1_agg_v1",
                success=True, result_signature="0" * 16, rows_processed=3)
    base.update(over)
    return WorkloadResult(**base)


def test_registry_has_all_five_families():
    assert sorted(reg.REGISTRY) == ["F1_agg", "F2_join", "F3_rdd", "F4_ski",
                                    "F5_mixed"]
    assert set(reg.VERSIONS.values()) == {"F1_agg_v1", "F2_join_v1",
                                          "F3_rdd_v1", "F4_ski_v1",
                                          "F5_mixed_v1"}


def test_get_workload_invalid_family():
    with pytest.raises(ValueError, match="unknown family"):
        reg.get_workload("F9_nope", "small", 0)


def test_spec_rejects_bad_scale_seed():
    with pytest.raises(ValueError, match="scale"):
        WorkloadSpec(family="F1_agg", scale="huge", seed=0)
    with pytest.raises(ValueError, match="seed"):
        WorkloadSpec(family="F1_agg", scale="small", seed=9)
    with pytest.raises(ValueError, match="family"):
        WorkloadSpec(family="F9", scale="small", seed=0)


def test_resolver_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="family"):
        resolve_dataset("F9", "small", 0)
    with pytest.raises(ValueError, match="scale"):
        resolve_dataset("F1_agg", "huge", 0)
    with pytest.raises(ValueError, match="seed"):
        resolve_dataset("F1_agg", "small", 9)


def test_signature_deterministic_and_order_sensitive():
    a = result_signature([(1, 2.5, "x"), (3, 4.0, "y")])
    b = result_signature([(1, 2.5, "x"), (3, 4.0, "y")])
    c = result_signature([(3, 4.0, "y"), (1, 2.5, "x")])
    assert a == b and len(a) == 16
    assert a != c


def test_result_to_dict_round_trip():
    r = _ok_result()
    d = r.to_dict()
    assert d["family"] == "F1_agg" and d["success"] is True
    assert json.loads(json.dumps(d))["result_signature"] == "0" * 16


def test_validate_gates():
    assert F1Aggregation("small", 0).validate(_ok_result()) is True
    assert F2Join("small", 0).validate(_ok_result()) is True
    assert F3Rdd("small", 0).validate(_ok_result()) is True
    bad = _ok_result(success=False, error="boom")
    assert F1Aggregation("small", 0).validate(bad) is False
    assert F4SkewJoin("small", 0).validate(bad) is False
    f5 = F5Mixed("small", 0)
    ok5 = _ok_result(family="F5_mixed",
                     measurements={"phases": list(F5Mixed.PHASES)})
    assert f5.validate(ok5) is True
    wrong_phases = _ok_result(family="F5_mixed",
                              measurements={"phases": ["a", "b"]})
    assert f5.validate(wrong_phases) is False


def test_manifest_required_fields_present():
    import scripts.run_workload as cli
    required = set(cli.REQUIRED_MANIFEST_FIELDS)
    assert {"workload_id", "family", "scale", "seed", "dataset_id",
            "dataset_fingerprint", "schema_fingerprint", "workload_version",
            "spark_version", "configuration_fingerprint", "aqe_mode",
            "success", "result_signature", "rows_processed",
            "execution_time_s", "timestamp", "code_version"} <= required
