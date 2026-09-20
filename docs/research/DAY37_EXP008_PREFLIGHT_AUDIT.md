# DAY37 — EXP-008 A3/A4 PREFLIGHT AUDIT (pre-execution, zero Spark)

Status: PRE-EXECUTION AUDIT ONLY. 0 Spark executions, 0 training runs,
0 TEST executions, 0 artifacts modified. A5 DISABLED. A3/A4 NOT AUTHORIZED.

HEAD 5cf0cf850f022750fa7df734328f6807e3546ee9 main. HEAD DECISIONS SHA256:
c5f0f7c147f46dc760d02807309c06d35ded159d33ff9b0c6ee1c59b0f0118d8. Worktree
DECISIONS SHA256: 313e6f0353670bef42e1c10bbfa3069dfc29d5e348617d81b1add5d2dde957e9
DIRTY. PLAN SHA256: db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63.
RL yaml SHA256: 8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80.
Reward yaml SHA256: a52131d5a0de63ef06d3dd5b181f1bbeda326df3ffffbd2ae1c69ed96571db1b.
Action SHA256: 580cf010f17b2cb0f7c3b7967d4fb560b7f973028e8a1909123e7d337f4c0528.
Reward-py SHA256: 0c5e67f45886443136d80630689a75d536c979df921a94496d6c61ae41f89798.
State SHA256: 3ce6ee042829b4374776617fdf74f1f7a375905d35e414a577823b149911bda0.
Q0 SHA256: 7d2ffb0c33fc4349a71d3e064781927425092ff86be2ee195705b3111de195.
Agent SHA256: 1c5fab897f8f652b90cd9011b1d84846459f04.
Loop SHA256: b513238d5148a16cc8e39283526082b0c199fee5ad7a00326d95f4ad3983a611.
Ablation SHA256: 69ab9c40e1688405b8b6f795783ada7fbf26c753bacb76d0aba215b7fb5b216a.
ARCH SHA256: 9520fc86931c058bf7b0911bf3c5bfeb5471083e5f3e2cd417e229899c33fb9b.
T_ref gate SHA256: e30a7b0c953d9965ed97722327f39006fef30f9c6bc980418b50247ebaa05392.
EXP007 analysis SHA256: e010072f0254a57e09656e4551d4c3ff3c6903ff9347c721b39d5ea8c0043b68.
UTC 2026-09-17. NO-GO (B1-B6). NOT AUTHORIZED.

## 1. Current repository state

HEAD 5cf0cf850f022750fa7df734328f6807e3546ee9 on main. Worktree DIRTY:
tracked mods to DECISIONS, ARCH freeze, run_exp005, run_training, agent q0 and
q_learning, rl init and state, training init and loop, one unit test; untracked
DAY34-36 analyses, exp005-007 JSON, analyze/freeze/run scripts, ablation module,
EXP-006/007 tests. Training manifests non-smoke: 8 totalling 343 live; smoke
live 15 excluded from SC6. EXP-007 analyzer self-check OK; EXP-007 and RL
action/reward unit tests pass. 0 Spark executions, 0 training, 0 TEST, 0 edits
to existing artifacts in this audit.

## 2. Decision chronology relevant to EXP-008

DEC-010 failure-as-observation (reward -1, Q-update applied). DEC-011
multi-step/A5 DISABLED, gamma 0.0; re-affirmed DEC-016 s7, DEC-023 s2, DEC-024 A5
row, DEC-025 s7, DEC-026 preamble. DEC-012/013/016 validation+budget chain.
DEC-015 three RL arms (M8 failed 0.2000 vs 0.70). DEC-016/C +84 validation.
DEC-018 operator governance + TEST seal. DEC-020/021 EXP-005 closure + EXP-006
scope. DEC-022 EXP-006 auth (105 executable TEST rows). DEC-023 EXP-007
methodology only (A1 v1 15-state, A2 v2 2-state, neutral Q0, TRAIN-only,
descriptive-only). DEC-024 gate NOT AUTHORIZED. DEC-025 ledger 336/500 rem 164
plan 140 headroom 24; amended 42 to 35 per seed. DEC-026 authorized EXP-007 TRAIN
(4x35) then EXECUTED 126 live (35+35+35+21), 0 failures, no TEST, A3/A4/A5
untouched. Latest HEAD: DEC-026. Worktree holds uncommitted DEC-022..026 text
plus DEC-027..032 drafts; drafts are NOT HEAD truth and do not authorize EXP-008.
EXP-008 methodology/scope/executions NOT AUTHORIZED (DEC-026 s1/s7); await
DEC-030 freeze + DEC-031 authorization.

