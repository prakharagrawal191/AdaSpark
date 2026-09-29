# Results addendum (Days 41–45 draft) — extensive experimentation X1–X10 + Track R

**Status:** DRAFT for author merge (new file; no artifact/ledger/manifest touched).
**Integrity:** every number below traces to the listed committed-or-new ledger; null/negative
outcomes reported; no frozen threshold changed.

## 1. New measurements (all 0 SC6, own register lines)

- X1 B3 validation (7 runs, 7/7 usable): B3≡B1 byte-identical on 8/8 cells (fp 285ad990e5bc).
  SC3 reduces to RL-vs-B1 in practice (DEC-016B confirmed empirically).
- X2 sampler sweep (6 runs): +9.4/−7.3/+1.8% at 0.5/1/2 Hz (n=1) — no monotonic scaling.
- X3 elog pairs (6 runs): median pair −3.9%, inside 11.89% noise; confound bounded, not removed.
- X6 B0' AQE-on (35 runs, 30 usable): F2 L −14.2% outside noise (favors B0'); rest inside/reversed;
  F3 L INCOMPLETE 0/5 (same WinError32 — AQE-independent). No pooling (side-by-side only).
- X8 rematch (10 runs): B1 2.964 vs RL-s1 2.947 (−0.6%) — EXP-005 gap NOT replicated; drift confirmed.
- X10 SC7 pilot (20 runs): 2/4 within ±5% (medium yes +2.7/+4.7%; small no +6.8/+11.7%).
- X9 Taxi (20 runs): tuned −78%/−70% vs B0; RL-s0 agg action 8 == tuned (identity from artifact).

## 2. Threats to validity (P2 rewrite source)

- **Construct:** reward dominated by clipped time term; R3 efficiency terms secondary; A3 ablation
  compares variants (derived-only for R4-log). T_ref never in state (state.py:36–53; reward.py:216).
- **Internal:** queue-order drift (B1-vs-B4 ≤84% F1L; X8 same-day ≈0%); day-to-day drift large
  (F2 L B1 4.89→2.96); paired within-day designs only; no cross-day pooling.
- **Conclusion:** frozen Wilcoxon/δ/Holm not runnable at n=6/3 (DAY34 §5) — all main comparisons
  descriptive + noise-adjudicated; bootstrap CIs assume i.i.d. while lag-1 is 0.584–0.886 —
  block intervals flip 2/7 sysmon verdicts (honest intervals reported).
- **External:** single host / synthetic-first; Taxi pilot is one month, one workload shape,
  analogical state mapping — feasibility, not a validity row.
- **Coverage:** F3 L structural on all arms incl. B0'; F3_rdd|medium T_ref null; F4 B2 undefined
  by design; failures excluded consistently, favoring no arm.

## 3. Methods detail (P4 source)

- Interleaving: rep-major queues with seeded block shuffle (ORDER_SEED 31 / exp002 design);
  X8 ran B1 block then RL-s1 block (limitation: not interleaved — drift favors neither arm by design,
  both ran same-config).
- Clocks: Day-3 runner clock, warm-up excluded, for all in-repo runs; X9 Taxi uses the same
  warm-up-excluded perf_counter structure without event-log merge (stated limitation).
- Sample accounting: every run in observations.jsonl with run_id; no imputation; medians over
  usable reps only; <5 usable = INCOMPLETE, never ranked.

## 4. Related work (P3 source)

- Matrix verified at 30 entries (A1–J3). Still to add: Costa'19 (JMH measurement),
  Mytkowicz'10 (profiler accuracy), Burchell'23 + search-method paragraph + Kieker/MooBench
  quantitative comparison (author task — needs source access).
- SC7 result (2/4) belongs next to the Mytkowicz/Burchell discussion as primary evidence.

## 5. Reproducibility audit (EXP-011)

- X10 is the pilot: ±5% holds on medium cells, fails on small (short-runtime drift-sensitive).
- Full EXP-011 (60 planned) does not fit pilot scope; remaining SC6 (17) is TRAIN-only —
  a full TEST re-run needs its own register line + DEC (same pattern as DEC-047/048).
