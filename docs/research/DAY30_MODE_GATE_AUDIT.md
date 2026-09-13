# Day 30 - Mode Gate Decision Audit

> **Day 30 · Status: COMPLETE · Gate state: DECIDED (DEC-011 signed 2026-09-13)
> · Type: decision day (PLAN line 276) · Execution budget spent: ZERO**
> Authority: `docs/PLAN.md` line 276 (`| 30 | Mode gate decision | multi-step
> only if stable (DEC) | decision recorded |`), section 12 line 119 (transition
> model and gamma), section 19 line 167 (F5 phase structure), section 24 line 188
> (ablation A5), line 283 (Day 37), lines 239/361 (risk R8 scope tier),
> line 346 (feasibility table); `DECISIONS.md` DEC-010 (precedence rule);
> Day-28 and Day-29 audits and their machine-readable artifacts.
>
> **Recommended decision (DRAFTED, NOT SIGNED): NO - multi-step mode is not
> enabled; `gamma` stays 0.0; ablation A5 is not run; NO PASS/FAIL verdict is
> emitted on the gate itself, because PLAN line 276 freezes no criterion.**
> The proposed DEC text lives in `docs/research/DAY30_MODE_GATE_DEC_DRAFT.md`
> (DEC-011, **SIGNED 2026-09-13**, now recorded in `DECISIONS.md`). No
> existing file was modified. No Spark, no training, no integration suite, no
> git write.

## 1. Objective

Execute and document the task named by frozen `docs/PLAN.md` line 276:

```
| 30 | Mode gate decision | multi-step only if stable (DEC) | decision recorded |
```

Day 30 is a **decision day**, not an execution day. Its frozen deliverable is
the string in the success column - **"decision recorded"** - and nothing else.
It runs no training, touches no Spark, and spends none of the frozen 500-run
research budget. This document is the evidence record behind that decision; the
decision text itself is drafted separately and is **unsigned** (section 7).

Nothing here is a claim about learning, convergence, optimality, stability in
general, or the merits of tabular Q-learning. Day 29 failing M8 is **not**
evidence that multi-step mode would fail, and **not** evidence that the method
cannot work. Section 11 states exactly what is and is not claimed.

## 2. What the gate controls (frozen text, with line references)

The gate is a single switch with five frozen consequences. All quotes are
verbatim from `docs/PLAN.md` at HEAD `4bcc01b`.

**PLAN section 12, line 119 - the transition model and the discount:**

> "Transition: bandit mode - s -> terminal (one decision per episode);
> multi-step mode - s_t = (context, phase_t, feedback) across 3 pipeline
> phases. ... Policy = e-greedy over Q. gamma = 0 (bandit, default) or 0.9
> (multi-step, gated Day 30). Update: Q(s,a) <- Q(s,a) + a[r - Q(s,a)]
> (gamma=0) or standard Q-learning with gamma*max_a' Q(s',a')."

**PLAN section 19, line 167 - where the phases come from:**

> "... + phase structure for multi-step mode (F5 has 3 natural phases)."

**PLAN section 24, line 188 - the ablation the gate unlocks:**

> "A5 gamma=0 vs gamma=0.9 multi-step, only if the Day-30 gate passed (RQ4)."

**PLAN line 283 - the day that would run it:**

> `| 37 | Ablations A3, A4 (A5) | reward variants; 4-action; multi-step if gated | ablations complete (M10) |`

**PLAN line 346 - the feasibility row that already scores it:**

> `| Multi-step mode | 3 | 4 | 3 | 3 | gated Day 30 |`

(Value 3 / Feasibility 4 / Complexity 3 / Risk 3, amber - verified by grep; the
only amber-gated RL component in that table.)

**PLAN lines 239 and 361 - a NO is pre-authorized under risk R8:**

> line 239: `| R8 | Timeline overrun | M | H | milestone slip >2 days | day-level plan, buffers D38/40/48-50 | drop multi-step, LinUCB, A5 |`
>
> line 361: "**Scope tier (R8):** drop multi-step -> drop LinUCB -> shrink
> ablations to A1+A3 -> 4-action space."

**The live switch in the repository** is one line, `configs/rl.yaml:8`:

```
gamma: 0.0                 # bandit mode (PLAN section 12); 0.9 = multi-step, gated Day 30
```

**Direction of the gate (FROZEN).** Bandit `gamma = 0` is PLAN's stated
*default*. A NO therefore changes no frozen artifact, invalidates no stored
result, requires no rollback and no code change; a YES turns on new machinery.
The burden of proof runs one way only.

## 3. The criterion, and whether PLAN froze it

