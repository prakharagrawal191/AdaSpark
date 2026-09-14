# DEC-016 Draft — EXP-005 Baseline Specifications, TEST Scope and Arm Count

> **Status.** **APPROVED (OPERATOR) — DEC-018 Decision D, 2026-09-14.**
> **NO SUPERVISOR REVIEWED THIS DOCUMENT.** DEC-018 Decision A converted the
> self-imposed supervisor gate into an operator decision and recorded the
> absence of supervisor review permanently. Decisions A–F stand as recorded in
> `DECISIONS.md`.
> Prepared: Day-32 baseline specification audit, HEAD `061bc3e`.
> Revised: Day-32 governance reconciliation, HEAD `1367fcc` — restructured into
> six separately approvable decisions (A–F), Decision E added, and the AQE
> question narrowed on the evidence.
> This is a DRAFT. It is NOT in `DECISIONS.md`, carries no signature, selects no
> option, and authorizes nothing. It proposes NO value for any undefined research
> constant. Spark executions during the audits that produced it: **0**.

---

## Why this draft exists

EXP-005 requires a full strategy set. Three strategies — B0', B3 and B4 — have
**no implementation anywhere in `src/`**, and the `BaselineStrategy` interface
that `ARCHITECTURE_FREEZE.md:66` specifies is unimplemented too. Auditing what
the repository actually defines surfaced six distinct questions. Three of them
cannot be closed by writing code, because the missing pieces are research
choices, not engineering details.

DEC-015 records that B0'/B3/B4 are unimplemented. This draft is narrower: it is
about their **specifications**, the **TEST execution scope**, and the **arm
count** — not their absence.

Each decision below is separately approvable. They are deliberately not collapsed
into one statement, because they have different owners, different evidence, and
different consequences if refused.

---

## Decision A — B0' identity

**Two frozen documents define B0' differently.**

| Source | Definition |
|---|---|
| `docs/PLAN.md:152` | "AQE-on default — Spark 3.x factory default (AQE enabled) — modern default + RQ6" |
| `docs/architecture/ARCHITECTURE_FREEZE.md:66` | "B0' **static-tuned EXP-003**" |
| `docs/architecture/ARCHITECTURE_FREEZE.md:88` | EXP-003 produces "validation-split statics (**B0'**/B1/B2)" |

