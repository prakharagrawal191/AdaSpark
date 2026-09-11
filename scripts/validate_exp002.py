#!/usr/bin/env python
"""EXP-002 structural / scientific-integrity validator (Day 22).

Checks that the configuration-sensitivity gate experiment is *scientifically
well formed*: the pre-registered design loads, the frozen grid and the frozen
B0 reference are intact, AQE is off everywhere, only PLAN-14 parameters vary,
run identity is deterministic, stored manifests are structurally valid, no
incomplete run is counted as valid, the VALIDATION/TEST splits were never
touched, the analysis output is reproducible from the stored records, and no
reinforcement-learning machinery has crept into the repository.

It does NOT decide whether the gate PASSES - that is scripts/analyze_exp002.py
(the gate verdict is scientific output, not an integrity property). This script
only verifies that whatever verdict was produced is reproducible and honest.

Checks that cannot run yet (no records on disk, no gate.json) report SKIP, never
a vacuous PASS. SKIPs do not fail the run but are counted and listed.

Exit code: 0 if no check FAILED, 1 otherwise.

Usage:
    python scripts/validate_exp002.py
    python scripts/validate_exp002.py --spec experiments/exp002.yaml
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.experiments import grid as grid_mod              # noqa: E402
from sparkrl.experiments.runner import RECORD_SCHEMA_VERSION  # noqa: E402
from sparkrl.experiments.spec import (EXPERIMENT_ID, ExperimentSpec,  # noqa: E402
                                      run_id_for, split_of,)
from sparkrl.monitoring import RunMetrics, validate_run_metrics  # noqa: E402
from sparkrl.monitoring.run_metrics import SCHEMA_VERSION as METRICS_SCHEMA  # noqa: E402
from sparkrl.spark.config import SparkConfig                  # noqa: E402
from sparkrl.workloads.base import FAMILIES                   # noqa: E402
from sparkrl.workloads.registry import REGISTRY               # noqa: E402

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

DEFAULT_SPEC = PROJECT / "experiments" / "exp002.yaml"
DEFAULT_RESULT_ROOT = PROJECT / "results" / "experiments" / "exp-002"
AUDIT_DOC = PROJECT / "docs" / "research" / "EXP002_CONFIGURATION_SENSITIVITY_AUDIT.md"
AUDIT_DOC_MIN_CHARS = 2000

REQUIRED_RECORD_KEYS = ("schema_version", "experiment_id", "spec_fingerprint",
                        "grid_fingerprint", "status", "attempt", "run_spec",
                        "metrics", "provenance")

# PLAN section 18: cells EXP-002 must never have touched.
FROZEN_FAMILY = "F4_ski"      # unseen TEST family
FROZEN_SCALE = "large"        # unseen TEST scale
FROZEN_SEEDS = (3, 4)         # 3 = VALIDATION (EXP-003), 4 = TEST

# --- RL containment (EXP-002 is calibration only; no agent exists yet) --------
# Flag *definitions*, not mentions: prose and docstrings legitimately discuss the
# future RL work, so only `class X` / `def X` headers and module-level bindings
# whose NAME carries an RL concept are treated as an implementation.
_KEYWORDS = r"(q_?learn|qtable|q_table|dqn|ppo|reward|policy|agent|epsilon)"
RL_DEF_RE = re.compile(r"^(class|def)\s+[A-Za-z0-9_]*" + _KEYWORDS, re.IGNORECASE)
RL_BIND_RE = re.compile(r"^[A-Za-z0-9_]*" + _KEYWORDS
                        + r"[A-Za-z0-9_]*\s*(:[^=]+)?=(?!=)", re.IGNORECASE)
RL_MODULE_NAMES = ("agent.py", "policy.py", "reward.py", "qlearning.py",
                   "q_learning.py", "dqn.py", "ppo.py", "replay_buffer.py")
RL_PLACEHOLDER = SRC / "sparkrl" / "agent" / "__init__.py"

# --- architecture freeze ------------------------------------------------------
FROZEN_PREFIXES = ("src/sparkrl/spark/", "src/sparkrl/workloads/",
                   "src/sparkrl/datagen/", "src/sparkrl/utils/",
                   "src/sparkrl/monitoring/", "configs/", "docs/PLAN.md")
# Day-19 work that was already uncommitted before Day 22 started. These are the
# ONLY permitted exceptions to the freeze.
KNOWN_UNCOMMITTED = {
    "src/sparkrl/monitoring/__init__.py",
    "src/sparkrl/monitoring/merge.py",
    "src/sparkrl/monitoring/run_metrics.py",
    "src/sparkrl/monitoring/sysmon.py",
    "tests/unit/test_metrics_merge.py",
}

FLOAT_TOLERANCE = 1e-9


# =============================================================================
# helpers
# =============================================================================
def _source_files() -> list[Path]:
    """Every Python source under src/ and scripts/ (no bytecode)."""
    files: list[Path] = []
    for root in (SRC, PROJECT / "scripts"):
        if root.is_dir():
            files.extend(p for p in sorted(root.rglob("*.py"))
                         if "__pycache__" not in p.parts)
    return files


def _substantive_lines(path: Path) -> int:
    """Lines that are neither blank nor a pure `#` comment (triviality proxy)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines()
               if line.strip() and not line.strip().startswith("#"))


