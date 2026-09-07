"""Small statistical helpers (plan §22). Pure stdlib, no numpy required.

CV is defined consistently project-wide as:  cv = sample_std / mean  (ddof=1).
"""
from __future__ import annotations

import statistics
from typing import Sequence


def timing_stats(times: Sequence[float]) -> dict:
    """Return mean/median/std/CV summary for a list of durations (seconds).

    Returns a dict with ``None`` values when the input is empty (n=0).
    """
    values = [float(t) for t in times]
    if not values:
        return {"n": 0, "mean_s": None, "median_s": None, "std_s": None, "cv": None}
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "n": len(values),
        "mean_s": round(mean, 4),
        "median_s": round(statistics.median(values), 4),
        "std_s": round(std, 4),
        "cv": round(std / mean, 4) if mean else None,
    }