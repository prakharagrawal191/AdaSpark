# Evidence Sufficiency Audit — Self-Adaptive Big Data Programming Using RL + Spark

**Date:** 2026-09-29 · **Base commit:** `a99ea47` (dirty tree, see §12)
**Policy:** Pre-register → authorize → run → analyze → report.
**Spend by this audit:** 0 Spark runs, 0 SC6, 0 historical edits.

Targets: (A) `manuscript/` case-study v1; (B) `docs/paper/icpe2027/main.tex`
+ `docs/report/PAPER_DRAFT_monitoring_overhead.md` (ICPE overhead paper).
Companions: `REQUIREMENT_DATA_COVERAGE.csv`, `EXPERIMENT_GAP_REGISTER.md`.

Integrity note: brief figures (109 X rows, SC6 488/500, X9 identity, BC=0.485,
lag-1 0.584–0.886, 4842/3228 rows, etc.) verified against UNTRACKED-but-present
files (`results/experiments/x*/`, `results/evaluation/x*_analysis.json`,
`exp009_robustness.json`, `exp009_synthesis.json`, DEC_047–051 drafts,
`scripts/demo.py`, `analyze_exp009_robustness.py`). Committed vs working-tree
sources distinguished below. Nothing untracked was committed/edited.

Method per claim: source artifact → raw JSONL → independent recompute (medians,
%-diffs, counts) → denominator/population/baseline → stats + CI → figure/table →
prose-vs-evidence grade. Validators re-run: validate_day31 (35/36, §12),
verify_paper_claims (55/55), verify_reproducibility (16/16), pytest unit (pass).
## 1b. Generalization (RQ3 H4 SC5) + ablations (RQ1/RQ4)

| Claim | Artifact | Raw? | n | Metric vs baseline | Stat | Status |
|---|---|---|---|---|---|---|
| SC5 evaluated | `exp006_analysis.json` | YES | 125 planned; B0 15 B2 5 RL-s0/s1 15 RL-s2 11 usable | advantage vs seen baseline NEVER FROZEN | n/a | NOT-EVALUABLE honest |
| F1/F4-large descriptive | same | YES | 3 cells 5/5; 2 F4 cells 0/5 | medians vs B0/B2/RL | descriptive | WEAK BUT DEFENSIBLE partial |
| Taxi transfer | `x9-taxi-pilot/observations.jsonl` (20 UNTRACKED) + analysis UNTRACKED | YES untracked | 2 cells × 2 arms × 5 | −78.05%/−69.82% vs B0 | descriptive | SUFFICIENT WITH LIMITATION feasibility |
| State effect isolated | `exp007_analysis.json` | YES | 126 TRAIN; A1 35+35 A2 35+21 | cross-seed agreement vs full ref | descriptive | OBSERVED NOT CAUSAL (Q0-confound) |
| Reward/action | `exp008_derived_ablation.json` | YES derived | 48 pairs | R3 vs time-only greedy | descriptive | DERIVED-ONLY (A5 DISABLED DEC-011) |
| Multi-step helps | — | NO | 0 | — | — | FUTURE WORK |

Taxi: full 2.030→0.445, half 1.561→0.471 recomputed. Substitution B0+B1+RL-s0
~30 authorized vs B0+TUNED 20 executed + rl_s0_identity (agg|S|le0 a8=G-p8-sp16
identical B1) documented in spec. One-month pilot, analogical mapping, no
event-log merge — disclosed. EXP-007: 0/4+0/2 agreement; neutral Q0 0.5 vs
EXP-002-derived ref blocks causality (stated).


Grades: A strong · B bounded (narrower wording) · C weak · D missing · F
contradicted (report as negative). Matrix statuses: SUFFICIENT / SUFFICIENT WITH
LIMITATION / WEAK BUT DEFENSIBLE / INSUFFICIENT / INCONCLUSIVE / NOT-EVALUABLE /
## 1c. Overhead (RQ5 SC6c2) — EXP-009 + ext + robustness + X2/X3

