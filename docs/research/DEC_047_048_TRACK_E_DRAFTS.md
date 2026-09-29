# Track-E decision drafts — SIGNED 2026-09-29, runs authorized under guards below

## DEC-047 (SIGNED) | EXP-005b B0' AQE-on execution authorization — 35 runs, own ledger

**Scope:** implement B0' driver path, execute 7 frozen TEST instances × B0' × 5 reps = 35 runs on a dedicated AQE-on register line (0 charged to SC6 training cap, which stays 483/500).
**Pre-registered prediction (to be frozen before first run):** "B0' (AQE-on default) beats B0 on shuffle-heavy cells by ≥5% median; RL-vs-B0' pooled comparison is FORBIDDEN by the no-pooling rule (runtime-adaptive vs static arms) — reported side-by-side only."
**Why:** settles the PLAN:72 AQE-on/off contribution; the largest single claim upgrade available (task X6).
**Guards:** TEST-crossing under DEC-014 pattern; `authorize_test_b0prime` entry point only; TRAIN semantics and SC6 ledger unchanged; any deviation voids the authorization.
**Status:** SIGNED 2026-09-29 — operator approval = GRANTED · Supervisor counter-signature: PENDING (runs proceed under operator authority; supervisor sign-off follows M2-freeze path).

## DEC-048 (SIGNED) | Validation-scoped confirmations — X1/X2/X3, SC6-exempt line

**Scope:** E1 (B3 ≡ B1 confirmation, ~8–16 runs), E5 (sampler sweep, ~30–60 runs), E6 (eventlog confound pairs, ~20–40 runs); all VALIDATION split, seed 3, AQE-off; own register line, 0 to SC6; frozen analysis code reused (`analyze_exp009.py` estimator, median-of-5 rule).
**Pre-registered predictions (to be frozen before first run):** X1: "B3 byte-identical to B1 on all validation cells." X2: "Overhead sub-linear in sampling rate; no verdict changes." X3: "Config confound < 1pp on decided cells."
**Why:** closes the three cheapest honest gaps (SC3, single-point sampler, elog confound) without touching TEST or SC6.
**Guards:** any TEST-cell, AQE-on, or TRAIN-charged run voids the authorization; null outcomes publish as-is.
**Status:** SIGNED 2026-09-29 — operator approval = GRANTED · Supervisor counter-signature: PENDING.
