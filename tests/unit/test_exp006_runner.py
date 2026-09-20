"""EXP-006 runner tests: spec integrity, authorization, queue, undefined rows,
execution/durability semantics, dry-slice isolation. No Spark is started."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.evaluation.freeze import artifact_fingerprint  # noqa: E402
from sparkrl.evaluation.strategies import StrategyResolutionError  # noqa: E402
from sparkrl.spark.config import SparkConfig  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "run_exp006", PROJECT / "scripts" / "run_exp006.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

REAL_SPEC = json.loads(
    (PROJECT / "results" / "evaluation" / "exp006_spec.json").read_text(
        encoding="utf-8"))


def _reseal(doc: dict) -> dict:
    doc["fingerprint"] = artifact_fingerprint(doc)
    doc["artifact_id"] = doc["fingerprint"]
    return doc


def _write_spec(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "exp006_spec.json"
    p.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
    return p


# ---------------------------------------------------------------- spec seal
def test_missing_spec_fails(tmp_path):
    with pytest.raises(SystemExit, match="missing"):
        mod.verify_sealed_spec(tmp_path / "nope.json")


def test_altered_content_without_reseal_fails(tmp_path):
    doc = copy.deepcopy(REAL_SPEC)
    doc["repetitions"] = 6
    with pytest.raises(SystemExit):
        mod.verify_sealed_spec(_write_spec(tmp_path, doc))


def test_altered_protocol_fails(tmp_path):
    doc = _reseal({**copy.deepcopy(REAL_SPEC), "protocol_version": "exp999/v1"})
    with pytest.raises(SystemExit, match="fingerprint"):
        mod.verify_sealed_spec(_write_spec(tmp_path, doc))


def test_altered_queue_rows_fail(tmp_path):
    doc = copy.deepcopy(REAL_SPEC)
    doc["queue"]["rows"][6]["rep"] = 9          # in-structure row tampering
    doc = _reseal(doc)                          # resealed, counts altered too
    with pytest.raises(SystemExit):
        mod.verify_sealed_spec(_write_spec(tmp_path, doc))


def test_queue_fingerprint_recomputes_positive_control():
    # The same canonicalization the runner verifies with must reproduce the
    # sealed queue fingerprint on the untouched artifact.
    qfp = hashlib.sha256(json.dumps(
        REAL_SPEC["queue"]["rows"], sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()
    assert qfp == REAL_SPEC["fingerprints"]["queue"] == mod.FROZEN_QUEUE_FP


def test_wrong_queue_count_fails():
    doc = copy.deepcopy(REAL_SPEC)
    doc["queue"]["rows"] = doc["queue"]["rows"][:-1]
    with pytest.raises(SystemExit, match="queue count"):
        mod.validate_spec(doc)


def test_b3_present_fails():
    doc = copy.deepcopy(REAL_SPEC)
    doc["arms"]["executable"] = sorted(doc["arms"]["executable"] + ["B3"])
    with pytest.raises(SystemExit, match="executable-arm list drifted"):
        mod.validate_spec(doc)


def test_b2_f4_executable_fails():
    doc = copy.deepcopy(REAL_SPEC)
    for r in doc["queue"]["rows"]:
        if r["arm"] == "B2" and r["family"] == "F4_ski":
            r["executable"] = True
            r["identity"] = {"kind": "config", "config_name": "G-p8-sp16",
                             "config_fingerprint": "x"}
            break
    with pytest.raises(SystemExit) as excinfo:
        mod.validate_spec(doc)
    # Counts guard or the dedicated DEC-019 guard, whichever fires first;
    # either way an executable B2 x F4_ski row can never pass validation.
    assert ("105" in str(excinfo.value)) or ("DEC-019" in str(excinfo.value))


def test_real_spec_passes_full_verification():
    doc = mod.verify_sealed_spec()   # read-only; the sealed artifact untouched
    assert doc["artifact_id"] == mod.FROZEN_SPEC_FP


# ------------------------------------------------------------ authorization
def test_dec022_absent_fails():
    with pytest.raises(SystemExit, match="exactly once"):
        mod.verify_dec022(text="nothing here")


def test_dec022_duplicated_fails():
    text = mod.DECISIONS_PATH.read_text(encoding="utf-8")
    start = text.index("## DEC-022")
    end = text.find("\n## DEC-", start + 1)
    section = text[start:end if end != -1 else len(text)]
    with pytest.raises(SystemExit, match="exactly once"):
        mod.verify_dec022(text=text + "\n\n" + section)


def test_dec022_wrong_fingerprint_fails():
    text = mod.DECISIONS_PATH.read_text(encoding="utf-8")
    bad = text.replace(mod.FROZEN_SPEC_FP, "0" * 64)
    with pytest.raises(SystemExit, match="fingerprint_bound"):
        mod.verify_dec022(text=bad)


def test_dec022_wrong_experiment_fails():
    text = mod.DECISIONS_PATH.read_text(encoding="utf-8")
    start = text.index("## DEC-022")
    end = text.find("\n## DEC-", start + 1)
    section = text[start:end if end != -1 else len(text)]
    tail = text[end if end != -1 else len(text):]
    tampered = text[:start] + section.replace("EXP-006", "EXP-999") + tail
    with pytest.raises(SystemExit, match="names_experiment"):
        mod.verify_dec022(text=tampered)


def test_dec022_real_passes():
    assert all(mod.verify_dec022().values())


# -------------------------------------------------------------------- queue
def test_duplicate_index_rejected(tmp_path):
    p = tmp_path / "obs.jsonl"
    row = {"queue_index": 1, "usable": True}
    mod.append_observation(p, row)
    mod.append_observation(p, row)
    with pytest.raises(SystemExit, match="duplicate queue_index"):
        mod.load_observations(p)


def test_resume_starts_at_first_missing_index():
    entries = [{"queue_index": i} for i in range(1, 6)]
    todo = mod.resume_indices(entries, {1: {}, 2: {}, 3: {}})
    assert [e["queue_index"] for e in todo] == [4, 5]


def test_empty_ledger_resumes_from_one():
    entries = [{"queue_index": i} for i in range(1, 4)]
    assert [e["queue_index"] for e in mod.resume_indices(entries, {})] == \
        [1, 2, 3]


# ---------------------------------------------------------------- undefined
def _f4_b2_entry(idx: int = 6) -> dict:
    return {"queue_index": idx, "arm": "B2", "family": "F4_ski",
            "scale": "large", "dataset_seed": 0, "rep": 1, "split": "test",
            "executable": False, "identity": {"kind": "undefined"},
            "provenance": {}}


def test_undefined_row_shape():
    row = mod.undefined_row(_f4_b2_entry())
    assert row["usable"] is False and row["undefined"] is True
    assert row["config_name"] is None and row["config_fingerprint"] is None
    assert row["execution_time_s"] is None
    assert row["event_log_status"] == "NOT_EXECUTED"
    assert "DEC-019" in row["error"] and "B1" in row["error"]
    assert "DEC-019" in row["arm_provenance"]["decision"]


def test_undefined_row_writes_zero_spark(tmp_path):
    def _no_spark(*a, **k):  # sentinel: any Spark attempt fails the test
        raise AssertionError("Spark must not be called for undefined rows")

    obs = tmp_path / "obs.jsonl"
    counts = mod.run_entries([_f4_b2_entry()], obs, None, {},
                             {"B2": None}, {}, set(), execute_fn=_no_spark)
    assert counts == {"spark_attempted": 0, "usable": 0, "failed": 0,
                      "undefined": 1}
    saved = json.loads(obs.read_text(encoding="utf-8").splitlines()[0])
    assert saved["config_name"] is None and saved["usable"] is False


# -------------------------------------------------- frozen identity + config
def test_frozen_b0_and_b2_resolve():
    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    ident = REAL_SPEC["arms"]["identities"]
    point, _d, prov = mod.resolve_static_arm(
        "B0", "F1_agg", "large", 0, base, ident["B0"])
    assert point.name == "B0" and prov["spec_fingerprint"] == mod.FROZEN_SPEC_FP
    point, _d, _p = mod.resolve_static_arm(
        "B2", "F1_agg", "large", 0, base, ident["B2"]["by_family"]["F1_agg"])
    assert point.name == "G-p8-sp16"


def test_b2_f4_remains_unresolvable():
    base = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")
    with pytest.raises(StrategyResolutionError):
        mod.resolve("B2", family="F4_ski", scale="large", dataset_seed=0,
                    base_config=base)


def test_policies_and_datasets_verify_readonly():
    doc = mod.verify_sealed_spec()
    fp = mod.verify_policies(doc)
    assert fp == doc["arms"]["identities"]["RL"]["manifest_fingerprint"]
    mod.verify_datasets(doc)  # raises on any drift


def test_dataset_drift_fails():
    doc = copy.deepcopy(REAL_SPEC)
    doc["selected_cells"]["cells"][0]["dataset_fingerprint"] = "0" * 64
    with pytest.raises(SystemExit, match="dataset fingerprint drift"):
        mod.verify_datasets(doc)


# --------------------------------------------------------- failure handling
class _Metrics:
    def __init__(self, usable, error=None, timeout=False):
        self.usable = usable
        self.error = error
        self.timeout = timeout
        self.execution_time_s = 1.5 if usable else None
        self.execution_time_source = "runner" if usable else None
        self.config_fingerprint = "cfg"
        self.dataset_fingerprint = "ds"
        self.event_log_status = "COMPLETE" if usable else "MISSING"


def _entry(idx, arm="B0"):
    return {"queue_index": idx, "arm": arm, "family": "F1_agg",
            "scale": "large", "dataset_seed": 0, "rep": 1, "split": "test",
            "executable": True,
            "identity": REAL_SPEC["arms"]["identities"]["B0"],
            "provenance": {}}


_B0_IDENTS = {"B0": REAL_SPEC["arms"]["identities"]["B0"], "B2": None}
_B2_MAP = REAL_SPEC["arms"]["identities"]["B2"]["by_family"]
_BASE = SparkConfig.from_yaml(PROJECT / "configs" / "baseline_b0.yaml")


def test_spark_failure_is_first_class(tmp_path):
    obs = tmp_path / "obs.jsonl"
    counts = mod.run_entries(
        [_entry(1)], obs, _BASE, {}, _B0_IDENTS, _B2_MAP, set(),
        execute_fn=lambda *a, **k: (_Metrics(False, "Py4JJavaError: boom"), {}))
    row = json.loads(obs.read_text(encoding="utf-8").splitlines()[0])
    assert row["usable"] is False and "boom" in row["error"]
    assert row["undefined"] is False
    assert counts["failed"] == 1 and counts["spark_attempted"] == 1


def test_orchestration_crash_is_durable_failure(tmp_path):
    obs = tmp_path / "obs.jsonl"

    def _crash(*a, **k):
        raise RuntimeError("jvm died")

    counts = mod.run_entries([_entry(1)], obs, _BASE, {}, _B0_IDENTS,
                             _B2_MAP, set(), execute_fn=_crash)
    row = json.loads(obs.read_text(encoding="utf-8").splitlines()[0])
    assert row["usable"] is False and "RuntimeError" in row["error"]
    assert row["execution_time_s"] is None
    assert counts["failed"] == 1


def test_usable_run_recorded(tmp_path):
    obs = tmp_path / "obs.jsonl"
    counts = mod.run_entries([_entry(1)], obs, _BASE, {}, _B0_IDENTS,
                             _B2_MAP, set(),
                             execute_fn=lambda *a, **k: (_Metrics(True), {}))
    row = json.loads(obs.read_text(encoding="utf-8").splitlines()[0])
    assert row["usable"] is True and row["execution_time_s"] == 1.5
    assert counts["usable"] == 1


# ---------------------------------------------------------------- durability
def test_append_preserves_completed_rows(tmp_path):
    p = tmp_path / "obs.jsonl"
    mod.append_observation(p, {"queue_index": 1, "usable": True})
    mod.append_observation(p, {"queue_index": 2, "usable": False})
    lines = p.read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["queue_index"] for l in lines] == [1, 2]
    done = mod.load_observations(p)
    assert mod.resume_indices([{"queue_index": i} for i in (1, 2, 3)],
                              done) == [{"queue_index": 3}]


# ---------------------------------------------------------------- dry slice
def test_dry_slice_isolation_paths():
    assert mod.DRY_DIR != mod.PROD_DIR
    assert "dry-slice" in mod.DRY_DIR.name
    assert mod.DRY_OBS != mod.PROD_OBS


def test_dry_slice_runs_exactly_seven_rows_no_index8(tmp_path, monkeypatch):
    seen = []

    def _fake_execute(run_spec, base, **k):
        seen.append(run_spec.order_index)
        return _Metrics(True), {}

    monkeypatch.setattr(mod, "DRY_DIR", tmp_path / "dry")
    monkeypatch.setattr(mod, "DRY_OBS",
                        tmp_path / "dry" / "observations.jsonl")
    monkeypatch.setattr(mod, "PROD_OBS",
                        tmp_path / "prod" / "observations.jsonl")
    monkeypatch.setattr(mod, "execute_run", _fake_execute)
    assert mod.dry_slice() == 0
    assert seen == [0, 1, 2, 3, 4, 5, 6]          # queue indices 1-7 only
    rows = [json.loads(l) for l in
            (tmp_path / "dry" / "observations.jsonl").read_text(
                encoding="utf-8").splitlines()]
    assert [r["queue_index"] for r in rows] == [1, 2, 3, 4, 5, 6, 7]
    assert (tmp_path / "dry" / "DRY_SLICE_ONLY").exists()
    summary = json.loads((tmp_path / "dry" / "summary.json").read_text(
        encoding="utf-8"))
    assert summary["dry_slice_only"] is True
    assert summary["counts"]["recorded"] == 7
    assert not (tmp_path / "prod" / "observations.jsonl").exists()
    assert not mod.PROD_OBS.exists()              # real production untouched


def test_dry_slice_refuses_non_executable_slice(tmp_path, monkeypatch):
    doc, base, rl, idents, b2map, frozen = mod.preflight()
    bad = copy.deepcopy(doc)
    bad["queue"]["rows"][0]["executable"] = False
    monkeypatch.setattr(mod, "preflight",
                        lambda: (bad, base, rl, idents, b2map, frozen))
    with pytest.raises(SystemExit, match="executable rows only"):
        mod.dry_slice()


def test_dry_slice_composition_is_frozen():
    rows = REAL_SPEC["queue"]["rows"][:7]
    assert all(r["executable"] for r in rows)
    assert Counter((r["arm"], r["rep"]) for r in rows) == Counter(
        [("B0", i) for i in range(1, 6)] + [("B2", 1), ("B2", 2)])