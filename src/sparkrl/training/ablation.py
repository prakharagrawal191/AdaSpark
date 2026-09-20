"""EXP-007 A1/A2 frozen ablation scope (DEC-023 as amended by DEC-025, Day 35).

A NON-EXECUTING configuration module: it encodes the DEC-023 training scope
as data and pure arithmetic, and it never plans, builds or launches anything.

Frozen by DEC-023 (methodology only) and amended by DEC-025 (exactly ONE
field: episodes per seed 42 -> 35; ``EXP-007 execution authorized = NO``):
* A1 = the frozen ``state-v1`` encoder (15 states, context only);
* A2 = the frozen feedback-only ``state-v2`` space (2 states);
* both arms train on the 7 eligible TRAIN/T_ref cells (``F3_rdd|medium``
  stays excluded because ``t_ref`` is null), dataset seed 0;
* A1 seeds = {0, 1}; A2 seeds = {0, 1}; seed 2 is NOT used (DEC-023
  section 7 disclosed compromise);
* 35 planned episodes per seed = 5 COMPLETE round-robin epochs x 7 cells
  (DEC-025 sections 3-4 amend DEC-023 section 6's 42 = 6 x 7; 35 = 5 x 7);
* planned live executions: A1 = 2 x 35 = 70; A2 = 70; combined 140;
* remaining TRAIN cap: 164 (authoritative figure of DEC-025 section 1;
  DEC-023 section 8's frozen "remaining = 184" stands as recorded history);
  headroom: 164 - 140 = 24.

The 500 cap (PLAN section 16 / SC6) is NOT raised here, and this module
performs zero live executions and creates no TEST artifact (DEC-023
section 9: EXP-007 is TRAIN-only).

FINGERPRINT DISCLOSURE (DEC-025 section 11 / DEC-024 section 6): the SHA-256
fingerprints recorded in DEC-024 section 6 are VOID for every file changed by
this 42 -> 35 amendment (this module among them), because those files changed
after DEC-025 was recorded. Re-verification is required at the future EXP-007
authorization gate. DEC-024 itself is NOT rewritten.
"""
from __future__ import annotations

from sparkrl.agent.q0 import (ABLATION_VARIANTS, VARIANT_A1, VARIANT_A2,
                              build_neutral_q0, neutral_state_schema)

EXP007_ID = "EXP-007"

# DEC-023 section 7: two seeds per ablation, NOT the main study's three.
ABLATION_SEEDS: tuple[int, ...] = (0, 1)

# DEC-023 section 6 as amended by DEC-025 sections 3-4: 35 planned episodes
# per seed = 5 COMPLETE round-robin epochs x 7 TRAIN cells (35 = 5 x 7). No
# new scheduling mechanism: the epoch count is exactly episodes / cells.
ABLATION_EPOCHS = 5
ABLATION_TRAIN_CELLS = 7
ABLATION_EPISODES_PER_SEED = ABLATION_EPOCHS * ABLATION_TRAIN_CELLS   # 35

# DEC-025 section 1 budget arithmetic (SC6 cap is frozen, never raised).
# NOTE: DEC-023 section 8's frozen figures - remaining = 184 and headroom = 16
# - stand unchanged as recorded history in DEC-023 and are NOT edited. DEC-025
# section 1 re-derives the authoritative spent figure (336 = 232 manifest sum
# over results/training/**/manifest.json + 84 from DEC-016 C + 20 from
# EXP-001) and the authoritative remaining figure (500 - 336 = 164), and
# section 4 freezes the amended headroom (164 - 140 = 24). The forward-looking
# figures encoded here are DEC-025's; the ledger is never re-derived here.
SC6_LIVE_CAP = 500
SC6_LEDGER_CITED = "336/500"   # DEC-023 s.13 / DEC-025 s.1 evidence
SC6_REMAINING = 164            # authoritative figure of DEC-025 section 1


def planned_executions(variant: str) -> int:
    """Planned maximum live executions for ONE ablation arm (70)."""
    if variant not in ABLATION_VARIANTS:
        raise ValueError(f"unknown ablation variant {variant!r}; "
                         f"expected one of {list(ABLATION_VARIANTS)}")
    return len(ABLATION_SEEDS) * ABLATION_EPISODES_PER_SEED


def combined_planned() -> int:
    """A1 + A2 planned maximum (140)."""
    return sum(planned_executions(v) for v in ABLATION_VARIANTS)


def sc6_remaining() -> int:
    """Remaining TRAIN executions before any EXP-007 run (164, DEC-025 s.1)."""
    return SC6_REMAINING


def sc6_headroom() -> int:
    """Remaining cap minus the combined planned maximum (24)."""
    return sc6_remaining() - combined_planned()


def exp007_budget_summary() -> dict[str, int | str | list[int]]:
    """The DEC-025 sections 1/4 budget table as a plain dict (tests/reports)."""
    return {
        "experiment_id": EXP007_ID,
        "planned_max_per_seed": ABLATION_EPISODES_PER_SEED,
        "seeds_per_variant": list(ABLATION_SEEDS),
        "a1_planned_max": planned_executions(VARIANT_A1),
        "a2_planned_max": planned_executions(VARIANT_A2),
        "combined_planned_max": combined_planned(),
        "sc6_cap": SC6_LIVE_CAP,
        "sc6_ledger_cited": SC6_LEDGER_CITED,
        "sc6_remaining": sc6_remaining(),
        "headroom": sc6_headroom(),
        "status": "NOT EXECUTED - methodology frozen by DEC-023 as amended by "
                  "DEC-025 (episodes per seed 42 -> 35); execution NOT "
                  "authorized",
    }
