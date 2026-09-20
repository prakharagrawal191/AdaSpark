# DAY37 — DEC-030: EXP-008 A3/A4 METHODOLOGY FREEZE

**Decision ID:** DEC-030
**Date:** 2026-09-17
**Status:** DECIDED — methodology frozen; execution NOT authorized
**Scope:** EXP-008 A3/A4 methodology only (reward variants A3; action-space ablation A4). Resolves only the methodological aspects of blockers B1–B4. B5 (budget) and B6 (implementation) remain separate required decisions. This decision authorizes ZERO executions.

---

## 1. Authority and Precedence

**Authoritative sources (in order):**

1. `docs/PLAN.md` — frozen project execution plan (HEAD 5cf0cf8).
2. `DECISIONS.md` — all decisions through DEC-026.
3. Current experiment registry (`experiments/registry.csv`).
4. Frozen architecture/design documents (`docs/architecture/ARCHITECTURE_FREEZE.md`, `COMPONENT_CONTRACTS.md`).
5. Existing implementation (`src/sparkrl/`).
6. Existing experiment artifacts (EXP-002, EXP-007).

**Precedent:** DEC-010 (precedence rule), DEC-026 (EXP-007 authorization; A3/A4 untouched).

**Not authoritative:** Worktree drafts DEC-027..DEC-032 (non-HEAD; do not authorize anything); `docs/research/DAY37_EXP008_PREFLIGHT_AUDIT.md` (evidence only); all older audit reports (evidence only).

---

## 2. Current Repository State

- **HEAD:** 5cf0cf850f022750fa7df734328f6807e3546ee9 (main).
- **Latest committed DEC:** DEC-026 (EXP-007 TRAIN authorized and executed: 126 live runs; A3/A4 untouched).
- **Worktree:** DIRTY — untracked Day-34..37 analyses, evaluation JSONs, scripts, ablation module, EXP-006/007 tests; tracked modifications to DECISIONS.md, ARCHITECTURE_FREEZE.md and several source files. Worktree DEC-027..032 drafts are NOT HEAD truth.
- **Cumulative live executions before EXP-008:** 379 (per preflight audit; NOT reconciled here — see §10).
- **SC6 cap:** 500 (frozen, PLAN §16 / rl.yaml).
- **A5:** DISABLED (DEC-011).
- **A3/A4 execution authorization:** NO (DEC-026 s1/s7).
- **No EXP-008 Spark execution, training, or TEST has occurred.**

## 3. A3 Methodology Freeze

### 3.1 A3 Intent (from PLAN section 24)

PLAN section 24 (line 188) registers three A3 reward variants:

1. **Time-only:** coefficients (1, 0, 0).
2. **Final/frozen R3:** coefficients (1, 0.2, 0.2).
3. **R4 log-ratio:** formula -ln(T / T_ref).

No other reward variant exists in registered PLAN intent. DEC-030 introduces none.

### 3.2 A3-arm-1: Time-Only Reward

| Field | Value | Source |
|-------|-------|--------|
| **Arm identifier** | A3-time-only | PLAN s24 intent |
| **Reward formula** | R = 1.0 * clip((T_ref - T) / T_ref, -1, +1) | Derived from R3 by term removal |
| **Coefficients** | w_time=1.0, w_task=0.0, w_spill=0.0, w_failure=1.0 | PLAN s24 (1,0,0); failure retained from R3 |
| **Failure behavior** | R = -1.0 exactly | DEC-010; retained from frozen R3 |
| **Clipping** | clip to [-1, +1] on the time delta | Retained from frozen R3 |
| **Task-imbalance term** | REMOVED (coefficient = 0.0) | Multi-term removal |
| **Spill-waste term** | REMOVED (coefficient = 0.0) | Multi-term removal |
| **Time term** | RETAINED (coefficient = 1.0) | PLAN s24 |
| **T_ref source** | EXP-002 TRAIN, B0 median, dataset seed 0 (presumed for A3) | TRefStore / rl.yaml |
| **State schema** | state-v1.5 (30 states) — UNFROZEN | B3/B4 |
| **Action schema** | mode12 (12 actions) — UNFROZEN | B3/B4 |
| **Q0 source** | REQUIRES EXPLICIT DECISION | B3 |
| **Alpha** | 0.2 (frozen main-study value) — UNFROZEN for arm | B4 |
| **Gamma** | 0.0 (frozen main-study value) — UNFROZEN for arm | B4, DEC-011 |
| **Epsilon** | 1.0 → 0.05, decay 0.95 (frozen main-study values) — UNFROZEN for arm | B4 |
| **Training seeds** | UNFROZEN — REQUIRES DECISION | B4 |
| **Dataset seed** | 0 (frozen: T_ref calibrated for seed 0 only) | rl.yaml, loop.py |
| **TRAIN cells** | UNFROZEN — REQUIRES DECISION | B4 |
| **Episode horizon** | UNFROZEN — REQUIRES DECISION | B4 |
| **Early-stop rule** | UNFROZEN — REQUIRES DECISION | B4 |
| **AQE condition** | aqe_enabled=false (presumed) — UNFROZEN for arm | B4 |
| **Warm-up behavior** | UNFROZEN — REQUIRES DECISION | B4 |
| **Cache behavior** | UNFROZEN — REQUIRES DECISION | B4 |
| **Live-execution charging rule** | UNFROZEN — REQUIRES DECISION | B5 |

