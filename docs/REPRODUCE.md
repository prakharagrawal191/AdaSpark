# Reproducing AdaSpark

This page says what can be reproduced from this repository today, how, and at what cost. It separates
three things that are easy to conflate:

| Tier | What it shows | Needs | Cost |
|---|---|---|---|
| **Integrity** | The committed results are internally consistent and were produced by the analysis code in this checkout | A clone | Seconds, 0 Spark |
| **Re-derivation** | Re-running the frozen analyzers on the recorded raw observations reproduces the committed results | The raw research records (not yet public, see below) | Minutes, 0 Spark |
| **Re-execution** | New Spark runs under the frozen protocols; a replication on your machine, not a re-derivation | Generated datasets, a quiet machine, hours | Hours to days of Spark time |

Absolute runtimes are machine-specific. Every comparison in the study is made within one machine, so a
re-execution elsewhere tests whether the *comparisons* replicate, not whether the seconds match.

## Environment

Tested only on the study machine: Windows 11 (24 logical cores, 31.4 GB RAM), Python 3.11.9, Java 17
(Eclipse Temurin 17.0.20), PySpark 3.5.9 in local mode, and the Hadoop 3.3.6 Windows binaries
(`winutils.exe`, `hadoop.dll`) under `HADOOP_HOME` (frozen backend, DEC-007;
[`docs/ENVIRONMENT_REPORT.md`](ENVIRONMENT_REPORT.md)). Dependencies are pinned in
[`requirements.txt`](../requirements.txt) and [`requirements-research.txt`](../requirements-research.txt).
Other platforms are untested.

`python scripts/env_check.py` checks a machine and writes nothing; `--write-report` overwrites the study
machine's record and is meant for that machine only.

## What a fresh clone contains

| Present in Git | Not in Git |
|---|---|
| Source, tests, frozen configs, frozen policies (`models/policies/`) | Generated datasets (about 5.1 GB; regenerate them) |
| Committed analysis outputs (`results/evaluation/*.json`) | Raw observations of every study except EXP-002 (`results/experiments/*`) |
| The EXP-002 raw record (`results/experiments/exp-002/`) | Training run records (`results/training/`) |
| Dataset manifests and SHA-256 sums ([`manuscript/datasets/`](../manuscript/datasets/)) | Spark event logs |

The raw records are git-ignored and await the archival deposit decided in DEC-045
([data availability statement](../manuscript/data_availability.md),
[deposit plan](research/SC8_RAW_OBSERVATION_DEPOSIT_PLAN.md)). Until it is published, re-derivation works
only on a machine that holds them. `scripts/sc8_deposit.py install` restores them into a clone from the
deposit archives; it has been rehearsed on the recording machine only
([rehearsal record](research/SC8_DEC045_REHEARSAL.md)).

## Integrity: from a fresh clone

```powershell
python -m pytest tests                                   # core tests; data-gated tests skip with a reason
python scripts/verify_reproducibility.py --integrity-only
```

The test run should end with `0 failed`. On a fresh clone 38 data-gated tests skip, and the summary line
says how many need the raw records (17) and how many need the generated datasets (21).

`--integrity-only` checks, with no raw data:

- each confirmatory artifact (`exp013_analysis.json`, `exp014_analysis.json`) against its own content hash;
- the analysis-code digests recorded in those artifacts against the code in this checkout (LF-normalised,
  DEC-037 §4), and that no deviation was recorded;
- the three frozen RL policies against their recorded fingerprints (`models/policies/exp005_rl_arms.json`);
- the EXP-002 sensitivity gate, re-derived from its committed raw record.

## Re-derivation: needs the raw records

```powershell
python scripts/verify_reproducibility.py
```

This runs the integrity checks plus, with 0 Spark executions:

- **L1:** every raw ledger matches the SHA-256 that its analysis artifact declares.
- **L2:** every committed analyzer re-derives its artifact. It is compared byte for byte where possible, and
  otherwise after excluding the fields that cannot match by construction (timestamps, the EXP-007 checkout
  path, embedded hashes). EXP-005, which never had an analyzer, gets a descriptive re-derivation instead.
  EXP-013 and EXP-014 are re-derived in memory through their analyzers' own `analyze()`.
- **L3:** the committed artifacts are unchanged by the run.

On the recording machine this reports 25 of 25 checks passing. A missing raw record is reported as a FAIL
that names the file: a deleted record must never pass.

## Re-execution: new Spark runs

1. Generate the datasets: `python scripts/generate_dataset_matrix.py` (all 30, about 5.1 GB; the disk
   check wants about 40 GiB free for the full matrix and about 1.2 GiB for one small dataset). Each
   regenerated `manifest.json` should reproduce the `generation_fingerprint`, `schema_fingerprint` and
   `checksum` recorded under [`manuscript/datasets/manifests/`](../manuscript/datasets/manifests/).
2. Dry-run a driver; for example `python scripts/run_exp013.py --plan` prints the frozen queue with 0 Spark
   executions and no writes. Most drivers follow `--plan` / `--run --allow-spark`; `run_exp002.py` uses
   `--dry-run`. Check each script's `--help`.
3. Execute under the quiet-machine protocol (mains power, high-performance plan, no sync or other heavy
   load; DEC-053 §7). Raw observations go to `results/experiments/<study>/`, which is git-ignored.
4. Analyze with the matching `scripts/analyze_*.py`. These write into `results/evaluation/` and replace the
   committed artifact, so compare with `git diff`.

Running anything that writes training manifests (`scripts/run_training.py`, or the live-Spark integration
tests with `SPARKRL_ALLOW_SPARK=1`) spends the training budget recorded in that checkout's
`results/training/`. In the study's own checkout that ledger is the governed SC6 record (DEC-037).

## Status by study

| Study | Integrity from a clone | Re-derivation | Re-execution | Notes |
|---|---|---|---|---|
| EXP-002 sensitivity grid | Yes (raw record committed) | Yes, from a clone | `scripts/run_exp002.py`, about 2.7 h | Source of the offline Q₀ |
| EXP-004 training (three seeds) | Policy fingerprints | Needs `results/training/` | `scripts/run_training.py --agent-seed N` | Spends training budget |
| EXP-005 first comparison | — | Needs raw records | `scripts/run_exp005.py` | Descriptive; superseded by EXP-013 |
| EXP-006 generalization | — | Needs raw records | `scripts/run_exp006.py` | SC5 not evaluable |
| EXP-007 / EXP-008 ablations | — | EXP-007 needs raw records; EXP-008 is derived | EXP-007 via the training loop | |
| EXP-009 overhead (4,842 runs) | — | Needs raw records | `scripts/run_exp009.py`, `run_exp009_ext.py`; 57 h elapsed | |
| EXP-013 confirmatory evaluation | Yes | Needs raw records | `scripts/run_exp013.py`; about 10 h | Headline H2/H3 result |
| EXP-014 overhead confirmation | Yes | Needs raw records | `scripts/run_exp014.py`; about 4.8 h | |
| Q₀ provenance analysis | — | Needs generated datasets only | `scripts/analyze_q0_provenance.py`, 0 Spark | See [D-NEW-01](decisions/D-NEW-01_q0_test_time_provenance.md) |
| X1–X3, X6, X8, X9, X10 pilots | Committed analyses only (X6, X9, X10) | Raw records not in Git | **No driver in this repository** | Pilot evidence only; X9 also needs the public NYC TLC month `yellow_tripdata_2023-01.parquet` |
| EXP-012 demo | — | — | `scripts/demo.py --mode live --allow-spark` | 5 training-split runs |
| Compute accounting (54 h of Spark) | — | Local event logs only | — | Not reproducible from the repository |

## Seeds, identities and fingerprints