**PLAN line 276 freezes no metric, no statistic, no threshold, no denominator,
no artifact and no evidence source.** Its success column is `decision recorded`,
not `gate passed`. The adjacent rows carry numbers, which makes the omission
conspicuous:

| PLAN line | success column |
|---|---|
| 266 (Day 20) | `overhead <=5% (M6)` |
| 267 (Day 21) | `median CV <=10%` |
| 274 (Day 28) | `reward trend up` (no number either) |
| 275 (Day 29) | `policies agree >= 70% (M8)` |
| **276 (Day 30)** | **`decision recorded`** |

**Grep evidence (verified, not asserted).** Case-insensitive
`stable|stability|unstable|oscillat*` occurs in `docs/PLAN.md` on exactly six
lines - 53, 115, 141, 145, 237, 276 - and line 115's hit is inside the word
"broadcastable", i.e. not a stability usage at all. Of the genuine five:

* line 53 - RQ4 prose ("learning stability and final policy quality"), no number;
* line 141 - section 15 reward design ("Stability: clipping; constant step-size
  alpha (noisy rewards); failures capped at -1"), a design note, no number;
* line 145 - section 16, the **only numeric use**: "early stop when the greedy
  policy is stable for 2 consecutive epochs";
* line 237 - risk R6 ("Unstable reward ... oscillating Q (Day 28)"), an early
  warning, no threshold;
* line 276 - the gate itself.

So the only numeric "stable" in the whole plan is the **early-stop rule**, and
three frozen or frozen-adjacent documents pre-emptively forbid reading it as
stability evidence:

* `docs/architecture/COMPONENT_CONTRACTS.md:103` - the early stop is
  "a budget-saving heuristic, never evidence of convergence";
* `docs/research/DAY27_TRAINING_LOOP_AUDIT.md` section 9 - "The rule is a
  budget-saving heuristic over argmax movement; it is not a convergence test";
* `docs/research/DAY28_FIRST_FULL_TRAINING_AUDIT.md` section 16 - lists "The
  policy is **optimal** or **stable**" among the claims the artifacts do NOT
  support.

No derived frozen document supplies the missing number either. Verified counts:
`ARCHITECTURE_FREEZE.md` has **zero** occurrences of the stable/stability family;
`COMPONENT_CONTRACTS.md` has two (line 66, and line 103 which is the disclaimer
above); `DECISIONS.md` has one (line 234, inside DEC-010 quoting PLAN section
15's "failures capped at -1"). A repo-wide grep for Day-30 / mode-gate /
multi-step across `docs/`, `src/`, `scripts/`, `configs/` and `tests/` returns
references to the gate's existence in 14 places and **a criterion in none**.

**Consequence for DEC-010.** The gap is a **silence inside PLAN itself**, not a
PLAN-vs-derived-document contradiction. DEC-010 established which document wins
when the two disagree; here nothing disagrees, so **DEC-010 has nothing to
arbitrate and must not be cited as though it supplied the criterion.**

**The two in-project precedents that govern the shape of the answer.**

1. **Day 29 (the M8 denominator).** PLAN line 275 froze the phrase "policies
   agree >= 70%" and no computation. The missing half was fixed **in writing
   before any policy was inspected** (`scripts/analyze_day29.py`
   PRE_SPECIFICATION; `day29_policy_agreement.json` records
   `fixed_before_any_policy_was_inspected: true`), on the stated ground that
   "a denominator chosen after seeing the policies would be a chosen result."
2. **Day 28 (the reward trend).** Faced with an undefined "reward trend up", the
   audit **refused to emit a PASS** and reported descriptives only:
   "Manufacturing a threshold after seeing the data would be a post-hoc gate,
   and none is invented here."

Day 30's phrase is **more** incomplete than Day 29's - M8 at least froze a metric
name and a threshold - so the same discipline applies a fortiori. A criterion
invented today, over numbers already observed, would select its own answer.

**A forward-looking criterion is offered, not adopted.** The DEC draft carries a
PROPOSED three-part criterion: C1 replicate consistency on the bandit arm at the
only cross-run threshold this project has ever frozen (0.70, PLAN line 275);
C2 per-decision signal separability above the MEASURED per-execution noise floor
0.069386; C3 affordability at or above the per-state density bandit already
achieved. It is **not frozen, not signed, and not applied to any past
measurement.** If signed, it binds only evidence produced afterwards.

## 4. Measured evidence (Day 28 and Day 29, with sources)

Every number in this section was read from a stored artifact; sources are named
inline. **None of it was produced today, and none of it is scored as a gate.**

### 4.1 Frozen numeric criteria and their evaluation status

| criterion | PLAN | status |
|---|---|---|
| H1/SC1 `>=10% spread on >=2 families` | 40 / 45 / 309 | **EVALUATED - PASS**: 4 of 4 evaluable families sensitive (`results/experiments/exp-002/analysis/gate.json`: `families_sensitive = [F1_agg, F2_join, F3_rdd, F5_mixed]`, `n_families_sensitive = 4`, criterion `min_families = 2`) |
| M8 `policies agree >= 70%` | 275 | **EVALUATED - FAIL, 0.2000** (`results/training/analysis/day29_policy_agreement.json`) |
| early stop `stable for 2 consecutive epochs` | 145 | **EVALUATED 4x** - fired in 3 of 4 training runs |
| EXP-001 `run CV <=10%` (20-run noise profile) | 234 / 267 / 308 | **NEVER EXECUTED** - `results/experiments/` contains only `exp-002` and `exp-002-discarded-pass1` |
| SC6 `<=500 training executions` | 45 | holds (section 6) |
| SC2-SC5, SC7, overhead | - | not yet due (Days 31+) |

**Only two frozen numeric gates have ever been evaluated to a verdict on this
project: EXP-002/H1 (PASS) and M8 (FAIL). Neither is the Day-30 gate.**

### 4.2 The sign conflict - why a criterion cannot honestly be picked now

* **Cross-run (Day 29):** M8 = **0.2000**, 1 of 5 evidence-bearing states
  unanimous against a frozen 0.70 threshold, **FAIL**. Variants recorded in the
  same artifact and explicitly not verdicts: union of stored q_tables 0.5000
  (inflated by 3 never-visited Q0-only rows), visited-by-any 0.2000, mean
  pairwise 0.26667. `scripts/validate_day29.py` re-run read-only today:
  **OVERALL PASS, 24/24**, including "analysis reproducible".
* **Within-run (Days 28-29):** the frozen early-stop rule fired in **3 of 4**
  runs (Day-28 seed 0 at 42 episodes; Day-29 seed 1 at 49; Day-29 seed 2 at 42).
  Day-29 seed 0 ran all 12 epochs / 84 episodes and never triggered.

Two frozen-adjacent, stability-flavoured numbers point in **opposite
directions**, and both were observed before any Day-30 criterion existed.
Whichever one a criterion adopted today would decide the gate by itself. That is
precisely the post-hoc construction Day 28 and Day 29 each refused.

### 4.3 Day-29 policy agreement in detail (context, NOT a gate score)

From `day29_policy_agreement.json`, denominator `D_all3` (states visited by all
three runs), greedy argmax over the stored `policy/v1` q_table, ties to the
lowest action index:

| state (D_all3) | s0 | s1 | s2 | unanimous | episodes s0/s1/s2 |
|---|---|---|---|---|---|
| agg\|S\|gt0 | a8 | a6 | a5 | no | 23/13/11 |
| agg\|S\|le0 | a8 | a8 | a8 | **yes** | 1/1/1 |
| join\|S\|gt0 | a4 | a1 | a5 | no | 24/14/12 |
| mixed\|S\|gt0 | a4 | a5 | a9 | no | 24/14/12 |
| rdd_sort\|S\|gt0 | a5 | a4 | a4 | no | 12/7/6 |

**Density note, recomputed today from the episode logs (read-only).** The single
unanimous state `state-v1.5|agg|S|le0` carries **1 episode per seed**, and the
actions actually executed in it were **6 (seed 0), 1 (seed 1), 0 (seed 2)** - so
its unanimous greedy action **a8 was executed by no seed**, and that argmax rests
on the shared frozen EXP-002 Q0 row. Hence **0 of 5** evidence-bearing states
have a unanimous greedy action that every seed actually ran. This is a **density
fact about the measurement**. It is **not** a verdict on tabular Q-learning, and
it is **not** an adjustment to M8 - the denominator is frozen and was not
re-chosen.

### 4.4 Evidence density at the current 1x state space (recomputed, read-only)

* 5 evidence-bearing states, **all** in size bin `|S|`; 8 states in the stored
  tables, 3 of them visited by no run; **25 of the 30 nominal v1.5 states were
  never entered at all**.
* Episodes per evidence-bearing state: seed 0 **16.8**, seed 1 **9.8**, seed 2
  **8.4** (`evidence_density.per_seed`). This is the highest per-state density
  the project has ever reached.
* (state, action) coverage of the 5 x 12 = 60-cell footprint, computed from
  `episodes.jsonl`: seed 0 **26**, seed 1 **15**, seed 2 **19**, **union 41
  (68.3%)** - **19 pairs were executed by no seed** after 175 live executions.
* Median distinct actions tried per (state, seed) pair: **4 of 12**. Exploration
  is concentrated: seed 0 spent 20 of its 24 `join|S|gt0` episodes on one action.
* Size binning aliases `small` and `medium` into `S` although their T_ref values
  differ by up to 8.4x (F2_join 2.214523 s vs 16.126881 s). The run manifests
  carry the consequence verbatim: reward variance driven by which cell ran is
  indistinguishable from within-state noise.

### 4.5 The measured per-execution noise floor

`day28_analysis.json` -> `repeat_execution_spread`: the largest reward range over
repeated executions of an **identical (cell, action, config fingerprint)** is
**0.06938622701884167** (`F5_mixed|small`, action 4, n = 4, sample sd
0.03374885985397845), with **no policy change involved**. For scale,
`F2_join|small` held one action across all six epochs of the Day-28 run and still
produced an OLS slope 68.5% the size of that run's headline slope.

The floor is MEASURED, it applies to a **whole-run** reward, and nothing in the
artifacts suggests it shrinks if that reward is later split across phases.

### 4.6 Wall clock (recomputed from `episodes.jsonl`, read-only)

217 training episodes (42 + 84 + 49 + 42) took **0.973 h** of measured workload
wall time; median 10.53 s, mean 16.15 s per execution. The 175 Day-29 replicate
episodes account for 0.788 h. **Compute time is not the binding constraint on
this project; executions against the frozen 500 cap are.**

## 5. What multi-step would require, and what it would cost

This section is code fact plus arithmetic. Nothing in it was measured today, and
nothing in it depends on any observed policy.

### 5.1 What already exists (FROZEN, verified)

* **The learner half is already correct.** `src/sparkrl/agent/q_learning.py`
  lines 225-233 implement the real bootstrap
  (`target = r + gamma * max_a' Q(s', a')` when `terminated` is False), and
  `FROZEN_GAMMAS = (0.0, 0.9)` (line 55) already admits 0.9.
  `tests/unit/test_rl_agent.py::test_nonterminal_update_bootstraps_with_gamma`
  pins the arithmetic exactly; the file passes on the frozen interpreter
  (11 passed, run today, no Spark).
* **The loop already threads the flag**: `src/sparkrl/training/loop.py:868` takes
  `terminated` from `env.step`, and line 908 puts it on the `Transition`.

**The cost of enabling is not in the Q-update.**

### 5.2 What does not exist (FROZEN code facts, verified)

1. **The environment cannot emit a non-terminal transition.**
   `src/sparkrl/rl/env.py:300-301`:
   `self._episode = None  # bandit mode: episode terminates` /
   `return state_after, reward.value, True, False, info`. The literal `True` is
   unconditional. **0 of the 232 recorded executions ever reached the bootstrap
   branch**, and the test suite pins the current behaviour:
   `tests/unit/test_rl_env.py:128`, `tests/integration/test_rl_env_smoke.py:33`
   and `tests/integration/test_rl_agent_env_smoke.py:34` each assert
   `terminated is True`.
2. **Multi-step is outside the frozen state schema.**
   `src/sparkrl/rl/state.py:36` fixes `SUPPORTED_SCHEMAS = ("state-v1",
   "state-v1.5")`; lines 94-97 and 151-154 raise on anything else, and
   `space_size` (line 127) knows only those two. There is no phase field.
   **INFERRED:** PLAN line 119's `s_t = (context, phase_t, feedback)` needs a new
   schema version, and the frozen `q0-exp002/v1` initialization is keyed on
   state-v1.5 keys, so it would not transfer to phase-augmented keys.
3. **No per-phase reward and no per-phase normalizer exist.**
   `src/sparkrl/workloads/families.py::F5Mixed.run` executes all three phases in
   **one** timed call under **one** configuration and emits phase *names* plus
   row counts (`measurements = {"phases": [...], "phase1_clean_rows": ...,
   "phase2_intermediate_rows": ..., "intermediate_cached": True, ...}`) - no
   per-phase timing anywhere. `src/sparkrl/rl/tref.py:60` keys T_ref by
   `family|scale` only, and `src/sparkrl/rl/reward.py:114` computes the frozen R3
   reward from a whole-run metrics mapping against a whole-run `t_ref`.
   **INFERRED:** a per-phase reward needs a new EXP-002-class calibration,
   charged to no dated line of the PLAN section 33 experiment register.
4. **The execution path is one session per run.**
   `src/sparkrl/experiments/runner.py:298` builds the session and lines 305-306
   stop it in a `finally`. There is no phase-segmented execution path.
5. **A bare config flip would be silently accepted, and would be wrong.** The
   loop's own docstring, written on Day 27 *before* this gate
   (`src/sparkrl/training/loop.py:654-658`): "That is harmless only because every
   bandit episode is terminal and never bootstraps; **a Day-30 multi-step gate
   would make it a wrong bootstrap target.**" `AgentConfig` validates gamma only
   against `FROZEN_GAMMAS` (`q_learning.py:94-95`), so editing `configs/rl.yaml:8`
   to `0.9` **loads cleanly** and nothing in env, loop, runner or validators
   refuses it.

### 5.3 A frozen-vs-frozen incompatibility

The frozen 12-action grid is `spark.sql.shuffle.partitions in {16,32,64,128}` x
execution parallelism (`local[N]` **and** `spark.default.parallelism = N`) -
`src/sparkrl/rl/action.py:5-12`. Two of those three Spark settings are
**builder-time**, and PLAN section 11 (line 115) freezes the consequence:
"changing parallelism (`local[N]`) => session restart". But PLAN section 11 also
defines F5 as the family whose "intermediate [is] consumed twice", and
`F5Mixed.run` implements exactly that with a JVM-side `.cache()` held between
phases 2 and 3.

**A per-phase parallelism change restarts the session; the restart destroys the
cached intermediate that makes F5 the multi-step workload in the first place.
Both sides are frozen.** Resolving it means amending something frozen - for
example restricting per-phase actions to `shuffle.partitions` only, itself a
change to the frozen 12-action grid. **That is a PLAN amendment, not a Day-30
decision.**

### 5.4 The arithmetic (INFERRED from frozen numbers; no policy observed)

Cost of visiting each (state, action) pair **once per seed**, at the frozen 3
seeds:

| reading | states | executions | against the 268 remaining |
|---|---|---|---|
| today's bandit footprint | 5 | 5 x 12 x 3 = **180** | 67% |
| F5-only multi-step (PLAN line 167): 4 states stay bandit, F5's 1 evidence-bearing state splits into 3 phases | 4 + 3 | (4 x 12 x 3) + (3 x 12 x 3) = 144 + 108 = **252** | 94% (16 left) |
| all-families multi-step (PLAN line 119): every state gains a 3-valued phase | 15 | 15 x 12 x 3 = **540** | 201%; also 108% of the entire frozen 500 |
| nominal v1.5 space (30 states), bandit, for comparison | 30 | 30 x 12 x 3 = **1080** | already impossible inside 500 |

That is `n = 1` per cell, against a MEASURED noise floor of **0.069386** - one
sample per cell, where repeats of an identical cell already differ by up to
0.069386 with no policy change at all. And the existing 5-state footprint is only
**68.3% covered after 175 executions across 3 seeds** (section 4.4).

**Two quantities PLAN does not define, both of which move these numbers:**

* whether one multi-step episode counts as **1 or 3** live executions against the
  500 cap - a **3x** swing in A5's cost;
* whether multi-step is **all families** (line 119) or **F5-only** (line 167) - a
  **2.14x** difference (540 vs 252).

**No claim is made that agreement would fall if the state space tripled.** The
arithmetic says only how many executions single-visit coverage costs and how many
remain.

### 5.5 Budget pots PLAN does not reconcile

An A5 arm at Day-29 scale is **252** executions. PLAN line 45 (SC6) caps
*training* at 500; PLAN line 315 gives EXP-008 - which owns A3, A4 and A5 -
roughly **300** runs. 252 is **84%** of EXP-008's line, or **94%** of the
training remainder, and **PLAN states both pots and reconciles neither.** Either
way A3 and A4 are crowded out. **This conflict is internal to PLAN; DEC-010
cannot arbitrate it** (section 3).

## 6. Budget position (recomputed today from all 9 manifests)

Summing `budget.budget_limit_this_run - budget.budget_remaining` over every
`results/training/**/manifest.json`:

| run | kind | live executions |
|---|---|---|
| train-a0-d0-20260912T052836Z | smoke | 3 |
| train-a0-d0-20260912T081149Z | smoke | 3 |
| train-a0-d0-20260912T081451Z | smoke | 3 |
| train-a0-d0-20260912T081737Z | smoke | 3 |
| train-a0-d0-20260912T082054Z | smoke | 3 |
| train-a0-d0-20260912T083120Z (Day 28) | training | 42 |
| train-a0-d0-20260912T112906Z (Day 29, seed 0) | training | 84 |
| train-a1-d0-20260912T115123Z (Day 29, seed 1) | training | 49 |
| train-a2-d0-20260912T120648Z (Day 29, seed 2) | training | 42 |
| **total** | | **232 of 500 spent; 268 remaining** |

The Day-29 audit's deliberately **conservative** figure is **238 consumed /
<= 262 remaining**, adding 6 reconstructed unledgered test executions (a
documented minimum, not an exact audit). **Both are reported side by side;
neither corrects the other.** Neither is near the cap, so the ledger does not by
itself decide the gate - only the *incremental* cost of an A5 arm does
(section 5.4).

Every manifest carries the same enforcement note verbatim: *"in-run only; the env
counter is per-process. Cross-run SC6 totals are the SUM over manifests, REPORTED
not enforced (COMP-EXP-11 deferred)."*

**Stale-figure trap, recorded so it is not repeated:**
`results/training/train-a0-d0-20260912T083120Z/analysis/day28_analysis.json`
still carries its then-correct ledger of **57 spent / 443 remaining**. Quoting it
today overstates headroom by 175 executions. Recompute from the manifests.

**Day 30 spent 0 executions.** The only commands run to produce this document
were read-only greps and artifact reads, `scripts/validate_day29.py` (read-only,
24/24 PASS) and one fast unit-test file (`tests/unit/test_rl_agent.py`, 11
passed, no Spark).

## 7. The decision and its status

### 7.1 The decision as drafted

> **NO - multi-step mode is not enabled.** `configs/rl.yaml:8` stays
> `gamma: 0.0`. Scope-tier rung 1 under risk R8 ("drop multi-step", PLAN line 361
> / line 239) is consumed. **Ablation A5 is not run**; Day 37 executes A3 + A4
> only.
>
> **NO PASS/FAIL verdict is emitted on the gate itself** - the Day-28 route -
> because PLAN line 276 froze no criterion and every candidate number is already
> observed, so a verdict issued today would be a post-hoc gate.
>
> **The plan defect is recorded alongside the decision** - PLAN line 276 freezes
> a gate with no criterion - so the question cannot recur, in the manner DEC-010
> recorded the missing precedence rule.
>
> This satisfies PLAN line 276's actual frozen deliverable: *"decision recorded"*.

### 7.2 What the decision rests on - and what it does not

**It rests on:**

1. **Enabling is a build, not a flag** - a new state schema, a non-terminal env,
   a phase-segmented execution path, per-phase metrics, a per-phase T_ref
   calibration, a per-phase reward and a multi-decision loop. None exists, and
   PLAN schedules none of it on any day (section 5.2).
2. **The repository's own Day-27 warning** that a bare gamma flip produces a
   wrong bootstrap target, together with the fact that the config layer would
   accept that one-token edit silently. An explicit recorded NO is the control
   that keeps it from happening by accident (section 5.2, item 5).
3. **A frozen-vs-frozen incompatibility** - session restart on a parallelism
   change versus F5's cached intermediate - that only a PLAN amendment can
   resolve (section 5.3).
4. **Arithmetic that is decisive independently of any policy observation:**
   252-540 executions for single-visit coverage against 268 remaining, at n = 1
   per cell against a measured 0.069386 noise floor (section 5.4).
5. **The asymmetry** - bandit is the frozen default, a NO invalidates nothing and
   is pre-authorized by R8, while a YES must discharge a burden that nothing in
   the artifacts discharges (section 2).

**It does NOT rest on any stability measurement.** M8 = 0.2000 appears in this
document as **context** (section 4.3), never as a gate score; the early-stop
firing rate appears as **context** (section 4.2), never as a criterion. No frozen
hyperparameter is retuned, and no past result is moved.

### 7.3 Status - SIGNED AND RECORDED (DEC-011, 2026-09-13)

**Day 30 is COMPLETE as analysis. The gate is NOT closed.**

| item | state |
|---|---|
| evidence record (this document) | **COMPLETE** |
| DEC text | **SIGNED**: `DECISIONS.md` DEC-011 (2026-09-13, approved option 1 - NO). Working record retained at `docs/research/DAY30_MODE_GATE_DEC_DRAFT.md` |
| `DECISIONS.md` | **NOT WRITTEN** - no DEC-011 entry exists; the file's last entry is still DEC-010 |
| `docs/PLAN.md`, `docs/architecture/*`, `configs/`, `src/`, `results/`, tests, scripts | **UNCHANGED** - zero existing files modified |
| gate state | **DECIDED** - resolved NO; gamma stays 0.0; A5 not run |
| execution budget spent | **0** |
| git | no write of any kind |

The DEC entry requires operator sign-off that **has not been given**. Until the
operator signs, the recommendation in section 7.1 is a **recommendation**, not a
recorded decision, and PLAN line 276's deliverable ("decision recorded") is
therefore **prepared but not yet discharged**. The draft's sign-off sheet offers
three options: approve NO; approve with a criterion pre-specified **first**
(C1/C2/C3 or the operator's own, applied only to evidence produced afterwards);
or escalate as a plan defect requiring a PLAN amendment before Day 31.

**Open questions the operator must settle** (carried in the draft; restated here
because they bound what this document can conclude):

1. Is a numeric criterion wanted **at all**, or is a criterion-free decision on
   frozen-default / scope-tier grounds acceptable? PLAN line 276 requires only
   "decision recorded", so both satisfy it. This is an operator call, not an
   agent's.
2. If a criterion is wanted, **over what evidence**? The only cross-run
   consistency number that exists (M8 = 0.2000) is bandit-mode and already
   observed; reusing it would violate the discipline the M8 pre-specification
   itself set out.
3. Should the DEC record that **EXP-001 was never run**, so the project has no
   independent run-to-run noise profile against which any stability criterion
   could have been resolved?
4. Record **both** budget figures side by side (232 manifest sum / 238
   conservative)?
5. Record the **plan defect** itself, so the question cannot recur?
6. Is one multi-step episode **1 or 3** live executions against the 500 cap?

## 8. Consequences for Days 31-37 and ablation A5

### 8.1 If the drafted NO is signed

| day / item | effect |
|---|---|
| 31 (eval harness + B1/B2), 32 (EXP-005), 33, 34 (EXP-006), 35 | **Unchanged.** All evaluate a frozen policy at the frozen default. |
| 36 (EXP-007: A1, A2 retrains) | **Unchanged.** Bandit retrains, as already planned. |
| 37 (EXP-008: "A3, A4 (A5)") | **A5 not run.** PLAN's own parenthetical "(A5)" and "multi-step if gated" anticipate exactly this. A3 + A4 receive the whole ~300-run register line instead of sharing it. |
| ablation set | Becomes **A1-A4**. RQ4 is answered by A3 (reward variants) + A4 (action space) only. The write-up must state that A5 was **not run and why**, and must make **no claim about what it would have shown**. |
| scope ladder (R8) | Rung 1 consumed. Rungs 2-4 (drop LinUCB -> shrink to A1+A3 -> 4-action space) remain available. |
| artifacts / code | **Zero changes.** `gamma` stays 0.0; `env.py` stays bandit-only; no manifest, policy or result is invalidated. |
| budget | 268 remaining (232 manifest sum) / <= 262 (conservative) stays available to Days 31-37. |

### 8.2 If a YES is signed instead

| item | effect |
|---|---|
| Days 31-35 | Acquire **unscheduled build work**: new state schema version, non-terminal env, phase-segmented execution path, per-phase metrics, per-phase T_ref calibration, per-phase reward, multi-decision loop. PLAN allocates no day to any of it. |
| before any A5 episode | A **new EXP-002-class per-phase T_ref calibration** must run, charged to a register line PLAN does not name. |
| Day 37 | A5 at Day-29 scale = **252** executions = 84% of EXP-008's ~300 line, or 94% of the training remainder; A3 and A4 are crowded out either way (section 5.5). |
| coverage | n = 1 per (state, action) at best, against a 0.069386 noise floor; episodes per evidence-bearing state fall from today's 8.4-16.8 toward single digits. |
| unresolved before a single episode | 1-vs-3 executions per multi-step episode; all-families vs F5-only; and the restart-vs-cache conflict, which requires changing something frozen. |

## 9. What would reopen the gate

Reopening requires **new evidence or an explicit PLAN amendment** - never a
re-reading of what is already measured.

1. A **PLAN amendment resolving the restart-vs-cache conflict** (section 5.3),
   e.g. restricting per-phase actions to `shuffle.partitions` only - itself a
   change to the frozen 12-action grid.
2. **Per-phase T_ref calibration and per-phase metric extraction actually
   existing**, with a named register line paying for them.
3. **Budget headroom for an A5 arm at or above the per-state density bandit has
   already achieved** - which first requires the operator to settle whether an A5
   retrain is charged to SC6's 500 (PLAN line 45) or EXP-008's ~300 (PLAN
   line 315).
4. A **signed criterion** (C1/C2/C3 or the operator's own), followed by a
   bandit-arm replicate measurement meeting it **on evidence produced after
   signing**.
5. An **explicit operator override** accepting the build as research cost and
   amending the plan to schedule it - in which case the gate is not "passed", it
   is **superseded**, and must be recorded as such.

**What would NOT reopen it:** re-deriving M8 over a different denominator;
adopting the early-stop rule as the stability criterion after the fact; tuning
any frozen hyperparameter to move a past result.

## 10. Limitations (factual only)

1. **PLAN line 276 froze no criterion.** Everything in section 3 is therefore an
   analysis of a *silence*, and the decision is made on frozen-default, code-fact
   and arithmetic grounds rather than against a measured threshold. A different
   operator could legitimately sign a forward-looking criterion instead; PLAN
   permits both.
2. **The decision is unsigned.** No DEC entry exists in `DECISIONS.md`. Nothing
   in this document has force until the operator signs (section 7.3).
3. **No multi-step evidence exists anywhere in this project.** Zero of the 232
   recorded executions were multi-step, no per-phase reward has ever been
   computed, and no phase-aware state has ever been encoded. Every statement
   about what multi-step *would* cost is INFERRED from frozen numbers and code,
   never measured.
4. **The cost arithmetic depends on two undefined quantities** (1-vs-3 executions
   per episode; all-families vs F5-only), which between them span 180 to 540
   executions. The range is reported rather than collapsed to a single figure.
5. **EXP-001 was never run**, so the project has no independent run-to-run noise
   profile. The 0.069386 floor is a by-product of the Day-28 training run
   (repeat executions within identical (cell, action, config) groups), not a
   dedicated noise study.
6. **The evidence behind M8 is thin and single-regime.** 5 evidence-bearing
   states, all in bin `|S|`; 68.3% (state, action) coverage; median 4 of 12
   actions tried per (state, seed). Only one density regime has ever been run, so
   nothing in the artifacts says how agreement responds to state-space size,
   discount, or density.
7. **The exact global execution count cannot be reconstructed** from stored
   artifacts (Day-29 limitation 1 still holds); 232 is the manifest sum, 238 the
   conservative bound, and enforcement remains COMP-EXP-11-deferred.
8. **No claim about learning is made or implied anywhere in this document**, in
   either direction. See section 11.

## 11. Exact interpretation

Supportable by these artifacts, stated exactly:

> **PLAN line 276 freezes a Day-30 gate whose criterion it never defines, and the
> project's two frozen-adjacent stability-flavoured numbers - cross-seed policy
> agreement 0.2000 (FAIL against its own 0.70) and an early-stop rule that fired
> in 3 of 4 runs - were both observed before any Day-30 criterion existed and
> point in opposite directions. Independently of them, enabling multi-step mode
> requires machinery that does not exist in the repository (non-terminal env,
> phase-aware state schema, per-phase metrics, per-phase T_ref, per-phase reward,
> multi-decision loop), is scheduled on no PLAN day, collides with a frozen PLAN
> constraint (session restart on a parallelism change versus F5's cached
> intermediate), and would cost 252-540 executions for single-visit coverage
> against 268 remaining. On those grounds the drafted decision is NO, with no
> PASS/FAIL verdict emitted on the gate itself. The decision is drafted and
> unsigned.**

NOT supportable by these artifacts, stated exactly:

> Multi-step mode **would fail**. Multi-step mode **would help**. Tabular
> Q-learning **cannot work** on this problem. The bandit framing **is** the right
> framing. The Day-29 policies are **unstable**, **converged**, **optimal** or
> **wrong**. M8 = 0.2000 **predicts** anything about a phase-augmented state
> space. The gate **failed**, or **passed**.

The difference is not rhetorical. Day 29 measured cross-seed agreement of a
bandit-mode argmax over a 5-state footprint at 8.4-16.8 episodes per state.
Nothing in it is phase-related; nothing in it varies the discount; nothing in it
measures how agreement responds to density. **A NO here is a scope and
buildability decision taken at the frozen default, not a scientific verdict on
multi-step mode** - and it forecloses the one measurement that could have
distinguished "the bandit framing is too coarse" from "the signal is
noise-limited here". That cost is recorded, not hidden.

## 12. Exact next task

**First, and off the critical path of any execution: operator sign-off.** Read
`docs/research/DAY30_MODE_GATE_DEC_DRAFT.md`, choose one of its three options,
and - if approved - paste the DEC-011 body (heading through the `**Status.**`
line, banner excluded) into `DECISIONS.md` after DEC-010. Until then the gate is
**DECIDED** (DEC-011 signed), and `configs/rl.yaml:8` stays `gamma: 0.0` by
frozen default, unchanged and untouched.

**Then, per frozen `docs/PLAN.md` line 277:**

> `| 31 | Eval harness + B1/B2 | frozen test set; static baselines tuned on validation | configs frozen |`

Day 31 is **NOT started here.** It is the day the frozen TEST split becomes
accessible for the first time (PLAN section 18: "Test (frozen until Day 31)"),
and it brings the evaluation harness plus the B1/B2 static baselines tuned on the
VALIDATION split. Read the plan before beginning it.

Still deferred and still absent, each with its owner: the execution cache and
durable cross-run budget enforcement (COMP-EXP-11); the orchestrator
(COMP-EXP-12); multi-step / gamma=0.9 and ablation A5 (this gate, pending
signature); EXP-003 / EXP-005 / EXP-005b; every deep-RL family. Day 30 built none
of them - implementing the thing under decision would have prejudged the gate.

**Budget entering Day 31: 232 of 500 spent by manifest sum, 268 remaining
(conservative bound: 238 spent, <= 262 remaining). REPORTED, not ENFORCED.**