**Classification (mandatory):** TIME-ONLY IS A **MULTI-TERM REMOVAL** FROM R3, NOT A PURE ONE-FACTOR ABLATION. Exactly two reward terms are removed simultaneously: the task-imbalance term AND the spill-waste term. Any observed difference between this arm and R3 cannot be attributed to a single removed term. This must be stated in any future analysis of this arm.

### 3.3 A3-arm-2: Final/Frozen R3 (unchanged primary reward)

| Field | Value | Source |
|-------|-------|--------|
| **Arm identifier** | A3-R3-frozen | PLAN s24 intent |
| **Reward formula** | R3 exactly as frozen (verbatim below) | configs/reward.yaml, sparkrl.rl.reward |
| **Frozen formula (verbatim)** | 1.0*clip((T_ref−T)/T_ref,−1,+1) + 0.2*(1−min(1,CV/0.5)) − 0.2*min(1,(spill/input)/0.10) − 1.0*1[fail] | PLAN §15; FROZEN_WEIGHTS |
| **Coefficients** | w_time=1.0, w_task=0.2, w_spill=0.2, w_failure=1.0; task_cv_ref=0.5; spill_ratio_ref=0.10; clip=[−1,+1] | reward.yaml (validator-enforced) |
| **Failure behavior** | R = −1.0 exactly; no other terms computed from a failed run | DEC-010; reward.py |
| **Clipping** | [−1, +1] on the time delta | Frozen R3 |
| **Task-imbalance term** | RETAINED (0.2) | Frozen R3 |
| **Spill-waste term** | RETAINED (0.2) | Frozen R3 |
| **Time term** | RETAINED (1.0) | Frozen R3 |
| **Missing CV / spill inputs** | Term contributes 0.0 and is recorded in `missing` — never guessed | reward.py |
| **T_ref source** | EXP-002 TRAIN, B0 median, dataset seed 0 | Frozen TRefStore gate artifact |
| **State/action schema** | UNFROZEN for A3 (see §12) | B3/B4 |
| **Q0 source** | REQUIRES EXPLICIT DECISION | B3 |
| **Alpha / gamma / epsilon** | Presumed frozen values (0.2 / 0.0 / 1.0→0.05) — UNFROZEN for arm | B4 |
| **Seeds / cells / horizon / early-stop / AQE / warm-up / cache** | UNFROZEN — REQUIRES DECISION | B4 |
| **Live-execution charging rule** | UNFROZEN — REQUIRES DECISION | B5 |

**CRITICAL:** R3 MUST remain exactly the frozen primary reward. This arm adds NO change to R3. It exists only as the registered comparator (1, 0.2, 0.2) inside A3's registered intent.

### 3.4 A3-arm-3: R4 Log-Ratio — INCOMPLETE, REQUIRES EXPLICIT DECISION

**Registered intent:** R4 = −ln(T / T_ref) (PLAN s24). This is the ONLY registered content.

**What IS determinable from existing authority:**

