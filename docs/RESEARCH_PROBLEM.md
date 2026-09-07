# Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark
## Research Problem Formalization

*AdaSpark · Day 4 of the frozen 50-day plan · authoritative source: `docs/PLAN.md` (frozen)*
*Backend frozen per DEC-007: PySpark 3.5.9 / Java 17 / native Windows local mode.*

> **Status: draft for supervisor review and sign-off (Day 5).** All framing, terminology,
> experiment IDs, hypotheses, and success criteria are taken verbatim from the frozen plan
> (`docs/PLAN.md`) and the experiment register (`experiments/registry.csv`). No new
> objectives, thresholds, or experiment IDs are invented. Where the frozen plan does not
> specify a value, this is flagged explicitly (see §18 "Items requiring confirmation").

---

## 1. Research Context

Big-data workloads continue to grow in volume, complexity, and operator diversity
(joins, aggregations, skew, mixed pipelines). Apache Spark is a de-facto standard
distributed/big-data processing engine on the JVM, exposing a rich SQL and RDD API and
shipping with Adaptive Query Execution (AQE) for a subset of runtime decisions.

However, Spark exposes on the order of two hundred configuration parameters. Default
settings are rarely optimal for a given workload, and the optimal settings shift with
data scale, data skew, and operator mix. Manual/static tuning of these parameters is
per-cluster, per-workload expert labour, and it goes stale as workloads drift. This is the
classic motivation for a **self-adaptive system** (Monitor–Analyze–Plan–Execute–Knowledge,
or "MAPE-K"): the system closes the loop and adjusts its own execution configuration based
on observed workload and runtime conditions.

Reinforcement learning (RL) is a natural fit for such a closed-loop decision task because
it learns a **policy** that maps observed state to configuration decisions, optimised
against a numerical reward derived from measured outcomes, and improves over time. In
this project, RL is used not as a general-purpose tool but as a targeted, sample-efficient
decision mechanism for Spark configuration selection.

*Established context above is distinct from the specific research problem in §2. A
systematic literature survey and gap verification are deferred to Days 6–10 (PLAN.md §5).*

## 2. Problem Statement

**Current situation.** Spark workloads are executed under a fixed (default or statically
tuned) configuration, even though the best configuration depends on workload and runtime
conditions that change.

**Problem.** Static or default Spark configuration selection does not adapt to workload
composition, data scale, or skew, and expert manual tuning does not generalise across
workloads and does not respond to drift.

**Limitation of existing approaches.** Offline Bayesian-optimisation tuners produce a
single static configuration per workload type and do not adapt online; deep-RL proposals
require thousands of executions and cluster-scale resources; and learned optimisers in
relational databases do not operate on Spark configuration. *(Gap to be verified against
the literature matrix, Days 6–10; PLAN.md §2/§5.)*

**Proposed research direction.** Learn, from a strictly limited number of online
executions, a policy π: s → a that maps a compact state s (workload context + runtime
feedback) to a discrete execution-configuration action a, so that a fixed, parameterized
Spark pipeline on a known single-node deployment becomes **self-adaptive**.

**Evaluation requirement.** The learned adaptive strategy must be compared — with
statistical validity and under a bounded training budget — against Spark's default
configuration, a static hand-tuned configuration, and a non-RL rule-based adaptive
heuristic, on both seen and unseen workload conditions, without runtime failure of any
submitted configuration.

The central problem is therefore **whether Spark execution decisions can be adapted based
on workload/runtime conditions using an RL-based strategy, and whether this produces
measurable benefit relative to appropriate baselines.**

*All framing above aligns with PLAN.md §2. The primary measurable objective is median
end-to-end execution time, with task-imbalance and spill waste as secondary indicators
(PLAN.md §1).*

## 3. Research Aim

Determine whether a sample-efficient Reinforcement Learning agent can make a Spark
big-data workload self-adaptive — measurably reducing execution time and improving
resource-efficiency indicators versus static and rule-based configuration strategies —
within the computational budget of a single 32 GB machine.

