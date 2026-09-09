# Architecture Candidates — A/B/C vs 8 Criteria

*AdaSpark · Day 11 · source: `docs/PLAN.md` §9 (candidate headers) + §31 Day-11 task row · frozen problem `docs/RESEARCH_PROBLEM.md` · gap `docs/research/RESEARCH_GAP.md` · tiers `docs/research/NOVELTY_TIERING.md`*

> **Status:** candidate evaluation and selection for implementation. NOT an experimental result. Empirical performance is determined later by EXP-001…EXP-012.

## 0. Source fidelity note (Step 1 finding)

PLAN.md §9 line 97 gives the three candidate column headers verbatim (A: Offline surrogate (grid/BO → static config) | B: Pure online RL | C: Hybrid offline-init + online adapt + cache (SELECTED)). The §31 Day-11 row requires "A/B/C vs 8 criteria (DEC)" with a "criteria table" deliverable. **PLAN.md does not enumerate the eight criteria as text anywhere** (verified by full-text search for "criteri*": only SC definitions, the line-97 table, and the Day-11 row match). Per the Day-11 instruction, this ambiguity is reported rather than silently resolved: **§5 derives the eight criteria from explicit frozen constraints, citing the exact PLAN line(s) behind each, and labels the unweighted 1–5 scoring as a Day-11 evaluation convention.** No frozen criterion was replaced because none was specified.

## 1. Requirements

The architecture must enable the frozen study without changing it:

- Answer RQ0–RQ6 with H1–H4 tested by EXP-001…EXP-012 (+EXP-005b AQE sub-condition); preserve SC1–SC8.
- Run on the frozen backend (DEC-007): native Windows local mode, PySpark 3.5.9, Python 3.11.9, Java 17, winutils shim, single 32 GB / 24-core node; GPU excluded.
- Respect hard constraints: AQE-off main study (§7); ≤500 cached training executions (§11, §23); 12-action space (§7, §21); v1.5 state (§7); T_ref from EXP-002 (§11); frozen unseen test set, no test access before Day 31 (§23); 5 seeded reps + Wilcoxon/Cliff's δ/Holm (§22); monitoring overhead ≤5% (§20); reproducibility ±5% (§33); timelines ≤10 s–10 min per job (§11).
- Reuse the Day-3 foundation: `SparkConfig` (+`configs/spark.yaml`), session layer, runner (warmup/timeout/fingerprint), timing harness, baseline workload, result structures, `experiments/registry.csv`.
- Degrade to Plan B (§39 tier 3: bandit-mode, 4 actions, benchmark framing) without rewrite if the EXP-002 gate fails.

## 2. Candidate A — Offline surrogate (grid/BO → static config)

Collect Spark measurements first (e.g., sensitivity grid + BO/surrogate search over the knob space), fit a performance model, emit **one static configuration** (per workload family at best). No meaningful online learning during future executions; deployment = lookup of the precomputed config. Literature family: C1–C5, C7, E1/CherryPick, J2/SMAC. MAPE-K reading: Monitor+Analyze once, Plan frozen, Knowledge = the fitted model.
## 3. Candidate B — Pure online RL

An ε-greedy tabular Q-learning agent starts with no prior knowledge and learns continually from successive live Spark executions: observe workload/runtime state → select a 12-action configuration → execute → measure → reward → update Q. No offline initialization, no T_ref calibration from a prior grid, no execution cache assumed. Literature family: D1/Mao et al., E2/Decima, C6, I2/SkinnerDB. MAPE-K reading: full loop with Plan = online RL learner, Knowledge = Q-table grown from scratch.

## 4. Candidate C — Hybrid offline-init + online adapt + cache (SELECTED — see §10)

Controlled prior measurements (the EXP-002 sensitivity grid) calibrate T_ref and pre-initialize the tabular Q-function; ε-greedy Q-learning then adapts online **within ≤500 cached executions**, reusing cached results instead of re-running identical (state, action) pairs. Day-24 gate before any RL is built (§38). Literature bridge: J2/SMAC-style surrogate/offline knowledge + J1/C7 transfer practice adapted into init, E1 few-trial discipline, I2 regret-budgeted precedent. MAPE-K reading: full loop; Knowledge seeded from the grid, then updated by bounded online Plan.
## 5. Eight Evaluation Criteria (derived — each cites its frozen source)

