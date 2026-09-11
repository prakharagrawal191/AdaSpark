"""T_ref store: default-configuration reference times for reward normalization.

Frozen source (PLAN section 15): "T_ref = default-configuration time for the
same workload instance + seed, calibrated once (EXP-002/003) and stored in the
manifest; used only for reward normalization - never shown to the agent as
state."

Day-25 source of truth: the EXP-002 analysis artifact
``results/experiments/exp-002/analysis/gate.json`` key ``t_ref_calibration``,
measured as the B0 median for (family, scale) at seed 0. This module is
STRICTLY READ-ONLY - it never writes to EXP-002 artifacts.

Keyed by ``family|scale``. Seed must be 0 (the only seed EXP-002 calibrated);
any other seed returns None, which the environment turns into the COMP-RL-08
hard error BEFORE executing Spark. ``F3_rdd|medium`` is null in the artifact
(invalid B0 panel) and therefore also resolves to None.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_GATE_PATH = PROJECT / "results" / "experiments" / "exp-002" / "analysis" / "gate.json"


class TRefStore:
    """Read-only accessor for calibrated T_ref values."""

    def __init__(self, mapping: Mapping[str, float | None] | None = None,
                 gate_path: str | Path = DEFAULT_GATE_PATH) -> None:
        if mapping is not None:
            self._source = "explicit-mapping"
            self._values: dict[str, float | None] = {str(k): v for k, v in mapping.items()}
        else:
            path = Path(gate_path)
            if not path.exists():
                raise FileNotFoundError(
                    f"T_ref source not found: {path} (EXP-002 gate artifact)")
            data = json.loads(path.read_text(encoding="utf-8"))
            calib = data.get("t_ref_calibration")
            if not isinstance(calib, dict):
                raise ValueError(f"no t_ref_calibration in {path}")
            self._source = f"exp002-gate:{path.name}"
            self._values = {str(k): (None if v is None else float(v))
                            for k, v in calib.items()}
            self._gate_analysis_version = data.get("analysis_version")

    @property
    def source(self) -> str:
        """Provenance of the loaded values (recorded in transition records)."""
        return self._source

    def get(self, family: str, scale: str, seed: int = 0) -> float | None:
        """T_ref in seconds, or None when not calibrated (never fabricated)."""
        if seed != 0:
            # EXP-002 calibrated seed 0 only; EXP-003 owns further calibration.
            return None
        return self._values.get(f"{family}|{scale}")

    def calibrated_keys(self) -> list[str]:
        """Keys with a non-null calibrated value (deterministic order)."""
        return sorted(k for k, v in self._values.items() if v is not None)