*(Aligns with PLAN.md §2 "Aim".)*

## 4. Research Objectives

Extracted verbatim from the frozen plan (PLAN.md §4). Every objective is traceable to at
least one experiment in the register.

| ID | Objective | Evidence / Experiment |
|----|-----------|------------------------|
| O1 | Reproducible single-node Spark + Python environment | EXP-001 (noise calibration), EXP-011 (reproducibility); environment reports |
| O2 | Parameterized workload suite (5 families × 3 scales) + seeded synthetic generators | EXP-002, EXP-006, EXP-010 |
| O3 | Monitoring pipeline (event logs + psutil) with a fixed metrics schema | EXP-009 (monitoring overhead) |
| O4 | Configuration-sensitivity grid scan and statistical feasibility gate (Days 23–24) | EXP-002 (SC1 gate) |
| O5 | RL environment + tabular Q-learning agent with offline initialization and execution cache | EXP-004 (training), EXP-007, EXP-008 (ablations) |
| O6 | Main comparison, generalization, ablation, AQE-complementarity, and overhead experiments with statistical validation | EXP-005, EXP-006, EXP-007, EXP-008, EXP-009, EXP-010 |
| O7 | Thesis, verified literature matrix, visualization suite, reproducible repository, presentation, live + backup demo | all experiments; M12–M14 artefacts |

## 5. Main Research Question

**Can an RL-based adaptive strategy select Spark execution configurations based on
workload and runtime conditions, and does this reduce execution time / resource
inefficiency compared with static or default configuration strategies, without exceeding
a practical training budget?**

*(This is the research question that directly investigates the self-adaptive Spark
optimization problem; it maps to the feasibility-gate RQ0 and the main comparison
experiments. Aligns with PLAN.md §2/§3.)*

## 6. Supporting Research Questions

All supporting RQs are taken from the frozen plan (PLAN.md §3). Identifiers EXP-001 …
EXP-012 reference `experiments/registry.csv` and are verified in §14.

| ID | Question | Investigates | Hypothesis | Experiment(s) | Primary metric | Expected evidence |
|----|----------|--------------|------------|----------------|----------------|--------------------|
| RQ0 (gate) | How sensitive is execution time of shuffle/join-heavy workloads to shuffle-partition and parallelism settings on single-node local-mode Spark? | Whether the action space has a meaningful effect (feasibility gate) | H1 | EXP-002 | median execution-time spread across configurations | ≥10% spread on ≥2 workload families |
| RQ1 | Which state representation yields better policies — workload context only, or context + runtime feedback? | Value of runtime feedback in the state | Related (evaluated via H2/H3 outcomes); see confirmation item | EXP-007 (A1/A2) | median execution time, reward | reward/policy-quality comparison between state variants |
| RQ2 | Does the learned policy outperform Spark defaults, static tuning, a data-size rule heuristic, and random search of equal budget? | Whether RL adds measurable benefit over strong non-RL alternatives | H2, H3 | EXP-003, EXP-004, EXP-005 | median execution time | RL ≥ heuristics ≥ default (see H2/H3) |
| RQ3 | Does the policy generalize to unseen data scales, unseen skew profiles, and an external public dataset, and what is the degradation? | Generalization of the learned policy | H4 | EXP-006, EXP-010 | execution time on unseen instances; degradation % | retains ≥50% of seen advantage; never below default (H4) |
| RQ4 | How do reward-function variants and action-space granularity affect learning stability and final policy quality? | Reward and action-space design | Related; see confirmation item | EXP-008 (A3/A4/A5) | learning stability, final policy quality | ablation table shows which design works best |
| RQ5 | What are the training cost (number of Spark executions) and the runtime overhead of the adaptation loop? | Practical feasibility of the adaptive loop | Related to H2/H3/SC6 | EXP-004, EXP-009 | Spark executions used; adaptation overhead % | ≤500 executions; overhead ≤5% (SC6) |
| RQ6 | How does the agent interact with built-in AQE — does it add value on top of AQE-on defaults? | Complementarity of RL with Spark's built-in AQE | Related; see confirmation item | EXP-005b (AQE condition), EXP-002 (AQE-off) | median execution time | RL-on-AQE-off vs AQE-on-default comparison |