def _load_records(result_root: Path) -> tuple[list[tuple[Path, dict]], list[str]]:
    """All stored run records as (path, record); plus a list of unreadable paths."""
    runs_dir = result_root / "runs"
    records: list[tuple[Path, dict]] = []
    unreadable: list[str] = []
    if not runs_dir.is_dir():
        return records, unreadable
    for path in sorted(runs_dir.rglob("*.json")):
        try:
            records.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            unreadable.append(f"{path}: {type(exc).__name__}: {exc}")
    return records, unreadable


def _json_diff(left: Any, right: Any, path: str = "") -> list[str]:
    """Deep structural diff with a float tolerance. [] means identical."""
    where = path or "<root>"
    if isinstance(left, dict) and isinstance(right, dict):
        out: list[str] = []
        for key in sorted(set(left) | set(right)):
            if key not in left:
                out.append(f"{where}.{key}: only on the right side")
            elif key not in right:
                out.append(f"{where}.{key}: only on the left side")
            else:
                out.extend(_json_diff(left[key], right[key], f"{path}.{key}"))
        return out
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [f"{where}: length {len(left)} != {len(right)}"]
        out = []
        for i, (a, b) in enumerate(zip(left, right)):
            out.extend(_json_diff(a, b, f"{path}[{i}]"))
        return out
    if isinstance(left, bool) or isinstance(right, bool):
        return [] if left is right else [f"{where}: {left!r} != {right!r}"]
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if abs(float(left) - float(right)) <= FLOAT_TOLERANCE:
            return []
        return [f"{where}: {left!r} != {right!r}"]
    return [] if left == right else [f"{where}: {left!r} != {right!r}"]


def _git(args: list[str]) -> tuple[int, str]:
    """Run git in the project root; never raises."""
    try:
        proc = subprocess.run(["git", *args], cwd=str(PROJECT),
                              capture_output=True, text=True, timeout=30)
        return proc.returncode, proc.stdout
    except Exception as exc:  # noqa: BLE001 - git absence must not crash the validator
        return 127, f"{type(exc).__name__}: {exc}"


# =============================================================================
# checks - each returns (state, summary, details)
# =============================================================================
def check_spec_loads(ctx: dict) -> tuple[str, str, list[str]]:
    """1. The pre-registered spec parses and satisfies its own invariants."""
    if ctx["spec_error"]:
        return FAIL, "spec failed to load/validate", [ctx["spec_error"]]
    spec = ctx["spec"]
    return PASS, (f"{spec.experiment_id} {spec.spec_version} "
                  f"fp={spec.fingerprint()[:12]} planned={spec.planned_run_count()}"), []


def check_grid(ctx: dict) -> tuple[str, str, list[str]]:
    """2. Grid structure: 13 points, unique identity, contiguous indices, 1 ref."""
    errors: list[str] = []
    try:
        points = grid_mod.build_grid()      # calls validate_grid internally
    except Exception as exc:  # noqa: BLE001
        return FAIL, "build_grid() raised", [f"{type(exc).__name__}: {exc}"]

    if len(points) != 13:
        errors.append(f"grid has {len(points)} points, expected 13 (B0 + 12)")
    names = [p.name for p in points]
    if len(set(names)) != len(names):
        errors.append(f"duplicate configuration names: {names}")
    if len({p.fingerprint() for p in points}) != len(points):
        errors.append("duplicate configuration fingerprints: grid points collide")
    refs = [p for p in points if p.is_reference]
    if len(refs) != 1:
        errors.append(f"expected exactly 1 reference point, found {len(refs)}")
    varied = [p for p in points if not p.is_reference]
    indices = sorted(p.grid_index for p in varied)
    if indices != list(range(12)):
        errors.append(f"varied grid indices {indices} != 0..11")
    else:
        # Frozen enumeration order: grid_index = parallelism_idx * 4 + shuffle_idx.
        for p in varied:
            expected = (grid_mod.PARALLELISM_LEVELS.index(p.parallelism)
                        * len(grid_mod.SHUFFLE_PARTITION_LEVELS)
                        + grid_mod.SHUFFLE_PARTITION_LEVELS.index(p.shuffle_partitions))
            if p.grid_index != expected:
                errors.append(f"{p.name}: grid_index {p.grid_index} != {expected}")
    if errors:
        return FAIL, f"{len(errors)} grid violation(s)", errors
    return PASS, (f"13 points, 12 varied indices 0..11, 1 reference, "
                  f"grid_fp={grid_mod.grid_fingerprint(points)[:12]}"), []


def check_b0_frozen(ctx: dict) -> tuple[str, str, list[str]]:
    """3. B0 is in the grid and configs/baseline_b0.yaml still matches it."""
    errors: list[str] = []
    if grid_mod.B0_NAME not in {p.name for p in grid_mod.build_grid()}:
        errors.append("B0 reference point absent from the grid")
    if ctx["base_config"] is None:
        errors.append(f"could not load the B0 config: {ctx['base_config_error']}")
    else:
        try:
            grid_mod.assert_b0_unchanged(ctx["base_config"])
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        return FAIL, "B0 reference drift", errors
    cfg = ctx["base_config"]
    return PASS, (f"B0 pinned: {cfg.master}, shuffle_partitions="
                  f"{cfg.shuffle_partitions}, default_parallelism="
                  f"{cfg.default_parallelism}, driver={cfg.driver_memory}"), []


