"""Unit tests for SparkConfig: loading, validation, fingerprint, overrides."""
from __future__ import annotations

import pytest

from sparkrl.spark.config import SparkConfig

pytestmark = [pytest.mark.unit]


def test_from_dict_defaults():
    cfg = SparkConfig.from_dict({"runtime": {}, "execution": {}, "workload": {}})
    assert cfg.master == "local[2]"
    assert cfg.shuffle_partitions == 200
    assert cfg.warmup_runs == 2
    assert cfg.timeout_seconds == 300.0
    assert cfg.seed == 42


def test_from_yaml(tmp_path):
    p = tmp_path / "spark.yaml"
    p.write_text(
        "runtime:\n  master: 'local[4]'\n  shuffle_partitions: 64\nexecution:\n"
        "  warmup_runs: 3\n  timeout_seconds: 60.0\nworkload:\n  seed: 7\n",
        encoding="utf-8")
    cfg = SparkConfig.from_yaml(p)
    assert cfg.master == "local[4]"
    assert cfg.shuffle_partitions == 64
    assert cfg.warmup_runs == 3
    assert cfg.timeout_seconds == 60.0
    assert cfg.seed == 7


def test_validation_rejects_bad_values():
    with pytest.raises(ValueError, match="master"):
        SparkConfig.from_dict({"runtime": {"master": "yarn"}})
    with pytest.raises(ValueError, match="shuffle_partitions"):
        SparkConfig.from_dict({"runtime": {"shuffle_partitions": 0}})
    with pytest.raises(ValueError, match="timeout_seconds"):
        SparkConfig.from_dict({"execution": {"timeout_seconds": -5}})
    with pytest.raises(ValueError, match="warmup_runs"):
        SparkConfig.from_dict({"execution": {"warmup_runs": -1}})


def test_fingerprint_stable_and_sensitive():
    base = SparkConfig.from_dict({"runtime": {}, "execution": {}, "workload": {}})
    same = SparkConfig.from_dict({"runtime": {}, "execution": {}, "workload": {}})
    other = SparkConfig.from_dict({"runtime": {"shuffle_partitions": 64}})
    assert base.fingerprint() == same.fingerprint()
    assert base.fingerprint() != other.fingerprint()
    assert len(base.fingerprint()) == 64  # sha256 hex


def test_fingerprint_ignores_dict_key_order():
    a = SparkConfig.from_dict({"runtime": {"shuffle_partitions": 32}, "execution": {}})
    b = SparkConfig.from_dict({"execution": {}, "runtime": {"shuffle_partitions": 32}})
    assert a.fingerprint() == b.fingerprint()


def test_to_spark_settings():
    cfg = SparkConfig.from_dict({"runtime": {"shuffle_partitions": 16,
                                             "default_parallelism": 4}})
    settings = cfg.to_spark_settings()
    assert settings["spark.sql.shuffle.partitions"] == "16"
    assert settings["spark.default.parallelism"] == "4"
    assert settings["spark.sql.adaptive.enabled"] == "false"
    assert "spark.eventLog.dir" not in settings  # session layer owns event-log wiring


def test_with_overrides_returns_validated_copy():
    base = SparkConfig.from_dict({"runtime": {}, "execution": {}, "workload": {}})
    warmed = base.with_overrides(warmup_runs=5, shuffle_partitions=32)
    assert warmed.warmup_runs == 5
    assert warmed.shuffle_partitions == 32
    assert base.warmup_runs == 2  # original untouched (frozen dataclass semantics)
    with pytest.raises(ValueError):
        base.with_overrides(shuffle_partitions=0)