# DAY35 — EXP-006 final descriptive analysis (corrected raw-ledger coverage)

Date: 2026-09-16 (UTC). Authority: raw production ledger
`results/experiments/exp-006/observations.jsonl` (SHA256
`be270c0be60be735e130165b8650d62272aed80f94aba1932140a706ad2eb577`).
Prior coverage audit superseded by authoritative reconciliation; existing
`results/evaluation/exp006_analysis.json` verified against the raw ledger and
corrected in place (B2 summary inversion fix; no raw-ledger/spec mutation).

## 1. Input integrity

- Ledger: 125 rows, queue_index 1–125 contiguous, no duplicates.
- Classification (actual ledger tokens): successful (`COMPLETE` + usable +
  runtime) = 61; failed (`MISSING` + !usable + config present) = 44;
  undefined (`NOT_EXECUTED` + !usable + B2 × F4_ski + DEC-019 error) = 20;
  unclassified = 0.
- Spec fingerprint `0f078dc2…eb54` and queue fingerprint `c88ba20c…917d4c`
  unchanged; selected-cells fingerprint `5fea06f2…17e5` verified.
- Spark executions during analysis = 0.

## 2. Corrected coverage (authoritative, raw-ledger derived)

| Cell | B0 | B2 | RL-s0 | RL-s1 | RL-s2 |
|---|---|---|---|---|---|
| F1_agg\|large\|s0 | 5/5 usable | 5/5 usable | 5/5 usable | 5/5 usable | 5/5 usable |
| F4_ski\|large\|s0 | 5/5 usable | UNDEFINED (5) | 5/5 usable | 5/5 usable | 5/5 usable |
| F4_ski\|large\|s4 | 5/5 usable | UNDEFINED (5) | 5/5 usable | 5/5 usable | 1/5 usable, 4 failed |
| F4_ski\|medium\|s3 | 0/5 usable, 5 failed | UNDEFINED (5) | 0/5 usable, 5 failed | 0/5 usable, 5 failed | 0/5 usable, 5 failed |
| F4_ski\|small\|s3 | 0/5 usable, 5 failed | UNDEFINED (5) | 0/5 usable, 5 failed | 0/5 usable, 5 failed | 0/5 usable, 5 failed |

Per-arm: B0 15/10/0; B2 5/0/20; RL-s0 15/10/0; RL-s1 15/10/0; RL-s2 11/14/0
(successful/failed/undefined of 25).

## 3. Complete cells (<5 usable = INCOMPLETE; 12 complete)

- F1_agg|large|s0: B0, B2, RL-s0, RL-s1, RL-s2.
- F4_ski|large|s0: B0, RL-s0, RL-s1, RL-s2.
- F4_ski|large|s4: B0, RL-s0, RL-s1.
- F4_ski|medium|s3: none eligible. F4_ski|small|s3: none eligible.
- RL-s2 on F4 large s4 is incomplete (1/5); no median fabricated.

## 4. Valid five-repetition medians (execution_time_s, seconds)

F1_agg|large|s0 — B0: 50.0035 (n=5: 44.9990, 49.1862, 50.0035, 50.0193,
52.5056). B2: 9.5379 (9.2645, 9.4767, 9.5379, 9.8952, 10.0373). RL-s0:
9.4241 (9.2632, 9.3740, 9.4241, 9.4599, 9.5413). RL-s1: 9.3587 (9.1035,
9.2076, 9.3587, 9.5157, 9.5772). RL-s2: 9.5217 (9.4330, 9.4940, 9.5217,
9.5472, 9.8617).

F4_ski|large|s0 — B0: 15.6217 (14.3150, 15.3240, 15.6217, 15.7353, 15.7647).
RL-s0: 7.6218 (7.5215, 7.5399, 7.6218, 7.6306, 7.6653). RL-s1: 7.6345
(7.6192, 7.6246, 7.6345, 7.6739, 8.0394). RL-s2: 7.5550 (7.4272, 7.5052,
7.5550, 7.5639, 7.5792).

F4_ski|large|s4 — B0: 14.6594 (12.5010, 14.6139, 14.6594, 15.7124, 15.7688).
RL-s0: 7.6842 (7.5724, 7.5852, 7.6842, 7.6971, 7.7785). RL-s1: 7.5564
(7.4525, 7.4545, 7.5564, 7.6181, 7.7203).

Descriptive single run only (not a median): RL-s2 on F4 large s4, one
successful observation 7.5360 s; cell incomplete; descriptive only. No
medians exist for F4 medium s3 or F4 small s3 (all executable arms 0/5).

## 5. Descriptive comparisons (denominators explicit)

- F1 large s0 (all five arms complete, 5/5 each): the four tuned arms cluster
  near ~9.4–9.5 s medians; B0 median 50.00 s (n=5). Descriptive only.
- F4 large s0 (B0 + three RL arms complete, 5/5 each): B0 median 15.62 s;
  RL-s0 7.62 s; RL-s1 7.63 s; RL-s2 7.55 s (each n=5). Descriptive only.
- F4 large s4 (B0 + RL-s0/RL-s1 complete, 5/5 each): B0 median 14.66 s; RL-s0
  7.68 s; RL-s1 7.56 s (each n=5). RL-s2 incomplete (1/5) and excluded.
- No pooling across incomplete cells.

## 6. B2

One eligible cell / five repetitions: F1_agg|large|s0 only (median 9.5379 s,
n=5). Undefined on all four F4 cells (20 structural undefined rows, not
performance failures). Not ranked across the five-cell experiment; five
repetitions of one cell are not five independent TEST cells (DEC-022 §5).

## 7. RL-s2

11 successful / 25 attempted; 14 failed. Complete cells: F1 large s0 and F4
large s0 (5/5 each). Incomplete: F4 large s4 (1/5), F4 medium s3 (0/5), F4
small s3 (0/5). No claim of better or worse.

## 8. Failure limitation

F4 medium s3 and F4 small s3 are not evaluable under the frozen
five-repetition rule: every executable observation failed (5/5 MISSING per
arm, 40 failures total across the two cells). Execution failures are reported
as a coverage limitation, not as a policy-performance finding.

## 9. Generalization interpretation

EXP-006 provides complete five-repetition evidence on the F1 large-s0 cell
and on the large-scale F4 cells where execution completed. The medium- and
small-scale F4 cells are not evaluable under the frozen five-repetition
completeness rule because all executable observations failed. Consequently,
EXP-006 provides partial descriptive evidence about generalization to the
unseen F4 family, but it does not establish generalization across the full
selected F4 scale range.

## 10. SC5

NOT EVALUABLE. The seen-relative-advantage baseline was never frozen before
EXP-006; none constructed from TEST data or EXP-005.

## 11. Inference

Descriptive only. No Wilcoxon, Cliff's delta, Holm, p-values, alpha, or
effect-size thresholds.

## 12. EXP-005 relationship

EXP-005 supplied descriptive evidence on its frozen TEST set; EXP-006 is a
separate descriptive generalization slice. Observations never pooled.

## 13. Reproducibility and validation

- Analysis rerun deterministically from the sealed ledger (no RNG, no Spark);
  byte-identical output verified across consecutive runs; analysis fingerprint
  recorded in `exp006_analysis.json`.
- Validation: 125 rows; 61/44/20; corrected matrix; 12-cell complete set
  exact; B2 = 1 eligible cell / 4 undefined cells; RL-s2 = 2 complete cells;
  no fabricated medians; ledger/spec unmutated.