def check_aqe_off(ctx: dict) -> tuple[str, str, list[str]]:
    """4. AQE OFF in the spec, every grid point, the B0 yaml and every record."""
    errors: list[str] = []
    spec = ctx["spec"]
    if spec is not None and spec.aqe_enabled:
        errors.append("spec declares aqe_enabled=true")
    for p in grid_mod.build_grid():
        if p.aqe_enabled:
            errors.append(f"grid point {p.name} has AQE enabled")
    if ctx["base_config"] is not None and ctx["base_config"].aqe_enabled:
        errors.append("configs/baseline_b0.yaml has aqe_enabled=true")
    for path, rec in ctx["records"]:
        rs = rec.get("run_spec") or {}
        label = rs.get("run_id", path.name)
        if rs.get("aqe_enabled") is not False:
            errors.append(f"{label}: run_spec.aqe_enabled="
                          f"{rs.get('aqe_enabled')!r} (must be false)")
        if (rec.get("metrics") or {}).get("aqe_enabled") is True:
            errors.append(f"{label}: metrics.aqe_enabled=True")
    if errors:
        return FAIL, f"{len(errors)} AQE violation(s)", errors
    if not ctx["records"]:
        return SKIP, ("spec/grid/B0 verified AQE-off; no stored run records to "
                      "inspect yet"), []
    return PASS, (f"AQE off in the spec, 13 grid points, the B0 yaml and "
                  f"{len(ctx['records'])} record(s)"), []


def check_varied_parameters(ctx: dict) -> tuple[str, str, list[str]]:
    """5. Only PLAN-14 parameters differ between a candidate and B0."""
    errors: list[str] = []
    allowed = set(grid_mod.VARIED_PARAMETERS)
    for p in grid_mod.build_grid():
        delta = p.delta_from_b0()
        if p.is_reference:
            if delta:
                errors.append(f"{p.name}: the reference point differs from B0 in "
                              f"{sorted(delta)}")
            continue
        if not delta:
            errors.append(f"{p.name}: identical to B0 (not a distinct condition)")
        illegal = sorted(set(delta) - allowed)
        if illegal:
            errors.append(f"{p.name}: varies non-permitted parameter(s) {illegal}")
    if errors:
        return FAIL, f"{len(errors)} action-space violation(s)", errors
    return PASS, f"only {sorted(allowed)} vary across the 12 candidates", []


def check_workloads_frozen(ctx: dict) -> tuple[str, str, list[str]]:
    """6. Every declared family is a frozen, registered workload."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    errors = []
    for fam in ctx["spec"].families:
        if fam not in FAMILIES:
            errors.append(f"{fam} is not in the frozen family set {list(FAMILIES)}")
        if fam not in REGISTRY:
            errors.append(f"{fam} is not in workloads.registry.REGISTRY")
    if errors:
        return FAIL, "workload definition drift", errors
    return PASS, (f"{len(ctx['spec'].families)} declared families all registered "
                  f"and inside the frozen set"), []


def check_run_ids_deterministic(ctx: dict) -> tuple[str, str, list[str]]:
    """7. plan() is reproducible and every stored run_id is recomputable."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    spec = ctx["spec"]
    errors: list[str] = []
    first = [r.run_id for r in spec.plan()]
    second = [r.run_id for r in spec.plan()]
    if first != second:
        errors.append("spec.plan() produced a different run_id sequence on replay")
    if len(set(first)) != len(first):
        errors.append("spec.plan() contains duplicate run ids")

    for path, rec in ctx["records"]:
        rs = rec.get("run_spec") or {}
        try:
            expected = run_id_for(rs["family"], rs["scale"], int(rs["seed"]),
                                  rs["config_name"], int(rs["rep"]))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{path.name}: cannot recompute run_id ({exc})")
            continue
        if rs.get("run_id") != expected:
            errors.append(f"{path.name}: stored run_id {rs.get('run_id')!r} != "
                          f"recomputed {expected!r}")
    if errors:
        return FAIL, f"{len(errors)} identity violation(s)", errors
    if not ctx["records"]:
        return SKIP, (f"plan() reproducible over {len(first)} ids; no stored "
                      f"records to re-derive yet"), []
    return PASS, (f"plan() reproducible ({len(first)} ids) and "
                  f"{len(ctx['records'])} stored run_id(s) recomputed"), []


