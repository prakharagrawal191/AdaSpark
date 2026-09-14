# DEC-016 Draft — EXP-005 Baseline Specification Gaps (B0', B3, B4) and the Seven-Instance Scope

> **Status.** **PENDING SUPERVISOR APPROVAL**
> Prepared: Day-32 baseline specification audit, HEAD `061bc3e`.
> This is a DRAFT. It is NOT in `DECISIONS.md`, carries no signature, selects no
> option, and authorizes nothing. It proposes NO value for any undefined research
> constant. Spark executions during the audit that produced it: **0**.

---

## Why this draft exists

EXP-005 (PLAN line 312) requires seven strategies. Three of them — B0', B3 and B4
— have **no implementation anywhere in `src/`**, and the `BaselineStrategy`
interface that ARCHITECTURE_FREEZE line 66 specifies is not implemented either.
Auditing what the repository actually defines for each surfaced five gaps, three
of which cannot be closed by writing code, because the missing pieces are
research choices rather than engineering details.

DEC-015 already records that B0'/B3/B4 are unimplemented. This draft is narrower:
it is about their **specifications**, not their absence.

---

## Gap 1 — B0' is defined two different ways in two frozen documents

| Source | Definition |
|---|---|
| `docs/PLAN.md:152` | "AQE-on default — Spark 3.x factory default (AQE enabled) — modern default + RQ6" |
| `docs/architecture/ARCHITECTURE_FREEZE.md:66` | "B0' **static-tuned EXP-003**" |
| `docs/architecture/ARCHITECTURE_FREEZE.md:88` | EXP-003 produces "validation-split statics (**B0'**/B1/B2)" |

