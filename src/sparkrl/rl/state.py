"""State representation: the frozen v1 / v1.5 discrete state spaces (COMP-RL-06).

Frozen source (PLAN section 13):

    v1  (15 states): workload_class in {agg, join, rdd_sort, skew_join, mixed}
                     x input_size_bin in {S<512MB, M 0.5-2GB, L>2GB}
    v1.5 (30 states): v1 x feedback_bin in {last_reward <= 0, > 0}
    v2 (2 states):    feedback_bin ONLY (EXP-007 A2, DEC-023 section 3)

Every field is categorical and derived deterministically:

* ``workload_class``  from the frozen family registry (F4_ski -> skew_join).
* ``input_size_bin``  from the DATASET MANIFESTS (Day-14 total bytes, recorded
  on disk before any run) - never from a live measurement.
* ``feedback_bin``    from the PREVIOUS episode's realized reward record. When
  no previous feedback exists (fresh episode, bandit mode), the pessimistic
  default ``le0`` is used. This is a Day-25 documented convention: the frozen
  30-state space has exactly two feedback bins, so "no history" must map into
  one of them; choosing ``le0`` biases exploration toward the workload rather
  than optimism. The convention is pinned by unit tests.

Continuous metrics (shuffle, spill, CV, CPU%, RSS) are collected AFTER
execution for reward/logging/multi-step mode and are NEVER part of the
tabular state (PLAN section 13). Nothing here normalizes, embeds, or learns.

Unknown schema version -> error (COMP-RL-06). Missing input size -> error:
a state must be deterministic; a caller without a dataset manifest cannot
construct an observation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_V1 = "state-v1"
SCHEMA_V15 = "state-v1.5"
# The frozen StateVector schema pair (v1 = context-only, v1.5 = context +
# feedback). This tuple is pinned by the Day-30 validator and MUST NOT grow:
# StateVector is by definition a workload-context state.
SUPPORTED_SCHEMAS = (SCHEMA_V1, SCHEMA_V15)

# EXP-007 A2 (DEC-023 section 3): the feedback-only schema. Deliberately
# OUTSIDE SUPPORTED_SCHEMAS - an A2 state carries NO workload context, so it
# is a distinct value object (FeedbackState), never a StateVector with hidden
# placeholder fields. The identifier follows the existing "state-v<N>"
# convention and is distinct from v1/v1.5.
SCHEMA_V2 = "state-v2"
ENCODER_SCHEMAS = (SCHEMA_V1, SCHEMA_V15, SCHEMA_V2)

# PLAN section 13 - frozen category sets. Order defines the state index.
WORKLOAD_CLASSES: tuple[str, ...] = ("agg", "join", "rdd_sort", "skew_join", "mixed")
SIZE_BINS: tuple[str, ...] = ("S", "M", "L")
FEEDBACK_BINS: tuple[str, ...] = ("le0", "gt0")   # last_reward <= 0 / > 0

# Frozen family -> class map (F4_ski is the skew family; PLAN section 13).
FAMILY_TO_CLASS: dict[str, str] = {
    "F1_agg": "agg",
    "F2_join": "join",
    "F3_rdd": "rdd_sort",
    "F4_ski": "skew_join",
    "F5_mixed": "mixed",
}

# Size-bin thresholds in bytes. S strictly below 512 MiB; M below 2 GiB;
# L at 2 GiB and above ("S<512MB, M 0.5-2GB, L>2GB", PLAN section 13).
_S_UPPER = 512 * 1024 * 1024
_M_UPPER = 2 * 1024 * 1024 * 1024

# Day-25 documented convention: no previous feedback maps to the pessimistic
# bin (see module docstring). Pinned by tests.
NO_FEEDBACK_BIN = "le0"

STATE_VERSION = "state-v1.5"  # default encoder schema


def size_bin_of(input_bytes: int | None) -> str:
    """Map a byte count onto the frozen size bins (deterministic)."""
    if input_bytes is None:
        raise ValueError("input_bytes is required to bin the state (no fabrication)")
    b = int(input_bytes)
    if b < 0:
        raise ValueError(f"input_bytes must be >= 0, got {input_bytes}")
    if b < _S_UPPER:
        return "S"
    if b < _M_UPPER:
        return "M"
    return "L"


def feedback_bin_of(last_reward: float | None) -> str:
    """Map the previous episode's reward onto the frozen feedback bins."""
    if last_reward is None:
        return NO_FEEDBACK_BIN
    return "gt0" if float(last_reward) > 0.0 else "le0"