| Field | Value | Source |
|-------|-------|--------|
| **Arm identifier** | A3-R4-log-ratio | PLAN s24 intent |
| **Registered formula** | R4 = −ln(T / T_ref) | PLAN s24 |
| **T_ref source (presumed)** | EXP-002 TRAIN, B0 median, dataset seed 0 | Presumed from R3 pattern — NOT separately frozen |
| **State/action schema** | UNFROZEN | B3/B4 |
| **Q0 source** | REQUIRES EXPLICIT DECISION | B3 |

**What is NOT frozen and CANNOT be derived (each item REQUIRES EXPLICIT DECISION):**

| Missing element | Status |
|-----------------|--------|
| Failure behavior (does R4 have a failure rule? what value?) | UNFROZEN — REQUIRES EXPLICIT DECISION |
| Clipping behavior (none exists for R4) | UNFROZEN — REQUIRES EXPLICIT DECISION |
| Coefficients/weights (no R4 weights exist anywhere) | UNFROZEN — REQUIRES EXPLICIT DECISION |
| T ≤ 0 | UNFROZEN — REQUIRES EXPLICIT DECISION (log of non-positive undefined) |
| T_ref ≤ 0 | UNFROZEN — REQUIRES EXPLICIT DECISION (R3 raises TRefMissing; R4 rule unstated) |
| Missing execution time | UNFROZEN — REQUIRES EXPLICIT DECISION |
| Failures / timeouts | UNFROZEN — REQUIRES EXPLICIT DECISION |
| Whether R4 removes the same two terms as time-only, or is a pure functional-form change of the time term | UNFROZEN — REQUIRES EXPLICIT DECISION |

**Implementation status:** R4 is UNIMPLEMENTED in the repository. No weights in reward.yaml, no validator, no unit tests. The formula is named in PLAN s24 but has no frozen implementation.

**Verdict:** R4 CANNOT be completely defined from existing frozen materials. Every missing part above is classified REQUIRES EXPLICIT DECISION. DEC-030 does NOT silently choose any semantics: no failure value, no clipping rule, no edge-case handling, and no Q0 treatment for R4 is invented here.

## 4. A4 Methodology Freeze

### 4.1 A4 Intent (from PLAN section 24)

A4 is the registered **4-action minimization / action-space ablation** (PLAN s24). Primary: mode12 = all 12 frozen actions. Candidate: mode4 = the pre-authorized Plan-B subset.

### 4.2 A4-arm-1: Mode4 Action-Space Reduction

| Field | Value | Source |
|-------|-------|--------|
| **Arm identifier** | A4-mode4 | PLAN s24 intent |
| **Action space** | mode4 = {0, 3, 6, 9} (4 actions) | ARCHITECTURE_FREEZE §9 / COMP-RL-07 |
| **Primary comparison** | mode12 = all 12 frozen actions | Frozen grid |
| **State schema** | state-v1.5 (30 states) — UNFROZEN | B3/B4 |
| **Reward** | Presumed R3 — UNFROZEN (must equal its control arm) | B1/B4 |
| **T_ref** | EXP-002 TRAIN, B0 median, dataset seed 0 (presumed) — UNFROZEN | B4 |
| **Q0 policy** | Structural compatibility FROZEN (§5.4); source choice UNFROZEN | B3 |
| **Alpha** | 0.2 (frozen main-study value) — UNFROZEN for arm | B4 |
| **Gamma** | 0.0 (frozen main-study value) — UNFROZEN for arm | B4, DEC-011 |
| **Epsilon schedule** | 1.0 → 0.05, decay 0.95 (frozen main-study values) — UNFROZEN for arm | B4 |
| **Training cells** | UNFROZEN — REQUIRES DECISION | B4 |
| **Seeds** | UNFROZEN — REQUIRES DECISION | B4 |
| **Horizon** | UNFROZEN — REQUIRES DECISION | B4 |
| **Early-stop** | UNFROZEN — REQUIRES DECISION | B4 |
| **AQE** | false (presumed) — UNFROZEN for arm | B4 |
| **Warm-up** | UNFROZEN — REQUIRES DECISION | B4 |
| **Cache** | UNFROZEN — REQUIRES DECISION | B4 |
| **Live-execution charging** | UNFROZEN — REQUIRES DECISION | B5 |

