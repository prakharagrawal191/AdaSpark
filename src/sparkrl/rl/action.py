"""Action mapper: the frozen 12-configuration action space (COMP-RL-07).

Frozen source (PLAN section 14):

    v1 - 12 actions: spark.sql.shuffle.partitions in {16, 32, 64, 128}
                     x execution parallelism (local[N] + default.parallelism=N)
                       in {2, 4, 8}

This is EXACTLY the EXP-002 varied grid (``sparkrl.experiments.grid``), so the
environment reuses the frozen ``ConfigPoint`` objects instead of duplicating
the domain. Enumeration order is the frozen grid order:
``grid_index = parallelism_index * 4 + shuffle_index``.

Pre-authorized Plan-B subset (ARCHITECTURE_FREEZE / COMP-RL-07): indices
{0, 3, 6, 9} in ``mode4``; mode4 is strictly contained in mode12.

Rejected actions (documented in PLAN section 14, never offered here):
executor memory, dynamic allocation, broadcast threshold / caching (v2,
ablation-only), arbitrary Spark properties.

Out-of-range / malformed / non-integer actions are rejected BEFORE any Spark
execution (COMP-RL-07: "out-of-range -> reject pre-exec"). B0 is the
reference condition and is NOT an action.
"""
from __future__ import annotations

from sparkrl.experiments.grid import ConfigPoint, build_grid, grid_fingerprint
from sparkrl.spark.config import SparkConfig

MODE12 = "mode12"
MODE4 = "mode4"
SUPPORTED_MODES = (MODE12, MODE4)

# Pre-authorized Plan-B 4-configuration subset (frozen indices).
MODE4_SUBSET = frozenset({0, 3, 6, 9})


class InvalidAction(ValueError):
    """Raised for any action outside the frozen action domain (pre-execution)."""


class ActionMapper:
    """Action index -> frozen configuration point (no learning, no search)."""

    def __init__(self, mode: str = MODE12) -> None:
        if mode not in SUPPORTED_MODES:
            raise ValueError(
                f"unknown action mode {mode!r}; expected one of {list(SUPPORTED_MODES)}")
        self.mode = mode
        points = [p for p in build_grid(include_b0=True) if p.grid_index is not None]
        points = sorted(points, key=lambda p: p.grid_index)  # type: ignore[arg-type]
        if len(points) != 12 or any(p.grid_index != i for i, p in enumerate(points)):  # type: ignore[arg-type]
            raise RuntimeError("frozen 12-action grid invariant violated")
        self._points: tuple[ConfigPoint, ...] = tuple(points)
        self._fingerprint = grid_fingerprint(build_grid(include_b0=True))

    # -- domain --------------------------------------------------------------
    @property
    def size(self) -> int:
        """Number of actions offered in the current mode (12 or 4)."""
        return 12 if self.mode == MODE12 else len(MODE4_SUBSET)

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        if value not in SUPPORTED_MODES:
            raise ValueError(
                f"unknown action mode {value!r}; expected one of {list(SUPPORTED_MODES)}")
        self._mode = value

    @property
    def grid_fingerprint(self) -> str:
        """Fingerprint of the frozen EXP-002 grid backing the action space."""
        return self._fingerprint

    def allowed_actions(self) -> tuple[int, ...]:
        if self.mode == MODE12:
            return tuple(range(12))
        return tuple(sorted(MODE4_SUBSET))

    def describe(self, action: int) -> ConfigPoint:
        """Return the frozen ConfigPoint for a valid action index."""
        self._validate(action)
        return self._points[action]

    def to_config(self, action: int, base_config: SparkConfig) -> tuple[SparkConfig, ConfigPoint, str]:
        """Map an action onto a concrete SparkConfig (deterministic).

        Returns ``(spark_config, config_point, config_fingerprint)``. AQE must
        remain OFF after application (frozen main-study control).
        """
        point = self.describe(action)
        cfg = point.apply_to(base_config)
        if cfg.aqe_enabled:
            raise RuntimeError(
                "AQE became enabled after action application (PLAN section 7)")
        return cfg, point, cfg.fingerprint()

    # -- validation ----------------------------------------------------------
    def _validate(self, action: int) -> None:
        if isinstance(action, bool) or not isinstance(action, int):
            raise InvalidAction(
                f"action must be an int in the frozen domain, got {action!r}")
        if not 0 <= action < 12:
            raise InvalidAction(
                f"action {action} out of range [0, 11] (frozen 12-action grid)")
        if self.mode == MODE4 and action not in MODE4_SUBSET:
            raise InvalidAction(
                f"action {action} is not in the pre-authorized Plan-B subset "
                f"{sorted(MODE4_SUBSET)} (mode4)")
