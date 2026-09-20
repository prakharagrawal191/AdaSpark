"""EXP-008 / SC6 budget reconciliation (DEC-030 B5 budget decision).

Deterministic, zero-Spark, read-only accounting script. It reconstructs the
SC6 TRAIN execution ledger from authoritative repository evidence (raw
manifests, artifact JSON, frozen configuration, DECISIONS.md) and emits
``results/evaluation/exp008_budget_reconciliation.json``.

It performs NO Spark execution, NO training, NO TEST execution, modifies no
existing artifact, and authorizes nothing.

Governance sources (quoted in the emitted JSON and in
``docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md``):
  * docs/PLAN.md line 45  -- "SC6 = training <=500 executions, monitoring
    overhead <=5% of job time" (frozen plan; the overhead component is
    EXP-009 scope and is not part of this reconciliation).
  * configs/rl.yaml line 17 -- live_execution_cap: 500 (frozen cap).
  * DEC-011 ledger composition: "(5 runs x 3) + 217 training (42 + 84 + 49
    + 42) = 232 of the frozen 500" -- smoke runs ARE charged.
  * DEC-016 C: B4 TRAIN calibration +84 (232 -> 316).
  * results/experiments/exp-001/spec.json: sc6_charge "20 TRAIN executions
    (316 -> 336 of 500)".
  * DEC-024/DEC-025: authoritative spent before EXP-007 = 336; remaining 164.
  * DEC-026: EXP-007 TRAIN authorized (max 140); executed live charge = the
    manifest sum of the four 20260917 EXP-007 manifests = 126.
  * DEC-030 section 10: B5 explicitly left to THIS budget decision.

Run:  python scripts/reconcile_exp008_budget.py
Output is byte-identical across runs on an unchanged repository.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

OUT_PATH = PROJECT / "results" / "evaluation" / "exp008_budget_reconciliation.json"

DECISIONS = PROJECT / "DECISIONS.md"
PLAN = PROJECT / "docs" / "PLAN.md"
RL_YAML = PROJECT / "configs" / "rl.yaml"
REGISTRY = PROJECT / "experiments" / "registry.csv"
TRAINING_ROOT = PROJECT / "results" / "training"

PREFLIGHT_MD = PROJECT / "docs" / "research" / "DAY37_EXP008_PREFLIGHT_AUDIT.md"
PREFLIGHT_JSON = PROJECT / "results" / "evaluation" / "exp008_preflight_audit.json"
DEC030_MD = PROJECT / "docs" / "research" / "DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md"
DEC030_JSON = PROJECT / "results" / "evaluation" / "exp008_methodology_freeze.json"
EXP007_ANALYSIS = PROJECT / "results" / "evaluation" / "exp007_analysis.json"
B4_SELECTION = PROJECT / "results" / "evaluation" / "b4_selection.json"
EXP001_SPEC = PROJECT / "results" / "experiments" / "exp-001" / "spec.json"
EXP002_ATTEMPTS = PROJECT / "results" / "experiments" / "exp-002" / "attempts.jsonl"
VALIDATION_OBS = PROJECT / "results" / "evaluation" / "validation_observations.json"
EXP005_OBS = PROJECT / "results" / "experiments" / "exp-005" / "observations.jsonl"
EXP005_SUMMARY = PROJECT / "results" / "experiments" / "exp-005" / "summary.json"
EXP006_OBS = PROJECT / "results" / "experiments" / "exp-006" / "observations.jsonl"
EXP006_SUMMARY = PROJECT / "results" / "experiments" / "exp-006" / "summary.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def jsonl_rows(path: Path) -> list:
    return [json.loads(line) for line in read_text(path).splitlines() if line.strip()]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=PROJECT, capture_output=True, text=True, check=True
    ).stdout.strip()



# ---------------------------------------------------------------------------
# 1. SC6 counting rule (traced to authoritative sources)
# ---------------------------------------------------------------------------
plan_text = read_text(PLAN).splitlines()
sc6_line = next(line for line in plan_text if "SC6 = training" in line)
assert "SC6 = training" in sc6_line

rl_text = read_text(RL_YAML)
cap_match = re.search(r"^live_execution_cap:\s*(\d+)", rl_text, re.MULTILINE)
assert cap_match, "live_execution_cap not found in configs/rl.yaml"
SC6_CAP = int(cap_match.group(1))

# Governance anchors that must exist in DECISIONS.md (read-only checks).
dec_text = read_text(DECISIONS)
GOVERNANCE_ANCHORS = [
    "of the frozen 500",                        # DEC-011 ledger composition (smoke charged)
    "316 -> 336 of 500",                        # EXP-001 charge quote (DEC-016 C era / DEC-024)
    "9e83742",                                  # B4 TRAIN calibration commit (DEC-016 C / DEC-025)
    "stands at 336/500",                        # DEC-018 closing status quote
    "the ledger state before the EXP-001 charge",  # DEC-025/DEC-026 explain DEC-023's stale 184
    "headroom: 24",                             # DEC-026 section 3
    "headroom = 24",                            # DEC-025 section 12
    "SC6 TRAIN ledger: 336/500",                # DEC-024 status
]
dec_text_normalized = re.sub(r"\s+", " ", dec_text)
missing_anchors = [a for a in GOVERNANCE_ANCHORS if a not in dec_text_normalized]
assert not missing_anchors, f"missing governance anchors in DECISIONS.md: {missing_anchors}"

SC6_COUNTING_RULE = {
    "cap": SC6_CAP,
    "cap_source": (
        "docs/PLAN.md line 45: \"" + sc6_line.strip() + "\"; "
        "configs/rl.yaml line 17: live_execution_cap: 500 (frozen cap "
        "(PLAN section 16 / SC6); env owns the guard)"
    ),
    "rule_text": (
        "SC6 counts live TRAIN-split Spark executions charged to the training "
        "register lines, under ONE global cap of 500 (not per run, not per "
        "experiment). Established and applied continuously by the DEC chain: "
        "DEC-011 (232), DEC-016 C (+84), EXP-001 spec.json (+20), DEC-024/"
        "DEC-025 (336/500), DEC-026 (+126)."
    ),

    "components": {
        "train_live_executions": {
            "charged": True,
            "evidence": "DEC-011: '(5 runs x 3) + 217 training (42 + 84 + 49 + 42) = 232 of the frozen 500'",
        },
        "smoke_executions": {
            "charged": True,
            "evidence": (
                "DEC-011 ledger explicitly includes '(5 runs x 3)' = the five "
                "results/training/smoke manifests at 3 live executions each; "
                "tests/integration/test_rl_training_smoke.py: 'running the "
                "integration suite SPENDS frozen budget'"
            ),
        },
        "failed_executions": {
            "charged": True,
            "evidence": (
                "DEC-010: failure is a first-class observation (reward -1, "
                "Q-update applied) - a failed live execution was consumed. No "
                "failure occurred inside any charged category (B4 84/84 usable, "
                "EXP-001 declared 20, EXP-007 0 failures), so the charged total "
                "is unaffected."
            ),
        },
        "undefined_or_not_executed_rows": {
            "charged": False,
            "evidence": (
                "DEC-025 section 12: execution arithmetic is per-episode "
                "(budget_limit = int(episodes)); unexecuted planned rows charge "
                "nothing (e.g. EXP-007 A2 seed 1: 21 of 35 executed; 14 rows "
                "unexecuted, no charge)"
            ),
        },
        "cache_hits": {
            "charged": False,
            "evidence": (
                "src/sparkrl/rl/env.py: 'Cache hits do NOT consume budget'; "
                "DEC-026 section 4: 'cache hits free; only live executions "
                "increment the budget'"
            ),
        },
        "validation_split_executions": {
            "charged": False,
            "evidence": (
                "DEC-012: EXP-003/B1-B2 selection is a separate authorized "
                "register line; DEC-013 validation execution gate (Model B); "
                "scripts/validate_day31.py: 'EXP-003 is a separate register line "
                "that is not charged to that cap at all'"
            ),
        },
        "test_split_executions": {
            "charged": False,
            "evidence": (
                "DEC-018 Decision B TEST seal; DEC-024 section 5 / DEC-025 "
                "section 13 / DEC-026 section 12; preflight audit section 12: "
                "'EXP-005 TEST 245 and EXP-006 125 do not charge SC6 TRAIN'"
            ),
        },
        "exp002_grid_and_references": {
            "charged": False,
            "evidence": (
                "EXP-002 is the SC1 sensitivity gate register line (PLAN section "
                "31, Days 23-24), executed before the SC6 ledger existed; "
                "DEC-011's ledger composition charges only the training manifests "
                "and no DEC ever charges EXP-002. Recorded as an explicit "
                "accounting-boundary convention; no retroactive re-designation "
                "(DEC-024 section 5 / DEC-025 section 13 precedent). The "
                "preflight audit's partial charge of 16 EXP-002 B0 references is "
                "rejected (cherry-picked subset of 208 runs)."
            ),
        },
        "cap_scope": {
            "global": True,
            "evidence": (
                "DEC-024 section 1: the SC6 TRAIN cap is 'a hard research "
                "constant'; the DEC chain maintains ONE ledger (232 -> 316 -> "
                "336 -> 462). Per-run limits are separate "
                "(budget_limit_this_run). Cross-run totals are 'REPORTED not "
                "enforced (COMP-EXP-11 deferred)' per "
                "src/sparkrl/training/loop.py BUDGET_ENFORCEMENT_NOTE - the "
                "global cap is enforced by decision governance only."
            ),
        },
        "second_sc6_component": {
            "in_scope_here": False,
            "evidence": (
                "PLAN line 45 also requires 'monitoring overhead <=5% of job "
                "time' (EXP-009 scope). It is a measured-overhead criterion, "
                "consumes no SC6 execution charge, and is out of scope here."
            ),
        },
        "conflict_resolution": {
            "evidence": (
                "DEC-010 precedence rule: PLAN governs over derived documents; a "
                "later decision amends an earlier one only by a NEW entry "
                "(DEC-021 clerical-correction tradition); raw manifests/artifacts "
                "outrank prose summaries (DEC-030 section 1)"
            ),
        },
    },
    "forward_charging_rule_for_exp008_frozen_by_this_decision": (
        "Every live TRAIN-split Spark execution of an EXP-008 A3/A4 arm charges "
        "SC6 1:1 (one execution per episode/cell transition, DEC-025 section 12 "
        "loop semantics). Cache hits are free. Failed live executions charge. "
        "Smoke runs charge. Undefined/not-executed rows do not charge. "
        "Validation-split and TEST-split executions do not charge (separate "
        "register lines). The cap remains 500, global, unchanged."
    ),
}




# ---------------------------------------------------------------------------
# 2. Reconstruction of the ledger from raw artifacts
# ---------------------------------------------------------------------------
manifests = []
for path in sorted(TRAINING_ROOT.rglob("manifest.json")):
    m = json.loads(read_text(path))
    manifests.append(
        {
            "run_dir": str(path.parent.relative_to(PROJECT)).replace("\\", "/"),
            "run_kind": m.get("run_kind"),
            "state_schema": m.get("state_schema"),
            "exp007_variant": m.get("exp007_variant"),
            "agent_rng_seed": m.get("agent_rng_seed"),
            "stop_reason": m.get("stop_reason"),
            "live_executions": int(m["budget"]["live_executions"]),
            "planned_executions": int(m["budget"].get("budget_limit_this_run", 0)),
            "recorded_cap": int(m["budget"]["live_execution_cap"]),
            "sha256": sha256_of(path),
        }
    )

smoke = [m for m in manifests if m["run_kind"] == "smoke"]
nonsmoke = [m for m in manifests if m["run_kind"] != "smoke"]
SMOKE_LIVE = sum(m["live_executions"] for m in smoke)
NONSMOKE_LIVE = sum(m["live_executions"] for m in nonsmoke)
MANIFEST_SUM_ALL = SMOKE_LIVE + NONSMOKE_LIVE

# Row-level manifest ledger (deterministic, sorted by run dir) -- evidence table.
manifest_ledger = [
    {
        "run_dir": m["run_dir"],
        "run_kind": m["run_kind"],
        "exp007_variant": m["exp007_variant"],
        "agent_rng_seed": m["agent_rng_seed"],
        "planned_executions": m["planned_executions"],
        "live_executions": m["live_executions"],
        "live_execution_cap": m["recorded_cap"],
        "stop_reason": m["stop_reason"],
    }
    for m in manifests
]

# Every manifest must record the frozen cap (rl.yaml).
assert all(m["recorded_cap"] == SC6_CAP for m in manifests)

# EXP-007 manifests: the four 2026-09-17 runs (DEC-026 scope: A1/A2, seeds {0,1}).
exp007_manifests = [m for m in manifests if m["exp007_variant"] is not None]
EXP007_LIVE = sum(m["live_executions"] for m in exp007_manifests)
exp007_breakdown = {
    f"{m['exp007_variant']}-s{m['agent_rng_seed']}": m["live_executions"]
    for m in exp007_manifests
}
assert exp007_breakdown == {"A1-s0": 35, "A2-s0": 35, "A1-s1": 35, "A2-s1": 21}, exp007_breakdown
assert EXP007_LIVE == 126
assert all(m["run_kind"] == "training" for m in exp007_manifests)

# Pre-EXP-007 manifest ledger (DEC-011 composition, re-summed by DEC-025).
PRE007_NONSMOKE = NONSMOKE_LIVE - EXP007_LIVE
MANIFEST_LEDGER_PRE007 = PRE007_NONSMOKE + SMOKE_LIVE
assert PRE007_NONSMOKE == 217
assert MANIFEST_LEDGER_PRE007 == 232

# B4 TRAIN calibration (DEC-016 C; machine-readable artifact).
b4 = json.loads(read_text(B4_SELECTION))
B4_CHARGE = int(b4["budget"])
assert b4["split"] == "train"
assert b4["observation_counts"] == {"failed": 0, "total": 84, "usable": 84}
assert B4_CHARGE == 84

# EXP-001 noise calibration (its own artifact declares the SC6 charge).
exp001 = json.loads(read_text(EXP001_SPEC))
assert exp001["sc6_charge"] == "20 TRAIN executions (316 -> 336 of 500)"
assert int(exp001["total_planned"]) == 20
EXP001_CHARGE = 20

# EXP-002 (SC1 gate) - attempted/completed/failed from raw attempts ledger.
exp002_rows = jsonl_rows(EXP002_ATTEMPTS)
EXP002_ATTEMPTED = len(exp002_rows)
EXP002_COMPLETED = sum(1 for r in exp002_rows if r.get("status") == "COMPLETED")
EXP002_FAILED = sum(1 for r in exp002_rows if r.get("status") == "FAILED")
assert (EXP002_ATTEMPTED, EXP002_COMPLETED, EXP002_FAILED) == (208, 189, 19)

# EXP-003 (validation split; DEC-012 separate register line).
val_obs = json.loads(read_text(VALIDATION_OBS))
EXP003_OBSERVATIONS = len(val_obs["observations"])
assert val_obs["recovered_count"] == EXP003_OBSERVATIONS
assert len(val_obs["non_validation_observations"]) == 0

# EXP-005 / EXP-006 (TEST split; sealed by DEC-018 Decision B).
exp005_rows = jsonl_rows(EXP005_OBS)
exp006_rows = jsonl_rows(EXP006_OBS)
exp005_summary = json.loads(read_text(EXP005_SUMMARY))
exp006_summary = json.loads(read_text(EXP006_SUMMARY))
assert exp005_summary["stage"] == "complete (245 of 245)"
assert exp006_summary["stage"] == "complete (125 of 125)"
assert len(exp005_rows) == 245
assert len(exp006_rows) == 125



# ---------------------------------------------------------------------------
# 3. Charge table
# ---------------------------------------------------------------------------
experiment_charges = [
    {
        "register_line": "EXP-002 (SC1 sensitivity gate, Days 23-24)",
        "split": "train",
        "planned": 208,
        "attempted": EXP002_ATTEMPTED,
        "successful": EXP002_COMPLETED,
        "failed": EXP002_FAILED,
        "undefined_or_not_executed": 0,
        "smoke": 0,
        "counts_toward_sc6": False,
        "authoritative_charge": 0,
        "evidence": (
            "results/experiments/exp-002/attempts.jsonl (208 rows: 189 "
            "COMPLETED, 19 FAILED); docs/research/EXP002_CONFIGURATION_"
            "SENSITIVITY_AUDIT.md: 'Planned total: 208 runs (192 grid + 16 "
            "reference)'; DEC-011's ledger composition charges only training "
            "manifests; no DEC charges EXP-002 to SC6"
        ),
    },
    {
        "register_line": "EXP-003 / B1-B2 selection (validation split)",
        "split": "validation",
        "planned": "PLAN section 31 envelope ~30; exact plan frozen by DEC-012 (not re-derived here)",
        "attempted": EXP003_OBSERVATIONS,
        "successful": EXP003_OBSERVATIONS,
        "failed": "not separately recorded (artifact records observations, not attempt outcomes)",
        "undefined_or_not_executed": "not separately recorded",
        "smoke": 0,
        "counts_toward_sc6": False,
        "authoritative_charge": 0,
        "evidence": (
            "results/evaluation/validation_observations.json (96 observations); "
            "DEC-012; DEC-013; scripts/validate_day31.py: 'EXP-003 is a separate "
            "register line that is not charged to that cap at all'"
        ),
    },
    {
        "register_line": "EXP-004 / RL main training (Day-27/29 runs incl. smoke)",
        "split": "train",
        "planned": "episodes planned per manifest (42/84/49/42 main runs; smoke 3 each)",
        "attempted": MANIFEST_LEDGER_PRE007,
        "successful": MANIFEST_LEDGER_PRE007,
        "failed": 0,
        "undefined_or_not_executed": 0,
        "smoke": SMOKE_LIVE,
        "counts_toward_sc6": True,
        "authoritative_charge": MANIFEST_LEDGER_PRE007,
        "evidence": (
            "10 manifests at DEC-024/025 gate time summing 232 = 15 smoke "
            "(5 smoke manifests x 3; one later smoke manifest records 0 live) + "
            "217 non-smoke (42+84+49+42); DEC-011; DEC-024/DEC-025 re-sums"
        ),
    },
    {
        "register_line": "B4 TRAIN calibration (DEC-016 C; feeds the EXP-005 B4 arm)",
        "split": "train",
        "planned": 84,
        "attempted": 84,
        "successful": 84,
        "failed": 0,
        "undefined_or_not_executed": 0,
        "smoke": 0,
        "counts_toward_sc6": True,
        "authoritative_charge": B4_CHARGE,
        "evidence": (
            "results/evaluation/b4_selection.json: budget 84, split 'train', "
            "observation_counts {failed: 0, total: 84, usable: 84}; DEC-016 C: "
            "'taking the ledger from 232 to 316 of 500'; commit 9e83742"
        ),
    },
    {
        "register_line": "EXP-001 noise calibration (Day 32)",
        "split": "train",
        "planned": 20,
        "attempted": 20,
        "successful": "declared 20 (artifact records the declared charge)",
        "failed": "not separately recorded in spec.json",
        "undefined_or_not_executed": 0,
        "smoke": 0,
        "counts_toward_sc6": True,
        "authoritative_charge": EXP001_CHARGE,
        "evidence": (
            "results/experiments/exp-001/spec.json: 'sc6_charge': '20 TRAIN "
            "executions (316 -> 336 of 500)'; DEC-024 section 5: NOT "
            "re-designated as non-charging"
        ),
    },


    {
        "register_line": "EXP-005 main comparison (TEST split)",
        "split": "test",
        "planned": 245,
        "attempted": 245,
        "successful": "245 observation rows recorded (analysis excludes the F3_rdd|large|s3 cell from comparisons)",
        "failed": "recorded inside observations (excluded-cell failures); artifact records observations, not attempt outcomes",
        "undefined_or_not_executed": 0,
        "smoke": 0,
        "counts_toward_sc6": False,
        "authoritative_charge": 0,
        "evidence": (
            "results/experiments/exp-005/{observations.jsonl,summary.json} (245 "
            "rows, split 'test', 'complete (245 of 245)'); DEC-018 Decision B "
            "TEST seal; preflight section 12: 'EXP-005 TEST 245 ... do not "
            "charge SC6 TRAIN'"
        ),
    },
    {
        "register_line": "EXP-006 generalization (TEST split)",
        "split": "test",
        "planned": 125,
        "attempted": 125,
        "successful": 125,
        "failed": "recorded inside observations; artifact records observations, not attempt outcomes",
        "undefined_or_not_executed": 0,
        "smoke": 0,
        "counts_toward_sc6": False,
        "authoritative_charge": 0,
        "evidence": (
            "results/experiments/exp-006/{observations.jsonl,summary.json} (125 "
            "rows, split 'test', 'complete (125 of 125)'); authorized by "
            "DEC-022; TEST split does not charge SC6 TRAIN"
        ),
    },
    {
        "register_line": "EXP-007 state ablations A1/A2 (TRAIN, DEC-026)",
        "split": "train",
        "planned": "140 maximum (2 x 35 A1 + 2 x 35 A2)",
        "attempted": EXP007_LIVE,
        "successful": EXP007_LIVE,
        "failed": 0,
        "undefined_or_not_executed": 14,
        "smoke": 0,
        "counts_toward_sc6": True,
        "authoritative_charge": EXP007_LIVE,
        "evidence": (
            "Four 2026-09-17 manifests: A1-s0=35 (planned_episodes), A2-s0=35 "
            "(early_stop_policy_stable), A1-s1=35 (planned_episodes), A2-s1=21 "
            "(early_stop_policy_stable); total 126, 0 failures; DEC-026 "
            "authorized maximum 140; preflight section 2: 'EXECUTED 126 live "
            "(35+35+35+21), 0 failures'"
        ),
    },
]

CUMULATIVE_BEFORE_EXP007 = MANIFEST_LEDGER_PRE007 + B4_CHARGE + EXP001_CHARGE
CUMULATIVE_AFTER_EXP007 = CUMULATIVE_BEFORE_EXP007 + EXP007_LIVE
REMAINING = SC6_CAP - CUMULATIVE_AFTER_EXP007

assert CUMULATIVE_BEFORE_EXP007 == 336
assert CUMULATIVE_AFTER_EXP007 == 462
assert REMAINING == 38

# Independent closure: the charge table itself must sum to the cumulative charge.
# (Integer charges only; non-charged register lines carry a string/numeric-zero charge.)
CHARGE_TABLE_SUM = sum(
    c["authoritative_charge"]
    for c in experiment_charges
    if isinstance(c["authoritative_charge"], int)
)
assert CHARGE_TABLE_SUM == CUMULATIVE_AFTER_EXP007, CHARGE_TABLE_SUM

cumulative = {
    "cap": SC6_CAP,
    "before_exp007": CUMULATIVE_BEFORE_EXP007,
    "before_exp007_derivation": "232 (training manifests incl. 15 smoke) + 84 (B4 TRAIN calibration) + 20 (EXP-001) = 336",
    "exp007_charge": EXP007_LIVE,
    "after_exp007": CUMULATIVE_AFTER_EXP007,
    "after_exp007_derivation": "336 + 126 = 462",
    "remaining_capacity": REMAINING,
    "remaining_derivation": "500 - 462 = 38",
    "manifest_ledger_cross_check": (
        f"results/training manifest sum = {MANIFEST_SUM_ALL} "
        f"({SMOKE_LIVE} smoke + {NONSMOKE_LIVE} non-smoke); "
        f"{MANIFEST_SUM_ALL} + {B4_CHARGE} (B4) + {EXP001_CHARGE} (EXP-001) = "
        f"{MANIFEST_SUM_ALL + B4_CHARGE + EXP001_CHARGE} = cumulative charge"
    ),
}




# ---------------------------------------------------------------------------
# 4. Resolution of every conflicting figure
# ---------------------------------------------------------------------------
conflicting_figures = [
    {
        "figure": 462,
        "source": "DEC-025 chain + DEC-026 charge: 336 + 126",
        "definition": "cumulative SC6 TRAIN charge after EXP-007 (smoke included, B4-84 included, EXP-001 included, EXP-007 126 included)",
        "counts_toward_sc6": True,
        "authoritative": True,
        "status": "CURRENT",
        "reason": (
            "Continuous with DEC-011 (232) -> DEC-016 C (316) -> EXP-001 spec "
            "(336) -> DEC-025 (336) -> DEC-026 (+126). Every component is "
            "machine-verified: manifest sum 358 = 343 non-smoke + 15 smoke; "
            "b4_selection.json budget 84 split 'train'; exp-001 spec.json "
            "sc6_charge; four EXP-007 manifests sum 126. This is the "
            "authoritative cumulative charge."
        ),
    },
    {
        "figure": 38,
        "source": "500 - 462; also exp008_methodology_freeze.json 'remaining_sc6_capacity_validation_excluded_basis': 38",
        "definition": "remaining SC6 TRAIN capacity under the authoritative DEC-chain counting rule",
        "counts_toward_sc6": "n/a (capacity)",
        "authoritative": True,
        "status": "CURRENT",
        "reason": (
            "Arithmetically reproducible from authoritative sources. Adopted as "
            "the current remaining capacity by this budget decision. (The "
            "DEC-030 artifact's label 'validation_excluded_basis' is a mislabel: "
            "38 is the DEC-chain basis; the DEC chain charges B4's 84 as TRAIN "
            "per DEC-016 C and never charged validation.)"
        ),
    },
    {
        "figure": 343,
        "source": "preflight audit sections 1 and 10; 8 non-smoke training manifests",
        "definition": "manifest-derived live sum EXCLUDING the 5 smoke manifests (15 live) and the 0-live smoke manifest; 42+84+35+35+49+35+21+42 = 343",
        "counts_toward_sc6": "partially - it is a manifest-only subtotal, not the SC6 ledger",
        "authoritative": False,
        "status": "STALE_AS_LEDGER (correct as a manifest subtotal)",
        "reason": (
            "Verified correct AS A MANIFEST SUBTOTAL (217 pre-EXP-007 non-smoke "
            "+ 126 EXP-007 = 343). It is NOT the SC6 charge: it omits the 15 "
            "smoke live executions that DEC-011 explicitly charged, omits B4's "
            "charged 84 and EXP-001's charged 20, and adds nothing else. "
            "232 - 15 + 126 = 343. Not adopted as the ledger."
        ),
    },
    {
        "figure": 379,
        "source": "preflight audit section 10 and exp008_preflight_audit.json 'cumulative_live_executions_before_exp008'; quoted (not selected) by DEC-030 sections 2 and 10",
        "definition": "343 + 20 (EXP-001) + 16 (EXP-002 B0 references) - the preflight 'nominal TRAIN-manifest+EXP001/B0' basis",
        "counts_toward_sc6": False,
        "authoritative": False,
        "status": "STALE / CONTRADICTED",
        "reason": (
            "Internally inconsistent basis: it EXCLUDES the 15 smoke executions "
            "that DEC-011 explicitly charged and EXCLUDES B4's 84 executions "
            "that DEC-016 C explicitly charged, while ADDING 16 EXP-002 B0 "
            "reference executions that no DEC ever charged (a cherry-picked "
            "subset of EXP-002's 208 runs - the other 192 grid runs are "
            "ignored). No decision authorizes this basis. Not adopted."
        ),
    },


    {
        "figure": 121,
        "source": "preflight audit section 10 ('nominal remaining 121'); exp008_preflight_audit.json 'remaining_sc6_capacity_nominal_train_only'; exp008_methodology_freeze.json 'remaining_sc6_capacity_nominal_train_only': 121",
        "definition": "500 - 379",
        "counts_toward_sc6": "n/a (capacity)",
        "authoritative": False,
        "status": "STALE / CONTRADICTED",
        "reason": (
            "Inherits the 379 basis's defects (smoke excluded contra DEC-011; "
            "B4-84 omitted contra DEC-016 C; 16 EXP-002 B0 references included "
            "without any DEC). Cross-check: 121 - 38 = 83 = 15 (smoke) + 84 "
            "(B4) - 16 (B0 refs), which is exactly the category disagreement "
            "between the two bases. Not adopted."
        ),
    },
    {
        "figure": -89,
        "source": "exp008_preflight_audit.json 'remaining_sc6_capacity_dec_chain_post007': -89; preflight audit section 10: 'DEC-chain remaining -89 (38 if validation held outside SC6; 121 TRAIN-manifest+EXP001/B0 basis)'; quoted (not selected) by DEC-030 section 10",
        "definition": "claimed 'DEC-chain post-EXP-007' remaining capacity",
        "counts_toward_sc6": "n/a (capacity)",
        "authoritative": False,
        "status": "NOT REPRODUCIBLE / INTERNALLY INCONSISTENT",
        "reason": (
            "The DEC chain itself yields 500 - 336 - 126 = 38, not -89. -89 "
            "equals 500 - 589, and 589 has no authoritative composition; the "
            "closest reconstruction is 379 + 84 + 126 = 589, which double-counts "
            "EXP-007's 126 (already inside 343/379) while simultaneously adding "
            "the B4-84 that the 379 basis excludes - mutually exclusive choices. "
            "An alternative coincidental composition (121 - 3 x 70 = -89, an "
            "illustrative 3-arm A3) matches no frozen rule. The preflight "
            "document's own derivation sentence is truncated mid-derivation, "
            "and the same JSON artifact is internally inconsistent elsewhere "
            "(projected_total_illustrative 519 implies headroom -19, yet "
            "headroom_illustrative is -229; -229 = 121 - 350 = 121 - 210 - 140). "
            "No decision adopted it (DEC-030 section 10 explicitly selected "
            "NONE). Rejected as non-reproducible and non-authoritative."
        ),
    },
    {
        "figure": 184,
        "source": "DEC-023 section 8/13: 'remaining TRAIN cap: 500 - 336 = 184'",
        "definition": "DEC-023's frozen remaining-capacity figure",
        "counts_toward_sc6": "n/a (capacity)",
        "authoritative": False,
        "status": "STALE (superseded; historical text preserved)",
        "reason": (
            "Arithmetic/ledger-state error: 500 - 336 = 164; 184 = 500 - 316, "
            "the ledger state BEFORE the EXP-001 charge. Corrected by DEC-024 "
            "section 3 and DEC-025 section 1 (164) WITHOUT rewriting DEC-023 "
            "(DEC-021 clerical-correction tradition). Forward-looking authority "
            "is 164 pre-EXP-007, 38 post-EXP-007."
        ),
    },


    {
        "figure": 164,
        "source": "DEC-024 section 3 table; DEC-025 section 1",
        "definition": "authoritative remaining SC6 TRAIN capacity BEFORE EXP-007 execution",
        "counts_toward_sc6": "n/a (capacity)",
        "authoritative": True,
        "status": "SUPERSEDED BY TIME (correct for its date)",
        "reason": "500 - 336 = 164; verified. Superseded by EXP-007's executed 126: 164 - 126 = 38.",
    },
    {
        "figure": 24,
        "source": "DEC-025 section 12; DEC-026 sections 3 and 14",
        "definition": "headroom at EXP-007 authorization time (164 - 140 planned)",
        "counts_toward_sc6": "n/a (capacity)",
        "authoritative": True,
        "status": "SUPERSEDED BY TIME (correct for its date)",
        "reason": "164 - 140 = 24 with 336 + 140 = 476 <= 500. EXP-007 then executed 126 (not 140): 476 - 14 = 462; remaining 38.",
    },
    {
        "figure": 519,
        "source": "exp008_preflight_audit.json 'projected_total_illustrative': 519 (379 + 140); preflight section 10",
        "definition": "illustrative projection: nominal basis 379 plus a DEC-023-parity A3/A4 shape of 140",
        "counts_toward_sc6": "n/a (illustrative projection)",
        "authoritative": False,
        "status": "ILLUSTRATIVE ONLY / INTERNALLY INCONSISTENT with the same artifact's headroom_illustrative (-229)",
        "reason": (
            "Built on the non-authoritative 379 basis; the same JSON records "
            "headroom_illustrative -229, which corresponds to a 729 projection "
            "(121 - 350), not to 519 (which implies -19). Neither projection is "
            "authorized by any decision. Not adopted."
        ),
    },
    {
        "figure": -229,
        "source": "exp008_preflight_audit.json 'headroom_illustrative': -229",
        "definition": "illustrative headroom after an unstated larger A3/A4 shape",
        "counts_toward_sc6": "n/a (illustrative capacity)",
        "authoritative": False,
        "status": "NOT REPRODUCIBLE / TRUNCATED DERIVATION",
        "reason": (
            "= 121 - 350 (= 210 + 140) under one reading; inconsistent with the "
            "same artifact's projected_total_illustrative 519. The preflight "
            "document's sentence is cut off mid-derivation ('headroom -229 "
            "(-103 even'). No decision adopted it. Rejected."
        ),
    },
]



# ---------------------------------------------------------------------------
# 5. Hypothetical EXP-008 capacity shapes (explicitly NOT authorized)
# ---------------------------------------------------------------------------
hypothetical = {
    "note": (
        "ILLUSTRATIVE ONLY. DEC-030 deliberately left A3/A4 seeds, horizon, "
        "cells, Q0 source, arm set, implementation and the charging rule "
        "unresolved (DEC-030 sections 10 and 12). This decision freezes only "
        "the charging rule and the remaining capacity (38). These shapes are "
        "NOT an authorized A3/A4 execution plan and must never be converted "
        "into authorized counts except by a separate authorization decision."
    ),
    "remaining_capacity_available": REMAINING,
    "shapes": [
        {"shape": "single arm, 1 agent seed, 35 episodes", "charged": 35, "fits": True, "remaining_after": 3},
        {"shape": "DEC-023-parity single arm, 2 agent seeds x 35 episodes", "charged": 70, "fits": False, "remaining_after": -32},
        {"shape": "two arms (e.g. one A3 + A4), 1 agent seed x 35 episodes each", "charged": 70, "fits": False, "remaining_after": -32},
        {"shape": "DEC-023-parity A3 + A4 (2 arms x 2 seeds x 35)", "charged": 140, "fits": False, "remaining_after": -102},
        {"shape": "three A3 reward arms + A4 at DEC-023-parity (4 x 70)", "charged": 280, "fits": False, "remaining_after": -242},
        {"shape": "PLAN section 31 EXP-008 envelope (~300 runs)", "charged": 300, "fits": False, "remaining_after": -262},
    ],
}


# ---------------------------------------------------------------------------
# 6. Fingerprints
# ---------------------------------------------------------------------------
fingerprint_files = [
    DECISIONS, PLAN, RL_YAML, REGISTRY,
    PREFLIGHT_MD, PREFLIGHT_JSON, DEC030_MD, DEC030_JSON,
    EXP007_ANALYSIS, B4_SELECTION, EXP001_SPEC, EXP002_ATTEMPTS,
    VALIDATION_OBS, EXP005_OBS, EXP005_SUMMARY, EXP006_OBS, EXP006_SUMMARY,
]
source_fingerprints = {
    str(p.relative_to(PROJECT)).replace("\\", "/"): sha256_of(p)
    for p in fingerprint_files
}
manifest_fingerprints = {m["run_dir"]: m["sha256"] for m in manifests}



# ---------------------------------------------------------------------------
# 7. Emit the deterministic JSON
# ---------------------------------------------------------------------------
head = git("rev-parse", "HEAD")
branch = git("rev-parse", "--abbrev-ref", "HEAD")

report = {
    "schema_version": "exp008-budget-reconciliation/v1",
    "artifact_kind": "EXP-008 / SC6 BUDGET RECONCILIATION (DEC-030 B5 budget decision)",
    "repository_head": head,
    "repository_branch": branch,
    "decision_record": "docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md",
    "latest_authoritative_dec": {
        "latest_recorded_decision_artifact": "DEC-030 (EXP-008 A3/A4 methodology freeze; docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md)",
        "latest_dec_in_decision_log": "DEC-026 (last heading in DECISIONS.md at HEAD 5cf0cf8)",
        "note": "DEC-030 section 10 explicitly left B5 (this reconciliation) unresolved.",
    },
    "sc6_cap": SC6_CAP,
    "sc6_cap_source": SC6_COUNTING_RULE["cap_source"],
    "sc6_counting_rule": SC6_COUNTING_RULE,
    "experiment_charges": experiment_charges,
    "exp007_charge": {
        "total": EXP007_LIVE,
        "breakdown": exp007_breakdown,
        "all_live_train_split": True,
        "failed": 0,
        "smoke_runs": 0,
        "counts_toward_sc6": True,
        "authorized_maximum": 140,
        "executed": 126,
        "unexecuted_planned_rows": 14,
        "evidence": "The four 2026-09-17 EXP-007 manifests (machine-verified); DEC-026 scope maximum 140.",
    },
    "cumulative_charge": cumulative,
    "conflicting_figures": conflicting_figures,
    "hypothetical_exp008_capacity": hypothetical,
    "budget_decision": {
        "decision_status": (
            "PASS - reconciliation complete. The existing SC6 cap (500) remains "
            "valid; the accounting is uniquely established and reproducible "
            "(462 charged / 38 remaining). No cap amendment is enacted. No "
            "de-scoping is enacted. EXP-008 execution remains NOT authorized."
        ),
        "state": "A-qualified",
        "state_meaning": (
            "State A (existing SC6 cap remains valid; headroom established) with "
            "a recorded conditional: any frozen A3/A4 execution plan whose "
            "SC6 charge exceeds 38 requires EITHER de-scoping to <= 38 charged "
            "live executions OR a formal cap amendment (a new DEC entry plus a "
            "PLAN amendment per the PLAN header's change-control rule). Because "
            "DEC-030 left the A3/A4 plan unfrozen, neither de-scoping nor a cap "
            "raise can be justified or enacted today without inventing scope."
        ),
        "cap_amendment_required": False,
        "cap_amendment_required_if": (
            "A frozen EXP-008 A3/A4 plan charges more than 38 live TRAIN "
            "executions and is not de-scoped. The PLAN section 31 envelope "
            "(~300 runs) cannot fit within 38 under the existing cap; DEC-011 "
            "already recorded that whether EXP-008's envelope sits inside SC6's "
            "500 or has a separate budget is an unresolved internal-PLAN "
            "conflict that DEC-010's precedence rule cannot arbitrate."
        ),
        "de_scoping_required": False,
        "de_scoping_required_if": (
            "The operator declines a cap amendment and freezes an A3/A4 plan "
            "whose charge exceeds 38; the plan must then be de-scoped to <= 38 "
            "charged live executions by its own decision."
        ),
        "execution_authorized": False,
        "implementation_authorized": False,
        "a5_status": "DISABLED (DEC-011; re-affirmed DEC-016 s7, DEC-023 s2, DEC-024 A5 row, DEC-025 s7, DEC-030 s9)",
        "no_spark_executed": True,
        "no_training_executed": True,
        "no_test_executed": True,
        "no_existing_artifact_modified": True,
    },
    "governance_impact": {
        "dec_030": "Unchanged and not invalidated: DEC-030 section 10 anticipated exactly this separate budget decision.",
        "exp008_methodology": "Unchanged: DEC-030's methodology freeze stands; seeds/horizon/cells/Q0/arm set remain unfrozen.",
        "experiment_registry": "Unchanged.",
        "plan": "Unchanged. If a >38-charged A3/A4 plan is later frozen without de-scoping, a PLAN amendment via a new DEC entry is required at that time (PLAN header change-control rule).",
        "sc6_wording": "Unchanged: PLAN line 45 and rl.yaml line 17 stand.",
        "prior_authorization_boundaries": "Unchanged: DEC-024/DEC-025/DEC-026 figures stand as recorded history; no entry rewritten.",
        "new_decision_sufficient": True,
        "note": "This reconciliation is the B5 budget decision DEC-030 required. Appending it to DECISIONS.md under a DEC number is a separate mechanical step, intentionally not performed by this task.",
    },
    "validation": {
        "zero_spark": True,
        "zero_training": True,
        "zero_test": True,
        "read_only_parsing": True,
        "assertions": [
            "8 non-smoke training manifests sum 343 (42+84+35+35+49+35+21+42)",
            "6 smoke manifests sum 15 live (5 x 3 + 1 x 0)",
            "manifest ledger pre-EXP-007 = 217 + 15 = 232 (DEC-011 composition)",
            "232 + 84 (B4) + 20 (EXP-001) = 336 (DEC-024/DEC-025)",
            "35 + 35 + 35 + 21 = 126 = EXP-007 manifest live sum",
            "336 + 126 = 462; 500 - 462 = 38",
            "343 + 20 + 16 = 379; 500 - 379 = 121 (rejected basis)",
            "121 - 38 = 83 = 15 + 84 - 16 (category disagreement between bases)",
            "EXP-002 attempts 208 = 192 grid + 16 reference (189 COMPLETED, 19 FAILED)",
            "EXP-003 validation observations 96; EXP-005 245/245; EXP-006 125/125 (all uncharged)",
            "all 14 training manifests record live_execution_cap = 500",
            "experiment_charges table sums to 462 == cumulative charge",
        ],
        "all_passed": True,
    },
    "source_fingerprints": source_fingerprints,
    "training_manifest_fingerprints": manifest_fingerprints,
    "training_manifest_ledger": manifest_ledger,
}



OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
OUT_PATH.write_text(text, encoding="utf-8", newline="\n")
print(f"wrote {OUT_PATH} ({len(text.encode('utf-8'))} bytes)")
print(f"cumulative charged = {CUMULATIVE_AFTER_EXP007}; remaining = {REMAINING}")
sys.exit(0)