**Determined:** A4 changes ONLY **action availability** (mode4 ⊂ mode12). Everything else must remain identical to the chosen control arm. Any difference other than action availability is flagged as a confound in §6.2.

### 4.3 Exact Four-Action Mapping (Verified)

{0, 3, 6, 9} is already the formally frozen Plan-B subset (ARCHITECTURE_FREEZE §9; COMP-RL-07; `src/sparkrl/rl/action.py` MODE4_SUBSET = frozenset({0, 3, 6, 9})). The frozen grid order is `grid_index = parallelism_index * 4 + shuffle_index` over parallelism {2,4,8} × shuffle {16,32,64,128}.

**mode12 (all 12 actions):**

| Index | Parallelism | Shuffle partitions | Configuration |
|-------|-------------|--------------------|---------------|
| 0 | 2 | 16 | local[2], sp=16, dp=2 |
| 1 | 2 | 32 | local[2], sp=32, dp=2 |
| 2 | 2 | 64 | local[2], sp=64, dp=2 |
| 3 | 2 | 128 | local[2], sp=128, dp=2 |
| 4 | 4 | 16 | local[4], sp=16, dp=4 |
| 5 | 4 | 32 | local[4], sp=32, dp=4 |
| 6 | 4 | 64 | local[4], sp=64, dp=4 |
| 7 | 4 | 128 | local[4], sp=128, dp=4 |
| 8 | 8 | 16 | local[8], sp=16, dp=8 |
| 9 | 8 | 32 | local[8], sp=32, dp=8 |
| 10 | 8 | 64 | local[8], sp=64, dp=8 |
| 11 | 8 | 128 | local[8], sp=128, dp=8 |

**mode4 (the exact four configurations):**

| Index | Parallelism | Shuffle partitions | Configuration |
|-------|-------------|--------------------|---------------|
| 0 | 2 | 16 | local[2]; spark.sql.shuffle.partitions=16; spark.default.parallelism=2 |
| 3 | 2 | 128 | local[2]; spark.sql.shuffle.partitions=128; spark.default.parallelism=2 |
| 6 | 4 | 64 | local[4]; spark.sql.shuffle.partitions=64; spark.default.parallelism=4 |
| 9 | 8 | 32 | local[8]; spark.sql.shuffle.partitions=32; spark.default.parallelism=8 |

**Verification:** mode4 is strictly contained in mode12; the selection restriction is already implemented and unit-validated (12-value Q rows; selection restricted to the allowed subset; out-of-subset actions rejected pre-execution via `InvalidAction`). AQE remains OFF under action application (action.py guard).

## 5. Q0 Methodology

### 5.1 Governing Rules (Phase 4)

1. No TEST-derived information.
2. No post-hoc Q0 construction.
3. No invented state mapping.
4. No invented action mapping.
5. No pooling unless already frozen.
6. No silent change to the primary-study Q0.
7. No reuse of an incompatible Q0 merely for convenience.

### 5.2 Q0 Classification Per Arm

| Arm | Classification | Rationale |
|-----|----------------|-----------|
| A3-time-only | REQUIRES NEW DECISION | Reward changes; state/action space may remain unchanged, but no DEC freezes the A3 Q0 source. Reuse of q0-exp002/v1 is PLAUSIBLE but not frozen. |
| A3-R3-frozen | REQUIRES NEW DECISION | Same state/action space as the primary study; q0-exp002/v1 plausible; provenance still UNFROZEN (B3). |
| A3-R4-log-ratio | REQUIRES NEW DECISION | Reward functional form changes; q0-exp002/v1 values were derived from R3 rewards, so compatibility is questionable; no frozen R4 Q0 exists. |
| A4-mode4 | EXISTING FROZEN MAPPING | mode4 restricts offered actions only; Q-table rows remain 12-wide; columns 0/3/6/9 are used as-is. No projection, no construction. |

**Mandatory statement:** Q0 compatibility for mode4 requires NO new mechanism. For the A3 arms the Q0 source decision is NOT made here — "Q0 compatibility requires a separate explicit decision." No projection is invented. No pooling is introduced. The primary-study Q0 behavior is not silently changed.

### 5.3 A3 Q0 Analysis