*Note on hypotheses: PLAN.md §2 defines H1–H4 covering RQ0, RQ2, and RQ3. RQ1, RQ4, RQ5,
and RQ6 specify *related* hypotheses through their outcomes/evaluation criteria rather
than standalone Hx statements; this is flagged for supervisor confirmation (§18).*

## 7. Hypotheses

All hypotheses are taken verbatim from PLAN.md §2; no thresholds are added beyond those
already present.

### H1 (sensitivity gate)
- **Research Question:** RQ0.
- **Null hypothesis (H1₀):** The action space produces no ≥10% median execution-time
  difference on any shuffle/join-heavy workload family on this hardware.
- **Alternative hypothesis (H1₁):** On shuffle/join-heavy workloads, the action space
  spans ≥10% median execution-time difference on this hardware.
- **Experiment:** EXP-002 (Day 23–24). If H1 is rejected, the pivot path (PLAN.md §39,
  scientific tier) is triggered before any RL is built.
- **Primary metric:** median execution-time spread (min vs max) across configurations,
  per workload family.
- **Expected direction:** a measurable, non-trivial spread (≥10% on ≥2 families) — this is
  the feasibility gate (SC1).

### H2
- **Research Question:** RQ2.
- **Null hypothesis (H2₀):** The trained policy does not reduce median execution time by
  ≥10% versus Spark defaults on at least half of the test workloads.
- **Alternative hypothesis (H2₁):** The trained policy reduces median execution time ≥10%
  versus Spark defaults on at least half of the test workloads (p < 0.05, paired).
- **Experiment:** EXP-004 (training), EXP-005 (main comparison).
- **Primary metric:** median execution time, relative improvement vs default (B0).
- **Expected direction:** ≥10% median reduction on ≥half of test workloads.

### H3
- **Research Question:** RQ2.
- **Null hypothesis (H3₀):** The policy is significantly worse than the rule heuristic
  and/or equal-budget random search, or is never better.
- **Alternative hypothesis (H3₁):** The policy is never significantly worse than, and on
  ≥half of test workloads better than, both the rule-based heuristic and random search of
  equal budget.
- **Experiment:** EXP-005 (RL vs B3 rule heuristic; RL vs B4 random search).
- **Primary metric:** median execution time (paired per workload-instance × seed).
- **Expected direction:** RL ≥ B3 and B4 (never significantly worse; better on ≥half).

### H4
- **Research Question:** RQ3.
- **Null hypothesis (H4₀):** On unseen scale/skew workloads, the policy either falls below
  the default or retains less than 50% of its seen-workload relative advantage.
- **Alternative hypothesis (H4₁):** On unseen scale/skew workloads, the policy retains
  ≥50% of its seen-workload relative advantage and never falls below the default.
- **Experiment:** EXP-006 (generalization), EXP-010 (public-dataset external validity).
- **Primary metric:** execution time on unseen instances; seen-vs-unseen relative
  advantage; degradation %.
- **Expected direction:** retains ≥50% of seen advantage; never below default (SC5).

## 8. Scope

### 8.1 In Scope

Within the approved project boundaries (PLAN.md §7, §14, §16):

- Single-node **local-mode Spark** (`local[N]`) on a fixed machine (native Windows,
  backend frozen by DEC-007).
- A **bounded, discrete action space**: v1 = 12 actions
  (`shuffle.partitions ∈ {16,32,64,128}` × parallelism `local[N] ∈ {2,4,8}`); an optional
  v2 extension (±4 actions: broadcast-threshold and caching) used only for ablations.
  Maximum action space ever used: 16.
