"""Unit tests for the DEC-039 EXP-008 zero-charge DERIVED ablation.

Everything here is deterministic and offline: no Spark session is opened and
the training ledger is untouched. The stored-artifact checks are read-only
fingerprint verifications against ``results/evaluation/``.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

PROJECT = Path(__file__).resolve().parents[2]

LIMITATION_INITIALIZATION = (
    "A3 here ablates the OFFLINE INITIALIZATION, not ONLINE LEARNING.")
LIMITATION_RQ4 = (
    "RQ4 asks about learning stability and final policy quality; the "
    "learning-stability half is UNANSWERED by this decision and is reported "
    "as a stated limitation, with no claim about what a trained comparison "
    "would have shown.")
LIMITATION_DESCRIPTIVE = (
    "Descriptive only - no threshold and no inferential statistic is "
    "computed or asserted (DEC-030 section 8).")


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_exp008_derived_ablation",
        PROJECT / "scripts" / "generate_exp008_derived_ablation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_greedy_tie_breaks_to_lowest_index() -> None:
    gen = _load_generator()
    row = [0.5] * 12
    assert gen.greedy_action(row, tuple(range(12))) == 0
    assert gen.greedy_action(row, (3, 6, 9)) == 3
    row2 = [0.0] * 12
    row2[9] = 1.0
    assert gen.greedy_action(row2, (3, 6, 9)) == 9


def test_subset_argmax_is_structural() -> None:
    """The mode4 greedy action is the argmax over the restricted row."""
    gen = _load_generator()
    rows = [[0.1 * a for a in range(12)], [1.0 - 0.05 * a for a in range(12)],
            [0.5] * 12, [0.0, 0.9, 0.0, 0.9, 0.0, 0.9, 0.0, 0.9,
                         0.0, 0.9, 0.0, 0.9]]
    allowed = tuple(sorted(gen.MODE4_SUBSET))
    for row in rows:
        sub = [row[a] for a in allowed]
        # argmax over the subset of the SAME row, mapped back to the index
        expected = allowed[gen.greedy_action(sub, tuple(range(len(sub))))]
        assert gen.greedy_action(row, allowed) == expected


def test_a3_r4_is_dropped_and_not_executable() -> None:
    from sparkrl.rl.reward import RewardCalculator
    with pytest.raises(RuntimeError):
        RewardCalculator(formula="A3-R4-log-ratio")


def test_stored_artifacts_are_sealed_and_descriptive() -> None:
    from sparkrl.evaluation import freeze as freeze_mod
    ablation = json.loads((PROJECT / "results" / "evaluation" /
                           "exp008_derived_ablation.json").read_text(
                               encoding="utf-8"))
    rerun = json.loads((PROJECT / "results" / "evaluation" /
                        "exp008_preflight_rerun.json").read_text(
                            encoding="utf-8"))
    for doc in (ablation, rerun):
        assert freeze_mod.artifact_fingerprint(doc) == doc["fingerprint"]
        assert doc["artifact_id"] == doc["fingerprint"]
        assert doc["executed"] is False
        assert doc["provenance"]["spark_executions"] == 0
    assert ablation["stated_limitations"] == [
        LIMITATION_INITIALIZATION, LIMITATION_RQ4, LIMITATION_DESCRIPTIVE]
    # A3-R4 is NOT retained in the table
    assert ablation["reward_variants"]["A3-R4-log-ratio"]["retained"] is False
    assert "A3-R4-log-ratio" not in ablation["ablation_table"]
    # the rerun records worst-case 0 / charge 0
    assert rerun["authorization"]["worst_case_live_train_executions"] == 0
    assert rerun["authorization"]["worst_case_ledger_charge"] == 0