- State/action space (state-v1.5 × 12 actions) may remain identical to the primary study for the time-only and R3 arms.
- q0-exp002/v1 was built from EXP-002 TRAIN records under frozen R3 rewards. For a time-only arm this would be initialization under a different reward — methodologically defensible IF frozen, but that choice has NOT been made.
- For R4, no Q0 was ever computed under the log-ratio reward; constructing one now would be post-hoc construction (forbidden by rule 2).
- Verdict: SAME FROZEN Q0 is available in kind (q0-exp002/v1) but NOT frozen in law for A3 → REQUIRES NEW DECISION per arm.

### 5.4 A4 Q0 Analysis

- Q-table structure: rows of 12 values keyed by state. mode4 does NOT change row width; it restricts which actions may be selected.
- Therefore q0-exp002/v1 rows are dimensionally compatible with mode4: indices {0, 3, 6, 9} exist in every row.
- An existing frozen Plan-B Q0 mechanism exists in exactly this sense: no mapping, no pooling, no construction.
- Verdict: EXISTING FROZEN MAPPING (structural). The choice of WHICH frozen Q0 source (q0-exp002/v1 vs q0-neutral/v1) for the A4 arm still requires the arm-freeze decision — flagged in §12.

## 6. Control / Confound Audit

### 6.1 A3 Control Table

| Factor | Primary (frozen) | A3-time-only | A3-R3-frozen | A3-R4 | Same/Different | Interpretation |
|--------|------------------|--------------|--------------|-------|----------------|----------------|
| state | state-v1.5 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B3/B4 |
| action | mode12 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B3/B4 |
| reward | R3 (1, 0.2, 0.2) | (1, 0, 0) multi-term removal | R3 unchanged | −ln(T/T_ref) | DIFFERENT (by design) | A3 isolates reward |
| Q0 | q0-exp002/v1 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B3 — interaction risk |
| alpha | 0.2 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| gamma | 0.0 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4; DEC-011 lock |
| epsilon | 1.0→0.05 @0.95 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| seeds | {0,1,2} main study | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 — see §7 |
| horizon | none frozen | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| early-stop | 2 stable epochs (main) | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| cells | TRAIN set | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| T_ref | EXP-002 B0 seed 0 | UNFROZEN (presumed same) | UNFROZEN (presumed same) | UNFROZEN | UNFROZEN | B4 |
| AQE | false | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| warm-up | frozen runner behavior | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| cache | execution cache | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| budget rule | SC6 | UNFROZEN | UNFROZEN | UNFROZEN | UNFROZEN | B5 |

**A3 confounds identified (NOT repaired silently):**

1. **Reward change is the intended factor** — but time-only removes TWO terms at once, so any A3-time-only vs R3 difference is a multi-term effect, not isolable per term.
2. **Q0 interaction:** differing Q0 sources across arms would confound reward effects with initialization. Unfrozen (B3).
3. **R4 functional-form change:** −ln vs clipped-linear changes the scale/meaning of the time signal; comparisons vs R3 confound functional form with coefficient/term differences. Edge semantics unfrozen (§3.4).

### 6.2 A4 Control Table

| Factor | Primary (frozen) | A4-mode4 | Same/Different | Interpretation |
|--------|------------------|----------|----------------|----------------|
| state | state-v1.5 | UNFROZEN | UNFROZEN | B3/B4 |
| action | mode12 (12) | mode4 (4) | DIFFERENT (intended) | Only action availability may differ |
| reward | R3 | UNFROZEN (must equal control) | UNFROZEN | B1/B4 |
| Q0 | q0-exp002/v1 | structurally compatible; source UNFROZEN | STRUCTURALLY SAME | B3 — source risk |
| alpha | 0.2 | UNFROZEN | UNFROZEN | B4 |
| gamma | 0.0 | UNFROZEN | UNFROZEN | B4 |
| epsilon | 1.0→0.05 @0.95 | UNFROZEN | UNFROZEN | B4 |
| seeds | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| horizon | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| early-stop | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| cells | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| T_ref | UNFROZEN (presumed same) | UNFROZEN (presumed same) | UNFROZEN | B4 |
| AQE | false | UNFROZEN | UNFROZEN | B4 |
| warm-up | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| cache | UNFROZEN | UNFROZEN | UNFROZEN | B4 |
| budget rule | SC6 | UNFROZEN | UNFROZEN | B5 |