- **Tabular / hybrid RL** approach: tabular Q-learning (ε-greedy) as primary; contextual
  bandit (γ=0) as co-primary/fallback; optional SARSA and (stretch) LinUCB. No deep RL.
- **Selected workload families**: aggregation, join, RDD sort/filter, skew join, mixed
  pipeline — 5 families × 3 scales, plus one public dataset for external validity.
- **Reproducible experiments**: seeded, config-driven, immutable manifests, frozen
  train/validation/test split (test frozen until Day 31).
- **Baseline comparison**: against Spark default, AQE-on default, static global, static
  per-family, a rule-based adaptive heuristic, and equal-budget random search.
- **Generalization study** to unseen scale/skew/family/public data.
- **Ablation studies** (A1–A5) on state, reward, and action-space design.
- **Statistical validation** (repetitions, medians, Wilcoxon, effect size, multiplicity
  correction).

### 8.2 Out of Scope

Preserved exclusions (PLAN.md §7, §38):

- **DQN / PPO / any deep RL** (rejected: sample cost ≫ budget; replaced by tabular Q).
- **Multi-node cluster deployment**; **Kubernetes**; YARN; streaming.
- **TB-scale infrastructure / unrealistically large datasets** (use 0.3–3 GB ladder).
- Uncontrolled production deployment; microservices; service layer (FastAPI/Flask).
- Executor-memory / dynamic-allocation tuning and arbitrary JVM/IO knobs (OOM/unmeasurable
  on fixed hardware).
- Multi-objective Pareto optimization; energy/cost modeling (time is the primary objective;
  imbalance + spill are secondary indicators only).

## 9. System Boundary

| Stage | Role | Detail (PLAN.md §8) |
|-------|------|---------------------|
| INPUT | Spark workload | fixed, parameterized pipeline described by a workload manifest (family, scale, skew, seed) |
| OBSERVATION | state characteristics | workload context + (optionally) runtime feedback → discretized state s |
| DECISION | Spark configuration/action | discrete action a (shuffle partitions × parallelism) selected by the policy π(s) |
| EXECUTION | Apache Spark | the workload runs under the chosen configuration on local-mode Spark |
| FEEDBACK | measured performance | end-to-end execution time, task-duration CV, spill; event logs + psutil |
| LEARNING | RL policy | reward computed from feedback; Q-table updated; policy improves over episodes |

**What remains outside the research system:** Spark engine internals (JVM tuning, memory
layout), cluster/resource-manager behaviour, system provisioning, and any change to the
workload itself — workloads are fixed inputs, not adaptive targets. Adaptation is confined
to the choice of execution configuration at the decision stage.

## 10. Assumptions

Only justified assumptions (supported by PLAN.md or DECISIONS.md). Fact vs assumption is
distinguished where relevant.

| ID | Assumption | Why required | How it will be checked |
|----|-----------|--------------|------------------------|
| A-1 | The machine power profile is fixed (plugged in, high-performance) during all timed experiments. | Execution-time comparisons assume stable sustained CPU behaviour (PLAN.md §23 quiet-machine protocol). | Recorded in each run manifest; EXP-001 quantifies noise; offenders flagged |
| A-2 | Background load is constant/negligible enough not to dominate timing variance. | Controlled environment for paired comparisons | Measured (EXP-001 noise calibration); quiet-machine protocol enforced |
| A-3 | The chosen Spark configuration action space is safely applicable on local-mode Spark without OOM or config-invalidity risk. | Action-space safety (PLAN.md §14) | EXP-002 grid; timeout guard converts pathological configs to reward −1 |
| A-4 | Seeded synthetic data generation is reproducible and avoids data leakage across splits. | Internal validity / reproducibility (PLAN.md §18/§27; SC7) | dataset regeneration script + checksums; frozen test split |
| A-5 | Median-of-N repetitions is a valid estimator for structured noise in this environment. | Statistical validity | EXP-001 calibrates N; reported with medians/IQR/CIs |
| A-6 | The winutils 3.3.6 shim is a sufficient Windows compatibility layer for the frozen PySpark 3.5.9 backend. | Correct backend function (DEC-007, DEC-006) | smoke matrix PASS (Day 2); env_check PASS |

