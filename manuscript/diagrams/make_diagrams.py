#!/usr/bin/env python
"""AdaSpark manuscript diagrams - original figures, matplotlib, 600 DPI PNG.

Naming: 'Fig NN <Title>.png' in manuscript/diagrams/.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

HERE = Path(__file__).resolve().parent
DPI = 600
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})


def save(fig, name):
    fig.savefig(HERE / name, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig01_evolution():
    stages = [
        ("2004-2012\nMapReduce", "Manual\nbatch jobs"),
        ("2012-2015\nSpark RDD", "In-memory\nunified API"),
        ("2015-2020\nDataFrames\n+ SQL", "Declarative\nCatalyst"),
        ("2020-2024\nAQE + DPP", "Runtime\nadaptivity"),
        ("2024+\nSelf-adaptive\n(AdaSpark)", "RL closed\nloop"),
    ]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    for i, (title, sub) in enumerate(stages):
        x = 0.6 + i * 1.9
        color = "#1f4e79" if i < 4 else "#b03a2e"
        box = mpatches.FancyBboxPatch((x - 0.8, 0.6), 1.6, 1.6,
                                      boxstyle="round,pad=0.05",
                                      facecolor=color, edgecolor="black")
        ax.add_patch(box)
        ax.text(x, 1.65, title, ha="center", va="center", color="white",
                fontsize=8, weight="bold")
        ax.text(x, 0.95, sub, ha="center", va="center", color="white",
                fontsize=7)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 1.15, 1.4), xytext=(x + 0.75, 1.4),
                        arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(5, 2.6, "Figure 1: Evolution of Big Data Programming Frameworks",
            ha="center", fontsize=10, weight="bold")
    save(fig, "Fig 01 Evolution of Big Data Programming Frameworks.png")


def _block(ax, x, y, w, h, title, sub="", color="#1f4e79", tcolor="white"):
    box = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03",
                                  facecolor=color, edgecolor="black")
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2 + 0.12, title, ha="center", va="center",
            color=tcolor, fontsize=8, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.22, sub, ha="center", va="center",
                color=tcolor, fontsize=7)


def fig02_ecosystem():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.text(5, 5.6, "Figure 2: Self-Adaptive Analytics Ecosystem",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 4.1, 2.0, 0.9, "Data sources", "batch/stream")
    _block(ax, 3.9, 4.1, 2.2, 0.9, "Spark execution", "jobs, DAG, shuffle")
    _block(ax, 7.7, 4.1, 2.0, 0.9, "Serving", "dashboards")
    _block(ax, 3.9, 2.7, 2.2, 0.9, "Monitoring", "sysmon + event log",
           color="#2e7d32")
    _block(ax, 3.9, 1.3, 2.2, 0.9, "RL optimization", "MAPE-K loop",
           color="#b03a2e")
    _block(ax, 0.3, 1.3, 2.0, 0.9, "Governance", "policies, audit",
           color="#6a1b9a")
    _block(ax, 7.7, 1.3, 2.0, 0.9, "Explainability", "traces, reports",
           color="#6a1b9a")
    for x0, y0, x1, y1 in [(2.3, 4.55, 3.9, 4.55), (6.1, 4.55, 7.7, 4.55),
                           (5.0, 4.1, 5.0, 3.6), (5.0, 2.7, 5.0, 2.2),
                           (2.3, 1.75, 3.9, 1.75), (6.1, 1.75, 7.7, 1.75),
                           (1.3, 4.1, 1.3, 2.2), (8.7, 4.1, 8.7, 2.2)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 02 Self-Adaptive Analytics Ecosystem.png")


def fig03_challenges():
    challenges = [
        ("Workload\nvariability", "mix/scale/skew\ndrift"),
        ("Resource\nutilization", "idle vs spill\nimbalance"),
        ("Scheduling\ninefficiency", "static partitions\nstage mismatch"),
        ("Dynamic\nenvironments", "thermal/noise\n±20% shifts"),
        ("Shuffle\nbottlenecks", "amplifies\nall above"),
    ]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    ax.text(5, 2.65, "Figure 3: Big Data Programming Challenges Landscape",
            ha="center", fontsize=10, weight="bold")
    for i, (title, sub) in enumerate(challenges):
        x = 0.7 + i * 1.9
        _block(ax, x - 0.8, 0.5, 1.6, 1.5, title, sub, color="#4a235a")
    save(fig, "Fig 03 Big Data Programming Challenges Landscape.png")


def fig04_taxonomy():
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 4: Literature Taxonomy Framework",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 3.3, 3.3, 3.4, 0.8, "Self-adaptive Spark (AdaSpark)",
           "RL closed loop", color="#b03a2e")
    branches = [  # the seven literature strands of Section III
        ("Spark\noptimization", "Starfish, OtterTune,\nCDBTune, AQE"),
        ("Config\nauto-tuning", "CausalConf,\nDeepCAT+, DOT"),
        ("RL\nmethods", "Q-learning,\nDQN/PPO contrast"),
        ("RL scheduling,\nautoscaling", "Decima, DeepHCM,\nASTRA"),
        ("Measurement\nmethodology", "Georges, Kalibera,\nMytkowicz"),
        ("Monitoring\noverhead", "Kieker,\nReichelt"),
        ("Self-adaptive,\nDataOps, MLOps", "MAPE-K + ML,\nlineage"),
    ]
    for i, (title, sub) in enumerate(branches):
        x, y, w, h = 0.05 + i * 1.42, 1.0, 1.34, 1.6
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03",
                                             facecolor="#1f4e79", edgecolor="black"))
        ax.text(x + w / 2, y + h * 0.72, title, ha="center", va="center", color="white",
                fontsize=7.5, weight="bold")
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center", color="white", fontsize=6.5)
        ax.annotate("", xy=(x + w / 2, y + h), xytext=(5.0, 3.3),
                    arrowprops=dict(arrowstyle="->", lw=1.0))
    save(fig, "Fig 04 Literature Taxonomy Framework.png")


def fig05_requirements():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 5: Requirements Engineering Model",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 3.0, 2.2, 0.9, "Stakeholder needs", "perf, scale, trust")
    _block(ax, 3.85, 3.0, 2.3, 0.9, "Functional reqs", "FR1-FR5")
    _block(ax, 7.45, 3.0, 2.25, 0.9, "Non-functional", "NFR1-NFR5")
    _block(ax, 1.6, 1.5, 2.5, 0.9, "Architecture", "12 components",
           color="#2e7d32")
    _block(ax, 5.9, 1.5, 2.5, 0.9, "Evaluation", "EXP-001..014",
           color="#2e7d32")
    for x0, y0, x1, y1 in [(2.5, 3.45, 3.85, 3.45), (6.15, 3.45, 7.45, 3.45),
                           (5.0, 3.0, 2.85, 2.4), (5.0, 3.0, 7.15, 2.4)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 05 Requirements Engineering Model.png")


def fig06_core():
    layers = [
        ("Security, Reliability & Governance", "#6a1b9a"),
        ("Explainability & Decision Intelligence", "#6a1b9a"),
        ("Monitoring, Feedback & Learning (MAPE-K observe)", "#2e7d32"),
        ("Self-Tuning & Resource Scheduling (MAPE-K execute)", "#ef6c00"),
        ("RL Optimization: state v1.5 x 12 actions, R3, Q-learning (plan)", "#b03a2e"),
        ("Spark Programming & Execution (jobs, DAG, shuffle)", "#1f4e79"),
    ]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.text(5, 6.6,
            "Figure 6: RL-Driven Spark Architecture (Core Figure)",
            ha="center", fontsize=10, weight="bold")
    for i, (title, color) in enumerate(layers):
        _block(ax, 0.8, 5.4 - i * 0.85, 8.4, 0.7, title, "", color=color)
    save(fig, "Fig 06 RL-Driven Spark Architecture.png")


def fig07_loop():
    fig, ax = plt.subplots(figsize=(10, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.text(5, 4.1, "Figure 7: Layered System Architecture (Training Loop)",
            ha="center", fontsize=10, weight="bold")
    steps = [("Observe\nstate v1.5", "#1f4e79"), ("Select\n12-action", "#b03a2e"),
             ("Execute\nSpark job", "#ef6c00"), ("Reward\nR3", "#2e7d32"),
             ("Update\nQ-table", "#6a1b9a")]
    for i, (title, color) in enumerate(steps):
        x = 0.25 + i * 1.95
        _block(ax, x, 1.6, 1.7, 1.2, title, "", color=color)
        if i < 4:
            ax.annotate("", xy=(x + 1.7 + 0.25, 2.2), xytext=(x + 1.7, 2.2),
                        arrowprops=dict(arrowstyle="->", lw=1.4))
    ax.annotate("", xy=(1.1, 1.6), xytext=(8.75, 1.6),      # next episode: back to Observe
                arrowprops=dict(arrowstyle="->", lw=1.0, ls="dashed",
                                connectionstyle="arc3,rad=-0.13"))
    ax.text(5, 0.7, "Q0 offline init -> online adapt (<=500) -> policy store",
            ha="center", fontsize=8, style="italic")
    save(fig, "Fig 07 Layered System Architecture.png")


def fig08_spark():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 8: Apache Spark Execution Framework",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 3.75, 3.3, 2.5, 0.8, "Driver", "DAG scheduler")
    _block(ax, 0.3, 1.7, 2.2, 0.9, "Executor 1", "tasks, spill")
    _block(ax, 3.9, 1.7, 2.2, 0.9, "Executor N", "tasks, spill")
    _block(ax, 7.5, 1.7, 2.2, 0.9, "Shuffle", "partitions")
    _block(ax, 0.3, 0.3, 4.55, 0.8, "Seeded datasets + manifests", "",
           color="#2e7d32")
    _block(ax, 5.15, 0.3, 4.55, 0.8, "Runner clock + metrics", "",
           color="#2e7d32")
    for x0, y0, x1, y1 in [(5.0, 3.3, 1.4, 2.6), (5.0, 3.3, 5.0, 2.6),
                           (5.0, 3.3, 8.6, 2.6), (5.0, 1.7, 5.0, 1.1)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 08 Apache Spark Execution Framework.png")


def fig09_rl_workflow():
    fig, ax = plt.subplots(figsize=(10, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.text(5, 4.1, "Figure 9: Reinforcement Learning Workflow",
            ha="center", fontsize=10, weight="bold")
    steps = [("State\nv1.5 (30)", "#1f4e79"), ("Policy\nε-greedy", "#b03a2e"),
             ("Action\n12-grid", "#ef6c00"), ("Reward\nR3", "#2e7d32"),
             ("Update\nQ ← Q+αδ", "#6a1b9a")]
    for i, (title, color) in enumerate(steps):
        x = 0.25 + i * 1.95
        _block(ax, x, 1.6, 1.7, 1.2, title, "", color=color)
        if i < 4:
            ax.annotate("", xy=(x + 1.95, 2.2), xytext=(x + 1.7, 2.2),
                        arrowprops=dict(arrowstyle="->", lw=1.4))
    ax.text(5, 0.7, "Q0 offline init -> α=0.2, γ=0.0, ε 1.0→0.05 -> policy store",
            ha="center", fontsize=8, style="italic")
    save(fig, "Fig 09 Reinforcement Learning Workflow.png")


def fig10_agent():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 10: RL Agent Interaction Model",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.5, 2.0, 2.6, 1.2, "Agent", "Q-table + Q0", color="#b03a2e")
    _block(ax, 6.9, 2.0, 2.6, 1.2, "Environment", "Spark + T_ref",
           color="#1f4e79")
    ax.annotate("", xy=(6.9, 2.9), xytext=(3.1, 2.9),
                arrowprops=dict(arrowstyle="->", lw=1.4))
    ax.text(5, 3.15, "action a (config)", ha="center", fontsize=8)
    ax.annotate("", xy=(3.1, 2.3), xytext=(6.9, 2.3),
                arrowprops=dict(arrowstyle="->", lw=1.4))
    ax.text(5, 1.95, "state s', reward r (R3)", ha="center", fontsize=8)
    _block(ax, 3.6, 0.4, 2.8, 0.8, "Budget guard ≤500", "env-owned",
           color="#2e7d32")
    save(fig, "Fig 10 RL Agent Interaction Model.png")


def fig11_allocation():
    fig, ax = plt.subplots(figsize=(10, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.text(5, 4.1, "Figure 11: Dynamic Resource Allocation Model",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.2, 2.0, 1.0, "Policy", "greedy action")
    _block(ax, 3.7, 2.2, 2.6, 1.0, "Resolver", "partitions × local[N]",
           color="#ef6c00")
    _block(ax, 7.7, 2.2, 2.0, 1.0, "Executors", "tasks + spill")
    for x0, y0, x1, y1 in [(2.3, 2.7, 3.7, 2.7), (6.3, 2.7, 7.7, 2.7)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.4))
    ax.text(5, 1.2, "session restart on parallelism change; F5 cache kept only when parallelism is unchanged",
            ha="center", fontsize=8, style="italic")
    save(fig, "Fig 11 Dynamic Resource Allocation Model.png")


def fig12_scheduling():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 12: Adaptive Scheduling Framework",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 3.0, 2.9, 0.9, "Static policies", "B0, B0′, B1, B2, B3")
    _block(ax, 6.8, 3.0, 2.9, 0.9, "Search and learned", "B4 search, RL-s0/s1/s2")
    _block(ax, 2.5, 1.5, 5.0, 0.9, "42 frozen TEST cells × 5 reps", "",
           color="#2e7d32")
    _block(ax, 2.5, 0.3, 5.0, 0.8, "Interleaved blocks + exact tests (EXP-013)", "",
           color="#6a1b9a")
    for x0, y0, x1, y1 in [(1.75, 3.0, 3.5, 2.4), (8.25, 3.0, 6.5, 2.4),
                           (5.0, 1.5, 5.0, 1.1)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 12 Adaptive Scheduling Framework.png")


def fig13_selftuning():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 13: Self-Tuning Architecture",
            ha="center", fontsize=10, weight="bold")
    comps = [("Partition\noptimizer", "#1f4e79"),
             ("Executor\nconfigurator", "#ef6c00"),
             ("Cache\nmanager", "#2e7d32"),
             ("Balance\nmonitor", "#6a1b9a")]
    for i, (title, color) in enumerate(comps):
        _block(ax, 0.25 + i * 2.44, 2.2, 2.2, 1.2, title, "", color=color)
    _block(ax, 2.5, 0.5, 5.0, 0.9, "Ablations A1-A4 (A5 gated NO)", "",
           color="#b03a2e")
    save(fig, "Fig 13 Self-Tuning Architecture.png")


def fig14_lifecycle():
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.5)
    ax.axis("off")
    ax.text(5, 3.1, "Figure 14: Parameter Optimization Lifecycle",
            ha="center", fontsize=10, weight="bold")
    phases = ["Calibrate\nT_ref", "Initialize\nQ0", "Adapt\n≤500",
              "Freeze\npolicy", "Evaluate\nsealed test"]
    for i, title in enumerate(phases):
        x = 0.3 + i * 1.94
        _block(ax, x, 0.9, 1.7, 1.2, title, "",
               color="#1f4e79" if i < 4 else "#2e7d32")
        if i < 4:
            ax.annotate("", xy=(x + 1.94, 1.5), xytext=(x + 1.7, 1.5),
                        arrowprops=dict(arrowstyle="->", lw=1.4))
    save(fig, "Fig 14 Parameter Optimization Lifecycle.png")


def fig15_explainable():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 15: Explainable RL Framework",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.6, 2.9, 1.0, "Policy store", "checkpoints + Q-tables")
    _block(ax, 3.6, 2.6, 2.8, 1.0, "Agreement check", "C = 0.20 vs 0.70",
           color="#b03a2e")
    _block(ax, 6.8, 2.6, 2.9, 1.0, "Report arms", "3 replicates, not 1",
           color="#2e7d32")
    _block(ax, 2.5, 1.0, 5.0, 0.9, "Decision log: refusal recorded (DEC-015)",
           "", color="#6a1b9a")
    for x0, y0, x1, y1 in [(3.2, 3.1, 3.6, 3.1), (6.4, 3.1, 6.8, 3.1),
                           (5.0, 2.6, 5.0, 1.9)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 15 Explainable RL Framework.png")


def fig16_decision():
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.text(5, 3.6, "Figure 16: Decision Intelligence Workflow",
            ha="center", fontsize=10, weight="bold")
    steps = ["Observe", "Score\nconf C", "C >= 0.70?\ndecide : disclose",
             "Trace\nmanifest", "Audit\nDEC log"]
    for i, title in enumerate(steps):
        x = 0.2 + i * 1.96
        color = "#b03a2e" if i == 2 else ("#2e7d32" if i > 2 else "#1f4e79")
        _block(ax, x, 1.2, 1.76, 1.2, title, "", color=color)
        if i < 4:
            ax.annotate("", xy=(x + 1.96, 1.8), xytext=(x + 1.76, 1.8),
                        arrowprops=dict(arrowstyle="->", lw=1.3))
    save(fig, "Fig 16 Decision Intelligence Workflow.png")


def fig17_monitoring():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 17: Monitoring and Feedback Loop",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.8, 2.2, 1.0, "Sampler", "1 Hz")
    _block(ax, 3.9, 2.8, 2.2, 1.0, "Event log", "COMPLETE req.")
    _block(ax, 7.5, 2.8, 2.2, 1.0, "Schema", "merge+validate")
    _block(ax, 1.5, 1.2, 3.0, 0.9, "Online: Q-update", "", color="#b03a2e")
    _block(ax, 5.5, 1.2, 3.0, 0.9, "Offline: adjudication", "",
           color="#2e7d32")
    for x0, y0, x1, y1 in [(2.5, 3.3, 3.9, 3.3), (6.1, 3.3, 7.5, 3.3),
                           (5.0, 2.8, 3.0, 2.1), (5.0, 2.8, 7.0, 2.1)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 17 Monitoring and Feedback Loop.png")


def fig18_governance():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 18: Security and Governance Architecture",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.8, 2.9, 1.0, "Policy enforcement", "budget, F-FAIL")
    _block(ax, 3.55, 2.8, 2.9, 1.0, "Access control", "split guards")
    _block(ax, 6.8, 2.8, 2.9, 1.0, "Fault tolerance", "stops, Plan B")
    _block(ax, 1.5, 1.2, 7.0, 0.9, "Audit trail: decision log DEC-001–055 + manifests + hashes",
           "", color="#6a1b9a")
    save(fig, "Fig 18 Security and Governance Architecture.png")


def fig19_testbed():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 19: Experimental Testbed Architecture",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.8, 2.9, 1.0, "Machine", "Win11, 24 cores")
    _block(ax, 3.55, 2.8, 2.9, 1.0, "Spark local[2]", "PySpark 3.5.9",
           color="#ef6c00")
    _block(ax, 6.8, 2.8, 2.9, 1.0, "Workloads", "F1-F5 x S/M/L")
    _block(ax, 0.3, 1.2, 4.55, 0.9, "Backend frozen (smoke 13/13)", "",
           color="#2e7d32")
    _block(ax, 5.15, 1.2, 4.55, 0.9, "Seeded data + manifests", "",
           color="#2e7d32")
    for x0, y0, x1, y1 in [(3.2, 3.3, 3.55, 3.3), (6.45, 3.3, 6.8, 3.3)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 19 Experimental Testbed Architecture.png")


def fig20_eval():
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.text(5, 3.6, "Figure 20: Evaluation Framework",
            ha="center", fontsize=10, weight="bold")
    steps = ["Median\ntime", "Gates\n10%/5%/.70", "Exact tests\n+ A/A control",
             "Intervals\n95% CI", "Ledger\n483/500"]
    for i, title in enumerate(steps):
        x = 0.2 + i * 1.96
        _block(ax, x, 1.2, 1.76, 1.2, title, "",
               color="#1f4e79" if i < 4 else "#2e7d32")
        if i < 4:
            ax.annotate("", xy=(x + 1.96, 1.8), xytext=(x + 1.76, 1.8),
                        arrowprops=dict(arrowstyle="->", lw=1.3))
    save(fig, "Fig 20 Evaluation Framework.png")


# Figures 21-24 are data-driven and live in make_result_figures.py, which reads the
# committed analysis artifacts instead of hand-typed values.


def fig25_reliability():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 25: Reliability Assessment Framework",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.8, 2.0, 1.0, "Claim", "10 claims")
    _block(ax, 2.9, 2.8, 2.0, 1.0, "Evidence", "artifacts",
           color="#ef6c00")
    _block(ax, 5.5, 2.8, 2.0, 1.0, "Verdict", "Table 13",
           color="#2e7d32")
    _block(ax, 7.9, 2.8, 1.8, 1.0, "Log", "DEC-001–055",
           color="#6a1b9a")
    for x0, y0, x1, y1 in [(2.3, 3.3, 2.9, 3.3), (4.9, 3.3, 5.5, 3.3),
                           (7.5, 3.3, 7.9, 3.3)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(5, 1.6, "Supported: sensitivity, budget, defaults (H2), A/A noise floor, sampler overhead,"
            " analysis reproducibility, auditability", ha="center", fontsize=8)
    ax.text(5, 1.1, "Rejected: static/random superiority (H3)  ·  Partial: measurement reproducibility"
            "  ·  Not evaluable: generalization  ·  Not established: event-log overhead", ha="center", fontsize=8)
    save(fig, "Fig 25 Reliability Assessment Framework.png")


def fig26_manufacturing():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 26: Smart Manufacturing Analytics Ecosystem",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.8, 2.2, 1.0, "Sensors", "batch streams")
    _block(ax, 3.9, 2.8, 2.2, 1.0, "Spark agg/join", "F1/F2 pattern",
           color="#ef6c00")
    _block(ax, 7.5, 2.8, 2.2, 1.0, "Quality\ncontrol", "dashboards")
    _block(ax, 2.5, 1.2, 5.0, 0.9, "RL tuning loop (prospective)", "",
           color="#b03a2e")
    for x0, y0, x1, y1 in [(2.5, 3.3, 3.9, 3.3), (6.1, 3.3, 7.5, 3.3),
                           (5.0, 2.8, 5.0, 2.1)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 26 Smart Manufacturing Analytics Ecosystem.png")


def fig27_finance():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 27: Financial Analytics Optimization Platform",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.8, 2.2, 1.0, "Risk feeds", "eod batches")
    _block(ax, 3.9, 2.8, 2.2, 1.0, "Spark mixed", "F5 pattern",
           color="#ef6c00")
    _block(ax, 7.5, 2.8, 2.2, 1.0, "Window", "headroom 3-5x")
    _block(ax, 2.5, 1.2, 5.0, 0.9, "Governed policy per family (prospective)",
           "", color="#2e7d32")
    for x0, y0, x1, y1 in [(2.5, 3.3, 3.9, 3.3), (6.1, 3.3, 7.5, 3.3),
                           (5.0, 2.8, 5.0, 2.1)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.2))
    save(fig, "Fig 27 Financial Analytics Optimization Platform.png")


def fig28_dashboard():
    # KPI tiles, not one bar axis: the four measures have different units (Section 19, Table 15)
    tiles = [("4.0×", "faster than\nSpark defaults", "RL, 37 TEST cells (EXP-013)", "#1f4e79"),
             ("1.22×", "slower than best\nstatic tuning", "the learner's bound (EXP-013)", "#c0392b"),
             ("≈57 h", "for one overhead\nadjudication study", "single node (EXP-009)", "#ef6c00"),
             ("≈60%", "of those runs\navoidable", "dependence-aware stopping", "#2e7d32")]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    ax.text(5, 2.95, "Figure 28: Business Impact Dashboard", ha="center", weight="bold", fontsize=11)
    for i, (value, what, src, color) in enumerate(tiles):
        x = 0.15 + i * 2.45
        ax.add_patch(mpatches.FancyBboxPatch((x, 0.2), 2.25, 2.3, boxstyle="round,pad=0.03",
                                             facecolor=color, edgecolor="black"))
        ax.text(x + 1.125, 1.75, value, ha="center", va="center", color="white", fontsize=20,
                weight="bold")
        ax.text(x + 1.125, 1.0, what, ha="center", va="center", color="white", fontsize=8.5)
        ax.text(x + 1.125, 0.55, src, ha="center", va="center", color="white", fontsize=7,
                style="italic")
    save(fig, "Fig 28 Business Impact Dashboard.png")


def fig29_roadmap():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 29: Challenges and Limitations Roadmap",
            ha="center", fontsize=10, weight="bold")
    items = ["Reward\ndesign", "Exploration\n483/500", "Single-node\nscale",
             "Overhead\n~60% waste", "M8 0.20\nno winner", "AQE-on\nno gain 0/6"]
    for i, title in enumerate(items):
        _block(ax, 0.15 + i * 1.64, 2.0, 1.5, 1.2, title, "",
               color="#b03a2e")
    save(fig, "Fig 29 Challenges and Limitations Roadmap.png")


def fig30_future():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 30: Future Research Roadmap",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.4, 2.9, 1.1, "Near: size-aware state,\nF3 lock, backfill", "",
           color="#2e7d32")
    _block(ax, 3.55, 2.4, 2.9, 1.1, "Mid: multi-agent,\nfederated, cluster",
           "", color="#ef6c00")
    _block(ax, 6.8, 2.4, 2.9, 1.1, "Long: LLM tuning,\ncognitive eng.", "",
           color="#6a1b9a")
    for x0, y0, x1, y1 in [(3.2, 2.95, 3.55, 2.95), (6.45, 2.95, 6.8, 2.95)]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=1.4))
    save(fig, "Fig 30 Future Research Roadmap.png")


def fig31_nextgen():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 31: Next-Generation Autonomous Analytics Ecosystem",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 1.0, 2.8, 2.4, 1.0, "LLM proposes", "configs")
    _block(ax, 3.8, 2.8, 2.4, 1.0, "RL adjudicates", "measurement",
           color="#b03a2e")
    _block(ax, 6.6, 2.8, 2.4, 1.0, "Loop learns", "bounded",
           color="#2e7d32")
    _block(ax, 2.5, 1.2, 5.0, 0.9, "Measurement stays the authority", "",
           color="#1f4e79")
    save(fig, "Fig 31 Next-Generation Autonomous Analytics Ecosystem.png")


def fig32_contribution():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Figure 32: Research Contribution Framework",
            ha="center", fontsize=10, weight="bold")
    _block(ax, 0.3, 2.4, 2.9, 1.1, "Governed loop\n(C1-C5, C8)", "",
           color="#1f4e79")
    _block(ax, 3.55, 2.4, 2.9, 1.1, "Measurements\n(C6-C7)", "",
           color="#2e7d32")
    _block(ax, 6.8, 2.4, 2.9, 1.1, "Honest bounds\n(M8, H2/H3)", "",
           color="#b03a2e")
    save(fig, "Fig 32 Research Contribution Framework.png")


if __name__ == "__main__":
    fig01_evolution()
    fig02_ecosystem()
    fig03_challenges()
    fig04_taxonomy()
    fig05_requirements()
    fig06_core()
    fig07_loop()
    fig08_spark()
    fig09_rl_workflow()
    fig10_agent()
    fig11_allocation()
    fig12_scheduling()
    fig13_selftuning()
    fig14_lifecycle()
    fig15_explainable()
    fig16_decision()
    fig17_monitoring()
    fig18_governance()
    fig19_testbed()
    fig20_eval()
    fig25_reliability()
    fig26_manufacturing()
    fig27_finance()
    fig28_dashboard()
    fig29_roadmap()
    fig30_future()
    fig31_nextgen()
    fig32_contribution()