Scoring convention (Day-11, unweighted, 1–5: 1 = very poor, 2 = weak, 3 = acceptable, 4 = strong, 5 = excellent). PLAN.md specifies no weights, so equal weighting is used and labeled as convention, not frozen text.

| ID | Criterion | Definition | Why it matters | Frozen source |
|---|---|---|---|---|
| K1 | RQ/EXP answerability | Can the architecture execute EXP-002/004/005(+005b)/006/007/008/009/010/011 unchanged and test H1–H4 for SC1–SC8 | Research validity is the selection basis | PLAN §5, §23; RESEARCH_PROBLEM §7/§13/§14 |
| K2 | Sample efficiency under the execution budget | Learning/computation fits ≤500 cached executions, 10 s–10 min/job, single 32 GB node | The existential cost constraint (R2/R8) | PLAN §11, §23, §38 |
| K3 | Experimental control & reproducibility | Train/validation/test separation, frozen policies, seeds, manifests, fingerprints, cache, AQE on/off control, ±5% re-run | Statistical validity + SC7/SC8 | PLAN §22, §23, §33 |
| K4 | Adaptivity to workload drift | Responds to workload/scale/skew change, incl. unseen conditions (H4/SC5) | Core RQ2/RQ3 claim under test | PLAN §2, §6; GAP §2 items 1–3 |
| K5 | Schedule & implementation feasibility | Buildable Days 12–33 on the frozen backend by reusing Day-3 foundation; no forbidden tech | 50-day realism | PLAN §31, §38–§39; DEC-007 |
| K6 | Measurement validity (state/reward/monitoring) | v1.5 state constructible; T_ref-calibrated reward; overhead ≤5%; spill/task-balance observable | RQ1/RQ4/RQ5 + SC6/SC8 depend on it | PLAN §7, §11, §20 |
| K7 | Risk & fallback (Plan-B recoverability) | Degrades to benchmark/bandit framing without rewrite if gate/learning/generalization fails | Protects the minimum viable contribution | PLAN §38–§39; RISK R2/R8 |
| K8 | AQE/baseline comparability | Supports 5–7 baselines incl. rule + equal-budget random, AQE-off main + AQE-on EXP-005b | RQ2/RQ6 + H2/H3 require it | PLAN §7, §21–§23 |

## 6. Candidate Comparison Matrix