Note: A-1/A-2 state the control assumptions that EXP-001 (Day 22) exists to validate; they
are **assumptions to be checked**, not established facts.

## 11. Constraints

| ID | Constraint | Source |
|----|-----------|--------|
| C-1 | **50-day timeline** with day-level schedule | PLAN.md §31 |
| C-2 | **Hardware**: single 32 GB machine, 24 logical cores, local disk | PLAN.md §0 |
| C-3 | **Single-node local Spark** — no cluster | PLAN.md §7 |
| C-4 | **Experiment budget**: ≤ ~1,000 Spark executions total; RL training ≤500 | PLAN.md §0, §16 |
| C-5 | **Runtime variability** handled via warm-up + repetitions + medians | PLAN.md §22/§23 |
| C-6 | **Training cost** bounded (tabular, cache, offline init) | PLAN.md §9/§16 |
| C-7 | **Reproducibility**: pinned env, seeds, manifests, one-command rerun | PLAN.md §27 |
| C-8 | **No deep RL / no new infra** during the project | PLAN.md §7, §38, §44 |
| C-9 | **Backend frozen** per DEC-007 (Python 3.11 / PySpark 3.5.9 / Java 17 / winutils). No further backend changes without re-gating. | DECISIONS.md DEC-007 |
| C-10 | **Frozen split** — test set stays frozen until Day 31 | PLAN.md §7 |

## 12. Research Contribution

Contribution is stated with academically cautious, defensible wording; no "first-ever",
"state-of-the-art", or "revolutionary" claims.

### 12.1 Engineering contribution
A complete, reproducible **AdaSpark** adaptive execution loop (monitor → state → decide →
configure → measure → learn) on top of Apache Spark, with: a config-driven
session/config/runner harness, an event-log-based metrics pipeline, an offline-initialized
tabular Q-learning agent with an execution cache, a resumable experiment runner, and a
reproducible repository. This contributes a *reference implementation* an M.Tech-level
self-adaptive Spark stack.

### 12.2 Experimental contribution
A controlled, seeded, statistically-tested empirical comparison:
- RL-based adaptive configuration selection vs (default, static global, static per-family,
  rule heuristic, random-search-equal-budget, AQE-on).
- across 5 workload families and 3 scales with a frozen unseen test set,
- including a generalization study and ablations.
This provides evidence (not claims) about whether and where sample-efficient RL adaptation
helps on single-node Spark.

### 12.3 Research contribution
The project **investigates** whether sample-efficient tabular/bandit RL can make Spark
configuration selection self-adaptive; it **evaluates** generalized to unseen workload
conditions; and it **empirically compares** RL against strong non-RL heuristics. The
question "does a single RL agent beat a carefully-tuned static rule, or is RL just
exploration?" is answered with data, not assumption.

*Any claims beyond these (e.g., "novelty") are gated by the literature matrix (Day 10,
PLAN.md §5/§6) and are not asserted here.*

## 13. Success Criteria SC1–SC8

Extracted from PLAN.md §2 (success criteria) and §25 (SC5 detail). Where the frozen plan
does not specify a value, it is explicitly marked rather than guessed.

