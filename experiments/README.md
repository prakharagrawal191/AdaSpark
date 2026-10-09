# Experiment Register

`registry.csv` is the **original plan register**: it lists the experiments planned in `docs/PLAN.md`
(EXP-001 … EXP-012) with their research questions, and every status in it still reads "planned". It is
kept as frozen at planning and is not a status ledger. It has no rows for the later confirmatory studies
(EXP-013, EXP-014) or the X-family pilots.

Current status of every experiment and claim: [`docs/research/CLAIM_EXPERIMENT_MAP.md`](../docs/research/CLAIM_EXPERIMENT_MAP.md).
How each study is reproduced, and at what cost: [`docs/REPRODUCE.md`](../docs/REPRODUCE.md).

As built, each study has a frozen driver (`scripts/run_exp*.py`) and a pre-registered analyzer
(`scripts/analyze_exp*.py`). Raw observations are written to `results/experiments/<study>/` (git-ignored,
pending the DEC-045 deposit) and analyses to `results/evaluation/`. The plan's `results/EXP-xxx/<timestamp>/`
layout and per-experiment YAML files were not adopted, apart from `exp002.yaml`. Whether to amend the plan
or update this register is an owner decision ([D-NEW-04](../docs/decisions/D-NEW-04_reproduction_plan_and_registry.md)).

Rule kept from the plan (§35/§37): results are never overwritten, and every run writes an immutable
manifest with the git SHA, package versions, seeds and configuration.