| Criterion | A (offline/static) | B (pure online RL) | C (hybrid + cache) | Evidence / rationale |
|---|---|---|---|---|
| K1 answerability | 3 — runs EXP-002/005/011, but no policy-learning EXPs (004/007/008 meaningless); H2–H4 untestable | 4 — runs all EXPs in principle, but cold start corrupts EXP-004 budget semantics and T_ref is uncalibrated | 5 — every EXP meaningful as frozen: grid → T_ref/init (002) → bounded training (004) → comparison (005/005b) → generalization (006/010) → ablations (007/008) → overhead/repro (009/011) | §23 protocol; §14 traceability |
| K2 sample efficiency | 4 — one search cost, cheap deployment; but search itself unbounded without cache discipline | 2 — cold-start Q-learning pays full live executions per update; deep-RL precedent needs thousands of trials (D1); infeasible-at-scale warning (C7) | 5 — offline init + cache reuse directly implements the ≤500 bound; few-trial discipline (E1) + surrogate practice (J2) + regret budget (I2) | §11/§23; GAP §1 items 6, 9 |
| K3 control/repro | 4 — static artifact trivially reproducible; but no frozen *policy* to version across workloads | 3 — stochastic cold start, uncalibrated T_ref undermines reward comparability; no-seed control harder | 5 — cache keys + fingerprints + manifests + frozen Q-tables + AQE flag version the full learning trace; test set untouched to Day 31 | §22/§23/§33; configs/spark.yaml AQE flag |
| K4 adaptivity | 2 — static config goes stale under drift (the MAPE-K motivation, §2); per-family lookup is not learning | 5 — continual learning is maximally adaptive in principle | 4 — bounded adaptation within budget; less open-ended than B, but adaptation is what is actually tested (RQ2/RQ3) | §2; RQ2/RQ3 |
| K5 feasibility | 5 — simplest to build (grid + BO + lookup) | 3 — RL loop + reward/state plumbing with no reuse of grid outputs; highest tuning/debugging load before Day 33 | 4 — reuses grid outputs as init (one pipeline, two phases); Day-3 runner/session/config reused; gated so RL never starts if gate fails | §31/§38; src/sparkrl/spark/*, workloads/baseline |
| K6 measurement | 3 — needs timing only; no state/reward/monitoring loop required (weak RQ1/RQ4 coverage) | 4 — full loop required but T_ref uncalibrated at start distorts R2/R3 rewards; overhead risk highest | 5 — T_ref calibrated from EXP-002 before any reward is computed; v1.5 state + event-log monitoring + ≤5% overhead all designed into the loop | §7/§11/§20 |
| K7 fallback | 3 — IS effectively the fallback (static-per-family = Plan-B-adjacent), but as primary it concedes RQ2–RQ4 upfront | 2 — failure modes (no sensitivity / instability / budget exhaustion) leave no artifact; rewrite to benchmark framing required | 5 — gate-gated: gate fail → grid + static/rule analysis IS the Plan-B contribution with zero rewrite; budget guard + cache + 4-action shrink pre-designed (§39 tier 3) | §38–§39; RISK R2/R8 |
| K8 baselines/AQE | 3 — comparable as one more static arm, but cannot test policy-vs-heuristic learning claims or AQE complementarity of learning | 4 — comparable, but uncalibrated cold start handicaps the RL arm unfairly vs equal-budget random | 5 — RL arm, rule heuristic, equal-budget random, statics, AQE-off main + AQE-on 005b all executable under identical manifests/seeds | §7/§21–§23 |

Totals (unweighted, convention): **A = 27 · B = 27 · C = 38.** Scores are ordinal decision aids, not measurements.
## 7. Experimental Compatibility (frozen EXPs unchanged?)

| EXP | A offline/static | B pure online | C hybrid + cache |
|---|---|---|---|
| 002 sensitivity grid (SC1 gate) | Yes — the grid IS the method | Partial — grid runs but T_ref/init unused; gate cannot calibrate learning | Yes — grid proves sensitivity AND calibrates T_ref AND pre-initializes Q |
| 004 RL training ≤500 (SC6) | N/A — no training exists | Strained — cold start spends budget learning what the grid could supply | Yes — budget semantics designed around cache + init |
| 005 main comparison (+equal-budget random) | Weak — static arm only; H2/H3 untestable | Yes in form, handicapped (uncalibrated start) | Yes — all 5–7 arms, identical protocol |
| 005b AQE-on | Static-vs-AQE only; no learning×AQE interaction | Yes but confounded by cold start | Yes — learned-policy × AQE isolated |
| 006/010 generalization (H4/SC5) | No policy to freeze/transfer | Policy exists, provenance unclear | Yes — frozen Q-table + manifests transferred |
| 007/008 ablations (A1–A5) | Meaningless — nothing to ablate | Possible but uninterpretable | Yes — variants differ against identical init |
| 009 overhead ≤5% | Trivially passes — uninformative | Highest risk (unbounded live loop) | Yes — monitoring + cache-hit path costed |
| 011 reproducibility ±5% | Yes (static) | Weakest (cold-start variance) | Yes — manifests replay cached traces |

No EXP definition is changed. Candidates making an EXP meaningless/strained score down.
## 8. Plan-B Compatibility

- A: Plan-B-adjacent by construction (static-per-family), but as primary it concedes RQ2–RQ4 without testing them — a scope surrender, not a fallback.
- B: poorest fallback. Gate fail / instability / budget exhaustion each strand sunk RL plumbing with no reportable artifact, requiring reframing under schedule pressure.
- C: fallback designed in. The EXP-002 grid + static/rule/random analysis is independently reportable (§39); 4-action/bandit shrink, multi-step drop, ablation narrowing are pre-authorized tiers needing no rewrite. Caching + manifests keep even negative results reproducible.

## 9. Risk Comparison

| Risk (PLAN §38) | A | B | C + mitigation |
|---|---|---|---|
| R2 insensitivity (killer) | Absorbs it but wastes the study | Fatal late (after RL built) | Gated Day 23–24: RL never starts; grid becomes the contribution |
| R8 RL underperformance | Never tries | Fully realized, no artifact | Bounded loss: init + baselines still answer RQ2 negatively with statistics |
| Budget overrun (≤500) | Search unbounded unless capped | Highest exposure (update = live run) | Cache + guard enforce the bound structurally |
| Reward/state misspecification | Untested (no loop) | Found late, expensively | T_ref calibration + A1–A5 ablations isolate it early |
| Schedule (RL by Day 33) | No risk, no reward | Highest build/debug load | Phased: grid (23–24) → env/agent (25–29) → demo (33) |
## 10. Recommended Architecture

**RECOMMENDED: Candidate C — Hybrid offline-init + online adapt + cache — selected for implementation (provisional, pending Day-12 contracts).**

Why selected: the only candidate scoring ≥4 on all eight criteria — every frozen EXP meaningful unchanged, the ≤500 budget enforced structurally, T_ref calibrated before any reward, Plan B a pre-designed operating point. Best fit for the research design under the criteria (not an empirical superiority claim; EXP-004/005 decide performance).

Why A rejected: cannot answer RQ1–RQ4 (no policy/state/reward, no learning×AQE interaction); concedes the core questions untested.
Why B rejected: most adaptive in principle, weakest where the study is most constrained — uncalibrated rewards, full live cost per update, cold-start variance vs equal-budget baselines, no graceful fallback.
Main trade-offs: bounded (not open-ended) adaptation; two-phase complexity vs A's simplicity; cache correctness becomes load-bearing.
Main risks: gate fail (→ Plan-B benchmark, handled); cache non-determinism (→ fingerprints + manifests + EXP-011); reward shaping errors (→ R3 primary + A3–A5 ablations).
Fallback: pre-authorized tiers (12→4 actions, drop multi-step/LinUCB, narrow ablations), grid + baseline evidence intact.
## 11. Decision Summary

Day-11 deliverable (PLAN §31 row 11: "criteria table" + DEC) is this document plus DEC-008 in DECISIONS.md. The hybrid was already named SELECTED in frozen §9/§44; Day 11 independently re-derives that selection from the eight criteria rather than inheriting it on authority — pre-selection and criteria evaluation agree.

## 12. Open Questions for Day 12

Exact Q-table schema + grid→init mapping; cache key + hit/miss semantics; v1.5 state vector spec + event→feature mapping; action→SparkConf table (12 actions); R3 reward inputs (T_ref store, spill/imbalance terms); budget-guard/cache interplay; AQE on/off surface; manifest/fingerprint formats; baseline harness interfaces; seed policy; test-set access guard.

# Architectural Invariants (hold regardless of candidate)

Single-node local mode (DEC-007) · reproducible execution (seeds, manifests) · configuration-driven operation (no hard-coded hyperparameters) · measurable state (context + runtime feedback) · bounded 12-action space · explicit T_ref-calibrated reward interface · budget guard (≤500) · cacheability (deterministic keys, fingerprints) · baseline comparability (identical protocol/seeds) · AQE control (off main, on 005b) · frozen test set untouched before Day 31 · ±5% re-run reproducibility + green tests · Plan-B recoverability (grid reportable, 4-action/bandit shrink w/o rewrite) · no cluster/K8s/cloud/microservices, no deep RL, no GPU in Spark path.

# Architecture Change Control

After the Day 11/12 freeze, substantive changes need a DECISIONS.md entry: previous design, new design, reason, affected EXP-ids, affected docs, migration impact. Editorial clarifications need only a commit note.