| SC ID | Criterion | Measurement | Evidence | Pass/Fail Condition | Experiment |
|-------|-----------|-------------|----------|---------------------|------------|
| SC1 | H1 sensitivity gate passes | median execution-time spread across configurations, per family | EXP-002 effect-size tables | ≥10% spread on ≥2 workload families | EXP-002 |
| SC2 | H2 accepted statistically | relative median improvement vs default (B0) | Wilcoxon p, effect size | ≥10% reduction on ≥half of test workloads (p<0.05 paired), else H2 not supported | EXP-004, EXP-005 |
| SC3 | H3 accepted: not worse than heuristics | median comparison RL vs B3/B4 | Wilcoxon + effect size | never significantly worse; better on ≥half | EXP-005 |
| SC4 | H3 accepted: better than random search | median comparison RL vs B4 | Wilcoxon + effect size | never significantly worse; better on ≥half | EXP-005 |
| SC5 | H4 accepted: generalization | seen-vs-unseen advantage; degradation % | per-workload table | retains ≥50% of seen advantage; never below default on any unseen instance (PLAN.md §25) | EXP-006, EXP-010 |
| SC6 | Training ≤500 execs; overhead ≤5% | Spark executions used; adaptation overhead % | EXP-004 budget logs; EXP-009 | ≤500 executions AND overhead ≤5% of job time | EXP-004, EXP-009 |
| SC7 | Re-run reproducibility within ±5% median | median execution time on re-run vs original | EXP-011 repro report | within ±5% median | EXP-011 |
| SC8 | Tests green; repo reproducible | unit + integration test status; fresh-clone run | CI-lite report | all unit/integration pass; fresh clone reproduces | ongoing (TEST), EXP-011 |

*Terminology note: the frozen plan's SC2–SC4 are grouped as "H2–H3 accepted statistically"
so SC2–SC4 all map to the H2/H3 experiments; this grouping is preserved verbatim.*

## 14. Research Traceability Matrix

Chain: RQ → Hypothesis → Experiment → Metric → Success Criterion → Report Chapter
(report structure per PLAN.md §34).

| RQ | Objective | Hypothesis | Experiment(s) | Metric | Success Criterion | Report Chapter |
|----|-----------|------------|---------------|--------|-------------------|----------------|
| RQ0 | O4 | H1 | EXP-002 | median execution-time spread | SC1 | Ch.9 (Results) |
| RQ1 | O5 | (see §7 note) | EXP-007 | median time, reward | (SC2/SC3 comparative) | Ch.9 |
| RQ2 | O5, O6 | H2, H3 | EXP-004, EXP-005 | median time, relative improvement | SC2/SC3/SC4 | Ch.9 |
| RQ3 | O2, O6 | H4 | EXP-006, EXP-010 | seen-vs-unseen advantage, degradation | SC5 | Ch.9 |
| RQ4 | O5, O6 | (see §7 note) | EXP-008 | learning stability, policy quality | (comparative) | Ch.9 |
| RQ5 | O5, O6 | (see §7 note) | EXP-004, EXP-009 | execs used; overhead % | SC6 | Ch.9 |
| RQ6 | O6 | (see §7 note) | EXP-005b, EXP-002 | median time (AQE conditions) | (comparative) | Ch.9/Ch.10 |

Reverse check: every major experiment answers a research question — EXP-001 (RQ0-adjacent
noise), EXP-002 (RQ0), EXP-003/004/005 (RQ2), EXP-006/010 (RQ3), EXP-007 (RQ1),
EXP-008 (RQ4), EXP-009 (RQ5), EXP-005b (RQ6), EXP-011 (SC7/repro), EXP-012 (demo). No
register experiment lacks a stated purpose.

<!-- CHUNK4 -->
## 15. Minimum Viable Research Contribution

Protected Plan-B contribution (PLAN.md §39, scope tier). If the full RL path is reduced,
what remains scientifically defensible:

- **Essential experiments retained:** EXP-002 (config-sensitivity study — the evidence
  that the optimization problem is real), EXP-005 (baseline comparison), and EXP-006
  (generalization), run on the same reproducible harness.
- **Defensible claim (Plan-B scope):** *"A tuned bandit/Q policy is shown to statistically
  match-or-beat a carefully-designed rule-based heuristic and to beat Spark defaults on at
  least two workload families, in a fully reproducible single-node setup."*