| Claim | Artifact | Raw? | n | Metric / baseline / stat | CI | Status |
|---|---|---|---|---|---|---|
| Training ≤500 | manifests + chk22 | YES | 483 counted | sum live TRAIN vs cap 500 | — | SUFFICIENT (§9F note) |
| Overhead ≤5% | `exp009_analysis.json` + `ext/analysis_ext.json` tracked | YES 4842/3228 | base 105; ext 4842 tot 3228 usable | O=100(medF−medB)/medB vs NO-SYSMON/NEITHER; 95% perc boot 4000 s0; DEC-042 interval rule | YES/cell | QUALIFIED PASS 6/7 iid; 4–5/7 block |
| √n model | same + robustness UNTRACKED | YES | 7 cells | obs/pred halfwidth; pre-reg falsification | — | FALSIFIED 7/7 (0.18–7.70×) |
| Sampler scaling | `x2 observations` (6 UNTRACKED) | YES | n=1/rate×arm | +9.4/−7.3/+1.8% vs NO-SYSMON | — | DESCRIPTIVE sign flips |
| Elog confound | `x3 observations` (6 UNTRACKED) | YES | n=3 | pair −3.9% vs 11.89% band | — | BOUNDED NOT REMOVED |
| Seed/BCa | robustness UNTRACKED | YES derived | seeds 0–4 + BCa s0 | halfwidth range | YES | SUFFICIENT stable |
| Dependence | same | YES | 21 series | lag1 ACF; CUSUM | — | SUFFICIENT 0.584–0.886 |
| Block honesty | same circular L=5/10/20 | YES | same | block halfwidth+verdict secondary | YES | SUFFICIENT flips 2 |

Seeds ≤0.44pp range; BCa agrees all 7. Blocks flip F5M-med (all L) + F5M-small
(L10/20); F1S INCONCLUSIVE throughout. BC 0.485<0.555 not bimodal (counts
128/14/72/25/3/3/1/../1 of 247). V2 first-PASS halts F1S n=29 F5S n=77 then
reverts — selection hazard; stable-PASS F5S n=220 F1S never.

MISSING / REQUIRES AUTHORIZED EXPERIMENT / FUTURE WORK.

## 1d. Reproducibility (SC7) + RL-specific + operational

| Claim | Artifact | n / metric | Status |
|---|---|---|---|
| Fresh ±5% | `x10 observations` (20 UNTRACKED) + analysis | 2x2x5; +2.71/+4.74 PASS med, +6.82/+11.73 FAIL small vs EXP-005 | PARTIAL 2/4 |
| Analysis reproduces | verify_reproducibility 16/16 | byte/content identity | SUFFICIENT |
| Full EXP-011 60 TEST | — | 0 | REQUIRES AUTHORIZED EXPERIMENT |
| State v1.5 (30 states; size manifest; missing→le0) | policies + audits | coverage full 5/30 A1 4/15 A2 2/2; M8 0.20 | SUFFICIENT WITH LIMITATION |
| Action 12 grid + 4-subset fingerprints | runs | 41/60 cells 68.3%; 16.8/9.8/8.4 ep/state/seed; restart on parallel change | SUFFICIENT WITH LIMITATION |
| Reward R3 frozen; T_ref not in state; floor 0.069 | reward.yaml + A3 | time dominates; 4/4 greedy agree | SUFFICIENT WITH LIMITATION |
| Learning Q a0.2 g0 e1→0.05; 84/49/42 ep; 0 failed; Q0-median; ckpt/25 | training analyses | bounded-budget holds; convergence NOT claimed | SUFFICIENT bounded |
| Evaluation frozen TEST sealed frozen greedy medians-of-5 | Day31 gate | B0/B1/B4 controls | SUFFICIENT |
| Demo 5 TRAIN B0 4.695 B3 1.424 ep1 1.417 G-p8-sp32 non-B3 ep2 1.730 ep3 1.765 | x-demo UNTRACKED | demo only | SUFFICIENT WITH LIMITATION |
| Resource/monitoring per-run CPU/mem/spill/CV; sampler ~3/s 1614 runs; elog 6/7 iid | manifests; ext rows | R3 refs 0.5/0.10; DEC-040s4 elog confound | SUFFICIENT WITH LIMITATION |

