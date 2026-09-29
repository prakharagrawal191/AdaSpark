# DEC-051 (SIGNED) | EXP-012 demo live rehearsal — 5 TRAIN-split runs, demo register line

**Scope:** `scripts/demo.py --mode live --allow-spark`: F5_mixed|small|seed0 (TRAIN, T_ref
calibrated) → B0 × 1 + B3 (G-p8-sp16) × 1 + frozen RL-s0 × 3 episodes, manifests to
results/experiments/x-demo/observations.jsonl (own demo line). Backup mode replays afterwards.

**Cost:** 5 TRAIN-split executions. SC6 stands at 483/500 (17 remain); these 5 are RECORDED on
the demo line and DISCLOSED here — they are TRAIN-split Spark executions of the same kind the
cap counts. Ledger after rehearsal: 488/500 reported (12 remain). No hidden spend.

**Pre-registered prediction:** "B0 slowest; B3 and RL-s0 cluster near the tuned time (RL-s0 agg
action is G-p8-sp16 by identity); all 5 usable."

**Guards:** frozen cell only; frozen policy only (no learning, epsilon 0.0); no overwrite
(backup replays); null/failure publishes as-is and the demo uses backup mode.

**Why:** PLAN §36 live demo is a Day-47 deliverable; a rehearsal without authorization would be
unledgered TRAIN spend.

**Status:** SIGNED 2026-09-29 — operator approval = GRANTED · Supervisor counter-signature: PENDING.
