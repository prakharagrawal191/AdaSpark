# Day 34 — EXP-005 TEST Analysis (sealed ledger, no new Spark)

**Status.** Analysis of the sealed 245-row TEST ledger. **0 Spark
executions.** No queue/spec/artifact/policy/config changed. No winner
selected by re-tuning; every comparison is on frozen arms over eligible
common cells, medians over 5 usable reps only (DEC-017 item 5), noise-bound
by DEC-018 Decision F (EXP-001 worst-cell CV = **0.1189**: within-cell arm
differences below ~12% are not independently established effects).
Machine companion: `results/evaluation/exp005_analysis.json`
(SHA256 `f1db5634…c6fa8`).

**Inputs (fingerprints).** `observations.jsonl` SHA256
`d928cf5d69fe5af10aac31a2e2a69723278ee0d22729d8109e8b95ae703d3ae1`
(245 rows, 1–245 contiguous, no dups; every row matches its frozen queue
entry; first-115 block SHA `e97c614d…3a79` unchanged).
`spec.json` queue 245, `artifact_id e3c90284…98449`,
`instances_fingerprint 1c33975a…c815` = `exp005_instances.json`
(7 instances). `baseline_selection.json` B1 = `G-p8-sp16`; B2 map
`{F1_agg: G-p8-sp16, F2_join: G-p8-sp16, F3_rdd: G-p8-sp64, F5_mixed:
G-p8-sp32}`; `b4_selection.json` B4 = `G-p8-sp16` (TRAIN, frozen).
PLAN H2/H3 + SC2–SC4 name Wilcoxon signed-rank + Cliff's δ + Holm
(§22–23); with only 6 eligible common cells (3 for B2 pairs) and no
frozen minimum-n/α/δ-threshold/mapping for this shape, those inferential
tests are **not run** — descriptive common-cell comparison only.

## 1. Coverage (35 rows/arm)

| Arm | Usable | Failed | INCOMPLETE | Complete/7 | Incomplete cells |
|---|---:|---:|---:|---:|---|
| B0 | 30 | 5 | 0 | 6 | F3_rdd\|large\|s3 (0/5 failed) |
| B1 | 30 | 5 | 0 | 6 | F3_rdd\|large\|s3 |
| B2 | 15 | 5 | 15 | 3 | F3 L failed; F4 L/s3, F4 S/s4, F4 M/s4 undefined |
| B4 | 30 | 5 | 0 | 6 | F3_rdd\|large\|s3 |
| RL-s0/s1/s2 | 30 each | 5 each | 0 | 6 each | F3_rdd\|large\|s3 |

Totals: 195 usable + 35 failed + 15 INCOMPLETE = 245.

## 2. Incomplete cells (structural, never rankings)

* **F3_rdd|large|s3 (indices 71–105): all 7 arms 0/5, INCOMPLETE.**
  `Py4JJavaError … PythonRDD.collectAndServe … sortPartition …
  PermissionError: [WinError 32]` (Windows sort/spill lock). Excluded from
  every pooled denominator for every arm.
* **B2 × F4_ski, undefined-by-design (DEC-019):** F4 L/s3 (116–120),
  F4 S/s4 (186–190), F4 M/s4 (221–225) — 0 Spark, `NOT_EXECUTED`, null
  config each. Failed ≠ undefined; the two categories are never merged.

## 3. Eligible cell medians (seconds; complete cells only)

| Instance | B0 | B1 | B2 | B4 | RL-s0 | RL-s1 | RL-s2 |
|---|---|---|---|---|---|---|---|
| F1_agg L s3 | 49.227439 | 10.087462 | 16.436034 | 18.558917 | 14.572057 | 15.645406 | 21.784035 |
| F2_join L s3 | 25.658124 | 4.888028 | 4.347029 | 4.026467 | 3.713726 | 3.678392 | 3.988509 |
| F3_rdd L s3 | — | — | — | — | — | — | — |
| F4_ski L s3 | 17.198124 | 4.421086 | — | 4.308031 | 7.457355 | 7.010272 | 6.993025 |
| F5_mixed L s3 | 38.106132 | 8.839050 | 9.663165 | 9.332184 | 8.924736 | 9.470902 | 9.218204 |
| F4_ski S s4 | 2.318799 | 0.460338 | — | 0.446927 | 0.565373 | 0.596443 | 0.601385 |
| F4_ski M s4 | 9.870819 | 1.619826 | — | 1.665195 | 2.915156 | 2.797510 | 2.877657 |

Configs on usable cells: B0 = `B0`; B1/B4 = `G-p8-sp16` everywhere;
B2 = `G-p8-sp16` (F1, F2), `G-p8-sp32` (F5); RL = `G-p8-sp16` (F1, F2),
`G-p2-sp16` (all F4), `G-p8-sp32` (F5). No B2 value on F4 exists.

## 4. Common-cell comparisons (paired; no imputation)

6-cell sums (B0/B1/B4/RL only): B0 142.3794 · B1 30.3158 · RL-s0 38.1484
· B4 38.3377 · RL-s1 39.1989 · RL-s2 45.4628 (descriptive scale proxy).
3-cell sums (B2-eligible F1 L/F2 L/F5 L): B1 23.8145 · RL-s0 27.2105 ·
RL-s1 28.7947 · B2 30.4462 · B4 31.9176 · RL-s2 34.9907 · B0 112.9917.
Per-cell RL-best vs best-static: F1 L +44.5% (B1 wins; B1-vs-B4 −45.6%
on the identical config = queue-order confound, B1 idx 6–10 vs B4 idx
16–20, not a config effect); F2 L −8.6% RL-s1 (inside noise); F4 L
+62.3%, F4 M +72.7%, F4 S +26.5% static (all outside noise);
F5 L +1.0% (inside noise). B2: +62.9% F1 L (outside), −11.1% F2 L and
+9.3% F5 L (inside/borderline). B1-vs-B4 same-config spread
(−45.6%…+21.4%) bounds the environment drift on long cells.

## 5. Findings (bounded)

1. B1 lowest 6-cell descriptive sum (30.32); RL-s0 38.15 ≈ B4 38.34;
   B0 far slowest (142.38). Only F1 L and B0 gaps clearly exceed noise.
2. Statics converge on TEST: B1 = B4 = `G-p8-sp16` everywhere
   co-executed; B2 matches on F1/F2.
3. RL seeds timing-spread on identical choices (F1 L 14.57/15.65/21.78).
4. Only above-noise RL-vs-static pattern: F4 `G-p2-sp16` vs `G-p8-sp16`
   (F4 L/M/S); all other B1/B4/RL gaps inside 11.89%.
5. F3 L missing for all arms; B2/F4 undefined for B2 only — excluded
   consistently, favouring no arm.
6. **No superiority/non-inferiority/hypothesis decision established:**
   frozen inferential tests not runnable at n=6/3 with no frozen
   minimum-n/alpha/mapping; H2/H3/SC2–SC4 undecided.

## 6. Claims NOT supported

"RL is superior", "RL failed", "RL converged", "B1 is universally best",
"B2 is worse because of F4", "B4 is optimal", "method improves Spark",
"statistically significantly better", "H2/H3 proved", "SC2–SC4 decided"
— none supported (§4–5, noise band, coverage gaps).

## 7. Reproducibility / validation

Read-only stdlib medians; rerun byte-identical (sums verified to <1e-6
modulo 4-decimal rounding). Raw SHA unchanged `d928cf5d…3ae1`. Tests:
`test_exp005_strategies` + `test_day31_evaluation` 46 passed + 1 skipped.
No Spark, no ledger write, no other experiment.
