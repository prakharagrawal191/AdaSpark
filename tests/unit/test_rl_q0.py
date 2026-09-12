"""Unit tests: offline Q0 from synthetic EXP-002 records (Day-26 fixture).

The fixture mimics the stored ``exp002-run/v1`` record schema. Dataset inputs
are controlled by monkeypatching ``resolve_dataset`` so bins are exact.
"""
import json

import pytest

from sparkrl.agent.q0 import LeakageError, Q0SourceError, build_q0_from_exp002
from sparkrl.agent.q_learning import QLearningAgent
from sparkrl.experiments.spec import ExperimentSpec
from sparkrl.rl.state import SCHEMA_V15, StateVector
from sparkrl.workloads.resolver import ResolvedDataset

_BYTES = {("F2_join", "small"): 100 * 1024 * 1024,      # -> S bin
          ("F2_join", "medium"): 1500 * 1024 * 1024,    # -> M bin
          ("F2_join", "large"): 3 * 1024 * 1024 * 1024, # -> L bin
          ("F4_ski", "small"): 100 * 1024 * 1024}


class FakeRD:
    def __init__(self, total_bytes):
        self.orders_manifest = {"total_bytes": total_bytes}
        self.lineitem_manifest = {"total_bytes": 0}


class FakeTRef:
    """Deterministic in-test T_ref (no real EXP-002 artifacts)."""

    def __init__(self, mapping):
        self._m = {k: float(v) for k, v in mapping.items()}
        self.source = "test-fixture"

    def get(self, family, scale, seed=0):
        return self._m.get(f"{family}|{scale}")


def record(family, scale, seed, grid_index, exec_s, cv, spill, *, usable=True):
    """One exp002-run/v1 dict."""
    name = f"rec-{family}-{scale}-{grid_index}-{exec_s:.1f}".replace(".", "-")
    return name, {
        "schema_version": "exp002-run/v1",
        "experiment_id": "EXP-002",
        "status": "COMPLETED" if usable else "FAILED",
        "spec_fingerprint": ExperimentSpec.from_yaml(
            "experiments/exp002.yaml").fingerprint(),
        "grid_fingerprint": "GRID",
        "run_spec": {
            "run_id": name, "family": family, "scale": scale, "seed": seed,
            "rep": 1, "config_grid_index": grid_index, "split": "train",
        },
        "metrics": {
            "execution_time_s": exec_s, "task_duration_cv": cv,
            "disk_spill_bytes": spill, "usable": usable,
            "application_id": "local-fake", "event_log_status": "COMPLETE",
        },
    }


def write_fixture(tmp_path, records):
    root = tmp_path / "runs"
    for run_id, rec in records:
        p = root / f"{run_id}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec), encoding="utf-8")
    return tmp_path          # load_records reads <result_root>/runs/*.json


def fake_resolve(monkeypatch):
    monkeypatch.setattr(
        "sparkrl.agent.q0.resolve_dataset",
        lambda family, scale, seed: FakeRD(_BYTES[(family, scale)]))


def test_q0_median_aggregation_and_bins(tmp_path, monkeypatch):
    fake_resolve(monkeypatch)
    rows = [
        record("F2_join", "small", 0, 1, 1.0, 0.1, 0),
        record("F2_join", "small", 0, 1, 2.5, 0.1, 0),
        record("F2_join", "small", 0, 2, 1.0, 0.1, 0),
        record("F2_join", "small", 0, 2, 4.0, 0.1, 0),
        record("F2_join", "small", 0, 2, 2.0, 0.1, 0),
    ]
    root = write_fixture(tmp_path, rows)
    r = build_q0_from_exp002(result_root=root, spec_path="experiments/exp002.yaml",
                             tref_store=FakeTRef({"F2_join|small": 5.0}))
    rows_q = r.q_table["state-v1.5|join|S|le0"]
    # R3 with T_ref=5, cv=0.1, no spill:
    #   t=1   -> clip(0.8) + 0.2*(1-0.2) = 0.96
    #   t=2.5 -> 0.5 + 0.16 = 0.66          action1 median of [0.96, 0.66] = 0.81
    #   t=4   -> 0.2 + 0.16 = 0.36          action2 median of [0.96, 0.36, 0.76]
    assert rows_q[1] == pytest.approx(0.81)
    assert rows_q[2] == pytest.approx(sorted([0.96, 0.36, 0.76])[1])


def test_invalid_records_skipped_and_counted(tmp_path, monkeypatch):
    fake_resolve(monkeypatch)
    rows = [
        record("F2_join", "small", 0, 1, 1.0, 0.1, 0, usable=True),
        record("F2_join", "small", 0, 1, 1.5, 0.1, 0, usable=False),
    ]
    root = write_fixture(tmp_path, rows)
    r = build_q0_from_exp002(result_root=root, spec_path="experiments/exp002.yaml",
                             tref_store=FakeTRef({"F2_join|small": 5.0}))
    assert r.provenance["records_valid_used"] == 1
    assert r.provenance["records_invalid_skipped"] == 1
    assert r.q_table["state-v1.5|join|S|le0"][1] == pytest.approx(0.96)


@pytest.mark.parametrize("family,scale,seed", [
    ("F2_join", "small", 3), ("F2_join", "small", 4),
    ("F2_join", "large", 0), ("F4_ski", "small", 0),
])
def test_leakage_raises(tmp_path, monkeypatch, family, scale, seed):
    fake_resolve(monkeypatch)
    rows = [record(family, scale, seed, 1, 1.0, 0.1, 0)]
    root = write_fixture(tmp_path / f"l-{family}-{scale}-{seed}", rows)
    with pytest.raises(LeakageError):
        build_q0_from_exp002(result_root=root,
                             spec_path="experiments/exp002.yaml",
                             tref_store=FakeTRef({f"{family}|{scale}": 5.0}))


def test_spec_fingerprint_mismatch_refused(tmp_path, monkeypatch):
    fake_resolve(monkeypatch)
    rows = [record("F2_join", "small", 0, 1, 1.0, 0.1, 0)]
    rows[0][1]["spec_fingerprint"] = "WRONG"
    root = write_fixture(tmp_path, rows)
    with pytest.raises(Q0SourceError):
        build_q0_from_exp002(result_root=root,
                             spec_path="experiments/exp002.yaml",
                             tref_store=FakeTRef({"F2_join|small": 5.0}))


def test_uncovered_pairs_get_optimistic_default(tmp_path, monkeypatch):
    fake_resolve(monkeypatch)
    rows = [record("F2_join", "small", 0, 4, 1.0, 0.1, 0)]  # only action 4
    root = write_fixture(tmp_path, rows)
    r = build_q0_from_exp002(result_root=root, spec_path="experiments/exp002.yaml",
                             tref_store=FakeTRef({"F2_join|small": 5.0}))
    ag = QLearningAgent(q_table=r.q_table)
    row = ag.q_values(StateVector("join", "S", SCHEMA_V15, "le0"))
    assert row[4] != 0.5                     # initialized from EXP-002
    assert all(v == 0.5 for i, v in enumerate(row) if i != 4)