def check_result_structure(ctx: dict) -> tuple[str, str, list[str]]:
    """8. Records live exactly where the pre-registered plan says they do."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    if not ctx["records"]:
        return SKIP, "no stored run records yet", []
    declared = {r.run_id: r.relative_path().as_posix() for r in ctx["spec"].plan()}
    runs_dir = ctx["result_root"] / "runs"
    errors = []
    for path, rec in ctx["records"]:
        rs = rec.get("run_spec") or {}
        run_id = rs.get("run_id")
        actual = path.relative_to(runs_dir).as_posix()
        if run_id not in declared:
            errors.append(f"{actual}: run_id {run_id!r} is not in the plan")
            continue
        if actual != declared[run_id]:
            errors.append(f"{run_id}: stored at {actual}, the plan declares "
                          f"{declared[run_id]}")
        if rs.get("relative_path") != declared[run_id]:
            errors.append(f"{run_id}: record relative_path "
                          f"{rs.get('relative_path')!r} != {declared[run_id]!r}")
    if errors:
        return FAIL, f"{len(errors)} misplaced record(s)", errors
    return PASS, f"{len(ctx['records'])} record(s) at their planned paths", []


def check_manifests(ctx: dict) -> tuple[str, str, list[str]]:
    """9. Raw manifests carry the required keys and structurally valid metrics."""
    errors = [f"unreadable record: {u}" for u in ctx["unreadable"]]
    if not ctx["records"] and not errors:
        return SKIP, "no stored run records yet", []
    for path, rec in ctx["records"]:
        label = (rec.get("run_spec") or {}).get("run_id") or path.name
        for key in REQUIRED_RECORD_KEYS:
            if key not in rec:
                errors.append(f"{label}: missing top-level key {key!r}")
        if rec.get("schema_version") != RECORD_SCHEMA_VERSION:
            errors.append(f"{label}: schema_version {rec.get('schema_version')!r} "
                          f"!= {RECORD_SCHEMA_VERSION!r}")
        if rec.get("experiment_id") != EXPERIMENT_ID:
            errors.append(f"{label}: experiment_id {rec.get('experiment_id')!r} "
                          f"!= {EXPERIMENT_ID!r}")
        metrics = rec.get("metrics") or {}
        if metrics.get("schema_version") != METRICS_SCHEMA:
            errors.append(f"{label}: metrics.schema_version "
                          f"{metrics.get('schema_version')!r} != {METRICS_SCHEMA!r}")
            continue
        try:
            problems = validate_run_metrics(RunMetrics.from_dict(metrics))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label}: RunMetrics.from_dict failed: "
                          f"{type(exc).__name__}: {exc}")
            continue
        errors.extend(f"{label}: {p}" for p in problems)
    if errors:
        return FAIL, f"{len(errors)} manifest violation(s)", errors
    return PASS, (f"{len(ctx['records'])} manifest(s) complete, metrics schema "
                  f"{METRICS_SCHEMA} valid"), []


def check_validity_bookkeeping(ctx: dict) -> tuple[str, str, list[str]]:
    """10. status == COMPLETED if and only if metrics.usable is true."""
    if not ctx["records"]:
        return SKIP, "no stored run records yet", []
    errors = []
    n_valid = 0
    for path, rec in ctx["records"]:
        label = (rec.get("run_spec") or {}).get("run_id") or path.name
        completed = rec.get("status") == "COMPLETED"
        usable = bool((rec.get("metrics") or {}).get("usable"))
        n_valid += int(usable)
        if completed != usable:
            errors.append(f"{label}: status={rec.get('status')!r} but "
                          f"metrics.usable={usable} - an incomplete run must never "
                          f"be treated as a valid observation")
    if errors:
        return FAIL, f"{len(errors)} validity-bookkeeping violation(s)", errors
    return PASS, (f"{len(ctx['records'])} record(s): {n_valid} valid, "
                  f"{len(ctx['records']) - n_valid} invalid-but-recorded"), []


def check_split_separation(ctx: dict) -> tuple[str, str, list[str]]:
    """11. Every stored run is a TRAIN cell, by its label and by recomputation."""
    if not ctx["records"]:
        return SKIP, "no stored run records yet", []
    errors = []
    for path, rec in ctx["records"]:
        rs = rec.get("run_spec") or {}
        label = rs.get("run_id", path.name)
        if rs.get("split") != "train":
            errors.append(f"{label}: run_spec.split={rs.get('split')!r} != 'train'")
        try:
            actual = split_of(rs["family"], rs["scale"], int(rs["seed"]))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: cannot classify the cell ({exc})")
            continue
        if actual != "train":
            errors.append(f"{label}: cell {rs['family']}/{rs['scale']}/"
                          f"seed{rs['seed']} classifies as {actual!r}")
    if errors:
        return FAIL, f"{len(errors)} split violation(s)", errors
    return PASS, f"all {len(ctx['records'])} record(s) are TRAIN cells", []


def check_test_set_frozen(ctx: dict) -> tuple[str, str, list[str]]:
    """12. Nothing under the result root touches the frozen VALIDATION/TEST cells."""
    root = ctx["result_root"]
    if not root.is_dir():
        return SKIP, "result root does not exist yet", []
    errors = []
    n_scanned = 0
    for path in sorted(root.rglob("*.json")):
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue                      # reported by the manifest check
        rs = blob.get("run_spec") if isinstance(blob, dict) else None
        if not isinstance(rs, dict):
            continue                      # spec.json / analysis output, not a run
        n_scanned += 1
        if rs.get("family") == FROZEN_FAMILY:
            errors.append(f"{path}: family {FROZEN_FAMILY} is the unseen TEST family")
        if rs.get("scale") == FROZEN_SCALE:
            errors.append(f"{path}: scale {FROZEN_SCALE} is the unseen TEST scale")
        if rs.get("seed") in FROZEN_SEEDS:
            errors.append(f"{path}: seed {rs.get('seed')} is frozen "
                          f"(3 = VALIDATION/EXP-003, 4 = TEST)")
    # Directory names are a second, cheaper witness of the same freeze.
    runs_dir = root / "runs"
    forbidden_dirs = {FROZEN_FAMILY, FROZEN_SCALE, "seed3", "seed4"}
    if runs_dir.is_dir():
        for path in sorted(runs_dir.rglob("*")):
            hit = forbidden_dirs.intersection(path.parts)
            if hit:
                errors.append(f"{path}: frozen-split path component(s) {sorted(hit)}")
    if errors:
        return FAIL, f"TEST-SET LEAK: {len(errors)} violation(s)", errors
    if not n_scanned:
        return SKIP, "no run records under the result root yet", []
    return PASS, (f"{n_scanned} record(s) scanned: no {FROZEN_FAMILY}, no "
                  f"'{FROZEN_SCALE}', no seed in {list(FROZEN_SEEDS)}"), []


def check_analysis_reproducible(ctx: dict) -> tuple[str, str, list[str]]:
    """13. Stored gate.json is exactly what the stored records still produce."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    if ctx["build_report"] is None:
        return SKIP, f"analysis module unavailable: {ctx['analysis_error']}", []
    gate_path = ctx["result_root"] / "analysis" / "gate.json"
    if not gate_path.is_file():
        return SKIP, "no analysis/gate.json yet (run scripts/analyze_exp002.py)", []
    try:
        stored = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return FAIL, "gate.json unreadable", [f"{gate_path}: {exc}"]

    records = [rec for _, rec in ctx["records"]]
    # Provenance fields are echoed back so the comparison is over the science only.
    try:
        recomputed = ctx["build_report"](records, ctx["spec"],
                                         generated_utc=stored.get("generated_utc"),
                                         code_version=stored.get("code_version"))
    except Exception as exc:  # noqa: BLE001
        return FAIL, "re-running the analysis raised", [f"{type(exc).__name__}: {exc}"]

    diffs = _json_diff(stored, recomputed)
    if diffs:
        head = [f"MISMATCH: stored gate.json is NOT reproducible from the "
                f"{len(records)} stored record(s) - {len(diffs)} difference(s)"]
        return FAIL, "gate.json NOT reproducible", head + diffs
    return PASS, (f"gate.json reproduced exactly from {len(records)} record(s); "
                  f"gate={stored.get('gate', {}).get('result')}"), []


