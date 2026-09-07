# Configuration

Configuration-driven execution (approved plan §36): no experiment parameters are
hard-coded in source.

- `spark.yaml` — Spark runtime defaults (consumed by `sparkrl.spark.session` from Day 3).
- Per-experiment configs live in `experiments/EXP-xxx.yaml` (created with each experiment).
- RL/training/reward configs (`rl.yaml`, `reward.yaml`) are added at M7/M8 — NOT before the
  Day-24 sensitivity gate passes (approved research constraint).
