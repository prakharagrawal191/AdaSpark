"""Skip unit tests whose research inputs are not on disk, saying which input is missing.

WHY THIS EXISTS. A fresh clone holds the code, the committed analysis artifacts
and the EXP-002 record, but not (a) the generated dataset matrix (about 5.1 GB,
regenerated with ``scripts/generate_dataset_matrix.py``) or (b) the raw research
records under ``results/experiments/`` and ``results/training/``, which are
git-ignored and await the DEC-045 archival deposit. Thirty-eight unit tests read
one of those, and on a clean checkout they failed with ``FileNotFoundError``,
indistinguishable from a software defect.

WHAT IT DOES. Each test below is listed with the inputs it reads. When one of
them is missing, the test is SKIPPED with a reason that names the input. When
they are present (the recording machine, or a clone with the deposit installed
and the datasets regenerated) nothing is skipped and every assertion runs
exactly as before. Test bodies are untouched: DECISIONS.md cites some of their
line numbers.

WHAT IT MUST NOT BREAK.
* ``pytest tests/unit`` is the validators' own gate (``validate_day30.py``
  check 23, ``validate_day31.py`` check 35). On the recording machine every
  listed input exists, so the gate runs the same tests as before.
* Only listed tests are touched. pytest hands this hook the whole session's
  items (see ``tests/integration/conftest.py``), so matching is by module file
  name and test function name.
* The SC6 ledger pin ``test_exp003_or_exp005_are_never_charged_to_sc6``
  (DEC-038) is gated on the EXP-001 record, not on the training manifests it
  counts: deleting training records from an installed deposit still fails it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
DATASETS = "datasets"  # requirement token: the complete generated dataset matrix

EXP001_OBS = "results/experiments/exp-001/observations.jsonl"
EXP001_SUMMARY = "results/experiments/exp-001/summary.json"
EXP005_OBS = "results/experiments/exp-005/observations.jsonl"
EXP006_OBS = "results/experiments/exp-006/observations.jsonl"
EXP009_OBS = "results/experiments/exp-009/observations.jsonl"
EXP009_EXT_OBS = "results/experiments/exp-009/ext/observations_ext.jsonl"
EXP009_EXT_ANALYSIS = "results/experiments/exp-009/ext/analysis_ext.json"
TRAINING = "results/training"  # requirement token: at least one training manifest
HARNESS = (EXP005_OBS, EXP006_OBS, EXP009_OBS, EXP009_EXT_OBS, TRAINING)

# module file -> {test function -> inputs it reads}
REQUIRES: dict[str, dict[str, tuple[str, ...]]] = {
    "test_exp001_maintenance.py": {
        "test_exp001_present_output_is_train_only": (EXP001_OBS,),
        "test_stored_median_cv_reproduces_and_passes": (EXP001_SUMMARY,),
        "test_exp003_or_exp005_are_never_charged_to_sc6": (EXP001_SUMMARY,),
    },
    "test_exp005_strategies.py": {
        "test_b3_collapses_onto_b1_at_this_data_scale": (DATASETS,),
        "test_b3_input_gb_comes_from_the_frozen_manifests": (DATASETS,),
    },
    "test_exp006_runner.py": {
        "test_policies_and_datasets_verify_readonly": (DATASETS,),
        "test_dataset_drift_fails": (DATASETS,),
        "test_dry_slice_runs_exactly_seven_rows_no_index8": (DATASETS,),
        "test_dry_slice_refuses_non_executable_slice": (DATASETS,),
    },
    "test_exp007_parity.py": {
        "test_build_env_and_agent_main_study_uses_exp002_q0": (DATASETS,),
    },
    "test_exp009_ext.py": {
        "test_queue_never_collides_with_the_dec040_record": (EXP009_OBS,),
        "test_baseline_record_is_pinned": (EXP009_OBS,),
        "test_ext_artifact_id_is_a_content_hash": (EXP009_EXT_ANALYSIS,),
    },
    "test_exp013.py": {
        "test_analysis_recovers_the_known_answer": (EXP005_OBS,),
        "test_analysis_excludes_incomplete_stages_and_short_cells": (EXP005_OBS,),
        "test_analysis_flags_code_deviation": (EXP005_OBS,),
    },
    "test_rl_env.py": {name: (DATASETS,) for name in (
        "test_reset_is_pure_no_execution_no_budget",
        "test_reset_determinism",
        "test_reset_last_reward_flips_feedback_bin",
        "test_budget_guard_done_at_episode_boundary",
        "test_step_executes_once_and_terminates",
        "test_action_to_config_deterministic",
        "test_invalid_action_rejected_pre_execution",
        "test_tref_missing_refuses_before_execution",
        "test_failed_execution_reward_minus_one_provenance_kept",
        "test_mode4_env_restricts_actions",
        "test_v1_state_schema_env",
        "test_transition_record_written_deterministic",
        "test_observation_never_carries_post_execution_metrics",
        "test_step_info_schema_frozen",
    )},
    "test_verify_reproducibility.py": {name: HARNESS for name in (
        "test_exp005_rederivation_matches_the_frozen_ledger",
        "test_exp005_rederivation_detects_a_tampered_sum",
        "test_exp005_rederivation_detects_tampered_coverage",
        "test_analyzer_byte_comparison_passes_on_an_exact_copy",
        "test_exp007_recorded_in_another_checkout_passes_once_mapped",
        "test_main_reports_pass_and_does_not_evaluate_sc7",
    )},
}


def _generated_dir() -> Path | None:
    """The dataset folder the workload resolver would use (same order and fallback)."""
    override = os.environ.get("SPARKRL_DATA_ROOT", "").strip()
    root = Path(override) if override else Path.home() / "sparkrl_data"
    for candidate in (root / "generated", Path("data") / "generated"):
        if (candidate / "index.json").exists():
            return candidate
    return None


def _datasets_complete() -> bool:
    """True when the generator's own summary reports all 30 datasets valid."""
    generated = _generated_dir()
    if generated is None:
        return False
    try:
        summary = json.loads((generated / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return summary.get("missing_physical") == 0 and \
        summary.get("valid_physical") == summary.get("total_physical")


def _missing(requirement: str) -> str | None:
    """Why a requirement is unmet, or None when it is met."""
    if requirement == DATASETS:
        return None if _datasets_complete() else (
            "the generated dataset matrix (run scripts/generate_dataset_matrix.py)")
    if requirement == TRAINING:
        root = PROJECT / TRAINING
        found = root.is_dir() and next(root.rglob("manifest.json"), None) is not None
        return None if found else f"{TRAINING}/ run manifests (raw research records)"
    return None if (PROJECT / requirement).exists() else f"{requirement} (raw research record)"


_SKIPPED = {"records": 0, "datasets": 0}


def pytest_collection_modifyitems(config, items):
    cache: dict[str, str | None] = {}
    for item in items:
        needs = REQUIRES.get(item.path.name, {}).get(getattr(item, "originalname", item.name))
        if not needs:
            continue
        reasons = [r for r in (cache.setdefault(n, _missing(n)) for n in needs) if r]
        if not reasons:
            continue
        kind = "datasets" if needs == (DATASETS,) else "records"
        _SKIPPED[kind] += 1
        detail = ("raw research records are not in this repository until the DEC-045 "
                  "deposit is installed" if kind == "records" else "datasets not generated")
        item.add_marker(pytest.mark.skip(reason=f"{detail}; missing: {'; '.join(reasons)}"))


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if any(_SKIPPED.values()):
        terminalreporter.write_line(
            f"data-gated unit tests skipped: {_SKIPPED['records']} need the raw research "
            f"records (DEC-045 deposit), {_SKIPPED['datasets']} need the generated datasets; "
            f"all other tests ran.")