These are different baselines, not two phrasings of one. Two further documents
side with PLAN: `docs/BASELINE_B0.md:37` ("a separate comparison condition (B0',
RQ6, EXP-005b)") and `docs/research/DAY17_BASELINE_AUDIT.md:38` ("condition
(B0', EXP-005b), not part of B0"). Seen from the EXP-003 side, the same conflict
appears: EXP-003's register line (`PLAN.md:310`) lists its strategies as
"B0,B1,B2" and does **not** mention B0'; `ARCHITECTURE_FREEZE.md:88` does.

**DEC-010's precedence rule already governs this**: PLAN governs where a derived
Day-12 document contradicts it. On that rule B0' is the AQE-on factory default,
and ARCHITECTURE_FREEZE:66/:88 are superseded on this point.

**Supervisor action:** confirm that DEC-010's precedence rule is intended to
resolve this, or state the contrary. No new constant is required either way.

---

## Decision B — B3 specification

`docs/PLAN.md:155` is the ONLY definition of the B3 baseline in the repository:

> `| B3 | Rule-based adaptive | partitions = clamp(input_GB x k, 16, 128);`
> `core-count rule for parallelism | the key "is RL needed?" baseline |`

`ARCHITECTURE_FREEZE.md:66` adds only the label "B3 rule heuristic". No formula,
constant or rule appears anywhere else.

*(The many `B3` entries in `docs/LITERATURE_MATRIX.md` are a literature entry ID
— the SkewTune paper — and are unrelated to this baseline. They must not be
mistaken for a specification.)*

| Item | Status |
|---|---|
| `input_GB` definition | `UNDEFINED` |
| `input_GB` measurement source / artifact | `UNDEFINED` |
| `input_GB` unit conversion | `UNDEFINED` |
| `input_GB` available pre-execution? | `UNDEFINED` |
| `k` value | `UNDEFINED` |
| `k` provenance / derivation | `UNDEFINED` |
| `k` scope (global vs per-family) | `UNDEFINED` |
| `k` tunability / calibration split | `UNDEFINED` |
| clamp target parameter | `UNDEFINED` |
| clamp bounds 16 / 128 meaning | partially implied, `UNDEFINED` as stated |
| parallelism rule | `UNDEFINED` |
| core-count definition | `UNDEFINED` |
| core-count source | `UNDEFINED` |

The clamp bounds 16 and 128 do coincide with the frozen shuffle-partition action
levels {16, 32, 64, 128} (`PLAN.md:127`), so the clamp plausibly targets
`spark.sql.shuffle.partitions` — but the repository never states this, and this
draft does not assert it.

**B3 is the baseline PLAN itself calls "the key 'is RL needed?' baseline", and
SC3 (`RESEARCH_PROBLEM.md:305`) gates on RL vs B3.** Choosing `k` or the
parallelism rule now — from hardware, from EXP-002, from B1, from observed
performance, or from general Spark practice — would be a research constant
invented *after* the RL results already exist. **No value is proposed here, and
no option is enumerated, because any option offered would itself be that
constant.**

**Supervisor action:** supply the undefined items; or amend PLAN to redefine B3;
or drop B3 and record the consequence for SC3.

---

## Decision C — B4 specification

| Source | Text |
|---|---|
| `docs/PLAN.md:156` | "Random search — uniform over the same 12 actions, same budget as RL — 'is it just exploration?'" |
| `ARCHITECTURE_FREEZE.md:66` | "B4 equal-budget random"; "Random strategies draw from the Orchestrator RNG stream (seeded, logged)" |

| Property | Status |
|---|---|
| 12-action domain | `DEFINED` — the frozen grid |
| RNG source | `DEFINED` — seeded orchestrator stream |
| "same budget as RL" referent | `UNDEFINED` |
| budget unit (executions? episodes?) | `UNDEFINED` |
| budget value | `UNDEFINED` |
| draw occurs per execution? | `UNDEFINED` |
| may actions be compared across a search? | `UNDEFINED` |
| may a best-found action be selected? | `UNDEFINED` |
| does any selection/tuning occur? | `UNDEFINED` |
| when B4 becomes frozen | `UNDEFINED` |

**DEC-015 makes the budget referent mathematically ambiguous.** The RL component
is now three arms of **84**, **49** and **42** episodes. "Same budget as RL" no
longer denotes a single quantity: it could mean SC6's 500-execution training cap,
any one of 84/49/42, their mean, their maximum, or a per-instance evaluation
budget. The ambiguity did not exist when the RL component was a single arm.

The second question is the research-critical one: if B4 searches within a budget
and then commits to its best-found configuration, "best" must be judged on some
measurement — which would reintroduce a tuning step, and that step's split would
have to be specified. If B4 instead draws once per measured run, no such step
exists. PLAN's wording ("random *search*") does not settle it.

**Supervisor action:** define the budget referent, the selection rule, and
whether B4's configuration is frozen before TEST.

---

## Decision D — the seven-instance TEST scope

`docs/PLAN.md:278` and `:312` scope EXP-005 to **7 instances**, and the
arithmetic is self-consistent: 7 instances x 7 strategies x 5 repetitions = 245,
matching the register's "~245".

The frozen TEST identity (`results/evaluation/test_freeze.json`, Day 31)
enumerates **43 cells**. `PLAN.md:163` additionally describes TEST conceptually
as including "a public dataset" and "F5 with unseen parameters", neither of which
is among those 43 enumerated family x scale x seed cells.

`NO AUTHORITATIVE 7-INSTANCE MAPPING` — no document states which 7 of the 43 are
EXP-005's instances, nor defines what an "instance" is. A mapping table cannot be
built from repository evidence, and none is invented here.

**Supervisor action:** define which TEST identities constitute the 7 instances,
and how an instance is defined.

---

## Decision E — EXP-005 arm count: 9 in effect, 7 in PLAN

DEC-015 (signed) constitutes the RL component as three arms, making the EXP-005
strategy set **nine**: B0, B0', B1, B2, B3, B4, RL-s0, RL-s1, RL-s2.

`docs/PLAN.md` still reads **7** in both places that state it:

- `:278` — "7 instances x **7 strategies** x 5 reps"
- `:312` — "RL vs B0,B0',B1,B2,B3,B4" with "~245"

`PLAN STRATEGY-COUNT CONFLICT`. DEC-015 records that the line-312 wording is
superseded by decision rather than by a PLAN edit, and DEC-014 carries the same
note inline. PLAN itself is unchanged and this draft does not change it.

**Supervisor action:** confirm that the 9-arm scope stands on DEC-015 alone, or
direct a PLAN amendment. `PLAN AMENDMENT REQUIRED AFTER SUPERVISOR DECISION` if
the latter.

---

## Decision F — implementation scheduling

| Work | Scheduled day | Explicitly scheduled? |
|---|---|---|
| B0 calibration | Day 17 | Yes — "Baseline calibration; B0 default runs" |
| B1/B2 selection | Day 31 | Yes — "Eval harness + B1/B2" |
| **B0' implementation** | — | **No** |
| **B3 implementation** | — | **No** |
| **B4 implementation** | — | **No** |
| **`BaselineStrategy` interface** | — | **No** (specified at `ARCHITECTURE_FREEZE.md:66`, unimplemented) |

Day 32 is "EXP-005 main comparison — queue completes"; it consumes the
strategies, it does not build them. `PLAN SCHEDULING GAP`.

All four items are implementable **without Spark and without opening TEST** —
they are configuration-selection rules, unit-testable against fixtures exactly as
the Day-31 harness was. Nothing here requires a real execution until EXP-005
itself runs.

**Supervisor action:** allocate these to a day explicitly, or fold them into
Day 32's scope in writing. No day number is proposed here.

---

## Resolved by this audit — the AQE role (formerly an open question)

The earlier revision of this draft raised, as an open question, whether an AQE-on
baseline belongs inside an AQE-off main study. On the evidence it is
**EXPLICITLY INTENDED**, and the question is withdrawn:

- `PLAN.md:72` states the experimental contribution as "controlled, seeded,
  statistically tested comparison across 5–7 baselines incl.
  random-search-equal-budget **and AQE-on/off conditions**".
- `PLAN.md:77` fixes AQE off **for the main study** so that *pre-execution
  configuration selection is well-defined* — a constraint on strategies that
  choose configurations, not a prohibition on an AQE-on reference point.
- `PLAN.md:152` gives B0' the role "modern default + RQ6", and `:312` lists it in
  EXP-005.
- EXP-005b (Day 38, `PLAN.md:284`) remains the full AQE-on **condition** — all
  strategies under AQE-on — which is a different scope from a single AQE-on
  baseline point inside EXP-005.

Decision A therefore narrows to the identity contradiction alone.

---

## Relationship to DEC-014, and sequencing

DEC-014 authorizes **TEST execution and its final scope**. DEC-016 defines the
**strategies and the design scope** that such an execution would run. They are
separate concerns and no content is moved between them here.

**DEC-014 cannot be soundly approved before Decisions D and E**, because its
execution scope depends on both:

`DEC-014 REQUIRES AMENDMENT BEFORE APPROVAL`

Its Option A currently reads "43 frozen TEST cells, 7 strategies, 5 repetitions,
~245 runs". Those statements are mutually incompatible: 43 x 7 x 5 = **1505**,
not 245. The "~245" figure requires **7 instances**, not 43 cells. DEC-014's
inline DEC-015 amendment correctly updates the strategy count (7 to 9) and the
projection (~245 to ~315, as 9/7 x 245), but that amendment inherits the same
premise — 43 x 9 x 5 = **1935**, not 315. The conflation of "43 frozen cells"
with "7 instances" is therefore still live, and the two readings differ by
roughly **6x** in TEST executions.

This is a scope defect, not an arithmetic blunder: DEC-014's cost model is
internally consistent *with a 7-instance scope*, and its cell count is
internally consistent *with the frozen TEST identity*. What is missing is
Decision D, which connects them.

---

## Supervisor decision matrix

| Question | Current state | Decision needed |
|---|---|---|
| A — B0' identity | contradictory across PLAN and ARCHITECTURE_FREEZE | confirm DEC-010 precedence resolves it |
| A2 — AQE role | **EXPLICITLY INTENDED** (`PLAN.md:72/77/152/312`) | none — resolved by this audit |
| B — B3 `input_GB` | `UNDEFINED` | define |
| B — B3 `k` (value, provenance, scope, tunability) | `UNDEFINED` | define |
| B — B3 clamp target | `UNDEFINED` | define |
| B — B3 parallelism / core-count rule | `UNDEFINED` | define |
| C — B4 budget referent, unit and value | `UNDEFINED` (ambiguous since DEC-015) | define |
| C — B4 selection rule and freeze point | `UNDEFINED` | define |
| D — TEST 7-instance mapping | `NO AUTHORITATIVE MAPPING` | define |
| E — EXP-005 arm count | 9 in effect (DEC-015), 7 in PLAN | reconcile; PLAN amendment if directed |
| F — implementation scheduling | absent for B0'/B3/B4 and `BaselineStrategy` | allocate explicitly |
| DEC-014 run scope | internally inconsistent (43 cells vs 7 instances) | amend before approval |

No invented values appear in this matrix, and none is offered as a
recommendation.

---

## Constraints this draft does not touch

TEST remains sealed. B1/B2 remain frozen. RL-s0/s1/s2 remain frozen and
published. `configs/rl.yaml`, the split guards, the reward, the StateVector,
gamma and all training code are untouched. `docs/PLAN.md` is unmodified. DEC-014's
approval status is unchanged. No approval is fabricated.

**Status.** **APPROVED (OPERATOR) — DEC-018 Decision D, 2026-09-14.** Decisions
A–F are recorded in `DECISIONS.md`. **NO SUPERVISOR REVIEWED THIS DOCUMENT**;
DEC-018 Decision A converted the self-imposed supervisor gate into an operator
decision and recorded that absence permanently.

*(The paragraph above this line describes the document's state before DEC-018 and
is retained as history, not rewritten.)*