Weak numbers: F5S 0.86pp iid→16.94/19.15 L10/20 (20–22x); F5M-med 2.00→25.8–26.9
(13x); F1S 14.95→20–24. Cause: CUSUM same-rep shifts all arms (host drift);
quiet 0.63–2.06% vs contention to 75.38%; second-half CV ~1.2–1.4% vs ~15–16%
all-data. No unevidenced noise excuse.
## 2. Claim verdicts (38 substantive claims)

Supported as written (14): gate 4/4; T_ref 7/8+exclusion; 6-cell sums;
F4 noise pattern; UNDECIDED H2/H3; sqrt-n falsified 7/7; lag-1 0.584–0.886;
6/7 PASS iid; block-flip disclosure; BC 0.485 non-bimodal; F3-large structural;
T_ref-null; 16/16 corroboration; 483/500 ledger (§9F).
Narrower wording (9): B3≡B1 validation-cells untracked→commit; X6 descriptive
no-pooling 6+1; X9 one-month pilot analogical; X10 fast/medium only; monitoring
cheap qualified iid6/7 block4–5/7; tuned-beats-B0 incl learner static-best;
RL≈B4 descriptive; budget 483+5 demo; ICPE controlled single-host+1 pilot.
Explicit limitation (6): single-host; synthetic-first; short-job resolution
(F5S 716); elog confound; X8 non-interleaved (B1-block then RL-block same-config
favors neither but weaker); Taxi Day-3 analog no elog merge.
Needs experiment (4): full SC7 60 TEST own line+DEC; AQE pooled interaction
(FORBIDDEN now, needs pre-reg); 2nd public family; dependence-aware stopping
## 3. Metric + stats audit

Execution time median-of-5 runner clock 2 warmups: prereg primary; denom usable
only (<5 INCOMPLETE never ranked); lower-better; n=5 thin/cell pooled 37–721;
CV 2.6–13.6%; AQE-off matched path/seeds/warmup/timeout queue-index; L2 exact.
%-diffs: formula exact; X8 denominators separated (§9A); 11.89% EXP-001 worst-CV
descriptive bar (not test) apt at n=6/3. Throughput derivable not headlined —
correctly absent. Resource: per-run fields; aggregated only R3 refs 0.5/0.10;
no standalone utilization claim; ms §22 Fig22 architectural labelled.
Reward R3 exact weights/clip/fail−1 per-cell T_ref; floor 0.069; efficiency
secondary (A3 4/4). M8 0.20 vs 0.70 valid FAIL→3 arms. Overhead O paired-median
exact; iid boot valid iff independent — VIOLATED (lag-1 0.584–0.886) → block
honest sensitivity 2 flips; disclosed both mss. SC7 ±5% pilot 2/4 valid PARTIAL.
Ledger manifests sum 483 chk22 green; +5 demo own line (488 TRAIN-split total;
ledger 483 per DEC-038/046, §9F). Means/SD: medians primary; IQR/CV present; no
means-claim. Wilcoxon/δ/Holm correctly NOT run (n=6/3 DAY34§5). CI 95% perc
boot 4000 s0; BCa agrees; circular block L=5/10/20 secondary labelled; primary
NEVER switched (DEC-044 D1; paired exploratory appendix only, never deciding).
## 4. Missing types; 5. New-run decision; 6. Reviewer test; 7. Gaps

