# Track-F decisions — SIGNED 2026-09-29, runs authorized under guards below

## DEC-049 (SIGNED) | EXP-011 SC7 reproducibility pilot — 2 TEST cells × 2 arms × 5 reps = 20 runs, own ledger

**Scope:** fresh re-runs of F4_ski|small|s4 + F4_ski|medium|s4 × B0 + B1 × 5 reps on TEST via the
EXP-005 purpose-scoped guard pattern (frozen instances only), AQE-off, own register line
(results/experiments/x10-sc7-pilot/), 0 to SC6. Adjudication: fresh median vs EXP-005 median
within ±5% per cell-arm (SC7 rule); 4/4 must pass for a PASS pilot.

**Pre-registered prediction:** "3/4 or 4/4 cell-arms reproduce within ±5% (fast cells, low CV)."

**Why:** first SC7 evidence (EXP-011 empty); X8 showed large day-to-day drift on F2 L, so a
same-week pilot on fast cells is the honest scope before any 60-run claim.

**Guards:** TEST-crossing under DEC-014 pattern; frozen instances only; B0/B1 static only
(no policy, no retraining); null (miss) publishes as-is and caps SC7 claims to pilot scope.

**Cost:** 20 TEST runs, own ledger, 0 SC6.

**Status:** SIGNED 2026-09-29 — operator approval = GRANTED · Supervisor counter-signature: PENDING.

## DEC-050 (SIGNED) | EXP-010 external-dataset pilot (NYC Taxi) — new data + family mapping

**Scope:** download one fixed NYC Taxi month (~1–2 GB Parquet) to SPARKRL_DATA_ROOT-external;
new datagen extension mapping Taxi columns onto join/agg workload shapes (1 family × 2 scales);
run B0 + B1 + RL-s0 × 5 reps (30 runs) on the new cells as TEST-unseen-generalization pilot.
If download fails: pseudo-public substitution per PLAN §18 (non-synthetic profile, documented).

**Pre-registered prediction:** "tuned arms cluster as on F1 L; B0 far slowest; no superiority claim —
pilot establishes transfer feasibility, not a verdict."

**Why:** EXP-010 empty; single host / synthetic-only is the sharpest external-validity attack.

**Guards:** new data manifest + checksums before any run; new cells classified TEST-unseen;
frozen policies only (no training on Taxi); own ledger, 0 SC6; substitution path declared upfront.

**Cost:** ~30 TEST runs + download/build time; own ledger, 0 SC6.

**Feasibility note (2026-09-29):** no Taxi data on disk; families frozen at 5 (F1–F5);
this is new capability (resolver + workload mapping), the largest build item in the backlog.

**Status:** SIGNED 2026-09-29 — operator approval = GRANTED · Supervisor counter-signature: PENDING.