def check_gate_deterministic(ctx: dict) -> tuple[str, str, list[str]]:
    """14. build_report is a pure function of (records, spec)."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    if ctx["build_report"] is None:
        return SKIP, f"analysis module unavailable: {ctx['analysis_error']}", []
    if not ctx["records"]:
        return SKIP, "no stored run records to analyse yet", []
    records = [rec for _, rec in ctx["records"]]
    pinned = {"generated_utc": "1970-01-01T00:00:00+00:00", "code_version": "pinned"}
    try:
        first = ctx["build_report"](records, ctx["spec"], **pinned)
        second = ctx["build_report"](records, ctx["spec"], **pinned)
    except Exception as exc:  # noqa: BLE001
        return FAIL, "build_report raised", [f"{type(exc).__name__}: {exc}"]
    left = json.dumps(first, sort_keys=True)
    right = json.dumps(second, sort_keys=True)
    if left != right:
        return FAIL, "build_report is not deterministic", _json_diff(first, second)
    return PASS, (f"two passes byte-identical ({len(left)} chars), "
                  f"gate={first.get('gate', {}).get('result')}"), []


def check_no_rl_implementation(ctx: dict) -> tuple[str, str, list[str]]:
    """15. No RL machinery exists: EXP-002 is a calibration experiment."""
    errors = []
    n_files = 0
    for path in _source_files():
        n_files += 1
        rel = path.relative_to(PROJECT).as_posix()
        if path.name in RL_MODULE_NAMES and _substantive_lines(path) > 0:
            errors.append(f"{rel}: RL-named module with "
                          f"{_substantive_lines(path)} substantive line(s)")
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            errors.append(f"{rel}: unreadable ({exc})")
            continue
        for number, line in enumerate(lines, start=1):
            if RL_DEF_RE.match(line) or RL_BIND_RE.match(line):
                errors.append(f"{rel}:{number}: RL definition: {line.strip()[:90]}")
    # The agent package is a reserved, deliberately empty placeholder (Day 26+).
    if not RL_PLACEHOLDER.is_file():
        errors.append(f"{RL_PLACEHOLDER} is missing (reserved empty placeholder)")
    elif _substantive_lines(RL_PLACEHOLDER) > 0:
        errors.append(f"{RL_PLACEHOLDER.relative_to(PROJECT).as_posix()} is no longer "
                      f"empty: an agent has been implemented")
    if errors:
        return FAIL, f"RL implementation detected ({len(errors)} hit(s))", errors
    return PASS, (f"{n_files} source file(s): no agent/policy/reward/Q-table/"
                  f"epsilon definition; agent/ placeholder still empty"), []


def check_no_exp001(ctx: dict) -> tuple[str, str, list[str]]:
    """16. EXP-001 was not smuggled in alongside EXP-002."""
    hits = [p.relative_to(PROJECT).as_posix()
            for p in list((PROJECT / "scripts").glob("run_exp001*.py"))
            + list((SRC / "sparkrl" / "experiments").glob("exp001*.py"))]
    if hits:
        return FAIL, "EXP-001 implementation present", hits
    return PASS, "no scripts/run_exp001*.py, no experiments/exp001*.py", []


def check_documentation(ctx: dict) -> tuple[str, str, list[str]]:
    """17. The EXP-002 audit document exists and is substantive."""
    rel = AUDIT_DOC.relative_to(PROJECT).as_posix()
    if not AUDIT_DOC.is_file():
        return FAIL, "audit document missing", [
            f"{rel} does not exist - EXP-002 is undocumented. It must be written "
            f"by hand; this validator will not create it."]
    size = len(AUDIT_DOC.read_text(encoding="utf-8", errors="replace"))
    if size < AUDIT_DOC_MIN_CHARS:
        return FAIL, "audit document is a stub", [
            f"{rel} is {size} chars, minimum {AUDIT_DOC_MIN_CHARS}"]
    return PASS, f"{rel} present ({size} chars)", []


def check_no_architecture_drift(ctx: dict) -> tuple[str, str, list[str]]:
    """18. Frozen Day-3/13/15/16/18/19 code is untouched in the working tree."""
    rc_status, status_out = _git(["status", "--porcelain"])
    if rc_status != 0:
        return SKIP, "git unavailable / not a repository", [status_out.strip()]
    rc_diff, diff_out = _git(["diff", "--name-only", "HEAD"])

    touched: set[str] = set()
    for line in status_out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:                        # rename: the destination matters
            path = path.split(" -> ", 1)[1].strip().strip('"')
        touched.add(path)
    if rc_diff == 0:
        touched.update(p.strip() for p in diff_out.splitlines() if p.strip())

    violations = sorted(
        p for p in touched
        if p not in KNOWN_UNCOMMITTED
        and "__pycache__" not in p and not p.endswith(".pyc")
        and any(p == prefix or p.startswith(prefix) for prefix in FROZEN_PREFIXES))
    if violations:
        return FAIL, f"{len(violations)} frozen path(s) modified", [
            f"{p} is frozen (allowed uncommitted exceptions: "
            f"{sorted(KNOWN_UNCOMMITTED)})" for p in violations]
    allowed_seen = sorted(touched & KNOWN_UNCOMMITTED)
    return PASS, (f"no frozen path modified; {len(allowed_seen)} known Day-19 "
                  f"exception(s) present"), []


def check_gate_artifact(ctx: dict) -> tuple[str, str, list[str]]:
    """19. gate.json exists, parses, and carries every required field."""
    gate_path = ctx["result_root"] / "analysis" / "gate.json"
    if not gate_path.is_file():
        return SKIP, ("no analysis/gate.json yet - the authoritative collection must "
                      "finish, then run scripts/analyze_exp002.py"), []
    try:
        report = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return FAIL, "gate.json is not valid JSON", [f"{gate_path}: {exc}"]

    errors: list[str] = []
    required_top = ("schema_version", "analysis_version", "experiment_id",
                    "generated_utc", "spec_fingerprint", "grid_fingerprint",
                    "metric", "execution", "configurations", "workloads", "scales",
                    "seeds", "repetitions", "aqe_enabled", "split", "panels",
                    "sensitivity", "gate", "t_ref_calibration")
    for key in required_top:
        if key not in report:
            errors.append(f"missing top-level key: {key}")
    for key in ("planned_runs", "records_found", "valid", "invalid", "missing",
                "invalid_breakdown", "invalid_runs"):
        if key not in (report.get("execution") or {}):
            errors.append(f"missing execution.{key}")
    gate = report.get("gate") or {}
    for key in ("criteria", "result", "reasons", "families",
                "families_sensitive", "n_families_sensitive"):
        if key not in gate:
            errors.append(f"missing gate.{key}")
    if gate.get("result") not in ("PASS", "FAIL"):
        errors.append(f"gate.result must be PASS or FAIL, got {gate.get('result')!r}")
    if report.get("experiment_id") != "EXP-002":
        errors.append(f"experiment_id is {report.get('experiment_id')!r}")
    if report.get("metric") != "execution_time_s":
        errors.append(f"metric is {report.get('metric')!r}, not execution_time_s")
    if report.get("aqe_enabled"):
        errors.append("gate.json records aqe_enabled=true")
    crit = gate.get("criteria") or {}
    if crit.get("min_relative_spread") != 0.10:
        errors.append(f"min_relative_spread is {crit.get('min_relative_spread')!r}, "
                      f"not the frozen PLAN H1 value 0.10")
    if crit.get("min_families") != 2:
        errors.append(f"min_families is {crit.get('min_families')!r}, not the frozen "
                      f"PLAN section 33 value 2")
    if ctx["spec"] is not None:
        if report.get("spec_fingerprint") != ctx["spec"].fingerprint():
            errors.append("gate.json spec_fingerprint does not match the current spec")
    if errors:
        return FAIL, "gate.json is malformed or contradicts the frozen design", errors
    return PASS, (f"gate.json valid: {gate['result']}, "
                  f"{report['execution']['valid']} valid / "
                  f"{report['execution']['planned_runs']} planned"), []


def check_inventory_complete(ctx: dict) -> tuple[str, str, list[str]]:
    """20. The authoritative dataset is fully inventoried against the 208-run design."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    spec = ctx["spec"]
    planned = {r.run_id for r in spec.plan()}
    if len(planned) != 208:
        return FAIL, f"design plans {len(planned)} runs, expected 208", []

    found, dupes = {}, []
    for path, rec in ctx["records"]:
        rid = (rec.get("run_spec") or {}).get("run_id")
        if rid in found:
            dupes.append(f"duplicate run_id {rid}: {found[rid]} and {path}")
        found[rid] = path

    errors = list(dupes)
    unexpected = sorted(set(found) - planned)
    for rid in unexpected:
        errors.append(f"run_id not in the pre-registered plan: {rid}")
    if ctx["unreadable"]:
        for path in ctx["unreadable"]:
            errors.append(f"unreadable manifest: {path}")

    missing = sorted(planned - set(found))
    counts = {"COMPLETED": 0, "FAILED": 0, "INCOMPLETE": 0, "other": 0}
    for _, rec in ctx["records"]:
        counts[rec.get("status") if rec.get("status") in counts else "other"] += 1
    summary = (f"planned=208 discovered={len(found)} completed={counts['COMPLETED']} "
               f"failed={counts['FAILED']} incomplete={counts['INCOMPLETE']} "
               f"missing={len(missing)}")
    if errors:
        return FAIL, "inventory is inconsistent with the frozen design", errors
    if missing:
        return SKIP, (summary + " - collection INCOMPLETE, the gate cannot be "
                      "evaluated on the full design yet"), \
            [f"first missing: {m}" for m in missing[:5]]
    return PASS, summary, []


