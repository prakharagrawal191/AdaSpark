# Experiment Register

`registry.csv` lists every planned experiment (IDs EXP-001 … EXP-012) with its research
question and status. Per-experiment YAML configs (`EXP-xxx.yaml`) and result folders
(`results/EXP-xxx/<timestamp>/`) are added when each experiment executes.

Rules (approved plan §35/§37): results are never overwritten; every run writes an
immutable manifest containing git SHA, package versions, seeds, and configuration.