## 3. Exact A3 definition

PLAN s24 intent only: time-only (1,0,0) vs final (1,0.2,0.2) vs R4 log-ratio.
PLAN s15 R3: 1.0*clip((Tref-T)/Tref,-1,+1)+0.2*(1-min(1,CV/0.5))
-0.2*min(1,(spill/input)/0.10)-1.0*1[fail]; failed run gives exactly -1.0
(DEC-010). R4=-ln(T/Tref) named but UNIMPLEMENTED (no weights, validator, test,
## 4. Exact A4 definition

PLAN s24 intent only: 4-action minimal vs 12-action full. Frozen full space:
mode12, 12 actions, grid_index=parallelism_index*4+shuffle_index over
parallelism (2,4,8) x shuffle (16,32,64,128); map 0:(2,16) 1:(2,32) 2:(2,64)
3:(2,128) 4:(4,16) 5:(4,32) 6:(4,64) 7:(4,128) 8:(8,16) 9:(8,32) 10:(8,64)
11:(8,128); B0 is reference not action; AQE OFF. Pre-authorized Plan-B
mechanism: mode4 {0,3,6,9}=(2,16),(2,128),(4,64),(8,32); Q-width ALWAYS 12
(selection restriction; 12-value rows validated; bootstrap over allowed only).
Whether A4 equals mode4 or another set: UNFROZEN (B2). Full twin table: UNFROZEN
(B3/B4). Mechanism pre-authorization is not arm selection; selection needs DEC-030.

## 5. A3 isolation audit

UNDECIDABLE until DEC-030 freezes arms. Reward+Q0 double change = INVALID as pure
reward ablation unless DEC re-scopes. R4 on derived Q0 still changes realized
Q-values via reward channel: DEC must declare ACCEPTABLE AND FROZEN or reject.
Time-only + neutral Q0 = double change. Verdict: REQUIRES NEW DECISION (B1/B3).
No silent fix.

## 6. A4 isolation audit

Mode4 on identical v1.5/R3/epsilon/cells/Tref/AQE/warm-up/horizon with derived
12-wide Q0 and selection restricted to {0,3,6,9} isolates action availability;
ACCEPTABLE AND FROZEN only if DEC-030 declares with twin table. Neutral-Q0
variant = action+Q0 confound (INVALID as pure ablation). Any state change =
INVALID. Horizon/seed/cell/Tref/epsilon/early-stop/Spark differences = confounds.
No mapping needed (Q-width 12). Verdict: REQUIRES NEW DECISION (B2/B3).

## 7. Q0 compatibility audit

No A3/A4 Q0 frozen (B3). Options: derived q0-exp002/v1 (median frozen-R3 TRAIN
obs, v1.5 le0 convention) or neutral q0-neutral/v1 (0.5 everywhere, no
## 8. Seed and replication audit

PLAN s16: 3 training seeds {0,1,2} = exploration replicates (agent rng_seed
only); dataset_seed is instance seed, T_ref for 0 only. Main study 0/1/2
(84/49/42 eps). EXP-007 {0,1}/arm (DEC-023 s7 compromise). A3/A4 seeds UNFROZEN
(B4). Illustrative parity {0,1} x 35 = 70/arm is NOT frozen, must not execute.
Power-vs-budget is DEC-030 tradeoff.

## 9. TRAIN-cell audit

Frozen 7 cells dataset-seed 0 T_ref exp002-gate:gate.json; F3_rdd|medium
t_ref_null excluded. F1_agg|small 22.347372, F1_agg|medium 36.669743,
F2_join|small 2.214523, F2_join|medium 16.126881, F3_rdd|small 25.10938,
F5_mixed|small 3.903756, F5_mixed|medium 32.759411. Round-robin rep=epoch, 7 per
epoch. Main study 84 (12 epochs); EXP-007 35 (5 epochs). A3/A4 inheritance
UNFROZEN (B4); recommended identical, only DEC-030 can freeze. No TEST in scope.

## 10. Budget reconciliation

Truth: manifests + ledger specs; stale DEC-025 rem-164 NOT reused (predates
EXP-007 execution). Non-smoke training: 8 manifests, 343 live
(42+84+35+35+49+35+21+42; episodes completed 343). Smoke live 15 excluded.
EXP-001 spec sc6_charge 20 TRAIN (316 to 336 of 500). B0 refs 16. Cumulative
TRAIN live before EXP-008: 379 (343+20+16); nominal remaining 121. DEC chain:
336 spent pre-007, rem 164; EXP-007 executed 126; DEC-chain remaining -89
(38 if validation held outside SC6; 121 TRAIN-manifest+EXP001/B0 basis).
Illustrative parity 70+70=140 projects 519 (379+140), headroom -229 (-103 even
## 11. Test-separation audit

EXP-008 TRAIN-only (DEC-023 s9; DEC-026 s12). No TEST queue/spec/ledger for
A3/A4. Guards: split_of + assert_train_only + SparkTuningEnv SplitViolation +
TRefMissing pre-execution. A3/A4 must not read/tune on/select from TEST. PASS:
no TEST touched; test_freeze 43 cells and EXP-005 245 / EXP-006 125 rows
untouched by this audit.

## 12. Implementation-support audit

Files: rl/reward.py, rl/action.py, rl/state.py, agent/q0.py, agent/q_learning.py,
training/loop.py, training/ablation.py, scripts/run_training.py. A3: NO support
(R3-only FORMULA_ID + FROZEN_WEIGHTS hard-validation; --variant A1/A2 only;
ablation.py A1/A2 only). A4: mechanism EXISTS (mode12/mode4, MODE4_SUBSET,
InvalidAction incl mode4 rejection, to_config AQE-OFF assert) but NO
ablation-arm plumbing. A5 blocked (no gamma-0.9 path; DEC-011). Verdict: B6
BLOCKING; execution today would require code changes needing their own DEC.

## 13. Validator/test audit

Validators exist: reward weights, InvalidAction incl mode4, state schemas
(v1/v1.5 + v2 FeedbackState separation), Q0 leakage guard (split_of TRAIN only),
budget/early-stop/checkpoint rules, TRefMissing pre-execution. Tests pass
zero-Spark read-only: EXP-007 scope/parity/Q0/state, RL action/reward. NO A3/A4
tests exist (nothing frozen to test). No integration/Spark executed here.

## 14. Contradiction/drift audit

N1: ARCH s9 A1/A2 sentence superseded by DEC-023 (PLAN governs derived Day-12
docs; tail note records; text retained). N2: ARCH failure semantics superseded
by DEC-010 (tail note; reward.py failed to -1.0 matches DEC-010). N3: T_ref
EXP-002/003 (PLAN) vs EXP-002-only impl (DEC-023 s5 froze EXP-007 source).
N4: EXP-008 ~300/Train-Test envelope (PLAN s33) vs TRAIN-only + exhausted
budget. Precedence: PLAN > DECISIONS > registry/specs > freeze docs >
## 16. Blocking issues

B1 A3 reward formulation(s) unfrozen. B2 A4 action subset unfrozen. B3 A3/A4 Q0
unfrozen (no mapping exists; inventing one forbidden). B4 seeds/horizon/
early-stop/cells/Tref/epsilon/warm-up/cache/limits unfrozen. B5 SC6 exhausted
(DEC-chain -89; illustrative headroom -229; nominal TRAIN-only 121 still cannot
authorize without budget DEC). B6 A3/A4 implementation gap (A3 no support; A4 no
arm plumbing). Any ONE blocks execution authorization.

## 17. Non-blocking issues

N1 S9 A1/A2 drift (precedence resolved, tail note). N2 failure-semantics drift
(resolved, impl matches DEC-010). N3 T_ref source question for DEC-030
(recommend EXP-002-only parity). N4 envelope vs TRAIN-only+budit for DEC-030.
N5 seed-count tradeoff for DEC-030. N6 stats gap (descriptive-only until DEC-030).
Carried, none blocks audit completion.

## 18. Required new DEC entries, if any

DEC-030 EXP-008 A3/A4 METHODOLOGY FREEZE: arm table (each A3 formula + frozen
params + removed-vs-R3 + single/multi verdict; A4 subset = mode4 {0,3,6,9} or
justified alternative); twin table (state/action/Q0/alpha/gamma/epsilon/seeds/
horizon/early-stop/cells/Tref/AQE/warm-up/cache/budget); isolation verdicts per
arm; stats section (frozen machinery or explicit descriptive-only); TRAIN-only
re-affirmation; implementation delta + tests. BUDGET DEC (standalone or DEC-030
series): reconcile SC6 from manifests, charge rule, raise cap or de-scope; BLOCKS
DEC-031. IMPLEMENTATION DEC: additive default-preserving A3/A4 + tests + guards;
A5 stays blocked. DEC-031 EXECUTION AUTHORIZATION: separate, after all above,
with worst-case counts and ledger charge.

## 19. Exact proposed EXP-008 freeze

NONE PROPOSED BY THIS AUDIT. A3/A4 arms, Q0, seeds, horizon, early-stop, cells,
T_ref, epsilon, warm-up, cache, budget: ALL UNFROZEN. Illustrative parity shape
(2 seeds x 35 = 70/arm, 7 TRAIN cells, dataset seed 0, frozen early-stop/epsilon/
AQE/warm-up) is NOT a freeze, NOT authorized, and must not be executed. This
section intentionally contains no executable specification.

## 20. GO / NO-GO recommendation

NO-GO. B1-B6 block execution authorization; the specification-freeze bar is NOT
met. A GO here would mean ONLY the specification is sufficiently frozen and
execution may be authorized by a separate decision; it would NOT authorize Spark
execution by itself. EXP-008 is ELIGIBLE for later DEC-031 ONLY AFTER DEC-030 +
budget DEC + implementation DEC (tests green) + clean preflight re-run with
headroom confirmed. This audit authorizes 0 executions, 0 training, 0 TEST.
No performance, novelty, superiority, or causal claim is made.

implementation > artifacts. No historical text edited; DEC-030 must resolve
N3/N4. No derived doc silently overrides PLAN or newer DEC.

## 15. Statistical-governance audit

PLAN s22/s23/s33 machinery (Wilcoxon signed-rank paired by instance x seed,
Mann-Whitney where unpaired, Cliff delta, Holm-Bonferroni, 5 reps, medians) is
the EXP-005 evaluation standard. NO DEC freezes any test, p-threshold,
effect-size threshold, Holm family, or acceptance count FOR EXP-008 ablations.
GAP (N6): descriptive-only until DEC-030 freezes machinery or defers inference.
No thresholds invented; historical results unmodified.

pre-EXP-007). PLAN ~300 envelope would project 679. Cap 500 frozen (PLAN s16,
rl.yaml). No headroom: new budget DEC must re-derive spent, state whether
validation/TEST charge SC6, and raise cap or de-scope (B5). EXP-005 TEST 245 and
EXP-006 125 do not charge SC6 TRAIN.

Runs: 20260912T083120Z 42 v1.5 early_stop; 20260912T112906Z 84 v1.5 planned;
20260917T055042Z 35 v1 planned; 20260917T061316Z 35 v2 early_stop;
20260912T115123Z 49 v1.5 early_stop; 20260917T060047Z 35 v1 planned;
20260917T062346Z 21 v2 early_stop; 20260912T120648Z 42 v1.5 early_stop.

projection). A1/A2 precedent DEC-023 s4: neutral with explicit constraint
language; inventing many-to-one projection or pooling FORBIDDEN. No reward/action
mapping exists. A4-mode4 derived needs no mapping (rows stay 12-wide).
A3-derived compatibility depends on frozen arm. DEC-030 must freeze Q0 per arm
with confound class. Auditor implements no mapping.

CLI, params). Which arms execute, exact frozen params, removed-vs-R3, and
single-vs-multi-factor: ALL UNFROZEN (B1). Time-only removes TWO terms
(multi-factor); R4 changes functional form. A3 state/action/Q0/alpha/gamma/
epsilon/seeds/horizon/early-stop/cells/Tref/AQE/warm-up/cache/budget: UNFROZEN
(B3/B4). Precedence: PLAN intent governs; no derived doc may invent arms.