def check_no_archived_contamination(ctx: dict) -> tuple[str, str, list[str]]:
    """21. Discarded first-pass manifests cannot reach the authoritative analysis."""
    root = ctx["result_root"].resolve()
    errors: list[str] = []
    archives = sorted(p for p in root.parent.glob("*discarded*") if p.is_dir())

    for archive in archives:
        if archive.resolve() == root or archive.resolve().is_relative_to(root):
            errors.append(f"archive {archive} sits INSIDE the authoritative result "
                          f"root - its manifests would be analysed")

    # Positive evidence: every analysed manifest lives under <root>/runs, and the
    # contaminated marker (B0 with a default.parallelism that is not local[N]'s N)
    # appears in no accepted record.
    for path, rec in ctx["records"]:
        if not Path(path).resolve().is_relative_to(root / "runs"):
            errors.append(f"analysed manifest outside <root>/runs: {path}")
        rs = rec.get("run_spec") or {}
        applied = (rec.get("provenance") or {}).get("applied_settings") or {}
        if rs.get("config_name") == "B0" and applied:
            dp = str(applied.get("spark.default.parallelism"))
            if dp not in ("2", "None"):
                errors.append(f"{rs.get('run_id')}: B0 recorded "
                              f"default.parallelism={dp} - this is the discarded "
                              f"pass-1 contamination signature")
    if errors:
        return FAIL, "contaminated observations may enter the analysis", errors
    n_arch = sum(len(list(a.rglob('*.json'))) for a in archives)
    return PASS, (f"{len(archives)} archive dir(s) holding {n_arch} discarded "
                  f"manifest(s), all outside the authoritative root; "
                  f"{len(ctx['records'])} analysed manifest(s) all inside it"), []