These are not two phrasings of one baseline. One is an AQE-on factory default
tied to RQ6; the other is a validation-tuned static configuration produced by
EXP-003. Two further documents side with PLAN: `docs/BASELINE_B0.md:37` ("a
separate comparison condition (B0', RQ6, EXP-005b)") and
`docs/research/DAY17_BASELINE_AUDIT.md:38` ("condition (B0', EXP-005b), not part
of B0").

**DEC-010's precedence rule already settles which text governs** — PLAN governs
where a derived Day-12 document contradicts it — so B0' is the AQE-on default.
That much may need no new decision. What is NOT settled, and is the actual
question recorded here:

> PLAN line 77 fixes **AQE off for the main study** and assigns AQE-on to
> EXP-005b / RQ6. Yet PLAN line 312 lists B0' among EXP-005's strategies. Is an
> AQE-on baseline inside the AQE-off main comparison intended, or does B0' belong
> only to EXP-005b?

Note the same contradiction seen from the EXP-003 side: EXP-003's register line
(PLAN:310) lists its strategies as "B0,B1,B2" and does not mention B0';
ARCHITECTURE_FREEZE:88 does.

**Requires:** a clarification, not a new constant.

---

## Gap 2 — B3's constant `k` and its parallelism rule are undefined

`docs/PLAN.md:155` is the ONLY definition of the B3 baseline in the repository:

> `| B3 | Rule-based adaptive | partitions = clamp(input_GB x k, 16, 128);`
> `core-count rule for parallelism | the key "is RL needed?" baseline |`

ARCHITECTURE_FREEZE:66 adds only the label "B3 rule heuristic". No formula, no
constant and no rule appears anywhere else.

*(The `B3` entries throughout `docs/LITERATURE_MATRIX.md` are a literature entry
ID — the SkewTune paper — and are unrelated to this baseline. They must not be
mistaken for a specification.)*

`UNDEFINED IN CURRENT PLAN/REPOSITORY`, every item below:

- `k` — its value, its derivation, its source
- whether `k` is global, per-family, or tunable
- whether `k` was meant to be calibrated, and if so on which split
- `input_GB` — which measurement, from which artifact, in which unit
- whether `input_GB` is known **before** execution (B3 must choose a
  configuration pre-execution, as every strategy in this project does)
- the "core-count rule for parallelism" — the rule itself
- what "core count" refers to: physical cores, logical processors, `local[N]`,
  `spark.default.parallelism`, or another quantity

The clamp bounds 16 and 128 do coincide with the frozen shuffle-partition action
levels {16, 32, 64, 128} (PLAN line 127), so the clamp plausibly targets
`spark.sql.shuffle.partitions` — but the repository never states this, and this
draft does not assert it.

**B3 is the baseline PLAN itself calls "the key 'is RL needed?' baseline", and
SC3 (`RESEARCH_PROBLEM.md:305`) gates on RL vs B3.** Choosing `k` or the
parallelism rule now — from hardware, from EXP-002, from B1, from observed
performance, or from general Spark practice — would be a new research choice made
after the RL results already exist. **No value is proposed here.**

**Requires:** a specification decision by the supervisor, or a PLAN amendment.

---

## Gap 3 — B4's budget and selection rule are underspecified

| Source | Text |
|---|---|
| `docs/PLAN.md:156` | "Random search — uniform over the same 12 actions, same budget as RL — 'is it just exploration?'" |
| `ARCHITECTURE_FREEZE.md:66` | "B4 equal-budget random"; "Random strategies draw from the Orchestrator RNG stream (seeded, logged)" |

Specified: the draw is uniform over the frozen 12-action grid, and the RNG source
is the seeded orchestrator stream.

Undefined:

- **"same budget as RL"** — which budget? SC6's 500-execution training cap? The
  episodes the evaluated policy actually trained on (84, 49 and 42 — and these
  now differ per arm under DEC-015)? A per-instance evaluation budget?
- **the selection rule.** "Random *search*" implies spending a budget and then
  using a result. Does B4 draw once per measured run, or search within the budget
  and then commit to its best-found configuration? If the latter, on what
  measurement is "best" judged, and does that reintroduce a tuning step?
- whether B4's configuration is **frozen before TEST**, as every other strategy
  is, or drawn live during evaluation.

DEC-015 sharpens the first question: with three RL arms of differing training
lengths, "same budget as RL" no longer has a single referent.

**Requires:** a specification decision.

---

## Gap 4 — "7 instances" is never mapped to the frozen TEST set

`docs/PLAN.md:278` and `:312` both scope EXP-005 to **7 instances**, and the
arithmetic is self-consistent: 7 instances x 7 strategies x 5 repetitions = 245,
matching the register's "~245".

But the frozen TEST identity (`results/evaluation/test_freeze.json`, Day 31)
enumerates **43 cells**, and PLAN line 163 describes TEST conceptually as "all
families x {L} x seeds{3,4} + F4 skew + public dataset + F5 with unseen
parameters" — which additionally includes a public dataset and an
unseen-parameter F5 variant that are not among the 43 enumerated
family x scale x seed cells.

**No document states which 7 of the 43 are EXP-005's instances, nor how an
"instance" is defined.** `EXP-005 INSTANCE MAPPING UNDEFINED`.

This also makes the pending **DEC-014 internally inconsistent**: its line 91
reads "43 frozen TEST cells, 7 strategies, 5 repetitions, ~245", but
43 x 7 x 5 = 1505, not 245. The ~245 figure requires 7 instances, not 43 cells.
Whichever way this resolves, DEC-014's execution scope needs correcting before it
is signed — the two readings differ by roughly 6x in TEST executions.

**Requires:** a scope definition, and a correction to DEC-014.

---

## Gap 5 — implementation of B0'/B3/B4 is scheduled on no day

| Work | Scheduled day | Explicitly scheduled? |
|---|---|---|
| B0 calibration | Day 17 | Yes — "Baseline calibration; B0 default runs" |
| B1/B2 selection | Day 31 | Yes — "Eval harness + B1/B2" |
| **B0' implementation** | — | **No** |
| **B3 implementation** | — | **No** |
| **B4 implementation** | — | **No** |
| `BaselineStrategy` interface | — | **No** (specified at ARCHITECTURE_FREEZE:66, unimplemented) |

Day 32 is "EXP-005 main comparison — queue completes"; it consumes the
strategies, it does not build them. `PLAN SCHEDULING GAP`.

---

## What the supervisor is asked to decide

1. **B0'** — confirm the PLAN reading (AQE-on default) under DEC-010's precedence
   rule, and state whether B0' belongs in EXP-005 (AQE-off main study) or only in
   EXP-005b / RQ6.
2. **B3** — supply `k`, its scope and derivation, the `input_GB` measurement and
   source, and the core-count parallelism rule; or amend PLAN to redefine B3; or
   drop B3 and record the consequence for SC3.
3. **B4** — define the budget referent, the selection rule, and whether B4's
   configuration is frozen before TEST.
4. **Seven instances** — define which TEST identities constitute the 7, and
   correct DEC-014's execution scope accordingly.
5. **Scheduling** — assign the implementation of B0'/B3/B4 and the
   `BaselineStrategy` interface to a day, or fold them into Day 32's scope
   explicitly.

Options are deliberately not enumerated for items 2 and 3: any option this draft
proposed would itself be a research constant invented after the RL results exist.

---

## Constraints this draft does not touch

TEST remains sealed. B1/B2 remain frozen. RL-s0/s1/s2 remain frozen and
published. `configs/rl.yaml`, the split guards, the reward, the StateVector,
gamma and all training code are untouched. No PLAN file is modified. No approval
is fabricated.

**Status.** **PENDING SUPERVISOR APPROVAL** — no option selected, no constant
proposed, no execution authorized.
