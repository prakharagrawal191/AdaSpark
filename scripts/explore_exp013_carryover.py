"""EXPLORATORY (post hoc, never deciding): EXP-013 carry-over after heavy default-config runs.

Prompted by an observation made while EXP-013 was running: in an early block an RL unit that
ran immediately after a 100 s B0 run took about twice as long as the B1/B4 units of the SAME
configuration in the same block. The pre-registered DEC-053 analysis treats such effects as
noise; this script only quantifies them so the report can say whether they exist. It is not part
of the frozen analysis, changes no verdict, and is labelled exploratory wherever it is cited.

Statistic: for every usable non-B0 run, r = execution_time / median(execution_time of its own
(cell, unit) over the 5 repetitions). Runs are split by whether the run immediately before
them in queue order (any block: the JVM persists across runs) was a B0 or B0' unit. Reported:
median r per group, the share of runs with r > 1 + 0.1189, and a two-sided permutation test
on the difference of group medians (20000 seeded resamples).
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OBS = PROJECT / "results" / "experiments" / "exp-013" / "observations.jsonl"
HEAVY = {"B0", "B0'"}
TAU = 0.1189


def main() -> int:
    rows = sorted((json.loads(l) for l in OBS.read_text(encoding="utf-8").splitlines() if l.strip()),
                  key=lambda r: r["queue_index"])
    by_unit: dict[tuple, list[float]] = {}
    for r in rows:
        if r["usable"]:
            by_unit.setdefault((r["block"].rsplit("|", 1)[0], r["unit"]), []).append(r["execution_time_s"])
    med = {k: statistics.median(v) for k, v in by_unit.items() if len(v) == 5}
    after_heavy, other = [], []
    prev = None
    for r in rows:
        if (prev is not None and r["usable"] and r["unit"] not in HEAVY
                and (key := (r["block"].rsplit("|", 1)[0], r["unit"])) in med):
            ratio = r["execution_time_s"] / med[key]
            (after_heavy if prev["unit"] in HEAVY else other).append(ratio)
        prev = r
    if not after_heavy or not other:
        print("not enough data yet")
        return 0
    obs = statistics.median(after_heavy) - statistics.median(other)
    pooled, n = after_heavy + other, len(after_heavy)
    rng = random.Random(0)
    extreme = 0
    for _ in range(20000):
        rng.shuffle(pooled)
        if abs(statistics.median(pooled[:n]) - statistics.median(pooled[n:])) >= abs(obs) - 1e-12:
            extreme += 1
    out = {"exploratory": True, "n_after_heavy": n, "n_other": len(other),
           "median_ratio_after_heavy": statistics.median(after_heavy),
           "median_ratio_other": statistics.median(other),
           "share_slow_after_heavy": sum(x > 1 + TAU for x in after_heavy) / n,
           "share_slow_other": sum(x > 1 + TAU for x in other) / len(other),
           "permutation_p_two_sided": (extreme + 1) / 20001}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
