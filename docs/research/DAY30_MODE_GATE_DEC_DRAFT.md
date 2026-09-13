# DAY 30 — MODE GATE DECISION — DEC-011 (DRAFT)

**SIGNED AND ADOPTED on 2026-09-13.** This file is retained as the Day-30
working record of how DEC-011 was reached. The AUTHORITATIVE text now lives
in `DECISIONS.md` as **DEC-011** (approved, option 1 — NO). Where this file
and `DECISIONS.md` differ, `DECISIONS.md` governs.

This file is the proposed text of `DEC-011`, prepared on Day 30 for operator
review. It has **not** been written into `DECISIONS.md`, and nothing in it has
been applied to `docs/PLAN.md`, `configs/`, `src/`, `results/`, or any other
existing file. Day 30 ran **no Spark, no training, no integration suite, and no
git write**; execution budget spent producing this draft: **ZERO**.

**To adopt:** sign §Approval below, then paste everything from the `## DEC-011`
heading to the `**Status.**` line into `DECISIONS.md`, after DEC-010.
**Do not paste this banner.**

Every number below was read from a named artifact; none is hand-typed from
memory. Claims are labelled MEASURED, FROZEN or INFERRED where the distinction
matters.

---

## DEC-011 | 2026-09-13 | Mode gate — multi-step mode NOT enabled; γ stays 0.0 (Day 30)

**Decision.** The Day-30 mode gate resolves **NO**. Multi-step mode is **not
enabled**. `configs/rl.yaml:8` stays `gamma: 0.0` (bandit — the frozen PLAN
default). Ablation **A5** (γ=0 vs γ=0.9 multi-step) is **not run**, and Day 37
executes **A3 + A4 only**. Scope-tier rung 1 under risk R8 — "drop multi-step"
(PLAN §44 line 361; PLAN line 239) — is hereby **consumed**.

**No PASS/FAIL verdict is emitted on the gate itself.** PLAN line 276 froze no
criterion (see *Criterion* below), so a verdict issued today would be a post-hoc
gate. What is recorded is a decision, which is exactly and only what PLAN line
276's success column requires: *"decision recorded"*.

**No code, test, configuration, hyperparameter or stored result is changed under
this decision.** This entry also records a **plan defect** — a frozen gate with
no criterion — so the question cannot recur, in the manner DEC-010 recorded the
missing precedence rule.

**Context.** PLAN line 276 reads, verbatim:
`| 30 | Mode gate decision | multi-step only if stable (DEC) | decision recorded |`.

A YES would turn on, all FROZEN: the multi-step transition model
`s_t = (context, phase_t, feedback)` across 3 pipeline phases and γ = 0.9 in
place of γ = 0 (PLAN line 119); ablation A5, which PLAN line 188 gates as "only
if the Day-30 gate passed"; Day 37's parenthetical "(A5) … multi-step if gated"
(PLAN line 283); and the F5 phase structure, "F5 has 3 natural phases" (PLAN
line 167).

The gate is an **opt-IN**. Bandit γ = 0 is the frozen *default* (PLAN line 119;
verified at `configs/rl.yaml:8`, `gamma: 0.0  # bandit mode (PLAN section 12);
0.9 = multi-step, gated Day 30`). A NO changes no frozen artifact, invalidates
no stored result, and requires no rollback and no code change. The burden of
proof runs one way only — toward enabling.

