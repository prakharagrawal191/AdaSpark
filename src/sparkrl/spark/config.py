"""Spark configuration model for AdaSpark.

Responsibilities (plan §36, §13): load configuration from YAML/dict, validate supported
values, convert to Spark settings, give a normalized representation, and provide a stable
configuration fingerprint/hash for the future experiment cache (Day 20).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_MASTER_RE = re.compile(r"^local(?:\[(\d+)\])?$")
_PATH_PLACEHOLDER = "null"


@dataclass(frozen=True)
class SparkConfig:
    """Normalized, validated Spark runtime configuration."""

    master: str = "local[2]"
    app_name: str = "sparkrl"
    driver_memory: str = "6g"
    ui_enabled: bool = False
    event_log_enabled: bool = True
    event_log_dir: str | None = None     # resolved later by session layer via utils.paths
    local_dir: str | None = None         # resolved later by session layer via utils.paths
    expected_spark_version_prefix: str = "3.5"
    aqe_enabled: bool = False
    shuffle_partitions: int = 200
    default_parallelism: int | None = None

    warmup_runs: int = 2
    warmup_micro_job: bool = True
    timeout_seconds: float = 300.0
    timeout_grace_seconds: float = 10.0

    baseline_rows: int = 1_000_000
    baseline_scale: str = "medium"
    seed: int = 42

    _extra: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SparkConfig":
        """Build a SparkConfig from a (possibly nested) dict, applying defaults."""

        def pick(*path: str, default: Any = None) -> Any:
            node: Any = raw
            for key in path:
                if not isinstance(node, Mapping) or key not in node:
                    return default
                node = node[key]
            return node

        cfg = cls(
            master=str(pick("runtime", "master", default="local[2]")),
            app_name=str(pick("runtime", "app_name", default="sparkrl")),
            driver_memory=str(pick("runtime", "driver_memory", default="6g")),
            ui_enabled=bool(pick("runtime", "ui_enabled", default=False)),
            event_log_enabled=bool(pick("runtime", "event_log_enabled", default=True)),
            event_log_dir=_as_optional_str(pick("runtime", "event_log_dir")),
            local_dir=_as_optional_str(pick("runtime", "local_dir")),
            expected_spark_version_prefix=str(
                pick("runtime", "expected_spark_version_prefix", default="3.5")),
            aqe_enabled=bool(pick("runtime", "aqe_enabled", default=False)),
            shuffle_partitions=int(pick("runtime", "shuffle_partitions", default=200)),
            default_parallelism=_as_optional_int(pick("runtime", "default_parallelism")),
            warmup_runs=int(pick("execution", "warmup_runs", default=2)),
            warmup_micro_job=bool(pick("execution", "warmup_micro_job", default=True)),
            timeout_seconds=float(pick("execution", "timeout_seconds", default=300.0)),
            timeout_grace_seconds=float(
                pick("execution", "timeout_grace_seconds", default=10.0)),
            baseline_rows=int(pick("workload", "baseline_rows", default=1_000_000)),
            baseline_scale=str(pick("workload", "baseline_scale", default="medium")),
            seed=int(pick("workload", "seed", default=42)),
        )
        cfg._validate()
        return cfg

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SparkConfig":
        """Load a SparkConfig from a YAML file (requires PyYAML, part of core env)."""
        import yaml

        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.from_dict(raw)

    def _validate(self) -> None:
        if not _MASTER_RE.match(self.master):
            raise ValueError(
                f"invalid spark.master {self.master!r}; expected local mode like 'local[2]'")
        if self.shuffle_partitions < 1:
            raise ValueError(f"shuffle_partitions must be >= 1, got {self.shuffle_partitions}")
        if self.default_parallelism is not None and self.default_parallelism < 1:
            raise ValueError(
                f"default_parallelism must be >= 1, got {self.default_parallelism}")
        if self.warmup_runs < 0:
            raise ValueError(f"warmup_runs must be >= 0, got {self.warmup_runs}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got {self.timeout_seconds}")
        if self.timeout_grace_seconds < 0:
            raise ValueError(
                f"timeout_grace_seconds must be >= 0, got {self.timeout_grace_seconds}")
        if self.seed < 0:
            raise ValueError(f"seed must be >= 0, got {self.seed}")
        if self.baseline_rows < 1:
            raise ValueError(f"baseline_rows must be >= 1, got {self.baseline_rows}")

    def to_spark_settings(self) -> dict[str, str]:
        """Return the subset of settings this module owns as ``spark.*`` pairs."""
        settings = {
            "spark.app.name": self.app_name,
            "spark.master": self.master,
            "spark.driver.memory": self.driver_memory,
            "spark.ui.enabled": str(self.ui_enabled).lower(),
            "spark.sql.shuffle.partitions": str(self.shuffle_partitions),
            "spark.sql.adaptive.enabled": str(self.aqe_enabled).lower(),
        }
        if self.default_parallelism is not None:
            settings["spark.default.parallelism"] = str(self.default_parallelism)
        return settings

    def normalized_dict(self) -> dict[str, Any]:
        """A plain-dict, canonical representation (used for fingerprint + manifests)."""
        return {
            "master": self.master,
            "app_name": self.app_name,
            "driver_memory": self.driver_memory,
            "ui_enabled": self.ui_enabled,
            "event_log_enabled": self.event_log_enabled,
            "expected_spark_version_prefix": self.expected_spark_version_prefix,
            "aqe_enabled": self.aqe_enabled,
            "shuffle_partitions": self.shuffle_partitions,
            "default_parallelism": self.default_parallelism,
            "warmup_runs": self.warmup_runs,
            "timeout_seconds": self.timeout_seconds,
            "timeout_grace_seconds": self.timeout_grace_seconds,
            "baseline_rows": self.baseline_rows,
            "baseline_scale": self.baseline_scale,
            "seed": self.seed,
        }

    def fingerprint(self) -> str:
        """Stable SHA-256 over the normalized config (sort_keys -> canonical)."""
        payload = json.dumps(self.normalized_dict(), sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def with_overrides(self, **overrides: Any) -> "SparkConfig":
        """Return a new SparkConfig with the given fields replaced (validated)."""
        values = dict(self.normalized_dict())
        values.update(overrides)
        raw = {"runtime": {}, "execution": {}, "workload": {}}
        for key, val in values.items():
            if key in ("warmup_runs", "warmup_micro_job", "timeout_seconds",
                       "timeout_grace_seconds"):
                raw["execution"][key] = val
            elif key in ("baseline_rows", "baseline_scale", "seed"):
                raw["workload"][key] = val
            else:
                raw["runtime"][key] = val
        return SparkConfig.from_dict(raw)


def _as_optional_str(value: Any) -> str | None:
    if value is None or value == _PATH_PLACEHOLDER:
        return None
    return str(value)


def _as_optional_int(value: Any) -> int | None:
    if value is None or value == _PATH_PLACEHOLDER:
        return None
    return int(value)