- Plan B is **not project failure**: the sensitivity study (EXP-002) and the 
  RL-vs-heuristics comparison are a complete, publishable M.Tech contribution even with a
  reduced action space (4 actions) and a bandit-only agent.

## 16. Ideal Final Contribution

The ideal AdaSpark end-state (PLAN.md §44): v1.5 state (workload context + runtime
feedback), 12-action space, cached hybrid offline-init + online Q-learning training, full
ablations A1–A5, generalization + AQE-complementarity studies, a 12-figure visualization
suite, and a 24/24 Definition-of-Done checklist.

**Minimum viable vs ideal** are clearly distinct: MVP = Plan-B scope (§15, 4 actions,
bandit-only, 3 experiments); ideal = full AdaSpark (§16, 12 actions, Q-learning, all
experiments). The ideal is an **aspiration reached only if the schedule and the Day-24
gate allow** — it is not a mandatory scope expansion (PLAN.md §38/§44).

## 17. Threats to Validity

Mitigations are *planned/documented* here; none is claimed to have succeeded yet.

### 17.1 Internal validity
- **Threat:** configuration effects masked by run-to-run noise. *Why:* could hide real
  differences. *Mitigation:* warm-up, repetitions, medians, paired stats (PLAN.md §23).
  *Evidence:* EXP-001 (noise), EXP-005 (paired).
- **Threat:** data leakage across train/validation/test (/ reward leakage into state). 
  *Why:* would overestimate generalization. *Mitigation:* frozen split; T_ref only for
  reward normalization, never in state. *Evidence:* EXP-006/EXP-010.

### 17.2 External validity
- **Threat:** single-machine synthetic results may not generalise to clusters/other data.
  *Why:* narrows claims. *Mitigation:* one public dataset (EXP-010); cautious scope
  wording; single-node framed as a controlled testbed. *Evidence:* EXP-010.

### 17.3 Construct validity
- **Threat:** the reward may not reflect the intended objective (execution time vs proxy
  terms). *Why:* could optimise the wrong thing. *Mitigation:* reward dominated by
  time-normalized term; ablations A3 test reward sensitivity. *Evidence:* EXP-008.

### 17.4 Statistical conclusion validity
- **Threat:** multiple comparisons inflate false positives; non-normality. *Why:* could
  wrongly conclude significance. *Mitigation:* paired Wilcoxon, effect size, Holm
  correction (PLAN.md §22/§33). *Evidence:* EXP-005 analysis.

## 18. Supervisor Sign-Off Checklist

| Status | Item |
|--------|------|
| [ ] | Research problem approved (§2) |
| [ ] | Main RQ approved (§5) |
| [ ] | Supporting RQs approved (§6) |
| [ ] | Objectives approved (§4) |
| [ ] | Hypotheses approved (§7) |
| [ ] | Scope approved (§8) |
| [ ] | System boundary approved (§9) |
| [ ] | SC1–SC8 approved (§13) |
| [ ] | Minimum contribution approved (§15) |
| [ ] | Ideal contribution approved (§16) |
| [ ] | Threats to validity reviewed (§17) |

### Items requiring confirmation
1. **Hypotheses for RQ1/RQ4/RQ5/RQ6 (§6/§7):** PLAN.md defines standalone hypotheses
   (H1–H4) for RQ0/RQ2/RQ3 only; RQ1/RQ4/RQ5/RQ6 have evaluation criteria but no explicit
   Hx. *Not a plan change — an interpretation to confirm.*
2. **SC2–SC4 grouping (§13):** the plan groups SC2–SC4 as "H2–H3 accepted statistically";
   I map SC3/SC4 to the H3 sub-claims (heuristics, random search) as an interpretation.
3. **EXP-005b:** the AQE condition (RQ6) is referenced as EXP-005b in the register but
   no dedicated register row exists (the register lists EXP-005 only). Confirmed as a
   sub-experiment of EXP-005, not a new ID.

*End of research problem formalization.*
<!-- CHUNK3 -->