def check_effective_config_readback(ctx: dict) -> tuple[str, str, list[str]]:
    """22. Every accepted observation proves its configuration actually applied."""
    if ctx["spec"] is None:
        return SKIP, "spec unavailable", []
    if not ctx["records"]:
        return SKIP, "no stored run records yet", []
    points = {p.name: p for p in ctx["spec"].grid}
    errors: list[str] = []
    checked = b0_checked = 0

    for path, rec in ctx["records"]:
        rs = rec.get("run_spec") or {}
        metrics = rec.get("metrics") or {}
        prov = rec.get("provenance") or {}
        name = rs.get("config_name")
        point = points.get(name)
        if point is None:
            errors.append(f"{rs.get('run_id')}: unknown configuration {name!r}")
            continue
        applied = prov.get("applied_settings")
        if not metrics.get("usable"):
            continue                      # invalid runs are not accepted observations
        checked += 1
        if not applied:
            errors.append(f"{rs.get('run_id')}: accepted as valid but has NO "
                          f"effective-configuration read-back")
            continue
        want_dp = str(point.effective_default_parallelism())
        expected = {
            "spark.master": point.master,
            "spark.sql.shuffle.partitions": str(point.shuffle_partitions),
            "spark.default.parallelism": want_dp,
            "sc.defaultParallelism": want_dp,
        }
        for key, want in expected.items():
            got = str(applied.get(key))
            if got != want:
                errors.append(f"{rs.get('run_id')}: {key} read back as {got!r}, "
                              f"configuration requires {want!r}")
        if str(applied.get("spark.sql.adaptive.enabled")).lower() != "false":
            errors.append(f"{rs.get('run_id')}: AQE read back as "
                          f"{applied.get('spark.sql.adaptive.enabled')!r}")
        if prov.get("applied_mismatches"):
            errors.append(f"{rs.get('run_id')}: accepted as valid despite recorded "
                          f"mismatches {prov['applied_mismatches']}")
        if metrics.get("execution_time_source") != "runner":
            errors.append(f"{rs.get('run_id')}: execution_time_source is "
                          f"{metrics.get('execution_time_source')!r}, not the "
                          f"authoritative runner clock")
        if point.is_reference:
            b0_checked += 1

    if errors:
        return FAIL, "effective-configuration provenance is not satisfied", errors
    return PASS, (f"{checked} accepted observation(s) verified against their requested "
                  f"knobs ({b0_checked} B0), all timed by the runner clock"), []


