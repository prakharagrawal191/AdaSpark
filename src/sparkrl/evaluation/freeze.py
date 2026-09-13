"""Immutable Day-31 artifacts: write once, fingerprint, verify, never overwrite.

Three artifacts live under ``results/evaluation/``:

    evaluation_spec.json    what a later day WILL run (declaration, no execution)
    baseline_selection.json the frozen B1/B2 outcome (VALIDATION data only)
    test_freeze.json        the TEST-split IDENTITY (no measurement, ever)

Identity follows the frozen ``sparkrl.agent.policy_store`` pattern: a SHA-256
content fingerprint over the canonical JSON that EXCLUDES the artifact id and
every timestamp, so rebuilding from identical inputs yields an identical id. An
existing artifact is never silently overwritten: an identical rebuild is a no-op,
anything else raises :class:`ArtifactExistsError`.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sparkrl.evaluation.spec import (EVAL_SPEC_VERSION, EXPERIMENT_ID,
                                     build_evaluation_spec, test_cells,)
from sparkrl.evaluation.selection import BaselineSelection
from sparkrl.experiments.spec import TEST
from sparkrl.workloads.resolver import resolve_dataset

PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT_DIR = PROJECT / "results" / "evaluation"

TEST_FREEZE_SCHEMA = "eval-test-freeze/v1"
SELECTION_SCHEMA = "eval-baseline-selection/v1"

# Fields excluded from the content fingerprint: identity and metadata only.
_FINGERPRINT_EXCLUDED = ("artifact_id", "fingerprint", "created_utc")

# PLAN section 18 declares two further test components that have no
# (family, scale, seed) cell in the frozen 75-dataset matrix. They are recorded
# as DECLARED-but-not-materialized rather than invented or silently omitted.
DECLARED_TEST_COMPONENTS_NOT_MATERIALIZED = (
    "public dataset (NYC Taxi subset, PLAN section 18 external validity)",
    "F5 with unseen parameters (PLAN section 18)",
)


class ArtifactExistsError(RuntimeError):
    """An immutable artifact already exists and differs (no silent overwrite)."""


class ArtifactCorrupt(ValueError):
    """A stored artifact failed its fingerprint verification."""


def _clock() -> str:
    return datetime.now(timezone.utc).isoformat()


def artifact_fingerprint(artifact: dict[str, Any]) -> str:
    """Deterministic content fingerprint (excludes identity + timestamps)."""
    body = {k: v for k, v in artifact.items() if k not in _FINGERPRINT_EXCLUDED}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seal(artifact: dict[str, Any], *, created_utc: str | None = None
         ) -> dict[str, Any]:
    """Stamp an artifact with its content fingerprint and identity."""
    sealed = dict(artifact)
    sealed.pop("artifact_id", None)
    sealed.pop("fingerprint", None)
    sealed.pop("created_utc", None)
    fingerprint = artifact_fingerprint(sealed)
    sealed["fingerprint"] = fingerprint
    sealed["artifact_id"] = fingerprint
    sealed["created_utc"] = created_utc or _clock()   # metadata, never identity
    return sealed


def provenance() -> dict[str, Any]:
    """Code + environment provenance. Reuses the frozen runner helper."""
    from sparkrl.experiments.runner import code_version   # lazy: keeps this offline

    return {
        "code_version": code_version(),
        "produced_by": "scripts/run_evaluation.py (Day 31)",
        "split_authority": "sparkrl.experiments.spec.split_of",
        "spark_executions": 0,
    }


def write_artifact(artifact: dict[str, Any], path: str | Path) -> Path:
    """Write atomically (tmp + os.replace); refuse to overwrite a DIFFERING file."""
    path = Path(path)
    fingerprint = artifact.get("fingerprint")
    if not fingerprint:
        raise ArtifactCorrupt("artifact has no fingerprint; call seal() first")
    if fingerprint != artifact_fingerprint(artifact):
        raise ArtifactCorrupt(f"{path.name}: fingerprint does not match content")
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("fingerprint") == fingerprint:
            return path                     # identical rebuild: a no-op, not an error
        raise ArtifactExistsError(
            f"{path} already exists with a DIFFERENT content fingerprint "
            f"({str(existing.get('fingerprint'))[:16]} != {fingerprint[:16]}). "
            f"Frozen artifacts are immutable; move the old file aside deliberately "
            f"if it is genuinely superseded.")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


def verify_artifact(path: str | Path) -> dict[str, Any]:
    """Re-read and re-verify a stored artifact. Raises on any mismatch."""
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    fingerprint = artifact_fingerprint(artifact)
    if artifact.get("fingerprint") != fingerprint:
        raise ArtifactCorrupt(
            f"{path.name}: stored fingerprint {str(artifact.get('fingerprint'))[:16]} "
            f"!= recomputed {fingerprint[:16]}")
    if artifact.get("artifact_id") != fingerprint:
        raise ArtifactCorrupt(f"{path.name}: artifact_id does not match content")
    manifest = artifact.get("manifest_fingerprint")
    if manifest is not None:
        recomputed = manifest_fingerprint(artifact.get("cells") or [])
        if manifest != recomputed:
            raise ArtifactCorrupt(
                f"{path.name}: manifest_fingerprint {manifest[:16]} != recomputed "
                f"{recomputed[:16]}; the frozen test-set identity has changed")
    return artifact


def manifest_fingerprint(cells: list[dict[str, Any]]) -> str:
    """Fingerprint over the frozen cell identity list alone."""
    canonical = json.dumps(cells, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# -- test_freeze.json ---------------------------------------------------------
def build_test_freeze(data_root: str | Path | None = None) -> dict[str, Any]:
    """Freeze the TEST-split IDENTITY. Contains no measurement and no metric.

    Cells come from ``split_of``; dataset ids and fingerprints are READ from the
    existing Day-14 manifests via ``resolve_dataset``. Nothing is executed and no
    test datum is opened.
    """
    cells: list[dict[str, Any]] = []
    for family, scale, seed in test_cells():
        resolved = resolve_dataset(family, scale, seed, data_root=data_root)
        cells.append({
            "family": family,
            "scale": scale,
            "seed": seed,
            "split": TEST,
            "dataset_id": resolved.dataset_id,
            "dataset_fingerprint": resolved.dataset_fingerprint,
            "schema_fingerprint": resolved.schema_fingerprint,
            "skew": resolved.skew,
        })
    cells.sort(key=lambda c: (c["family"], c["scale"], c["seed"]))

    return seal({
        "schema_version": TEST_FREEZE_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "frozen_on": "Day 31 (PLAN line 277)",
        "content": "IDENTITY ONLY - no measurement, no metric, no result",
        "executed": False,
        "test_execution_status": (
            "SEALED - EXP-005 is Day 32-33 and EXP-006 is Day 34 "
            "(PLAN lines 312-313)"),
        "split_authority": "sparkrl.experiments.spec.split_of",
        "cell_count": len(cells),
        "cells": cells,
        "declared_components_not_materialized": list(
            DECLARED_TEST_COMPONENTS_NOT_MATERIALIZED),
        "manifest_fingerprint": manifest_fingerprint(cells),
        "manifest_source": "data/generated/datasets/*/{orders,lineitem}/manifest.json",
        "verification": (
            "later commands must recompute manifest_fingerprint over 'cells' and "
            "refuse to proceed on any mismatch"),
        "provenance": provenance(),
    })


# -- baseline_selection.json --------------------------------------------------
def build_baseline_selection_artifact(selection: BaselineSelection
                                      ) -> dict[str, Any]:
    """Freeze the B1/B2 outcome. Validation data only - no test datum appears."""
    payload = selection.to_dict()
    artifact = {
        "schema_version": SELECTION_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "frozen_on": "Day 31 (PLAN line 277)",
        "definitions": {
            "B1": "PLAN line 153 - Static global: one config tuned on validation, "
                  "used everywhere",
            "B2": "PLAN line 154 - Static per-family: best validation-grid config "
                  "per family",
        },
        "contains_test_data": False,
        "no_research_claim": (
            "this artifact records which configuration was selected on validation; "
            "it establishes nothing about whether any strategy beats another"),
        "provenance": provenance(),
    }
    artifact.update(payload)
    return seal(artifact)


# -- evaluation_spec.json -----------------------------------------------------
def build_evaluation_spec_artifact(base_config: Any, repetitions: int | None = None
                                   ) -> dict[str, Any]:
    """Freeze the versioned evaluation specification. Declares, never executes."""
    from sparkrl.evaluation.spec import EVALUATION_REPETITIONS

    spec = build_evaluation_spec(
        base_config,
        EVALUATION_REPETITIONS if repetitions is None else repetitions)
    spec["provenance"] = provenance()
    spec["spec_version"] = EVAL_SPEC_VERSION
    return seal(spec)


def artifact_path(name: str, artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR) -> Path:
    return Path(artifact_dir) / name
