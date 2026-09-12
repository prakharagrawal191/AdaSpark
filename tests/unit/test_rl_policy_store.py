"""Unit tests: versioned immutable policy store (COMP-RL-10)."""
import json

import pytest

from sparkrl.agent.policy_store import (PolicyCorrupt, PolicyExistsError,
                                        PolicyVersionMismatch,
                                        agent_from_artifact,
                                        build_policy_artifact, load_policy,
                                        policy_fingerprint, save_policy)
from sparkrl.agent.q_learning import QLearningAgent
from sparkrl.rl.state import SCHEMA_V15, StateVector

S_A = StateVector("join", "S", schema_version=SCHEMA_V15, feedback_bin="le0")
PROV = {"source": "exp002", "records_valid_used": 1}


def make_artifact(tmp_path, tamper=None, build_kw=None, **agent_kw):
    agent_kw.setdefault("q_table", {"state-v1.5|join|S|le0": [0.5] * 12})
    ag = QLearningAgent(rng_seed=5, **agent_kw)
    art = build_policy_artifact(ag, init_provenance=dict(PROV),
                                created_utc="2026-01-01T00:00:00Z")
    if tamper:
        tamper(art)
    return art


def test_roundtrip_save_load(tmp_path):
    art = make_artifact(tmp_path)
    path = save_policy(art, tmp_path)
    assert path.exists() and path.name.startswith("policy-")
    loaded = load_policy(art["policy_id"], tmp_path)
    assert loaded["q_table"] == art["q_table"]
    assert loaded["epsilon"] == art["epsilon"]
    ag = agent_from_artifact(loaded)
    assert ag.q_table() == art["q_table"]
    assert ag.rng_seed == 5 and ag.updates == 0


def test_policy_id_is_content_fingerprint_not_timestamp():
    a1 = build_policy_artifact(QLearningAgent(rng_seed=1),
                               init_provenance=dict(PROV), created_utc="t1")
    a2 = build_policy_artifact(QLearningAgent(rng_seed=1),
                               init_provenance=dict(PROV), created_utc="t2")
    assert a1["policy_id"] == a2["policy_id"]      # metadata excluded
    a3 = build_policy_artifact(QLearningAgent(rng_seed=2),
                               init_provenance=dict(PROV))
    assert a1["policy_id"] != a3["policy_id"]      # content differs


def test_save_is_immutable(tmp_path):
    art = make_artifact(tmp_path)
    save_policy(art, tmp_path)
    # same id, different Q content -> must refuse, never overwrite
    tampered = dict(art)
    tampered["q_table"] = {"state-v1.5|join|S|le0": [9.9] * 12}
    with pytest.raises(PolicyExistsError):
        save_policy(tampered, tmp_path)
    # file on disk unchanged
    on_disk = json.loads((tmp_path / f"policy-{art['policy_id'][:16]}.json")
                         .read_text(encoding="utf-8"))
    assert on_disk["q_table"] == art["q_table"]


def test_load_rejects_tampered_file(tmp_path):
    art = make_artifact(tmp_path)
    path = save_policy(art, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["q_table"]["state-v1.5|join|S|le0"][0] = 42.0
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PolicyCorrupt):
        load_policy(art["policy_id"], tmp_path)


def test_load_rejects_version_mismatch(tmp_path):
    art = make_artifact(tmp_path)
    path = save_policy(art, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["contract_versions"]["state_schema"] = "state-v9"
    data["policy_id"] = policy_fingerprint(data)   # re-sign (internally valid)
    save_policy(data, tmp_path)                    # new version id
    with pytest.raises(PolicyVersionMismatch):
        load_policy(data["policy_id"], tmp_path)


def test_policy_artifact_contains_required_provenance(tmp_path):
    art = build_policy_artifact(QLearningAgent(rng_seed=0),
                                init_provenance={"source": "exp002",
                                                 "records_valid_used": 2})
    assert set(art) >= {"policy_schema", "policy_id", "learner_version",
                        "learner_config", "contract_versions", "q_table",
                        "epsilon", "rng_seed", "updates", "episodes",
                        "q0_provenance"}
    assert art["contract_versions"]["state_schema"] == SCHEMA_V15
    assert "exp002" in art["q0_provenance"]["source"]


def test_no_pickle_no_executable_policy(tmp_path):
    art = make_artifact(tmp_path)
    raw = json.dumps(art, sort_keys=True)
    assert "pickle" not in raw
    assert callable(agent_from_artifact(art).select_action)