| Item | Value | Where it is pinned |
|---|---|---|
| Dataset seeds and skew | seeds 0–4; Zipf skew 1.0 (F1, F2, F3, F5), 1.5 (F4) | `configs/datagen.yaml`, `manuscript/datasets/` |
| Split rule | test = family F4, scale large, or seed 4; validation = seed 3 | `sparkrl.experiments.spec.split_of` |
| Frozen test identity | 43 cells, artifact `699e98df…` | `results/evaluation/test_freeze.json` |
| Training seeds | agent seeds 0, 1, 2 on dataset seed 0 | `configs/rl.yaml`, `models/policies/exp005_rl_arms.json` |
| EXP-013 queue | 900 entries, block seed 20261001, fingerprint `fe159085…` | DEC-053; pinned by `tests/unit/test_exp013.py` |
| EXP-014 queue | 270 runs, seed 20261002, fingerprint `709d2024…` | DEC-054; pinned by `tests/unit/test_exp014.py` |
| Bootstrap intervals | 4,000 resamples, seed 0 | the analyzers (their code digests are recorded in the artifacts) |

## Execution accounting: the 500-execution budget versus the whole study

The training budget (success criterion SC6) caps executions on the **training split**. It is not the cost
of the study, and it is not the cost of the policy that was evaluated.

| Component | Purpose | Split | Executions | Counted in the 500 cap |
|---|---|---|---:|---|
| EXP-002 sensitivity grid | H1 gate, reference times, **source of Q₀** | training (+ default reference) | 208 (+39 in a discarded first pass) | No |
| EXP-003 B1/B2 selection | Tune the static baselines | validation | 96 | No |
| B4 random-search calibration | Random-search baseline | training | 84 | Yes |
| EXP-001 noise calibration | Noise band ±11.89% | training | 20 | Yes |
| RL training (Day 28–29) | First run + three seeds (+15 smoke runs) | training | 232 | Yes |
| EXP-007 state ablation | Ablation training | training | 126 | Yes |
| Accidental smoke executions | Charged and disclosed, never deleted (DEC-033, DEC-038) | training | 21 | Yes |
| EXP-012 demo rehearsal | Live demo | training | 5 | Disclosed on its own line (488 combined) |
| EXP-005, EXP-006, X6, X8, X10 | Test-split studies and pilots | test | 245 + 132 + 35 + 10 + 20 queue entries | No |
| EXP-013 | Confirmatory H2/H3 | test | 808 executed of 900 queued | No |
| EXP-009, EXP-014, X1–X3 | Overhead studies and confirmations | validation | 4,959 + 270 + 19 | No |
| X9 | NYC Taxi pilot | external data | 20 | No |

The charged total is 232 + 84 + 20 + 126 + 21 = **483 of 500**; `scripts/validate_day31.py` check 22
recomputes it. About 6,900 further executions ran on other ledger lines. Online training (232 executions)
changed none of the evaluated policy's test-time choices, which all come from the EXP-002-derived Q₀ or a
tie-break ([D-NEW-01](decisions/D-NEW-01_q0_test_time_provenance.md)). Timings per study and per day are in
[`docs/PROJECT_HISTORY.md`](PROJECT_HISTORY.md).

## Planned reproduction tooling that was not built

The frozen plan (`docs/PLAN.md` §27) promised `scripts/run_experiment.py`, `scripts/reproduce_all.sh`, this
walkthrough, and a `results/EXP-XXX/<timestamp>/` layout. This page is the walkthrough. The study instead
used one frozen driver and one pre-registered analyzer per experiment, with results under
`results/experiments/<study>/`; no one-command reproduction exists. Amending the frozen plan is an owner
decision ([D-NEW-04](decisions/D-NEW-04_reproduction_plan_and_registry.md)). The experiment register
[`experiments/registry.csv`](../experiments/registry.csv) is the original plan register (EXP-001 to EXP-012
as planned); current statuses are in [`docs/research/CLAIM_EXPERIMENT_MAP.md`](research/CLAIM_EXPERIMENT_MAP.md).
