"""Integration (no Spark): real EXP-002 storage -> Q0 -> agent -> policy store.

Uses the ACTUAL stored EXP-002 records and gate artifact. The Q0 builder is
safe for a real-EXP-002 run inside the test suite because it only READS
storage and (for bytes) dataset manifests; the policy artifact is written to
a temp policy dir.
"""
import json

import pytest

from sparkrl.agent import (build_policy_artifact, build_q0_from_exp002,
                           load_policy, policy_fingerprint, save_policy)
from sparkrl.agent.q_learning import QLearningAgent
from sparkrl.rl.state import SCHEMA_V15, StateVector

pytestmark = pytest.mark.integration


def test_offline_init_from_real_exp002(tmp_path):
    q0 = build_q0_from_exp002()
    p = q0.provenance
    # training-only accounting (LeakageError would have raised otherwise)
    assert p["source"] == "exp002"
    assert p["records_scanned"] == 208
    assert p["records_valid_used"] + p["records_invalid_skipped"] \
        + p["records_b0_reference"] + p["records_tref_missing_skipped"] \
        == 208
    assert p["pairs_initialized"] >= 1
    # all initialized states carry the no-history feedback bin (le0) because
    # offline initialization has no prior episode - and never a test cell.
    for key in q0.q_table:
        parts = key.split("|")
        assert parts[0] == SCHEMA_V15 and parts[3] == "le0"
        assert parts[1] in ("agg", "join", "rdd_sort", "mixed")  # no skew_join

    # agent + immutable policy artifact round-trip
    agent = QLearningAgent(q_table=q0.q_table, rng_seed=0)
    art = build_policy_artifact(agent, init_provenance=dict(p))
    path = save_policy(art, tmp_path)
    loaded = load_policy(art["policy_id"], tmp_path)
    assert loaded["q_table"] == q0.q_table
    assert loaded["q0_provenance"]["spec_fingerprint"] == p["spec_fingerprint"]
    # deterministic identity: rebuilding from the same inputs yields the same id
    agent2 = QLearningAgent(q_table=q0.q_table, rng_seed=0)
    art2 = build_policy_artifact(agent2, init_provenance=dict(p),
                                 created_utc="different")
    assert art2["policy_id"] == art["policy_id"]

    # the initialized policy prefers a sensible action for join|S
    st = StateVector("join", "S", schema_version=SCHEMA_V15, feedback_bin="le0")
    a = agent.select_action(st, epsilon=0.0)
    assert 0 <= a < 12
    assert json.loads(path.read_text(encoding="utf-8"))["policy_id"] \
        == art["policy_id"]


def test_offline_policy_leakage_guard(tmp_path):
    # The builder reads only TRAIN cells; every stored EXP-002 run is TRAIN,
    # so constructing Q0 must never raise LeakageError for the real data.
    q0 = build_q0_from_exp002()
    assert q0.provenance["leakage_guard"].startswith("split_of()")