**A4 confounds identified (NOT repaired silently):**

1. **Action-space reduction (intended factor).** All other factors must equal the control arm; any deviation is a confound and must be flagged at authorization time.
2. **Possible Q0 mismatch** — if A4's Q0 source differs from its control arm's, action effects are confounded with initialization (B3; §5.4).
3. **Action-selection distribution differences** — ε-greedy over 4 vs 12 actions yields different exploration coverage and per-action visit rates under the same schedule. Inherent to the factor; must be reported, not "repaired".

## 7. Seed / Horizon Freeze (Phase 6)

| Parameter | Status | Evidence |
|-----------|--------|----------|
| A3 seed count / identities | UNFROZEN — REQUIRES DECISION | No DEC freezes them; EXP-007's {0,1} is EXP-007-scoped (DEC-023/025) and does NOT auto-apply |
| A4 seed count / identities | UNFROZEN — REQUIRES DECISION | Same — no DEC freezes A4 seeds |
| A3 episode limit | UNFROZEN — REQUIRES DECISION | None frozen for EXP-008 |
| A4 episode limit | UNFROZEN — REQUIRES DECISION | None frozen for EXP-008 |
| A3/A4 TRAIN cells | UNFROZEN — REQUIRES DECISION | None frozen; the 7-cell T_ref-calibrated TRAIN set exists as the only calibrated basis but is not frozen for A3/A4 |
| A3/A4 early-stop rule | UNFROZEN — REQUIRES DECISION | The PLAN §16 rule exists for the main study; no DEC extends it to A3/A4 |

**Mandatory statement:** seeds, horizon, cells and early-stop are NOT selected here to fit any budget. The methodology decision precedes budget arithmetic (§10). The preflight audit's "illustrative parity shape" (2 seeds × 35 episodes × 7 cells) is explicitly NOT a freeze and must not be treated as one.

## 8. Statistical Governance (Phase 7)

**Already frozen (main study / EXP-005 standard):** PLAN §22/§23/§33 — 5 reps, medians, Wilcoxon signed-rank paired by instance×seed, Mann-Whitney where unpaired, Cliff's δ, Holm-Bonferroni correction. This machinery exists and is the registered evaluation standard for EXP-005.

**NOT frozen for EXP-008 A3/A4:** p-value threshold, effect-size threshold, Holm family definition, multiple-testing correction scope, minimum successful cells, superiority threshold, and the choice between descriptive-only vs inferential analysis. The Day-37 audit's proposed Wilcoxon/Holm procedure is EVIDENCE, not authority; it is not adopted here.

**Verdict:** whether a separate statistical-governance DEC is required LATER is left open by this DEC. Until such a DEC exists, any EXP-008 analysis that eventually runs remains descriptive-only with no thresholds invented. No inferential analysis is performed by this DEC.

## 9. A5 Lock (Phase 8)

- A5 is NOT part of this DEC.
- A5 remains DISABLED under DEC-011 (Day-30 mode gate = NO; multi-step not enabled; γ stays 0.0).
- No γ=0.9 implementation or execution may be introduced by this DEC.
- No multi-step RL is opened by this decision.
- `configs/rl.yaml` gamma remains 0.0; DEC-030 makes no change and permits none.

## 10. Budget Firewall (Phase 9)

- B5 is NOT resolved by DEC-030. Budget reconciliation is a separate required decision.
- DEC-030 does not calculate or freeze a new remaining budget, does not raise the cap, does not de-scope arms, does not redefine SC6, and does not decide whether validation/TEST charge SC6.
- Contradictory figures cited from the preflight audit, NONE selected as authoritative: spent before EXP-008 = 379; remaining-capacity candidates = −89 (DEC-chain post-EXP-007), 121 (nominal TRAIN-only), 38 (validation-excluded basis). SC6 cap = 500 (frozen).
- **Explicit dependency:** EXP-008 execution remains unauthorized until a separate budget decision establishes a valid headroom calculation (from manifests, with a stated charging rule), a separate implementation decision (B6) is complete, and a separate authorization decision (DEC-031 or equivalent) is signed.