Missing (claim-gated): variance COVERED (EXP-001+trajectories); repeatability
PILOT X10 2/4 full missing G-01; rematch COVERED X8/X1; seeds COVERED 3+5;
workload/size PARTIAL +Taxi no 2nd family G-02; drift MEASURED no controlled
warm/cold G-03 (no causal drift claim made — correctly confound); elog/monitor
COVERED+X2/X3 clean-removal impossible permanent bound; AQE PILOT side-by-side
pooled FORBIDDEN G-04; policy/action/reward instability COVERED as observed;
leakage guards verified chk05–10/18–19 Taxi external-unseen analogical; T_ref
DIAGNOSED backfill TRAIN DEC G-05; telemetry design-only G-06; hygiene G-07.
New runs: ZERO by this audit. DEC-047–051 ONLY untracked drafts absent ledger
(ends DEC-046) → ledger absence = NOT established; X1/X2/X3/X6/X8/X9/X10/demo
provenance-orphaned until committed (G-00 P0, 0 runs). Budget: brief 488/500
(12 left) vs ledger 483/500 (17 left): reconciled 483 SC6-counted +5
demo-disclosed = 488 TRAIN-split total. No ledger-authorized high-gain run fits
cap; G-01–G-06 need new DECs → DO NOT RUN (drafts gap register §B; stability
gated never first-PASS never until-significant).
Reviewer: −0.6% = x8 JSONL (2.964 vs 2.947 recomputed −0.565%); independent n
<< nominal (blocks quantify); noisy = regime contention (CUSUM same-rep quiet
0.63–2.06% vs 75.38%; analysis_ext drift_diagnostic); B1 validation-frozen
DEC-012/013 artifact 0a0ecbe G-p8-sp16; generalizable NO broad (6 TEST descr;
Taxi pilot; SC5 NOT EVALUABLE); replicate F2L NO medium YES 2/4 overhead 6/7→2
flip; serial conceded quantified; raw tracked EXP-002/005/006/009-base/ext
(4.8MB) X/robust/synth untracked deposit pending DEC-045 HELD; reproduce 16/16
## 9. Provenance issues (brief §29)

A. X8: fresh −0.57% same-config same-day; −8.6% RL-s1 vs B4 EXP-005 in-noise
different baseline; −24.7% (B1 4.888 vs 3.678 in fig desc = −24.75%) ONLY fig
desc unsourced — G-08 correct/drop; audit uses −0.57% + −8.6%. B. X1: fp
f857d8de all 7 rows verified; SparkConfig 285ad990 8/8 CLAIMED no 8-cell
artifact (X1 = 7 validation) — narrow to 7/7 executed (G-08). C. X9: auth ~30
B0+B1+RL-s0 vs exec 20 B0+TUNED + rl_s0_identity — spec documents; feasibility
holds. D. X6 spec.json 1 instance (F4-small-s4) vs ledger 7 cells — STALE/PARTIAL
amend spec no rows (G-08). E. Track R path hardcoded Temp/opencode vs committed
results/evaluation — DOCUMENTED (G-08; hand-copy step unrecorded → G-00). F. SC6
488 vs 483 = 483 SC6-counted +5 demo-disclosed (§5). G. Raw X git-ignored
(results/logs/plots/data except exp-002 + evaluation json): X/robust/synth/figs
UNTRACKED → Availability committed-artifacts OVERSTATED for X (G-00/G-08 commit
or reword deposit-pending).
## 10. Figures/tables; 11. Availability; 12. Hygiene; 13. Readiness; 14. Report

