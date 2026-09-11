"""RL layer (Days 25+): environment contract, state/action/reward components.

Frozen authority:
    PLAN sections 12-16 (RL formulation, state, action, reward, algorithm)
    DEC-009 / ARCHITECTURE_FREEZE (Candidate C)
    COMPONENT_CONTRACTS COMP-RL-06..09

Day-25 boundary: the ENVIRONMENT CONTRACT only. No Q-table, no learning rule,
no exploration schedule, no cache, no policy store. Every module here states
its frozen source and its deferred responsibilities explicitly.
"""
from sparkrl.rl.state import (  # noqa: F401
    FEEDBACK_BINS,
    FAMILY_TO_CLASS,
    SCHEMA_V1,
    SCHEMA_V15,
    SIZE_BINS,
    WORKLOAD_CLASSES,
    StateEncoder,
    StateVector,
)
from sparkrl.rl.action import MODE12, MODE4, MODE4_SUBSET, ActionMapper, InvalidAction  # noqa: F401
from sparkrl.rl.reward import FORMULA_ID, Reward, RewardCalculator, TRefMissing  # noqa: F401
from sparkrl.rl.tref import TRefStore  # noqa: F401
from sparkrl.rl.env import (  # noqa: F401
    ENV_VERSION,
    BudgetExhausted,
    EpisodeDone,
    Observation,
    SparkTuningEnv,
    SplitViolation,
    StepInfo,
)
