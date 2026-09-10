"""Dataset resolver: (family, scale, seed) -> physical dataset (Day 15).

Day 14 uses a compact physical layout with logical family mappings:
75 logical (family x scale x seed) entries share 30 physical datasets
(2 skews x 3 scales x 5 seeds). This resolver reads the authoritative
``data/generated/index.json`` and never substitutes another dataset.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkrl.utils.paths import resolve_data_root
from sparkrl.workloads.base import (FAMILIES, FAMILY_SKEW, SCALES, SEEDS,)


@dataclass
class ResolvedDataset:
    """Physical dataset backing one logical (family, scale, seed) request."""

    family: str
    scale: str
    seed: int
    skew: float
    physical_id: str
    physical_dir: Path
    orders_path: Path
    lineitem_path: Path
    orders_manifest: dict[str, Any] = field(default_factory=dict)
    lineitem_manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return self.physical_id

    @property
    def dataset_fingerprint(self) -> str:
        return self.lineitem_manifest.get(
            "generation_fingerprint",
            self.orders_manifest.get("generation_fingerprint", ""))

    @property
    def schema_fingerprint(self) -> str:
        return self.orders_manifest.get("schema_fingerprint", "")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"manifest not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest at {path} is not valid JSON: {exc}")


def resolve_dataset(family: str, scale: str, seed: int,
                    data_root: str | Path | None = None) -> ResolvedDataset:
    """Resolve (family, scale, seed) to its physical dataset; fail loudly."""
    if family not in FAMILIES:
        raise ValueError(
            f"unknown family {family!r}; expected one of {list(FAMILIES)}")
    if scale not in SCALES:
        raise ValueError(
            f"unknown scale {scale!r}; expected one of {list(SCALES)}")
    if seed not in SEEDS:
        raise ValueError(
            f"unknown seed {seed!r}; expected one of {list(SEEDS)}")

    root = Path(data_root) if data_root is not None else resolve_data_root(create=False)
    index_path = root / "generated" / "index.json"
    if not index_path.exists():
        alt = Path("data") / "generated" / "index.json"
        if alt.exists():
            index_path = alt
            root = Path("data")
        else:
            raise FileNotFoundError(
                f"dataset index not found: {index_path} "
                f"(SPARKRL_DATA_ROOT={os.environ.get('SPARKRL_DATA_ROOT', '')!r})")

    index = _read_json(index_path)
    entry = next(
        (e for e in index.get("logical", [])
         if e.get("family") == family and e.get("scale") == scale
         and e.get("seed") == seed),
        None)
    if entry is None:
        raise FileNotFoundError(
            f"no logical entry for {family} x {scale} x seed {seed}")

    expected_skew = FAMILY_SKEW[family]
    physical_id = entry["physical_id"]
    if expected_skew == 1.5 and "1.5" not in physical_id:
        raise ValueError(
            f"F4_ski must resolve to a skew-1.5 dataset, got {physical_id}")
    if expected_skew == 1.0 and "1.5" in physical_id:
        raise ValueError(
            f"{family} must resolve to a skew-1.0 dataset, got {physical_id}")

    physical_dir = root / "generated" / "datasets" / physical_id
    orders_dir = physical_dir / "orders"
    lineitem_dir = physical_dir / "lineitem"
    if not physical_dir.is_dir():
        raise FileNotFoundError(f"physical dataset missing: {physical_dir}")
    if not orders_dir.is_dir():
        raise FileNotFoundError(f"orders table missing: {orders_dir}")
    if not lineitem_dir.is_dir():
        raise FileNotFoundError(f"lineitem table missing: {lineitem_dir}")

    orders_manifest = _read_json(orders_dir / "manifest.json")
    lineitem_manifest = _read_json(lineitem_dir / "manifest.json")
    for name, manifest, table in (
            ("orders", orders_manifest, "orders"),
            ("lineitem", lineitem_manifest, "lineitem")):
        for key, want in (("scale", scale), ("seed", seed)):
            if manifest.get(key) != want:
                raise ValueError(
                    f"{name} manifest mismatch: "
                    f"{key}={manifest.get(key)!r}, requested {want!r}")
        if manifest.get("table") != table:
            raise ValueError(
                f"{name} manifest table is {manifest.get('table')!r}")
    manifest_skew = float(orders_manifest.get("zipf_parameter", expected_skew))
    if abs(manifest_skew - expected_skew) > 1e-12:
        raise ValueError(
            f"orders manifest zipf_parameter "
            f"{orders_manifest.get('zipf_parameter')!r} != {expected_skew}")

    orders_path = orders_dir / "data"
    lineitem_path = lineitem_dir / "data"
    if not orders_path.is_dir() or not any(orders_path.glob("*.parquet")):
        raise FileNotFoundError(f"no orders parquet under {orders_path}")
    if not lineitem_path.is_dir() or not any(lineitem_path.glob("*.parquet")):
        raise FileNotFoundError(f"no lineitem parquet under {lineitem_path}")

    return ResolvedDataset(
        family=family, scale=scale, seed=seed, skew=expected_skew,
        physical_id=physical_id, physical_dir=physical_dir,
        orders_path=orders_path, lineitem_path=lineitem_path,
        orders_manifest=orders_manifest, lineitem_manifest=lineitem_manifest)