Figs: ICPE 2 tracked PDFs re-render identical hash-masked; 55/55 traced 21/21
in-page green. ms v1 32/15: measured exp002/exp005/exp007/exp009 identical L2;
X-figs values recomputed OK provenance-orphaned G-00. Axes honest (0 bars;
log-log 1/sqrt ref dashed); negatives plotted. Conceptual Figs 1–20/24–32
architectural non-measured correctly. A4 derived labelled. Eqs 1–10 editable
match code. Refs: ms 39 (band 30–50 outline.md; planning 8–15 vs 30–50 RESOLVED
for final band — 39 complies; ≥80% 2020–25 journal count author task G-09;
foundations [1]–[5] justified + ICPE thread [27]–[30]). ICPE 5 verified +
DEC-044 D5 novelty honored (no priority for non-independence/steady-state).
Availability: code complete src+scripts + policy JSONs; raw EXP-002/009-base/ext
TRACKED (ext 4.8MB tracked — corrects outside-VC boilerplate; HELD via DEC-045
not absence); X/robust/synth untracked → honest today = committed+tracked 16/16
plus working-tree pilots deposit-pending DEC-045 D1–D11 approved D4 ORCID
pending HELD to ICPE 2027-01-25; no URL invented; rehearsal 567+10582 files
green; videos placeholder G-09; env Win11/Py3.11.9/J17/Spark3.5.9/24c/6GB
local[2] pinned Tab.9 + env report.
Hygiene: chk26 FAILS unknown 5 new JSON (allow-list pre-R/X) FIX new DEC cover;
chk27 msg DEC-012/013 vs allow DEC-046 bundle; registry.csv stale H1/G-07;
empty env/runner placeholders H2; §9/G-08 doc repairs; budget quote both + §5
sentence.
Readiness: ms Setup A Metrics A(block-limit) Results B (X-P0 blocks A)
Comparative B Trust B Limitations A Appendix A Availability B Refs B Diagrams A
prospective labelled Videos D. ICPE body A− 6pp self-contained. Overall
CONDITIONAL GO bounded story; NO-GO superiority/broad-general/unqualified-cheap
(neither ms claims). BLOCKING = governance: commit DEC-047–051 + chk26 DEC,
G-08 repairs, submit. No SC6 spend.
§32 Report: 38 claims: 14 full 9 bounded 6 limited 4 new-exp drafted 3 negative
1 defer + X G-00 overlay. Grades A14 B11 C6 D3 (full SC7, 2nd family, pooled AQE)
F3 (F2L repl, sqrt-n, single-policy) + G-00 overlay 7. Metrics §3+stats. Causes
evidenced; no unevidenced excuse. New runs ZERO (unauthorized; drafted PENDING).
Budget before 483/500 ledger; +5 demo = 488 TRAIN-split; audit 0; after 483
(17 left) + demo closed. Missing §7/G-00–G-09. Readiness §13 conditional GO.
DoD 20: 1–2 traced ✓ 3–5 quantified/evidenced ✓ 6–8 gaps, 0 unauthorized, N/A
new rules ✓ 9 zero edits ✓ 10–12 X8/dependence/negatives visible ✓ 13–15 honest
availability clear provenance (G-00) sourced figs ✓ 16 narrowed ✓ 17 reconciled
✓ 18 listed ✓ 19 chk26 FAIL disclosed+fix ✓ 20 this decision+evidence ✓.
Bottom line: ready to submit bounded feasibility (tabular RL ≤483 matches
equal-budget search trails static disagrees seeds →3 arms; overhead small iid
fragile blocks 4–5/7; sqrt-n falsified ~3000 avoidable; Taxi feasibility).
Single block governance not science. No SC6 spend.


+55/55 + IDs; no more runs: no authorized gain fits cap.
Gaps: G-00 provenance orphan ALL X P0 0 runs NEEDS LEDGER COMMIT; G-01 SC7-60
TEST P1 60 own line NEEDS DEC; G-02 2nd family P2 ~30–60 NEEDS DEC; G-03 drift
controlled P3 ~20–40 NEEDS DEC if claimed; G-04 AQE pooled P2 new pre-reg NEEDS
DEC; G-05 T_ref backfill P2 TBD NEEDS TRAIN DEC; G-06 telemetry P3 design exempt;
G-07 hygiene P3 0 bundle; G-08 doc repairs (X8 −24.7% desc, X1 8/8 vs 7, X6 spec
1 vs 7, R hardcoded path, availability overstatement) P0 0; G-09 refs/videos P3.

Registered unpaired diff-of-medians; reps matched by interleave → paired 1.2–4.8x
tighter (35.7x F1S 50/50 split) exploratory DEC-044 D2/D3 future primary.
Outliers retained; <5 INCOMPLETE only. No multiple-comparison correction owed
(no inference); 6-cell sums descriptive illustration. ACF Eq8 CUSUM Eq9 BC Eq10
match code. Stabilization canonical/V1/V2 reported.

prospective (retro 2.9–4.5x/2976 runs is NOT a rule — F5S PASS→INCONC→PASS).
Contradicted/negative (3): F2L −8.6% replicability (X8 −0.6% drift FALSIFIED);
sqrt-n prediction (0.18–7.70x FALSIFIED); single-policy promotion (M8 0.20 vs
0.70 FAILED→3 arms). Remove/defer (1): pooled RL-vs-B0′ superiority (FORBIDDEN
side-by-side only). X-family blocked on G-00 provenance commit (7 items).
Feasibility Grade A bounded: learnable ≤500, matches equal-budget search,
trails static, disagrees seeds. Superiority/generalization/unqualified-cheap
Grade C/D/F — neither manuscript claims them.

