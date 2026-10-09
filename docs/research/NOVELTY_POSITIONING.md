# Novelty and literature positioning

**Date:** 2026-10-09. **Basis:** the repository's verified literature (`manuscript/references_added.json`,
Crossref-verified 2026-10-02; [`docs/LITERATURE_MATRIX.md`](../LITERATURE_MATRIX.md)) plus web verification
on 2026-10-09 of closely related work that the repository did not cite. Descriptions come from titles,
abstracts and bibliographic records; the full texts were not re-read, so the experimental details of other
work are reported only as their abstracts state them.

## 1. Closest prior work

### Reinforcement learning for Spark configuration (the closest in method)

| Work | What it does | How AdaSpark differs |
|---|---|---|
| Huang, Zhang & Zhai, "A Novel Reinforcement Learning Approach for Spark Configuration Parameter Optimization", *Sensors* 22(15):5930, 2022, [doi:10.3390/s22155930](https://doi.org/10.3390/s22155930) | Modified Q-learning over a neural-network performance model; the abstract reports 47%, 43%, 31% and 45% average improvements over the default configuration on four application types | **Q-learning for Spark tuning is not new.** Their gains are also measured against defaults. AdaSpark uses no surrogate model (it learns from measured runs), has a fixed execution budget, and evaluates against static, heuristic and random-search baselines on a sealed test split |
| Zhang, Xu, Wang & Shen, "An innovative parameter optimization of Spark Streaming based on D3QN with Gaussian process regression", *Mathematical Biosciences and Engineering* 20(8):14464–14486, 2023, [doi:10.3934/mbe.2023647](https://doi.org/10.3934/mbe.2023647) | Dueling double deep Q-network with Gaussian-process regression for Spark Streaming; up to 30.24% improvement | Deep rather than tabular RL, streaming workloads |
| DeepCAT+: low-cost, transferrable online configuration auto-tuning for big-data frameworks, *IEEE TPDS*, 2024, [doi:10.1109/tpds.2024.3459889](https://doi.org/10.1109/tpds.2024.3459889) | Online auto-tuner in the deep-RL line that the case-study report reviews | Large online budgets; AdaSpark studies a bounded tabular learner |

### Bayesian-optimization, search and model-based Spark tuners

| Work | What it does |
|---|---|
| Fekry et al., "To Tune or Not to Tune? In Search of Optimal Configurations for Data Analytics" (Tuneful), KDD 2020, pp. 2494–2504, [doi:10.1145/3394486.3403299](https://doi.org/10.1145/3394486.3403299) | Incremental sensitivity analysis and Bayesian optimization; online, from zero prior knowledge |
| Xin, Hwang & Yu, "LOCAT: Low-Overhead Online Configuration Auto-Tuning of Spark SQL Applications", SIGMOD 2022, [doi:10.1145/3514221.3526157](https://doi.org/10.1145/3514221.3526157) | Low-overhead online tuning of Spark SQL applications |
| Li et al., "Towards General and Efficient Online Tuning for Spark", PVLDB 16(12):3570–3583, 2023, [doi:10.14778/3611540.3611548](https://doi.org/10.14778/3611540.3611548) | Constrained Bayesian optimization with a safe region during real periodic runs; deployed at Tencent (reported 57% memory and 35% CPU savings on 25K production tasks within 20 iterations) |
| Shen et al., "Rover: An Online Spark SQL Tuning Service via Generalized Transfer Learning", KDD 2023, pp. 4800–4812, [arXiv:2302.04046](https://arxiv.org/abs/2302.04046) | Online tuning service with expert-assisted Bayesian optimization and history transfer; reported 50.1% memory savings on 12K real Spark SQL tasks |
| QHB+: accelerated configuration optimization for Spark SQL performance tuning, *IEEE Access*, 2024, [doi:10.1109/access.2024.3391333](https://doi.org/10.1109/access.2024.3391333) | Accelerated configuration search for Spark SQL |
| Yu, Bei & Qian, "Datasize-Aware High Dimensional Configurations Auto-Tuning of In-Memory Cluster Computing" (DAC), ASPLOS 2018, [doi:10.1145/3173162.3173187](https://doi.org/10.1145/3173162.3173187) | Datasize-aware performance model plus a genetic algorithm; a secondary summary reports an average 30.4× speed-up over default configurations |
| CausalConf: datasize-aware configuration auto-tuning for recurring big-data jobs, *IEEE TPDS*, 2025, [doi:10.1109/tpds.2025.3560304](https://doi.org/10.1109/tpds.2025.3560304) | Datasize-aware tuning for recurring jobs |
| ATCS: auto-tuning configurations of big-data frameworks with generative adversarial nets, *IEEE Access*, 2020, [doi:10.1109/access.2020.2979812](https://doi.org/10.1109/access.2020.2979812) | Generative-model-based configuration tuning |
| BestConfig (SoCC 2017, [doi:10.1145/3127479.3128605](https://doi.org/10.1145/3127479.3128605)); CherryPick (NSDI 2017) | General-system and cloud-configuration search |

### Context

- **Database knob tuning:** OtterTune (Van Aken et al., SIGMOD 2017, pp. 1009–1024, doi:10.1145/3035918.3064029
  as given by bibliographic aggregators and the authors' repository); the knob-tuning survey in *IEEE TKDE*
  2023 ([doi:10.1109/tkde.2023.3266893](https://doi.org/10.1109/tkde.2023.3266893)); DOT (PVLDB 2025).
- **Runtime adaptation inside Spark:** Adaptive Query Execution (Spark 3.0, 2020), which re-optimizes
  shuffle partitions, joins and skew at runtime and is on by default in Spark 3.x.
- **Learned query optimization:** Neo (PVLDB 12(11), 2019, [doi:10.14778/3342263.3342644](https://doi.org/10.14778/3342263.3342644)) and
  Bao (SIGMOD 2021, [doi:10.1145/3448016.3452838](https://doi.org/10.1145/3448016.3452838)).

**Two lessons from this literature.** "Faster than the default configuration" is the field's usual and weak
bar: DAC reports 30× and the 2022 Q-learning paper 31–47%. And production online tuners already use
Bayesian optimization with safety constraints. A paper whose headline is "an RL tuner beats Spark defaults"
would not be new.

## 2. What is new in AdaSpark, and what is not

**Defensibly new (narrow, methodological and empirical):**

1. A **pre-registered, A/A-controlled confirmatory evaluation** of an RL Spark tuner on a sealed test split
   against a validation-chosen static configuration, a rule heuristic and equal-budget random search. Its
   recorded result is negative: the policy is 1.22× slower than static tuning (H3 rejected).
2. A **provenance analysis** showing that every test-time choice of the evaluated policy is its offline,
   grid-derived initialization or a tie-break. The gain over defaults is therefore attributable to the
   initialization, not to online learning ([D-NEW-01](../decisions/D-NEW-01_q0_test_time_provenance.md)).
   This is a cautionary finding for any evaluation of initialized learners.
3. A **measurement-method finding:** repeated Spark runs on one machine are serially correlated (lag-1
   autocorrelation +0.58 to +0.89), which falsified the standard √n repetition model on 7 of 7 cells. It is
   reported separately in `docs/report/PAPER_DRAFT_monitoring_overhead.md`.
4. An **identical-configuration control** that exposed a queue-position artifact: identical configurations
   differed by up to 2.16× in a non-randomized comparison, and by a median of 2.0% once interleaved.

**Engineering integration, not novel:** the monitor–analyze–plan–execute loop around Spark, event-log and
psutil monitoring, tabular Q-learning with optimistic and offline initialization, budget guards, and the
governance tooling.

**Known or replicated:** tuned configurations beat defaults by large factors; Q-learning has been applied to
Spark tuning; Bayesian-optimization online tuning works in production; Spark's AQE adapts at runtime.

## 3. Claims the evidence does not support

| Do not claim | Why |
|---|---|
| The first RL or Q-learning approach to Spark tuning | Huang et al. 2022; Zhang et al. 2023; the DeepCAT line |
| RL tunes Spark better than static tuning, a heuristic or random search | H3 rejected: 1.22× and 1.21× slower |
| The 4.0× gain comes from online learning or self-adaptation | Every test-time choice is offline Q₀ or a tie-break (D-NEW-01) |
| A sample-efficient learner found the policy within 500 executions | The evaluated choices come from the 208-attempt grid, outside the cap; online training changed none of them |
| Faster than Spark's defaults, unqualified | B0 is `local[2]` with AQE off; AQE on (the Spark 3.x default) was never compared with RL |
| Adaptive at test time | Evaluation used frozen decisions without feedback history |
| Generalizes to unseen workloads or to real data | SC5 not evaluable; one 20-run pilot month |
| Applies to clusters or production scale | One Windows machine, local mode, inputs of at most about 0.4 GB |
| Pre-registered, unqualified | Internal: committed to this repository, not an external registry; counter-signatures pending |
| Reproducible from a fresh clone | Raw records await the DEC-045 deposit; SC8 rehearsed on the recording machine only |
| Monitoring overhead ≤5% | The sampler only; the event log's pass was not re-established |
| About 3,000 runs were avoidable | A retrospective count; no stopping rule was built |

## 4. The narrowest defensible contribution statement

> We report a controlled, pre-registered single-machine case study of a bounded tabular reinforcement-
> learning controller that selects one of twelve Spark configurations per job. Its frozen policy ran about
> 4× faster than a default baseline but 1.22× slower than a validation-chosen static configuration, and
> every one of its test-time choices turned out to be inherited from its sensitivity-grid initialization or
> a tie-break, so online learning contributed nothing measurable under the evaluation protocol. Repeated
> runs were serially correlated enough to falsify the standard √n repetition model. The contribution is an
> evaluation method and an honest negative result: how to keep "beats defaults" from being mistaken for
> "learns to tune". It is not a new tuning algorithm.

## 5. Suggested positioning

An empirical, negative-result and methodology paper, not an algorithm paper. Title directions that match
the evidence:

- "Beating Defaults Is Not Learning: A Controlled Evaluation of Tabular Reinforcement Learning for Spark
  Configuration Selection"
- "Does Online Reinforcement Learning Tune Spark? A Pre-Registered Single-Machine Study"

The paper is much stronger if the learning-effect experiment E2 in
[D-NEW-02](../decisions/D-NEW-02_learning_effect_and_baseline_experiments.md) is run. Whichever way it
comes out, it turns "online learning contributed nothing measurable under this protocol" into a measured
statement about online learning itself.
