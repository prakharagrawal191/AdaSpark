"""Versioned, immutable policy store (COMP-RL-10: "versioned store").

Artifacts are plain JSON (no pickle, no executable objects) under
``models/policies/``. Identity is a content fingerprint over the canonical
JSON (sorted keys, excludes ``created_utc`` metadata), so a rebuild from
identical inputs yields the identical policy identity. An existing policy id
is NEVER overwritten (``PolicyExistsError``); loading verifies the
fingerprint and the contract-version compatibility (state/action/reward/
learner schemas) and rejects anything else (``PolicyVersionMismatch``).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkrl.agent.q_learning import AGENT_VERSION, AgentConfig, QLearningAgent
from sparkrl.rl.action import ActionMapper
from sparkrl.rl.reward import FORMULA_ID
from sparkrl.rl.state import SCHEMA_V15

PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_DIR = PROJECT / "models" / "policies"

POLICY_SCHEMA = "policy/v1"


class PolicyExistsError(RuntimeError):
    """An immutable policy version already exists (no silent overwrite)."""


class PolicyVersionMismatch(ValueError):
    """Policy artifact incompatible with the current environment contract."""


class PolicyCorrupt(ValueError):
    """Policy artifact failed integrity verification."""


def policy_fingerprint(artifact: dict[str, Any]) -> str:
    """Deterministic content fingerprint (excludes identity + metadata)."""
    body = {k: v for k, v in artifact.items()
            if k not in ("policy_id", "created_utc")}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_policy_artifact(agent: QLearningAgent, *,
                          init_provenance: dict[str, Any],
                          created_utc: str | None = None) -> dict[str, Any]:
    """Serialize the agent into a versioned, self-describing artifact."""
    artifact: dict[str, Any] = {
        "policy_schema": POLICY_SCHEMA,
        "policy_id": None,                       # filled after fingerprinting
        "learner_version": AGENT_VERSION,
        "learner_config": {
            "alpha": agent.config.alpha,
            "gamma": agent.config.gamma,
            "epsilon_start": agent.config.epsilon_start,
            "epsilon_min": agent.config.epsilon_min,
            "epsilon_decay": agent.config.epsilon_decay,
            "q0_default": agent.config.q0_default,
            "q0_source": agent.config.q0_source,
            "q0_aggregation": agent.config.q0_aggregation,
            "action_mode": agent.config.action_mode,
        },
        "contract_versions": {
            "state_schema": SCHEMA_V15,
            "action_grid_fingerprint": agent.mapper.grid_fingerprint,
            "reward_formula": FORMULA_ID,
        },
        "q_table": {k: list(v) for k, v in sorted(agent.q_table().items())},
        "epsilon": agent.epsilon,
        "rng_seed": agent.rng_seed,
        "updates": agent.updates,
        "episodes": agent.episodes,
        "q0_provenance": dict(init_provenance),
    }
    artifact["policy_id"] = policy_fingerprint(artifact)
    if created_utc is not None:                  # metadata only, never identity
        artifact["created_utc"] = created_utc
    return artifact


def save_policy(artifact: dict[str, Any],
                policy_dir: str | Path = DEFAULT_POLICY_DIR) -> Path:
    """Persist immutably; refuse to overwrite an existing policy version."""
    pid = artifact.get("policy_id")
    if not pid:
        raise PolicyCorrupt("artifact has no policy_id")
    directory = Path(policy_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"policy-{pid[:16]}.json"
    if path.exists():
        # A version with this id already exists: identical rebuild is the
        # only acceptable outcome; anything else is an immutability breach.
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("policy_id") == pid and \
                policy_fingerprint(existing) == policy_fingerprint(artifact):
            return path
        raise PolicyExistsError(
            f"policy version {pid[:16]} already exists and differs")
    if pid != policy_fingerprint(artifact):
        raise PolicyCorrupt("policy_id does not match artifact content")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(artifact, indent=1, sort_keys=True),
                   encoding="utf-8")
    path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")
    tmp.unlink()
    return path


def verify_compatibility(artifact: dict[str, Any]) -> None:
    """Reject policies built under a different frozen contract version."""
    versions = artifact.get("contract_versions") or {}
    expected = {
        "state_schema": SCHEMA_V15,
        "action_grid_fingerprint": ActionMapper().grid_fingerprint,
        "reward_formula": FORMULA_ID,
    }
    for key, want in expected.items():
        if versions.get(key) != want:
            raise PolicyVersionMismatch(
                f"policy {key}={versions.get(key)!r} != current contract {want!r}")
    if artifact.get("learner_version") != AGENT_VERSION:
        raise PolicyVersionMismatch(
            f"learner_version={artifact.get('learner_version')!r} != {AGENT_VERSION!r}")
    if artifact.get("policy_schema") != POLICY_SCHEMA:
        raise PolicyVersionMismatch(
            f"policy_schema={artifact.get('policy_schema')!r} != {POLICY_SCHEMA!r}")


def load_policy(policy_id: str,
                policy_dir: str | Path = DEFAULT_POLICY_DIR) -> dict[str, Any]:
    """Load + integrity-check + compatibility-check one policy version."""
    path = Path(policy_dir) / f"policy-{policy_id[:16]}.json"
    if not path.exists():
        raise FileNotFoundError(f"policy {policy_id[:16]} not found in {policy_dir}")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("policy_id") != policy_id or \
            policy_fingerprint(artifact) != policy_id:
        raise PolicyCorrupt(f"policy {policy_id[:16]} failed fingerprint check")
    verify_compatibility(artifact)
    return artifact


def agent_from_artifact(artifact: dict[str, Any], *,
                        rng_seed: int | None = None) -> QLearningAgent:
    """Rebuild an agent from a verified artifact (Q + counters + epsilon)."""
    verify_compatibility(artifact)
    cfg = artifact["learner_config"]
    config = AgentConfig(
        alpha=cfg["alpha"], gamma=cfg["gamma"],
        epsilon_start=cfg["epsilon_start"], epsilon_min=cfg["epsilon_min"],
        epsilon_decay=cfg["epsilon_decay"], q0_default=cfg["q0_default"],
        q0_source=cfg["q0_source"], q0_aggregation=cfg["q0_aggregation"],
        action_mode=cfg["action_mode"])
    return QLearningAgent(
        config, rng_seed=artifact["rng_seed"] if rng_seed is None else rng_seed,
        q_table=artifact["q_table"], epsilon=artifact["epsilon"],
        updates=artifact["updates"], episodes=artifact["episodes"])
