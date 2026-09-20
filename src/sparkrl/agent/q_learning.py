"""Tabular Q-learning agent (COMP-RL-10) - the ONLY authorized learner.

Frozen source: PLAN section 16 ("Primary: tabular Q-learning (e-greedy) ...
Hyperparameters (config-driven): alpha=0.2; gamma in {0, 0.9}; epsilon
1.0->0.05 decay 0.95/episode; optimistic init Q0=+0.5; no replay buffer
(tabular); checkpoint every 25 episodes; 3 training seeds {0,1,2}; cap 500
executions") and COMP-RL-10 ("e-greedy tabular Q + versioned store; inputs
(StateVector, e) -> action; update(transition); update-fail -> Q untouched +
abort; provenance Q-version + e + update count; seeded tie-break; save/load
round-trip").

Design invariants:
* Q key = ``StateVector.key()`` (frozen Day-25 state identity), never object
  identity, never raw floats. Serialized as ``schema|class|bin|feedback``.
* Action dimension is ALWAYS the frozen 12-action grid (mode4 is a selection
  restriction, not a different table).
* Update rule (frozen): Q(s,a) <- Q(s,a) + alpha * [r + gamma * max_a' Q(s',a')
  - Q(s,a)]; TERMINAL transitions never bootstrap (bandit mode: r is the
  full target regardless of gamma).
* update() validates the transition COMPLETELY before mutating Q; any
  invalid transition leaves Q untouched and raises (COMP-RL-10 failure rule).
* Exploration uses an agent-owned seeded RNG (``random.Random``) - never the
  global RNG. Exploitation tie-breaks to the LOWEST frozen action index.
* The agent owns NO Spark execution, no T_ref, no guards, no reward
  computation: it consumes the environment's transition (reward comes from
  the frozen R3 calculator via SparkTuningEnv; never recomputed here).
* No replay buffer, no target network, no neural network (frozen rejections).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from sparkrl.rl.action import MODE12, MODE4_SUBSET, ActionMapper
from sparkrl.rl.state import SCHEMA_V15, FeedbackState, StateVector

PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_RL_YAML = PROJECT / "configs" / "rl.yaml"

AGENT_VERSION = "tabular-q/v1"

# Frozen hyperparameters (PLAN section 16). load validates against these.
FROZEN_HYPERPARAMS: dict[str, float] = {
    "alpha": 0.2,
    "epsilon_start": 1.0,
    "epsilon_min": 0.05,
    "epsilon_decay": 0.95,
    "q0_default": 0.5,
}
FROZEN_GAMMAS = (0.0, 0.9)


class InvalidTransition(ValueError):
    """update() rejected the transition; Q remains untouched (COMP-RL-10)."""


class RLConfigError(ValueError):
    """configs/rl.yaml disagrees with the frozen PLAN-section-16 values."""


@dataclass(frozen=True)
class AgentConfig:
    """Frozen learner hyperparameters (validated against PLAN section 16)."""

    alpha: float
    gamma: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    q0_default: float
    q0_source: str = "exp002"
    q0_aggregation: str = "median"
    action_mode: str = MODE12

    @classmethod
    def from_yaml(cls, path: str | Path = DEFAULT_RL_YAML) -> "AgentConfig":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if raw.get("learner") != "tabular-q":
            raise RLConfigError(f"learner={raw.get('learner')!r} != 'tabular-q'")
        for key, frozen in FROZEN_HYPERPARAMS.items():
            value = raw.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise RLConfigError(f"{key} missing/invalid: {value!r}")
            if not math.isclose(float(value), frozen, rel_tol=0.0, abs_tol=1e-12):
                raise RLConfigError(
                    f"{key}={value} disagrees with frozen PLAN-section-16 "
                    f"value {frozen}")
        gamma = raw.get("gamma")
        if not any(math.isclose(float(gamma), g, abs_tol=1e-12) for g in FROZEN_GAMMAS):
            raise RLConfigError(f"gamma={gamma!r} not in frozen set {FROZEN_GAMMAS}")
        if raw.get("q0_aggregation") != "median":
            raise RLConfigError("q0_aggregation must be 'median' (PLAN section 22)")
        return cls(alpha=float(raw["alpha"]), gamma=float(gamma),
                   epsilon_start=float(raw["epsilon_start"]),
                   epsilon_min=float(raw["epsilon_min"]),
                   epsilon_decay=float(raw["epsilon_decay"]),
                   q0_default=float(raw["q0_default"]),
                   q0_source=str(raw.get("q0_source", "exp002")),
                   action_mode=str(raw.get("action_mode", MODE12)))


@dataclass(frozen=True)
class Transition:
    """One learner-consumed transition (from SparkTuningEnv.step()).

    ``state``/``next_state`` are a context ``StateVector`` (v1/v1.5) or, for
    the EXP-007 A2 ablation (DEC-023 section 3), a feedback-only
    ``FeedbackState``. Both carry a stable ``key()`` identity; the learner is
    state-schema agnostic.
    """

    state: StateVector | FeedbackState
    action: int
    reward: float
    next_state: StateVector | FeedbackState | None
    terminated: bool
    info: Mapping[str, Any] = field(default_factory=dict)


def state_key_of(state: StateVector) -> str:
    """Frozen serializable Q-table key for a Day-25 state."""
    return "|".join(str(part) for part in state.key())


class QLearningAgent:
    """epsilon-greedy tabular Q-learning agent (frozen hyperparameters)."""

    def __init__(self, config: AgentConfig | None = None, *,
                 rng_seed: int = 0, q_table: dict[str, list[float]] | None = None,
                 epsilon: float | None = None,
                 updates: int = 0, episodes: int = 0) -> None:
        self.config = config if config is not None else AgentConfig.from_yaml()
        self.mapper = ActionMapper(mode=self.config.action_mode)
        self._n_actions = 12  # frozen grid; mode4 restricts SELECTION only
        self.rng_seed = int(rng_seed)
        self._rng = random.Random(self.rng_seed)
        self._q: dict[str, list[float]] = {}
        if q_table is not None:
            self._import_q(q_table)
        self.epsilon = (self.config.epsilon_start if epsilon is None
                        else float(epsilon))
        self.updates = int(updates)
        self.episodes = int(episodes)

    # -- Q-table -------------------------------------------------------------
    def _import_q(self, q_table: Mapping[str, Iterable[float]]) -> None:
        for key, values in q_table.items():
            vals = [float(v) if v is not None else self.config.q0_default
                    for v in values]
            if len(vals) != self._n_actions:
                raise InvalidTransition(
                    f"Q row {key!r} has {len(vals)} values; frozen domain is 12")
            self._q[str(key)] = vals

    def _row(self, state: StateVector) -> list[float]:
        """Q row for a state, creating a default (optimistic) row if absent."""
        key = state_key_of(state)
        row = self._q.get(key)
        if row is None:
            row = [self.config.q0_default] * self._n_actions
            self._q[key] = row
        return row

    def q_values(self, state: StateVector) -> tuple[float, ...]:
        """Read-only view of Q(s, .)."""
        return tuple(self._row(state))

    def q_table(self) -> dict[str, list[float]]:
        """Deep copy of the table (safe for serialization)."""
        return {k: list(v) for k, v in self._q.items()}

    @property
    def n_states(self) -> int:
        return len(self._q)

    # -- action selection (COMP-RL-10) ----------------------------------------
    def allowed_actions(self) -> tuple[int, ...]:
        return self.mapper.allowed_actions()

    def select_action(self, state: StateVector, epsilon: float | None = None) -> int:
        """epsilon-greedy over the frozen action domain (seeded, deterministic).

        Exploitation ties break to the LOWEST frozen action index. Exploration
        draws uniformly over the allowed subset from the agent-owned RNG.
        """
        eps = self.epsilon if epsilon is None else float(epsilon)
        if not 0.0 <= eps <= 1.0:
            raise ValueError(f"epsilon must be in [0, 1], got {eps}")
        allowed = self.allowed_actions()
        if self._rng.random() < eps:
            return allowed[self._rng.randrange(len(allowed))]
        row = self._row(state)
        best = max(allowed, key=lambda a: (row[a], -a))  # tie -> lowest index
        return best

    def decay_epsilon(self) -> float:
        """One episode of the frozen schedule: e <- max(e_min, e * decay)."""
        self.epsilon = max(self.config.epsilon_min,
                           self.epsilon * self.config.epsilon_decay)
        return self.epsilon

    # -- learning update (frozen rule) -----------------------------------------
    def update(self, transition: Transition) -> float:
        """Q(s,a) <- Q(s,a) + alpha * [r + gamma*maxQ(s') - Q(s,a)].

        Terminal transitions never bootstrap. The transition is fully
        validated BEFORE mutation; an invalid transition leaves Q untouched
        and raises ``InvalidTransition`` (COMP-RL-10 failure rule).
        """
        s, a, r = transition.state, transition.action, transition.reward
        if not isinstance(s, (StateVector, FeedbackState)):
            raise InvalidTransition(
                f"state must be a StateVector (v1/v1.5) or an A2 "
                f"FeedbackState (state-v2), got {type(s)!r}")
        if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < self._n_actions:
            raise InvalidTransition(f"action {a!r} outside the frozen 12-action grid")
        if isinstance(r, bool) or not isinstance(r, (int, float)) \
                or not math.isfinite(float(r)):
            raise InvalidTransition(f"reward {r!r} is not a finite number")
        if not isinstance(transition.terminated, bool):
            raise InvalidTransition("terminated must be bool")
        ns = transition.next_state
        if ns is not None and not isinstance(ns, (StateVector, FeedbackState)):
            raise InvalidTransition(
                "next_state must be StateVector/FeedbackState or None")

        row = self._row(s)
        old_q = float(row[a])
        if transition.terminated:
            target = float(r)                      # no bootstrap from a terminal
        else:
            if ns is None:
                raise InvalidTransition(
                    "non-terminal transition requires next_state for bootstrapping")
            next_row = self._row(ns)
            target = float(r) + self.config.gamma * max(
                next_row[a2] for a2 in self.allowed_actions())
        delta = self.config.alpha * (target - old_q)
        new_q = old_q + delta
        if not math.isfinite(new_q):
            raise InvalidTransition(f"update produced non-finite Q: {new_q!r}")
        row[a] = new_q                             # mutation is last, after all checks
        self.updates += 1
        return float(delta)

    def end_episode(self) -> float:
        """Close one episode: applies the frozen epsilon decay."""
        self.episodes += 1
        return self.decay_epsilon()

