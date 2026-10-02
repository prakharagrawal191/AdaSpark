#!/usr/bin/env python
"""Data-driven manuscript figures 21-24, rendered from committed artifacts (600 DPI PNG).

  Fig 23  RL convergence      <- results/training/<three seed runs>/episodes.jsonl
  Fig 21  benchmark results    <- results/evaluation/exp013_analysis.json
  Fig 22  resource utilization <- results/experiments/exp-013/observations.jsonl
  Fig 24  comparative radar    <- results/evaluation/exp013_analysis.json

No value is typed by hand. Usage: python make_result_figures.py [23|21|22|24|all]
"""
import json
import math
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DPI = 600
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})
SEED_RUNS = {"seed 0": "train-a0-d0-20260912T112906Z", "seed 1": "train-a1-d0-20260912T115123Z",
             "seed 2": "train-a2-d0-20260912T120648Z"}
FAMILIES = ("F1_agg", "F2_join", "F3_rdd", "F4_ski", "F5_mixed")
UNIT_STYLE = {"B0": ("#7f7f7f", "o"), "B1": ("#1f4e79", "s"), "B4": ("#6baed6", "D"),
              "RL": ("#c0392b", "^"), "B2": ("#2e7d32", "v"), "B0'": ("#ef6c00", "P")}
TAU = 0.1189


