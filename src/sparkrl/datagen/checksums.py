"""Canonical content checksums + dataset manifests (Day 13).

Checksum rule: FNV-1a 64-bit over the canonical row encoding
"col|col|..." joined per table in row-index order (NOT over Parquet
bytes, which embed writer metadata). Timestamps are manifest metadata
only and never enter content identity.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sparkrl.datagen.generator import GenerationSpec
from sparkrl.datagen.schema import SCHEMA_VERSION, schema_fingerprint

_FNV_OFFSET = 14695981039346656037
_FNV_PRIME = 1099511628211
_MASK64 = (1 << 64) - 1


def _fnv1a_64(data: bytes, state: int = _FNV_OFFSET) -> int:
    for byte in data:
        state ^= byte
        state = (state * _FNV_PRIME) & _MASK64
    return state


def encode_row(row: tuple) -> bytes:
    """Canonical per-row encoding: str(col) joined by '|', floats repr'd."""
    parts = []
    for value in row:
        if isinstance(value, float):
            parts.append(repr(value))
        else:
            parts.append(str(value))
    return "|".join(parts).encode("utf-8")


def checksum_rows(rows: Iterable[tuple]) -> dict[str, Any]:
    """Fold canonical row encodings into {fnv1a_hex, row_count}."""
    state = _FNV_OFFSET
    count = 0
    for row in rows:
        state = _fnv1a_64(encode_row(row), state)
        state = _fnv1a_64(b"\n", state)
        count += 1
    return {"fnv1a_hex": format(state, "016x"), "row_count": count}


@dataclass(frozen=True)
class DatasetManifest:
    """Machine-readable dataset identity (content-addressed, timestamp-free)."""

    dataset_id: str
    generator_version: str
    schema_version: str
    schema_fingerprint: str
    scale: str
    table: str
    row_count: int
    seed: int
    zipf_parameter: float
    key_cardinality: int
    file_format: str
    file_count: int
    total_bytes: int
    checksum: str
    generation_fingerprint: str
    code_version: str
    generation_timestamp: str  # metadata ONLY, never part of identity

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable manifest (field order fixed for readability)."""
        return asdict(self)

    def to_json(self) -> str:
        """Canonical JSON encoding (sorted keys) for storage/comparison."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


def build_manifest(dataset_id: str, spec: GenerationSpec, checksum: str,
                   file_count: int, total_bytes: int,
                   code_version: str = "unrecorded") -> DatasetManifest:
    """Assemble a manifest; timestamp stamped at build (metadata only)."""
    return DatasetManifest(
        dataset_id=dataset_id,
        generator_version="datagen-v1",
        schema_version=SCHEMA_VERSION,
        schema_fingerprint=schema_fingerprint(spec.table),
        scale=spec.scale,
        table=spec.table,
        row_count=spec.rows,
        seed=spec.seed,
        zipf_parameter=spec.skew,
        key_cardinality=spec.key_cardinality,
        file_format="parquet",
        file_count=file_count,
        total_bytes=total_bytes,
        checksum=checksum,
        generation_fingerprint=spec.fingerprint(),
        code_version=code_version,
        generation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def validate_manifest(manifest: DatasetManifest, spec: GenerationSpec,
                      checksum: str) -> list[str]:
    """Cross-check manifest identity against a live spec + recomputed checksum."""
    errors: list[str] = []
    if manifest.row_count != spec.rows:
        errors.append(f"row_count {manifest.row_count} != spec {spec.rows}")
    if manifest.seed != spec.seed:
        errors.append("seed mismatch")
    if manifest.zipf_parameter != spec.skew:
        errors.append("zipf_parameter mismatch")
    if manifest.key_cardinality != spec.key_cardinality:
        errors.append("key_cardinality mismatch")
    if manifest.checksum != checksum:
        errors.append("checksum mismatch: content differs from manifest")
    if manifest.generation_fingerprint != spec.fingerprint():
        errors.append("generation_fingerprint mismatch")
    if manifest.schema_fingerprint != schema_fingerprint(spec.table):
        errors.append("schema_fingerprint mismatch")
    return errors
