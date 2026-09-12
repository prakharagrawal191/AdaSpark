"""RL agent layer (Day 26): tabular Q-learning + versioned policy store.

COMP-RL-10 only. No DQN/PPO/neural RL, no replay, no target network, no
adaptive execution cache, no experiment orchestration.
"""
from sparkrl.agent.q_learning import (  # noqa: F401
    AGENT_VERSION,
    AgentConfig,
    InvalidTransition,
    QLearningAgent,
    RLConfigError,
    Transition,
    state_key_of,
)
from sparkrl.agent.q0 import (  # noqa: F401
    LeakageError,
    Q0Result,
    Q0SourceError,
    Q0_VERSION,
    build_q0_from_exp002,
)
from sparkrl.agent.policy_store import (  # noqa: F401
    POLICY_SCHEMA,
    PolicyCorrupt,
    PolicyExistsError,
    PolicyVersionMismatch,
    agent_from_artifact,
    build_policy_artifact,
    load_policy,
    policy_fingerprint,
    save_policy,
    verify_compatibility,
)

