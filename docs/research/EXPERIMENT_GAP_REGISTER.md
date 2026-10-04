# Experiment Gap Register — PENDING AUTHORIZATION drafts (DO NOT RUN)

**Policy:** Pre-register → authorize → run → analyze → report. Every entry below
is PENDING unless ledger-signed. No Spark execution by this audit (0 runs 0 SC6).
Stopping doctrine: stability-gated (PASS and stays PASS + block-L10 agrees);
never first-PASS-anywhere (F1S n29 / F5S n77 revert); never until-significant.
Interpretation fixed before data: PASS = whole 95% CI on one side of gate (DEC-042);
straddle = INCONCLUSIVE both ways; FAIL only if whole CI beyond gate adversely.
Own register lines; 0 SC6 unless stated TRAIN.

## A. Gaps

G-00 | Claims: ALL X1/X2/X3/X6/X8/X9/X10/demo + R-derivatives | Current: rows on
disk UNTRACKED cite DEC-047–051 drafts absent DECISIONS.md (ends DEC-046) |
Why insufficient: ledger absence = authorization NOT established; Availability
committed-artifacts OVERSTATED for X | Explanations: working-tree drafts claim
SIGNED 2026-09-29 operator GRANTED supervisor PENDING — signature inside
uncommitted file is not ledger authorization | Existing support: specs + JSONL +
recomputed medians all match | Need experiment? NO — 0 runs | Auth: NEEDS LEDGER
COMMIT (or re-authorize) | Runs 0 | Metric/Baseline/Comparison/Stopping N/A |
Risk: paper cites orphaned evidence | Priority P0 | Action: commit DECs + track
files + chk26 allow-list DEC (bundle G-07/G-08) or re-authorize; until then cite
X as working-tree pilots.

G-01 | SC7 measurements reproduce | Current: X10 2/4 (med PASS small FAIL);
EXP-011 60 empty | Why: 4 pilot arms cannot support population claim; short-cell
drift unmeasured | Cause: short-runtime drift-sensitive (X10 small +6.8/+11.7 vs
med +2.7/+4.7) measured not assumed | Support: X10 JSONL + rule | Need? YES 60
TEST own line | Auth NEEDS DEC | Runs 60 (2 cells×2 arms×5 ×3 waves) | Metric
fresh-vs-frozen median % | Baseline EXP-005 medians | Comparison ±5% per cell-arm
4/4 PASS pilot; full 60/60 for claim | Stop: 3 stability waves; halt on 2nd FAIL
wave | Interpretation: PASS only 60/60 else PARTIAL/FAIL publish as-is | Risk
TEST-crossing needs DEC-014 pattern | P1.

G-02 | External validity beyond pilot | Current: Taxi 20 feasibility one month
one shape analogical | Why: single external point cannot support generality |
Support: X9 JSONL −78/−70 + identity | Need? YES ~30–60 + build | Auth NEEDS DEC
| Metric median % tuned vs B0 + identity check | Baseline B0 + frozen RL | Stop:
manifest+checksums then 5 reps; halt on download fail→substitution path | Risk
new capability (resolver+mapping) largest build | P2.

G-03 | Causal drift/cache attribution | Current: CUSUM/ACF measured confound;
no controlled warm/cold or background-load contrast | Why: only needed IF causal
drift claim ever made (none made — correctly confound) | Need? CONDITIONAL
~20–40 validation | Auth NEEDS DEC if claimed | Metric shift % + ACF delta |
Baseline same-cell interleaved | Stop: pre-reg contrast; halt on confound
overlap | P3.

G-04 | AQE pooled interaction | Current: X6 side-by-side F2L −14.2%; pooling
FORBIDDEN no-pooling rule | Why: runtime-adaptive vs static pooling invalid under
current rule | Need? YES only under NEW pre-registration | Auth NEEDS DEC |
Metric side-by-side medians (pooling only if new DEC explicitly permits + defines
estimator) | Stop: 35-run scope; halt on TEST deviation | Risk: changes comparison
logic | P2.