def save(fig, name):
    fig.savefig(HERE / name, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def running_median(vals, w=9):
    return [statistics.median(vals[max(0, i - w + 1): i + 1]) for i in range(len(vals))]


def fig23_convergence():
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for (label, run), color in zip(SEED_RUNS.items(), ("#1f4e79", "#ef6c00", "#2e7d32")):
        eps = [json.loads(l) for l in (ROOT / "results" / "training" / run / "episodes.jsonl")
               .read_text(encoding="utf-8").splitlines() if l.strip()]
        x = [e["episode_index"] for e in eps]
        r = [e["reward"] for e in eps]
        td = [abs(e["td_delta"] or 0.0) for e in eps]
        axes[0].scatter(x, r, s=6, color=color, alpha=0.35)
        axes[0].plot(x, running_median(r), color=color, label=f"{label} ({len(eps)} ep.)")
        axes[1].plot(x, running_median(td), color=color, label=label)
        axes[2].plot(x, [e["epsilon_used"] for e in eps], color=color, label=label)
    axes[0].set(title="(a) Reward per episode (running median, w=9)", xlabel="Episode",
                ylabel="R3 reward")
    axes[1].set(title="(b) |TD error| (running median, w=9)", xlabel="Episode",
                ylabel="|r − Q(s,a)|")
    axes[2].set(title="(c) Exploration rate ε", xlabel="Episode", ylabel="ε")
    axes[2].axhline(0.05, ls="--", color="gray", lw=0.8)
    for ax in axes:
        ax.legend(fontsize=7)
    fig.suptitle("Figure 23: RL Convergence Analysis — budget-bounded training under the "
                 "500-execution guard; convergence is not claimed (cross-seed agreement 0.20)",
                 weight="bold", fontsize=9)
    fig.tight_layout()
    save(fig, "Fig 23 RL Convergence Analysis.png")


def load_analysis():
    path = ROOT / "results" / "evaluation" / "exp013_analysis.json"
    if not path.exists():
        sys.exit("exp013_analysis.json not found: run scripts/analyze_exp013.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def cell_medians(doc):
    out = {}
    for key, v in doc["cell_medians"].items():
        cell, unit = key.rsplit("|", 1)
        if v["n_usable"] == 5:
            out.setdefault(cell, {})[unit] = v["median"]
    return out


def fig21_benchmarks():
    med = cell_medians(load_analysis())
    cells = [c for f in FAMILIES for c in sorted(med) if c.startswith(f) and "B1" in med[c]]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.axhspan(1 - TAU, 1 + TAU, color="#dddddd", label="±11.89% noise band (EXP-001)")
    for unit in ("B0", "B4", "RL", "B2", "B0'"):
        xs = [i for i, c in enumerate(cells) if unit in med[c]]
        ax.scatter(xs, [med[cells[i]][unit] / med[cells[i]]["B1"] for i in xs], s=18,
                   color=UNIT_STYLE[unit][0], marker=UNIT_STYLE[unit][1],
                   label={"B4": "B4 (A/A: same config as B1)", "B0'": "B0′ (AQE-on)"}.get(unit, unit))
    ax.axhline(1.0, color=UNIT_STYLE["B1"][0], lw=1, label="B1 = B3 (reference)")
    ax.set_yscale("log")
    ax.set_xticks(range(len(cells)))
    ax.set_xticklabels([c.replace("|", " ").replace("_", "") for c in cells], rotation=90, fontsize=6)
    ax.set_ylabel("Median time ÷ B1 median (log scale; lower is faster)")
    ax.set_title("Figure 21: Performance Benchmark Results — EXP-013, randomized interleaved "
                 "blocks, median of 5 repetitions per cell", weight="bold")
    ax.legend(fontsize=7, ncol=3)
    save(fig, "Fig 21 Performance Benchmark Results.png")


def fig22_utilization():
    doc = load_analysis()
    rows = [json.loads(l) for l in (ROOT / "results" / "experiments" / "exp-013" / "observations.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["usable"] and r["stage"] in doc["stages_complete"] and r.get("resources")]
    groups = ("B0", "B1", "RL")
    metrics = [("sys_cpu_percent_mean", "Host CPU utilization during run (%)", 1.0),
               ("shuffle_write_bytes", "Shuffle write per run (MB)", 1 / 2**20),
               ("total_time_s", "Session time incl. warm-ups (s)", 1.0)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    width = 0.26
    for ax, (field, label, scale) in zip(axes, metrics):
        for k, unit in enumerate(groups):
            vals = []
            for fam in FAMILIES:
                xs = [r["resources"].get(field) for r in rows
                      if r["family"] == fam and r["unit"] == unit and r["resources"].get(field) is not None]
                vals.append(statistics.median(xs) * scale if xs else 0.0)
            ax.bar([i + (k - 1) * width for i in range(len(FAMILIES))], vals, width,
                   color=UNIT_STYLE[unit][0], label=unit)
        ax.set_xticks(range(len(FAMILIES)))
        ax.set_xticklabels([f.split("_")[0] for f in FAMILIES])
        ax.set_title(label, fontsize=8)
        ax.legend(fontsize=7)
    fig.suptitle("Figure 22: Resource Utilization Analysis — per-run medians by workload family "
                 "and configuration (EXP-013 monitoring records)", weight="bold", fontsize=9)
    fig.tight_layout()
    save(fig, "Fig 22 Resource Utilization Analysis.png")


def fig24_radar():
    med = cell_medians(load_analysis())
    arms = ("B0", "B4", "RL", "B2")
    speed = {a: [] for a in arms}
    for fam in FAMILIES:
        for a in arms:
            logs = [math.log(med[c]["B1"] / med[c][a]) for c in med
                    if c.startswith(fam) and a in med[c] and "B1" in med[c]]
            speed[a].append(math.exp(sum(logs) / len(logs)) if logs else float("nan"))
    angles = [2 * math.pi * i / len(FAMILIES) for i in range(len(FAMILIES))] + [0.0]
    fig, ax = plt.subplots(figsize=(6.2, 6.2), subplot_kw={"polar": True})
    ax.plot(angles, [1.0] * len(angles), color=UNIT_STYLE["B1"][0], lw=1.2, label="B1 = B3 (1.0)")
    for a in arms:
        vals = speed[a] + speed[a][:1]
        ax.plot(angles, vals, color=UNIT_STYLE[a][0], marker=UNIT_STYLE[a][1],
                label={"B4": "B4 (same config as B1)", "B2": "B2 (F4 undefined)"}.get(a, a))
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f.split("_")[0] for f in FAMILIES])
    ax.set_title("Figure 24: Comparative Radar Chart\nper-family geometric-mean speed relative to "
                 "B1 (outward = faster), EXP-013", weight="bold", pad=18, fontsize=9)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.15, -0.18), fontsize=7, ncol=3)
    save(fig, "Fig 24 Comparative Radar Chart.png")


if __name__ == "__main__":
    want = sys.argv[1] if len(sys.argv) > 1 else "all"
    for key, fn in (("23", fig23_convergence), ("21", fig21_benchmarks),
                    ("22", fig22_utilization), ("24", fig24_radar)):
        if want in (key, "all"):
            fn()