CHECKS = [
    ("01 spec_loads", check_spec_loads),
    ("02 grid_valid", check_grid),
    ("03 b0_frozen", check_b0_frozen),
    ("04 aqe_off", check_aqe_off),
    ("05 varied_parameters", check_varied_parameters),
    ("06 workloads_frozen", check_workloads_frozen),
    ("07 run_ids_deterministic", check_run_ids_deterministic),
    ("08 result_structure", check_result_structure),
    ("09 raw_manifests", check_manifests),
    ("10 validity_bookkeeping", check_validity_bookkeeping),
    ("11 split_separation", check_split_separation),
    ("12 test_set_frozen", check_test_set_frozen),
    ("13 analysis_reproducible", check_analysis_reproducible),
    ("14 gate_deterministic", check_gate_deterministic),
    ("15 no_rl_implementation", check_no_rl_implementation),
    ("16 no_exp001", check_no_exp001),
    ("17 documentation", check_documentation),
    ("18 no_architecture_drift", check_no_architecture_drift),
    ("19 gate_artifact", check_gate_artifact),
    ("20 inventory_complete", check_inventory_complete),
    ("21 no_archived_contamination", check_no_archived_contamination),
    ("22 effective_config_readback", check_effective_config_readback),
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="EXP-002 structural / scientific-integrity validator")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC),
                    help="pre-registered experiment spec YAML")
    ap.add_argument("--result-root", default=None,
                    help="override the result root (default: taken from the spec)")
    ap.add_argument("--max-details", type=int, default=12,
                    help="max detail lines printed per failing check (0 = all)")
    args = ap.parse_args(argv)

    # ---- context shared by every check --------------------------------
    spec: ExperimentSpec | None = None
    spec_error: str | None = None
    try:
        spec = ExperimentSpec.from_yaml(args.spec)
    except Exception as exc:  # noqa: BLE001 - a bad spec is a FAIL, not a crash
        spec_error = f"{type(exc).__name__}: {exc}"

    base_config = None
    base_config_error = None
    b0_path = PROJECT / (spec.base_config_path if spec else "configs/baseline_b0.yaml")
    try:
        base_config = SparkConfig.from_yaml(str(b0_path))
    except Exception as exc:  # noqa: BLE001
        base_config_error = f"{type(exc).__name__}: {exc}"

    if args.result_root:
        result_root = Path(args.result_root)
    elif spec is not None:
        result_root = PROJECT / spec.result_root
    else:
        result_root = DEFAULT_RESULT_ROOT

    records, unreadable = _load_records(result_root)

    # The analysis module is written concurrently; its absence is a SKIP, not a crash.
    build_report = None
    analysis_error = None
    try:
        from sparkrl.analysis.exp002 import build_report  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        analysis_error = f"{type(exc).__name__}: {exc}"

    ctx = {"spec": spec, "spec_error": spec_error,
           "base_config": base_config, "base_config_error": base_config_error,
           "result_root": result_root, "records": records, "unreadable": unreadable,
           "build_report": build_report, "analysis_error": analysis_error}

    # ---- header -------------------------------------------------------
    print("=" * 78)
    print("EXP-002 CONFIGURATION-SENSITIVITY VALIDATOR")
    print("=" * 78)
    print(f"project     : {PROJECT}")
    print(f"spec        : {args.spec}")
    print(f"B0 config   : {b0_path}")
    print(f"result root : {result_root}")
    print(f"records     : {len(records)} found"
          + (f" ({len(unreadable)} unreadable)" if unreadable else ""))
    if spec is not None:
        print(f"planned     : {spec.planned_run_count()} runs "
              f"({len(spec.grid)} configs x {len(spec.families)} families x "
              f"{len(spec.scales)} scales x {spec.repetitions} reps)")
    print()
    print(f"{'CHECK':<26} {'RESULT':<7} DETAIL")
    print("-" * 78)

    results = []
    for name, fn in CHECKS:
        try:
            state, summary, details = fn(ctx)
        except Exception as exc:  # noqa: BLE001 - a broken check FAILS, never crashes
            state, summary, details = FAIL, "check raised", [
                f"{type(exc).__name__}: {exc}"]
        results.append((name, state, summary, details))
        print(f"{name:<26} {state:<7} {summary}")

    failed = [r for r in results if r[1] == FAIL]
    skipped = [r for r in results if r[1] == SKIP]
    passed = [r for r in results if r[1] == PASS]

    if failed:
        print()
        print("FAILURE DETAIL")
        print("-" * 78)
        cap = args.max_details if args.max_details > 0 else None
        for name, _, summary, details in failed:
            print(f"[{name}] {summary}")
            for line in details[:cap]:
                print(f"    - {line}")
            if cap is not None and len(details) > cap:
                print(f"    ... and {len(details) - cap} more")
    if skipped:
        print()
        print("SKIPPED (not yet verifiable - this is NOT a pass)")
        print("-" * 78)
        for name, _, summary, _ in skipped:
            print(f"[{name}] {summary}")

    print()
    print("=" * 78)
    verdict = FAIL if failed else PASS
    print(f"OVERALL: {verdict}  ({len(passed)} passed, {len(skipped)} skipped, "
          f"{len(failed)} failed of {len(results)} checks)")
    if skipped and not failed:
        print("NOTE: skipped checks are unverified, not satisfied - re-run once the "
              "missing inputs exist.")
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
