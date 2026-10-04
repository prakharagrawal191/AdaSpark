# AdaSpark — Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark

M.Tech research project. **Status:** experiments EXP-001 to EXP-014 are reported in the case-study
report (`manuscript/AdaSpark_CaseStudy_Report.docx`); every scope and verdict decision is in
`DECISIONS.md` (DEC-001 to DEC-055).

An RL agent observes workload context and Spark runtime feedback, selects an execution
configuration (shuffle partitions, execution parallelism) before each run, and learns from
the measured outcome. The learned policy is compared, with statistical validation, against
Spark defaults, static tuning, a rule-based heuristic, and random search — on multiple
synthetic workload families plus one public dataset, on single-node local-mode Spark.

## Repository layout

```
src/sparkrl/        package: spark/ datagen/ workloads/ monitoring/ env/ agent/ runner/ analysis/ utils/
scripts/            env_check.py (Day 1); runners/trainers/eval scripts from Day 3+
configs/            cross-cutting configuration (spark.yaml, later rl.yaml, reward.yaml)
experiments/        experiment registry (registry.csv) + per-experiment YAML configs
data/ results/ logs/ plots/   generated artifacts (bulk data lives OUTSIDE the repo — see below)
tests/              unit/ integration/ system/ fixtures/
docs/               ENVIRONMENT_REPORT.md, DECISIONS.md, report/, figures/, decisions/
models/policies/    trained policy checkpoints (small JSONs, committed)
notebooks/          analysis/EDA only — core logic always lives in src/
```

## Setup (Windows 11 · Python 3.11.9 · Java 17 · PySpark 3.5.9 — frozen Day 2, DEC-007)

The virtual environment intentionally lives **outside** this repository, because the repo
sits in a OneDrive-synced folder (see `docs/DECISIONS.md`, DEC-001/DEC-002). The Day-1
Python 3.12 / PySpark 4.0.4 environment (`%USERPROFILE%\sparkrl_env`) is kept for
forensics but is **not** the project backend (DEC-006/DEC-007).

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -m venv "$env:USERPROFILE\sparkrl_env311"
& "$env:USERPROFILE\sparkrl_env311\Scripts\Activate.ps1"
pip install -r requirements.txt
pip install -e . --no-deps
```

Bulk data (datasets, Spark event logs, Spark temp) is written to
`%USERPROFILE%\sparkrl_data` by default. Override the location with the
`SPARKRL_DATA_ROOT` environment variable. No absolute paths are hard-coded in code.

## Verify the environment

```powershell
python scripts/env_check.py     # regenerates docs/ENVIRONMENT_REPORT.md + environment_report.json
```

## Run the tests

```powershell
python -m pytest -m unit          # fast, no Spark required
python -m pytest -m integration   # local-mode Spark smoke tests (PySpark required)
```

## Day-3 timing harness (M5 foundation)

The reusable session/config/runner stack lives in `src/sparkrl/spark/` and the
deterministic baseline workload in `src/sparkrl/workloads/baseline.py`. Validate timing
stability (target: warm CV < 10%):

```powershell
python scripts/run_smoke_warm.py --config configs/spark.yaml
```

Output: `results/validation/day03_timing.json` + `.csv` (labelled validation data, not
research findings). Design details: `docs/day03_timing_harness.md`.

## Research gates (must not be violated)

- No RL implementation before the Day-24 configuration-sensitivity gate (EXP-002) passes.
- No deep RL (DQN/PPO), no multi-node clusters, no Kubernetes — approved exclusions.
- AQE is OFF in the main study; AQE-on is a separate comparison condition (EXP-005b).
- The full approved planning document is committed as `docs/PLAN.md` (Day 2).

## Contributors

- [@prakharagrawal191](https://github.com/prakharagrawal191) — author and maintainer
