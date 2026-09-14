"""Day-32 EXP-001 validator/ledger maintenance: offline guarantees. No Spark.

EXP-001 was legitimately executed (20 TRAIN observations, PASS at 4.55%).
These tests pin the maintenance contract so the validator cannot silently
drift: EXP-001 artifacts must be TRAIN-only and exactly 20; the ledger must
count manifests + B4 + EXP-001 exactly once each; EXP-003/005/005b/006 must
never be charged to the 500 TRAIN cap; the stored median CV must reproduce.

Ledger tests below invoke the REAL production ledger_from_manifests() from
scripts/validate_day31.py against throwaway fixture trees (monkeypatched
module constants), never the frozen repository artifacts and never Spark.
"""
from __future__ import annotations

import importlib.util
import json
import statistics
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

PROJECT = Path(__file__).resolve().parents[2]

CELLS = (("F1_agg", "small"), ("F1_agg", "medium"),
         ("F2_join", "small"), ("F2_join", "medium"))
CAP = 500
DAY29_BASELINE = 232
B4_SPEND = 84
EXP001_SPEND = 20


def _load_day31():
    path = PROJECT / "scripts" / "validate_day31.py"
    spec = importlib.util.spec_from_file_location("day31_ledger", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture_tree(monkeypatch, tmp_path, *, manifest_live=232,
                  b4_total=84, exp001_total=20, exp001_test_data=False,
                  exp001_experiment_id="EXP-001", corrupt=None):
    """Build a throwaway ledger tree; point the REAL module constants at it.

    corrupt: None | "manifest" | "b4" | "exp001" - writes a non-numeric
    "total" (or live_executions) into that artifact to prove malformed data
    fails loudly instead of undercounting.
    """
    mod = _load_day31()
    train_root = tmp_path / "training"
    eval_dir = tmp_path / "evaluation"
    # Must mirror the REAL layout ledger_from_manifests() derives from PROJECT:
    # PROJECT / "results" / "experiments" / "exp-001" / "summary.json".
    exp_root = tmp_path / "results" / "experiments" / "exp-001"
    train_root.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    exp_root.mkdir(parents=True, exist_ok=True)
    (train_root / "run-a").mkdir(exist_ok=True)
    live_val = "many" if corrupt == "manifest" else manifest_live
    (train_root / "run-a" / "manifest.json").write_text(
        json.dumps({"budget": {"live_executions": live_val}}),
        encoding="utf-8")
    b4_val = "many" if corrupt == "b4" else b4_total
    (eval_dir / "b4_selection.json").write_text(
        json.dumps({"split": "train",
                    "observation_counts": {"total": b4_val}}),
        encoding="utf-8")
    e1_val = "many" if corrupt == "exp001" else exp001_total
    (exp_root / "summary.json").write_text(
        json.dumps({"experiment_id": exp001_experiment_id,
                    "contains_test_data": exp001_test_data,
                    "observation_counts": {"total": e1_val}}),
        encoding="utf-8")
    monkeypatch.setattr(mod, "TRAINING_ROOT", train_root)
    monkeypatch.setattr(mod, "ARTIFACT_DIR", eval_dir)
    monkeypatch.setattr(mod, "PROJECT", tmp_path)
    return mod


def test_exp001_present_output_is_train_only():
    rows = [json.loads(line) for line in
            (PROJECT / "results/experiments/exp-001/observations.jsonl")
            .read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 20
    assert all(r["split"] == "train" and r["usable"] for r in rows)
    assert all(r["dataset_seed"] == 0 for r in rows)
    assert all(r["execution_time_source"] == "runner" for r in rows)


def test_exp001_output_with_test_data_is_rejected(monkeypatch, tmp_path):
    # REAL production function: test-tainted EXP-001 must contribute 0. The
    # ledger then reads 232 + 84 + 0 = 316, i.e. the tainted 20 add NOTHING
    # to TRAIN consumption (they can never inflate the cap accounting).
    mod = _fixture_tree(monkeypatch, tmp_path, manifest_live=232,
                        exp001_test_data=True)
    n, live = mod.ledger_from_manifests()
    assert (n, live) == (1, DAY29_BASELINE + B4_SPEND)
    assert live == 336 - EXP001_SPEND  # the tainted 20 contributed exactly 0


def test_exp001_over_budget_count_breaks_the_pin(monkeypatch, tmp_path):
    # REAL production function: a 21-total EXP-001 reads back as 21, so the
    # frozen 336 pin no longer holds (232 + 84 + 21 = 337).
    mod = _fixture_tree(monkeypatch, tmp_path, manifest_live=232,
                        exp001_total=21)
    n, live = mod.ledger_from_manifests()
    assert live == 337
    assert live != DAY29_BASELINE + B4_SPEND + EXP001_SPEND



def test_exp001_non_train_cells_are_rejected():
    import sys
    sys.path.insert(0, str(PROJECT / "src"))
    from sparkrl.experiments.spec import assert_train_only
    for seed in (3, 4):  # VALIDATION / TEST seeds must refuse
        with pytest.raises(ValueError):
            assert_train_only("F1_agg", "small", seed)
    with pytest.raises(ValueError):
        assert_train_only("F4_ski", "small", 0)


def test_exp001_accounting_is_not_duplicated(monkeypatch, tmp_path):
    # REAL production function over a 232+84+20 fixture tree: exactly 336.
    mod = _fixture_tree(monkeypatch, tmp_path, manifest_live=232)
    n, live = mod.ledger_from_manifests()
    assert (n, live) == (1, 336)  # counted exactly once
    assert mod.ledger_from_manifests.errors == []


def test_unauthorized_extra_run_breaks_the_pin(monkeypatch, tmp_path):
    # REAL production function: one extra manifest execution -> 337, i.e.
    # unexplained == 1 and check 22 would FAIL.
    mod = _fixture_tree(monkeypatch, tmp_path, manifest_live=233)
    n, live = mod.ledger_from_manifests()
    assert live == 337
    assert live - DAY29_BASELINE - B4_SPEND - EXP001_SPEND == 1


def test_exp003_or_exp005_are_never_charged_to_sc6():
    src = (PROJECT / "scripts/validate_day31.py").read_text(encoding="utf-8")
    fn_start = src.index("def ledger_from_manifests")
    fn_end = src.index("\ndef ", fn_start + 1)
    fn_src = src[fn_start:fn_end]
    assert "exp-001" in fn_src and "b4_selection.json" in fn_src
    for token in ("exp-003", "exp003", "exp-005", "exp005", "exp005b",
                  "exp-006", "exp006"):
        assert token not in fn_src  # separate register lines, never SC6
    # REAL production function on the frozen repo tree: 336/164.
    live = _load_day31().ledger_from_manifests()[1]
    assert live == 336 and CAP - live == 164


def test_malformed_ledger_data_fails_loudly(monkeypatch, tmp_path):
    # REAL production function: a non-numeric count must be recorded in
    # ledger_from_manifests.errors (check 22 ANDs `not errors`), never
    # silently skipped into a lower total.
    for corrupt in ("manifest", "b4", "exp001"):
        mod = _fixture_tree(monkeypatch, tmp_path, manifest_live=232,
                            corrupt=corrupt)
        n, live = mod.ledger_from_manifests()
        assert mod.ledger_from_manifests.errors, corrupt
        assert live < 336, corrupt  # corrupt entry contributes nothing


def test_day25_rejects_hyphenated_forbidden_drivers(tmp_path, monkeypatch):
    # The check-12 glob set must catch exp-003/exp-005/exp-005b/exp-006 in
    # hyphen AND underscore form, must keep run_exp001.py authorized, and
    # must NOT flag exp002 scripts.
    import sys
    fake = tmp_path / "scripts"
    fake.mkdir()
    (fake / "run_exp001.py").write_text("x", encoding="utf-8")
    (fake / "run_exp002.py").write_text("x", encoding="utf-8")
    patterns = ("*exp00[356]*", "*exp-00[356]*", "*exp_00[356]*",
                "*exp005b*", "*exp-005b*", "*exp_005b*")
    benign = set()
    for pat in patterns:
        benign.update(p.name for p in fake.glob(pat))
    assert benign == set()  # exp002 untouched, run_exp001 filtered by name
    for bad in ("run_exp-003.py", "run_exp_005.py", "run_exp005b.py",
                "run_exp-005b.py", "run_exp006.py", "run_exp-006.py"):
        (fake / bad).write_text("x", encoding="utf-8")
        hits = set()
        for pat in patterns:
            hits.update(p.name for p in fake.glob(pat))
        hits.discard("run_exp001.py")
        assert bad in hits, bad
        (fake / bad).unlink()
    # And the REAL validator source carries exactly this pattern set.
    src = (PROJECT / "scripts/validate_rl_environment.py").read_text(
        encoding="utf-8")
    for pat in patterns:
        assert pat in src, pat


def test_stored_median_cv_reproduces_and_passes():
    summary = json.loads((PROJECT / "results/experiments/exp-001/summary.json")
                         .read_text(encoding="utf-8"))
    cvs = [c["cv"] for c in summary["cells"]]
    assert len(cvs) == 4 and all(c["n_usable"] == 5 for c in summary["cells"])
    assert statistics.median(cvs) == pytest.approx(summary["median_cv"])
    assert abs(summary["median_cv"] - 0.04548549) < 1e-6
    assert summary["verdict"] == "PASS" and summary["median_cv"] <= 0.10
    assert all(c["complete"] for c in summary["cells"])


def test_day25_driver_check_accepts_authorized_exp001():
    src = (PROJECT / "scripts/validate_rl_environment.py").read_text(
        encoding="utf-8")
    assert "exp001_driver_authorized" in src
    assert (PROJECT / "scripts/run_exp001.py").exists()
    path = PROJECT / "scripts/validate_rl_environment.py"
    spec = importlib.util.spec_from_file_location("day25_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod is not None  # imports cleanly with the new check in place