**Criterion. NOT frozen by PLAN — and deliberately not invented here.** PLAN
line 276 names no metric, no statistic, no threshold, no denominator, no
artifact and no evidence source; its success column is "decision recorded", not
"gate passed". Adjacent rows do carry numbers (line 275 "policies agree ≥70%
(M8)"; line 267 "median CV ≤10%"), which makes the omission conspicuous rather
than stylistic. Across PLAN, "stable/stability/oscillat*" is numeric exactly
once — line 145's **early-stop** rule, "early stop when the greedy policy is
stable for 2 consecutive epochs" — and that rule is a budget-saving heuristic
which three frozen documents pre-emptively forbid reading as stability evidence:
`COMPONENT_CONTRACTS.md` ("a budget-saving heuristic, never evidence of
convergence"), `docs/research/DAY27_TRAINING_LOOP_AUDIT.md` ("it is not a
convergence test"), and `docs/research/DAY28_FIRST_FULL_TRAINING_AUDIT.md`,
which lists "the policy is optimal or stable" among the claims its artifacts do
not support. No derived frozen document supplies the missing number either.

This gap is a **silence in PLAN itself**, not a PLAN-vs-derived-document
contradiction. **DEC-010's precedence rule therefore has nothing to arbitrate
here**, and is not cited as though it does.

**No criterion is fixed retroactively**, because every candidate number already
exists and was observed before any criterion was written down. Two in-project
precedents govern the shape of that answer. Day 29 fixed the missing half of M8
**in writing before any policy was inspected**
(`results/training/analysis/day29_policy_agreement.json`:
`fixed_before_any_policy_was_inspected: true`, and "a denominator chosen after
seeing the policies would be a chosen result"). Day 28, faced with an undefined
"reward trend up", **refused to emit a PASS** and reported descriptives only.
Day 30's phrase is *more* incomplete than M8's — M8 at least froze a metric name
and a threshold — so the same discipline applies a fortiori.

If the operator prefers a criterion on the record rather than a criterion-free
decision, the honest form is **forward-looking**: signed first, applied only to
evidence produced afterwards. The Day-30 brief proposes C1 (bandit-arm
cross-seed greedy-policy agreement ≥ 0.70 over a pre-specified denominator, at
3 agent seeds) / C2 (the per-decision reward multi-step would learn from is
separable above the project's measured per-execution noise floor) / C3
(affordability at ≥ the per-state density bandit already achieved, and physical
executability of the frozen 12-action grid per phase inside one Spark session).
Signed today it still yields NO — C2 has never been measurable and C3 is refuted
by arithmetic and code facts — but that is a consequence, not the ground this
entry rests on.

**Evidence (MEASURED, with sources). This decision rests on NO stability
measurement.** The stability-flavoured numbers are recorded here as *context*,
explicitly not as gate scores:

1. **Cross-run policy agreement (M8, Day 29).** 0.2000 over the pre-specified
   primary denominator `D_all3` — 1 of 5 evidence-bearing states unanimous —
   against the frozen 0.70 threshold; `verdict.status = FAIL`. Variants, labelled
   in the artifact itself as not verdicts: union-of-tables 0.5000 (8 states,
   inflated by the 3 that no run ever visited), visited-by-any 0.2000, pairwise
   mean 0.26666666666666666. Source:
   `results/training/analysis/day29_policy_agreement.json`.
2. **Within-run early stop.** Fired in 3 of the 4 stored training runs
   (42, 49, 42 episodes); the Day-29 seed-0 replicate ran all 12 epochs /
   84 episodes and never triggered (`runs.*.stop_reason`, same artifact).
3. Items 1 and 2 are both stability-flavoured and both frozen-adjacent, and they
   point in **opposite directions**. Both were observed before any criterion
   existed, so whichever one a criterion selected today would determine the
   answer — which is precisely why neither is used as one.
4. **Evidence density behind the 0.2000.** Episodes per evidence-bearing state:
   16.8 (seed 0), 9.8 (seed 1), 8.4 (seed 2). The single unanimous state
   `state-v1.5|agg|S|le0` carries **1 episode per seed**, and its unanimous
   greedy action 8 **was executed by no seed** (the three seeds ran actions 6, 1
   and 0 there), so that argmax rests on the shared frozen EXP-002 Q0 row.
   **0 of 5** evidence-bearing states therefore have a unanimous greedy action
   that every seed actually ran. This is a **density fact about the
   measurement**; it is **not** a verdict on tabular Q-learning.
5. **Cell coverage at 1×** (recomputed from `visit_counts` in the same
   artifact): of the 5 × 12 = 60-cell footprint, seed 0 covered 26 cells, seed 1
   15, seed 2 19; **union 41 (68.3%)** — 19 cells executed by no seed, after 175
   live episodes across 3 seeds.
6. **Measured per-execution reward noise floor: 0.06938622701884167.** Largest
   repeat-execution reward range over an identical (cell, action, config
   fingerprint): `F5_mixed|small|a4`, n = 4, sample sd 0.03374885985397845, with
   **no policy change involved**. Source:
   `results/training/train-a0-d0-20260912T083120Z/analysis/day28_analysis.json`
   (`max_range`, in the block labelled "MEASURED NOISE FLOOR").
7. **Budget ledger, recomputed from all 9 training manifests:** 15 smoke
   (5 runs × 3) + 217 training (42 + 84 + 49 + 42) = **232** of the frozen 500
   spent, **268 remaining**. The Day-29 validator's deliberately conservative
   figure is **238 consumed / ≤262 remaining** (it adds 6 reconstructed
   unledgered test executions). Both are recorded side by side; neither corrects
   the other. Every manifest carries: "in-run only; the env counter is
   per-process. Cross-run SC6 totals are the SUM over manifests, REPORTED not
   enforced (COMP-EXP-11 deferred)". *Caution for future readers:*
   `train-a0-d0-20260912T083120Z/analysis/day28_analysis.json` still carries its
   then-correct ledger of 57 spent / 443 remaining; quoting it would overstate
   headroom by 175.
8. **Artifact integrity re-verified read-only today:** `scripts/validate_day29.py`
   → OVERALL PASS, 24 checks, 24 pass, 0 fail, 0 skip — including check 18,
   "analysis reproducible — analyzer deterministic; temp output == stored
   artifact". That run wrote no artifact and spent no execution budget.
9. **EXP-001 was never executed** — there is no `results/experiments/exp-001`.
   The project therefore has **no independent run-to-run noise profile** (PLAN
   line 308: 20 runs, CV ≤10%), which limits what any stability criterion could
   ever have been resolved against beyond the measured floor in item 6.

**Grounds the decision does rest on** — code facts, arithmetic over frozen
numbers, and the frozen default. None of them depends on an observed policy.

- **Enabling is a build, not a flag.** The learner half already exists and is
  correct: `src/sparkrl/agent/q_learning.py:226,232` implements both the terminal
  target and the bootstrapping target. Nothing else does. The environment cannot
  emit a non-terminal transition (`src/sparkrl/rl/env.py:300-301` —
  `self._episode = None  # bandit mode: episode terminates`, then
  `return state_after, reward.value, True, False, info`); **0 of 232** recorded
  executions have ever reached the bootstrap branch. The frozen state schema has
  no phase field (`src/sparkrl/rl/state.py:36`,
  `SUPPORTED_SCHEMAS = (SCHEMA_V1, SCHEMA_V15)`), and the frozen `q0-exp002/v1`
  init is keyed on state-v1.5 keys — **INFERRED:** PLAN line 119's `s_t` needs a
  new schema version and that Q0 would not transfer to it. No per-phase
  measurement exists: `src/sparkrl/workloads/families.py:223` `F5Mixed.run()`
  executes all three phases in ONE timed call under ONE config and emits phase
  *names* and row counts, not per-phase times. No per-phase normaliser exists:
  `src/sparkrl/rl/tref.py:60`, `TRefStore` is keyed `f"{family}|{scale}"`. A
  per-phase reward would require a new EXP-002-class calibration that PLAN
  schedules on no day and charges to no register line.
- **The repo's own Day-27 warning.** `src/sparkrl/training/loop.py:654-658`,
  written before this gate: using `state_after` as `Transition.next_state` "is
  harmless only because every bandit episode is terminal and never bootstraps; a
  Day-30 multi-step gate would make it a wrong bootstrap target." Yet
  `AgentConfig.from_yaml` validates γ only against
  `FROZEN_GAMMAS = (0.0, 0.9)` (`q_learning.py:55,94`), so a one-token edit to
  `configs/rl.yaml:8` **loads cleanly** and nothing in env, loop, runner or
  validators rejects it. An explicit recorded NO is the control that keeps that
  edit from happening by accident.
- **A frozen-vs-frozen incompatibility.** Per-phase action changes over the
  frozen 12-action grid (`spark.sql.shuffle.partitions ∈ {16,32,64,128}` ×
  execution parallelism `local[N]` + `spark.default.parallelism ∈ {2,4,8}`, PLAN
  line 127) require a **session restart** whenever parallelism changes (PLAN line
  115: "changing parallelism (`local[N]`) ⇒ session restart") — that is 2 of the
  3 config keys the grid sets. But F5 is defined by a JVM-cached intermediate
  "consumed twice" (PLAN line 115; `families.py:223`), and a restart destroys that
  cache. **Both sides are frozen.** Resolving the conflict requires a **PLAN
  amendment**, which is not a Day-30 decision to make.
- **Arithmetic (INFERRED from frozen numbers; decisive independently of any
  policy observation).** One execution per (state, action) per seed at the frozen
  3 seeds costs: **180** at today's 5-state footprint (67% of the 268 remaining);
  **252** on the F5-only reading (5 − 1 + 3 = 7 states — 94% of the remainder,
  leaving 16); **540** on the all-families reading (15 states — 2.01× the
  remainder and 1.08× the entire frozen 500). The nominal 30-state space would
  need 1080 and cannot be covered once per action per seed inside the full 500.
  All of that is n = 1 per cell against the 0.069386 noise floor of Evidence item
  6, while the existing 5-state footprint is still only 68.3% covered after 175
  executions. An A5 arm at Day-29 scale (252) is 84% of EXP-008's ~300-run
  register line (PLAN line 315) or 94% of the training remainder (PLAN line 45,
  SC6 ≤500) — **PLAN states both pots and reconciles neither**.
- **The asymmetry.** Bandit is the frozen default; a NO is pre-authorised (PLAN
  line 361; PLAN line 239 under R8) and is rung 1 of the scope ladder rather than
  a failure state. PLAN's own feasibility table (line 346) already scores
  multi-step Feas 3 / Value 4 / Cplx 3 / Risk 3, amber "gated Day 30".
  `ARCHITECTURE_FREEZE.md` describes Plan-B as "droppable via config selectors
  only — same components, same manifests, no rewrite". *Note that freeze's exact
  scope:* it is a claim about **dropping**, and for dropping it is accurate; it is
  **not** a claim that *enabling* is config-only, and the code facts above show it
  is not.

**No learning claim, in either direction.** Day 29 failing M8 is **not** evidence
that tabular Q-learning cannot work here, and nothing in these artifacts is
evidence that multi-step would fix or worsen anything. M8 measured bandit-mode
cross-seed agreement; nothing in it is phase-related, and no artifact measures
whether agreement responds to state-space size, discount, or evidence density —
only one density regime has ever been run. No frozen hyperparameter is retuned
and no past result is moved by this entry.

**Affected components.** None modified. COMP-RL-07 (state encoder), COMP-RL-09
(environment) and COMP-RL-10 (agent) stay bandit-only as implemented and tested;
`configs/rl.yaml:8` stays `gamma: 0.0`. The multi-step build named under
*Grounds* — new state schema version, non-terminal env path, phase-segmented
execution, per-phase metrics, per-phase T_ref calibration, per-phase reward,
multi-decision loop — is **not** undertaken. COMP-EXP-11 (cache) and COMP-EXP-12
(orchestrator) remain deferred and are untouched by this entry.

**Affected documents.** None modified. PLAN lines 119, 167, 188, 276, 283, 346
and 361 remain as frozen; this entry records how line 276 is discharged and does
not amend it. **Plan defect recorded:** PLAN line 276 freezes a gate
("multi-step only if stable") whose predicate is defined nowhere in PLAN and
nowhere in any derived frozen document. The defect is recorded here, not
corrected — correcting it would be a PLAN amendment, out of scope for a Day-30
decision. `ARCHITECTURE_FREEZE.md` and `COMPONENT_CONTRACTS.md` are unaffected:
their Plan-B "droppable via config selectors" language describes exactly the path
taken. DEC-010 is cited in this entry only to be **set aside as inapplicable**
(see *Criterion*); nothing in DEC-010 is altered.

**Affected experiments.** **A5 is not run** — PLAN line 188 gates it on this gate
passing. **Day 37** executes A3 + A4 only; PLAN line 283's parenthetical "(A5)"
and "multi-step if gated" already anticipate this. **EXP-008** (RQ4, PLAN line
315, ~300 runs) proceeds with A3 + A4 receiving that whole register line rather
than sharing it. The ablation set becomes **A1–A4**; RQ4 is answered by A3
(reward variants) + A4 (action space) only, and the write-up must state that A5
was not run **and why**, making **no claim about what it would have shown**.
EXP-005, EXP-006, EXP-007 and the Day-31 evaluation harness are unaffected —
they evaluate a frozen policy at the frozen default. No stored manifest, policy,
checkpoint or result is invalidated.

**Consequences.** Days 31–37 proceed unchanged at γ = 0.0, with zero unscheduled
build work. Day 30 spends **0** executions; the ledger stays at 232 by manifest
sum (268 remaining) / 238 conservative (≤262 remaining), all of which remains
available to Days 31–37. Scope-ladder rung 1 is consumed; rungs 2–4 (drop LinUCB
→ shrink ablations to A1+A3 → 4-action space) remain available under R8. The
discount dimension of RQ4 is left unexamined **by decision, and that limitation
must be stated as such in the report** — it is not a measured result. Any future
edit that sets `gamma: 0.9` must cite a superseding DEC entry: the config layer
will not stop it, and this entry is the only control that does.

**What would reopen this.** Reopening requires **new evidence or an explicit PLAN
amendment** — never a re-reading of what is already measured.

1. A PLAN amendment resolving the **restart-vs-cache conflict** (for example by
   restricting per-phase actions to `shuffle.partitions` only — itself a change to
   the frozen 12-action grid).
2. **Per-phase T_ref calibration and per-phase metric extraction actually
   existing**, with a named register line paying for them.
3. Budget headroom sufficient for an A5 arm at **≥ the per-state density bandit
   already achieved** (8.4–16.8 episodes per evidence-bearing state) — which first
   requires the operator to settle whether an A5 retrain is charged to SC6's ≤500
   (PLAN line 45) or to EXP-008's ~300 (PLAN line 315). *That conflict is internal
   to PLAN; DEC-010's precedence rule cannot arbitrate it.*
4. A **signed criterion** (C1/C2/C3 or the operator's own), followed by a
   bandit-arm replicate measurement meeting it **on evidence produced after
   signing**.
5. An **explicit operator override** accepting the build as research cost and
   amending PLAN to schedule it — in which case the gate is not "passed", it is
   **superseded**, and must be recorded as such in a new DEC entry.

**What would NOT reopen it:** re-deriving M8 over a different denominator;
adopting the early-stop rule as the stability criterion after the fact; tuning
any frozen hyperparameter to move a past result.

**Open questions carried to the operator with this entry.**
(i) Is a criterion-free decision on frozen-default / scope-tier grounds
acceptable, or should a numeric criterion be pre-specified? PLAN line 276
requires only "decision recorded", so both discharge it; the choice is the
operator's, not an agent's. (ii) Should the DEC record that EXP-001 was never
run, so the project has no independent run-to-run noise profile? *(Recorded
above, Evidence item 9.)* (iii) Are both budget figures recorded side by side?
*(Yes, Evidence item 7; neither constrains this gate.)* (iv) Is one multi-step
episode **1 or 3** live executions against the 500 cap? Undefined in PLAN, and
it changes A5's cost by 3×. (v) Is multi-step all-families (PLAN line 119) or
F5-only (PLAN line 167)? A 2.14× cost difference, also undefined.

**Approval.**

- [ ] **APPROVE — NO.** Multi-step not enabled; γ stays 0.0; A5 not run; no
      PASS/FAIL emitted; plan defect recorded. *(recommended)*
- [ ] **APPROVE with a pre-specified criterion.** Sign C1/C2/C3 (or your own)
      first; apply it only to evidence produced afterwards.
- [ ] **REJECT / escalate** as a plan defect requiring a PLAN amendment before
      Day 31.

Operator signature: ________________________   Date: ______________

Supervisor counter-signature follows the same pending path as the M2 freeze
(`docs/research/M2_FREEZE.md`, "PROVISIONALLY FROZEN — awaiting supervisor
signature"); this entry is the artifact to counter-sign.

**Status.** **SUPERSEDED BY THE SIGNED DEC-011 IN `DECISIONS.md`.** On
signature this becomes: DECIDED — mode gate resolved NO; multi-step not enabled;
γ = 0.0 retained; A5 not run; plan defect recorded; no code, test, configuration,
hyperparameter or stored result changed.