G-05 | F3_rdd|medium T_ref backfill | Current: null everywhere TRAIN; 7-cell
panels unequal | Why: unlocks coverage + eligibility | Need? calibration TBD |
Auth NEEDS TRAIN DEC | Metric median B0 reference | Stop: calibration 5 reps;
halt on fragile RDD recurrence | P2.

G-06 | Per-sample telemetry schema | Current: job-time deltas only; mechanism
unattributed | Why: next overhead study attributable | Need? design-only 0 runs |
Auth EXEMPT (no Spark) | P3.

G-07 | Hygiene registry/placeholders/messages | Current: registry.csv stale all
planned; empty env/runner; chk27 msg vs allow-list | Why: confusion only zero
claim | Need? 0 runs bundle next DEC | P3.

G-08 | Doc repairs (0 runs): X8 fig desc −24.7% unsourced→correct/drop; X1 8/8
vs 7 executed→narrow 7/7; X6 spec 1 vs 7→amend spec no rows; R hardcoded Temp
path→record copy step; Availability committed→HELD+deposit-pending; SC6 quote
both + §5 sentence; ICPE TODO(DOI) kept | Auth: bundle with G-00 DEC | P0.

G-09 | Refs ≥80% 2020–25 journal count verification + videos README-only +
CCSXML/AI-disclosure placement | Current: ms 39 band-OK count task open; ICPE 5
verified; videos placeholder | Auth: editorial + author tasks | P3.

## B. DEC drafts PENDING (DO NOT RUN — copy into DECISIONS.md only on operator sign)

DEC-G00: ledger-commit of DEC-047–051 + chk26 allow-list (5 new JSON) + G-08 doc
repairs. Scope: 0 Spark; 0 SC6; PLAN unchanged; TEST untouched. Acceptance: chk
26 36/36; X files tracked; G-08 wording landed. Stopping N/A.
DEC-G01: EXP-011 full 60 TEST own line (2 cells×2 arms×5 ×3 waves) DEC-014
pattern frozen instances B0/B1 AQE-off; ±5% rule; stability-gated; null caps
claims pilot scope. Cost 60 TEST 0 SC6.
DEC-G02: 2nd public family ~30–60 + manifest/checksums; frozen policies no
training; B0 vs tuned descriptive feasibility; substitution path declared.
Cost ~30–60 external-unseen 0 SC6.
DEC-G04: AQE pooled-interaction pre-registration (estimator + pooling rule +
no-pooling default retained unless new rule fires). Cost 0 new unless scope
reopened (then 35 AQE-on ledger).
DEC-G05: F3_rdd|medium TRAIN calibration backfill TBD reps; eligibility refresh
frozen code; halt on fragility. Cost TBD TRAIN (fits 17 only if ≤17 else own line
+ justification).
Each: metric/baseline/comparison/stopping/interpretation fixed above; data
retained as observed; negative publishable; budget fits or own line; TEST seal
per guards.

## C. Status after EXP-013 (DEC-053/055, 2026-10-02)

- **H2/H3 (formerly UNDECIDED):** decided by EXP-013 — H2 ACCEPTED, H3 REJECTED (see CLAIM_EXPERIMENT_MAP.md).
- **G-01 (SC7):** partially addressed — one fresh wave over 39 cell-arms of the EXP-005 cells (18/39 within ±5%); the 3-wave EXP-011 design remains open.
- **G-04 (AQE):** side-by-side re-test done; X6's lead not replicated; pooled estimator still unregistered.
- **G-10 (new) — state cannot perceive scale:** every input in the study is size bin S (<512 MiB); a size-aware state is needed before any scale-generalization claim. Design work, 0 runs.
- **G-11 (new) — F3_rdd file lock:** WinError 32 on `F3_rdd` (large: all configurations; medium: default and `G-p4-sp128`); root cause undiagnosed. Zero-execution diagnosis first.
- **Overhead (EXP-014, DEC-054):** sampler component evidenced on 6/7 cells under the paired statistic; event-log component inconclusive on 4/7 at n = 10–15 (0 FAIL) — a larger paired study of the event-log arm is the remaining gap (G-12, new).