## 11. Execution Authorization

**Execution authorization: NO.**

DEC-030 authorizes ZERO Spark executions, ZERO training runs, ZERO TEST executions. It does not modify training artifacts, EXP-005/006/007 results, the RL implementation, PLAN.md, or any historical decision. It does not enable A5. A3/A4 remain UNIMPLEMENTED (B6 — separate decision).

## 12. Unresolved Methodological Fields (each: UNFROZEN — SEPARATE DECISION REQUIRED)

| # | Field | Applies to |
|---|-------|-----------|
| 1 | Final arm set to execute (which A3 formulas; whether A3-R4 is retained despite incompleteness) | A3 |
| 2 | Q0 source per arm (q0-exp002/v1 vs q0-neutral/v1 vs other frozen-compatible source) | A3 (all arms); A4 |
| 3 | State schema per arm (state-v1.5 presumed; not frozen) | A3; A4 |
| 4 | Action schema for A3 (mode12 presumed; not frozen) | A3 |
| 5 | Reward arm for A4 control pairing (must equal its control) | A4 |
| 6 | Seeds (count + identities) | A3; A4 |
| 7 | TRAIN cells | A3; A4 |
| 8 | Episode horizon | A3; A4 |
| 9 | Early-stop rule | A3; A4 |
| 10 | AQE condition confirmation (presumed OFF) | A3; A4 |
| 11 | Warm-up behavior | A3; A4 |
| 12 | Cache behavior | A3; A4 |
| 13 | Whether A3 and A4 share seeds/cells/horizon | both |
| 14 | Statistical governance (descriptive vs inferential; thresholds) | both |
| 15 | R4 complete specification (failure rule, clipping, edge cases, weights) | A3-R4 |
| 16 | Epsilon schedule / alpha / gamma if deviating from frozen values | A3; A4 |
| 17 | Live-execution charging rule and headroom (B5) | both — SEPARATE BUDGET DEC |
| 18 | Implementation authorization (B6) | both — SEPARATE DEC |

## 13. Implementation Delta (summary only — NOT authorized)

- **A3:** requires new reward machinery beyond frozen R3: a time-only formula (multi-term removal of the task-imbalance and spill-waste terms with retained failure −1.0 and clipping), and, if A3-R4 is ever retained, a full R4 implementation (formula, weights, validator, unit tests, edge-case semantics). Current `sparkrl.rl.reward` implements exactly one frozen formula (R3) and refuses any other — an additive, default-preserving extension would be required.
- **A4:** `ActionMapper` already supports mode4 (MODE4_SUBSET = {0, 3, 6, 9}; selection restriction validated). Wiring mode4 into a training-loop arm is the only implementation gap.
- **A5:** no implementation exists and none may be added under this DEC.

## 14. Files Modified by This Decision

None. DEC-030 records methodology only. This DEC creates two new artifacts (this document and `results/evaluation/exp008_methodology_freeze.json`) and modifies NO existing file: no code, no configuration, no hyperparameter, no stored result, no PLAN text, no historical DEC text.

## 15. Approval

**Status:** DECIDED — methodology frozen; execution NOT authorized.

**What DEC-030 fixes:** A3 registered intent and exact formulas (time-only as an explicit multi-term removal; R3 unchanged; R4 named with all missing semantics marked for separate decision); A4 exact action subset {0, 3, 6, 9} with verified configurations; Q0 classifications per arm (no projection invented); control/confound audit; seed/horizon explicitly NOT frozen; statistics NOT frozen (no thresholds invented); A5 lock reaffirmed; budget firewall with explicit dependency; execution authorization = NO.

**Gate chain to any future execution:** (1) this DEC-030; (2) a separate budget DEC resolving B5; (3) a separate implementation DEC resolving B6 with green zero-Spark tests; (4) a separate authorization DEC (DEC-031 or equivalent) with worst-case counts and ledger charge, plus a clean preflight re-run. Any methodological field marked "UNFROZEN — SEPARATE DECISION REQUIRED" must be resolved by such a DEC before authorization. Until then, EXP-008 A3/A4 remain: **FROZEN IN INTENT, UNFROZEN IN DETAIL, UNAUTHORIZED IN EXECUTION.**

---

*End of DEC-030.*