@dataclass(frozen=True)
class StateVector:
    """One discrete tabular state (value object; equality is by value)."""

    workload_class: str
    input_size_bin: str
    schema_version: str = SCHEMA_V15
    feedback_bin: str | None = None   # None only in schema v1

    def __post_init__(self) -> None:
        if self.schema_version not in SUPPORTED_SCHEMAS:
            raise ValueError(
                f"unknown state schema {self.schema_version!r}; "
                f"expected one of {list(SUPPORTED_SCHEMAS)}")
        if self.workload_class not in WORKLOAD_CLASSES:
            raise ValueError(
                f"unknown workload_class {self.workload_class!r}; "
                f"expected one of {list(WORKLOAD_CLASSES)}")
        if self.input_size_bin not in SIZE_BINS:
            raise ValueError(
                f"unknown input_size_bin {self.input_size_bin!r}; "
                f"expected one of {list(SIZE_BINS)}")
        if self.schema_version == SCHEMA_V1:
            if self.feedback_bin is not None:
                raise ValueError("schema v1 has no feedback_bin; it must be None")
        else:
            if self.feedback_bin not in FEEDBACK_BINS:
                raise ValueError(
                    f"schema v1.5 requires feedback_bin in {list(FEEDBACK_BINS)}; "
                    f"got {self.feedback_bin!r}")

    # -- frozen enumeration -------------------------------------------------
    @property
    def state_index(self) -> int:
        """Deterministic index into the frozen state space (0..14 / 0..29)."""
        c = WORKLOAD_CLASSES.index(self.workload_class)
        s = SIZE_BINS.index(self.input_size_bin)
        if self.schema_version == SCHEMA_V1:
            return c * len(SIZE_BINS) + s
        f = FEEDBACK_BINS.index(self.feedback_bin)  # type: ignore[arg-type]
        return c * (len(SIZE_BINS) * len(FEEDBACK_BINS)) + s * len(FEEDBACK_BINS) + f

    @staticmethod
    def space_size(schema_version: str = SCHEMA_V15) -> int:
        if schema_version == SCHEMA_V1:
            return len(WORKLOAD_CLASSES) * len(SIZE_BINS)          # 15
        if schema_version == SCHEMA_V15:
            return len(WORKLOAD_CLASSES) * len(SIZE_BINS) * len(FEEDBACK_BINS)  # 30
        if schema_version == SCHEMA_V2:
            return len(FEEDBACK_BINS)                               # 2 (A2)
        raise ValueError(f"unknown state schema {schema_version!r}")

    # -- serialization ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Deterministic serializable form (fixed field order via asdict)."""
        d = asdict(self)
        d["state_index"] = self.state_index
        return d

    def key(self) -> tuple[str, str, str, str | None]:
        """Hashable identity key (stable across processes)."""
        return (self.schema_version, self.workload_class,
                self.input_size_bin, self.feedback_bin)


@dataclass(frozen=True)
class FeedbackState:
    """A2 state (EXP-007, DEC-023 section 3): ONLY the runtime-feedback bin.

    Frozen definition (read literally from PLAN section 24 / section 31 row 36
    and frozen by DEC-023): the workload-context state is removed, so the A2
    state retains exactly ``feedback_bin in {le0, gt0}`` - 2 states, nothing
    else. workload_class is NOT retained; input_size_bin is NOT retained;
    there is no third bin and no default bin beyond the documented no-history
    convention (``None -> le0``). The encoding is deterministic and the state
    keys are the stable strings ``state-v2|le0`` / ``state-v2|gt0``.

    This is NOT a StateVector and must never carry workload context: the
    schema identifier is deliberately outside ``SUPPORTED_SCHEMAS``, and the
    key tuple has no class/size component at all, so no workload or size
    information can leak into the Q-table key.
    """

    feedback_bin: str
    schema_version: str = SCHEMA_V2

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_V2:
            raise ValueError(
                f"FeedbackState requires schema {SCHEMA_V2!r}; "
                f"got {self.schema_version!r}")
        if self.feedback_bin not in FEEDBACK_BINS:
            raise ValueError(
                f"unknown feedback_bin {self.feedback_bin!r}; "
                f"expected one of {list(FEEDBACK_BINS)}")

    @property
    def state_index(self) -> int:
        """Deterministic index into the frozen 2-state A2 space (0..1)."""
        return FEEDBACK_BINS.index(self.feedback_bin)

    @staticmethod
    def space_size(schema_version: str = SCHEMA_V2) -> int:
        if schema_version != SCHEMA_V2:
            raise ValueError(f"unknown state schema {schema_version!r}")
        return len(FEEDBACK_BINS)                               # 2

    def to_dict(self) -> dict[str, Any]:
        """Deterministic serializable form (fixed field order)."""
        return {"schema_version": self.schema_version,
                "feedback_bin": self.feedback_bin,
                "state_index": self.state_index}

    def key(self) -> tuple[str, str]:
        """Hashable identity key - schema + feedback bin ONLY."""
        return (self.schema_version, self.feedback_bin)


class StateEncoder:
    """Workload context (+ optional feedback) -> StateVector (COMP-RL-06)."""

    def __init__(self, schema_version: str = SCHEMA_V15) -> None:
        if schema_version not in ENCODER_SCHEMAS:
            raise ValueError(
                f"unknown state schema {schema_version!r}; "
                f"expected one of {list(ENCODER_SCHEMAS)}")
        self.schema_version = schema_version

    def encode(self, family: str, input_bytes: int | None,
               last_reward: float | None = None) -> StateVector | FeedbackState:
        """Encode one workload context into the frozen discrete state.

        Raises on unknown family or missing/negative input size - a state is
        never fabricated from absent facts (PLAN section 13). EXCEPTION (A2
        only, DEC-023 section 3): under schema ``state-v2`` the state retains
        ONLY the feedback bin, so ``family`` and ``input_bytes`` are consumed
        and discarded (they must not influence the state in any way, and an
        absent size cannot falsify a state that has no size component).
        """
        try:
            wclass = FAMILY_TO_CLASS[family]
        except KeyError:
            raise ValueError(
                f"unknown family {family!r}; expected one of "
                f"{sorted(FAMILY_TO_CLASS)}") from None
        if self.schema_version == SCHEMA_V2:
            return FeedbackState(feedback_bin=feedback_bin_of(last_reward))
        sbin = size_bin_of(input_bytes)
        fbin = None
        if self.schema_version == SCHEMA_V15:
            fbin = feedback_bin_of(last_reward)
        return StateVector(workload_class=wclass, input_size_bin=sbin,
                           schema_version=self.schema_version, feedback_bin=fbin)

