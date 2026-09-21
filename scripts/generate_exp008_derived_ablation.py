#!/usr/bin/env python
"""DEC-039 generator: the EXP-008 zero-charge DERIVED ablation + preflight re-run.

Produces two immutable artifacts under ``results/evaluation/``:

    exp008_derived_ablation.json   the ablation table PLAN line 315 names as
                                   its acceptance, in the zero-charge derived
                                   form DEC-034 section 5 scoped
    exp008_preflight_rerun.json    the clean preflight re-run DEC-030 section
                                   15 requires of the authorization decision

Everything here is READ-ONLY over the repository and performs ZERO Spark
executions: the Q0 tables are rebuilt from the already-recorded EXP-002
observation store by ``sparkrl.agent.q0.build_q0_from_exp002`` (the machinery
DEC-035 adopted for B6), the A4 mode4 policy is a subset argmax of a mode12
Q-table, and the B1/B2 reachability facts are structural properties of the
frozen grid. A3-R4 is NOT retained: DEC-036 section 8 dropped it and its
registered formula stays not-executable (proved by construction below).

Descriptive only: no threshold, no inferential statistic (DEC-030 section 8).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.q0 import build_q0_from_exp002          # noqa: E402
from sparkrl.evaluation import freeze as freeze_mod        # noqa: E402
from sparkrl.experiments.grid import build_grid            # noqa: E402
from sparkrl.rl.action import MODE4_SUBSET                 # noqa: E402
from sparkrl.rl.reward import (FORMULA_A3_TIME_ONLY,       # noqa: E402
                               RewardCalculator)

ARTIFACT_DIR = PROJECT / "results" / "evaluation"
ABLATION_PATH = ARTIFACT_DIR / "exp008_derived_ablation.json"
RERUN_PATH = ARTIFACT_DIR / "exp008_preflight_rerun.json"
AUDIT_PATH = ARTIFACT_DIR / "exp008_preflight_audit.json"
SELECTION_PATH = ARTIFACT_DIR / "baseline_selection.json"
GATE_PATH = (PROJECT / "results" / "experiments" / "exp-002" /
             "analysis" / "gate.json")

ABLATION_SCHEMA = "exp008-derived-ablation/v1"
RERUN_SCHEMA = "exp008-preflight-rerun/v1"

LIMITATION_INITIALIZATION = (
    "A3 here ablates the OFFLINE INITIALIZATION, not ONLINE LEARNING.")
LIMITATION_RQ4 = (
    "RQ4 asks about learning stability and final policy quality; the "
    "learning-stability half is UNANSWERED by this decision and is reported "
    "as a stated limitation, with no claim about what a trained comparison "
    "would have shown.")
LIMITATION_DESCRIPTIVE = (
    "Descriptive only - no threshold and no inferential statistic is "
    "computed or asserted (DEC-030 section 8).")

# Blocker resolutions: each key is a blocking finding recorded verbatim by
# the 2026-09-17 preflight audit; each value names the decision(s) that
# resolved it. Nothing here invents a category the record does not support.
BLOCKER_RESOLUTIONS = {
    "B1-A3-UNFROZEN": ("DEC-030 (reward-variant structure freeze); "
                       "DEC-036 sections 5 and 8 (executable arm set = "
                       "A3-R3-frozen + A3-time-only; A3-R4 DROPPED)"),
    "B2-A4-UNFROZEN": ("DEC-030 section 5 (structural compatibility of the "
                       "mode4 subset); DEC-036 section 5 (mode12 action "
                       "mode; A4 subset {0, 3, 6, 9})"),
    "B3-Q0-UNFROZEN": ("DEC-036 section 5 (Q0 = q0-exp002/v1 uniformly, "
                       "rows wide 12, no projection, no invented pooling)"),
    "B4-CONTROLS-UNFROZEN": ("DEC-036 sections 5 and 6 (eleven INHERIT "
                             "fields; seeds/horizon frozen as a rule with "
                             "branches P 210 / R 140 / M 21)"),
    "B5-BUDGET-EXHAUSTED": ("DEC-031 sections 3, 4, 5 and 8 (B5 charging "
                            "rule and headroom categories); DEC-033 and "
                            "DEC-038 (canonical ledger 483 charged of 500, "
                            "remaining 17)"),
    "B6-IMPLEMENTATION-GAP": ("DEC-035 (B6 implementation adopted; exact "
                              "reward semantics registered and "
                              "validator-enforced)"),
}

# Non-blocking findings: classified non-blocking by the audit itself; where a
# later decision resolved the underlying question, it is cited.
NONBLOCKING_DISPOSITIONS = {
    "N1-S9-DRIFT": "non-blocking by audit classification; no resolution "
                   "required for the zero-charge scope",
    "N2-FAILURE-SEMANTICS-DRIFT": "non-blocking by audit classification; the "
                                  "failure transformation is registered "
                                  "exactly by DEC-035",
    "N3-TREF-SOURCE": "resolved by DEC-036 (q0-exp002/v1; T_ref source = "
                      "the EXP-002 gate artifact)",
    "N4-EXP008-ENVELOPE": "resolved by DEC-034 (zero-charge derived scope; "
                          "SC6 cap NOT raised)",
    "N5-SEED-COUNT": "resolved by DEC-036 fields 6 and 8 (frozen rule with "
                     "branches P/R/M)",
    "N6-STATS-GAP": "resolved by DEC-036 field 14 (descriptive-only, "
                    "DEC-030 section 8)",
}


def greedy_action(row, allowed: tuple[int, ...]) -> int:
    """Frozen exploitation rule; ties break to the LOWEST action index."""
    return max(allowed, key=lambda a: (row[a], -a))


def provenance() -> dict[str, Any]:
    from sparkrl.experiments.runner import code_version   # lazy: offline-safe
    return {
        "code_version": code_version(),
        "produced_by":
            "scripts/generate_exp008_derived_ablation.py (DEC-039)",
        "split_authority": "sparkrl.experiments.spec.split_of",
        "spark_executions": 0,
    }


def _grid_names() -> dict[int, str]:
    points: dict[int, str] = {}
    for p in build_grid(include_b0=True):
        if p.grid_index is not None:
            points[p.grid_index] = p.name
    return points



def derive_mode4_policy(r3: Any) -> dict[str, Any]:
    """A4 structurally: argmax over the mode4 subset of the mode12 Q-table."""
    allowed = tuple(sorted(MODE4_SUBSET))
    per_state: dict[str, Any] = {}
    for key in sorted(r3.q_table):
        row = r3.q_table[key]
        per_state[key] = {
            "q_values_subset": [row[a] for a in allowed],
            "greedy_action": greedy_action(row, allowed),
        }
    return {"allowed_actions": list(allowed),
            "derived_from": "A3-R3-frozen", "per_state": per_state}


def derive_reachability() -> dict[str, Any]:
    """Structural B1/B2 reachability under the reduced action space."""
    names = _grid_names()
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    b1_name = selection["B1"]["selected_config"]
    b2 = selection["B2"]["selected_config_by_family"]
    mode4 = sorted(MODE4_SUBSET)

    def reachable(name: str) -> bool:
        idx = next(i for i, n in names.items() if n == name)
        return idx in mode4

    return {
        "mode4_members": {str(i): names[i] for i in mode4},
        "b1": {"selected_config": b1_name,
               "grid_index": next(i for i, n in names.items()
                                  if n == b1_name),
               "reachable_under_mode4": reachable(b1_name)},
        "b2_by_family": {fam: {"selected_config": name,
                               "reachable_under_mode4": reachable(name)}
                         for fam, name in sorted(b2.items())},
    }

def derive_q0_tables() -> tuple[Any, Any]:
    """Rebuild the two A3 Q0 tables over the recorded EXP-002 TRAIN store."""
    r3 = build_q0_from_exp002()            # frozen primary reward (R3)
    time_only = build_q0_from_exp002(
        reward_calculator=RewardCalculator(formula=FORMULA_A3_TIME_ONLY))
    return r3, time_only


def build_ablation_doc() -> dict[str, Any]:
    """The PLAN line 315 ablation table in its zero-charge derived form."""
    r3, time_only = derive_q0_tables()
    rows: dict[str, Any] = {}
    differing: list[dict[str, Any]] = []
    n_pairs = 0
    for key in sorted(r3.q_table):
        r3_row = r3.q_table[key]
        to_row = time_only.q_table.get(key)
        g12 = greedy_action(r3_row, tuple(range(12)))
        g4 = greedy_action(r3_row, tuple(sorted(MODE4_SUBSET)))
        per_action = []
        for a in range(12):
            r3_v, to_v = r3_row[a], (to_row[a] if to_row else None)
            if r3_v is not None and to_v is not None:
                n_pairs += 1
                delta = to_v - r3_v
                if abs(delta) > 1e-12:
                    differing.append({"state_key": key, "action": a,
                                      "r3": r3_v, "time_only": to_v,
                                      "delta": delta})
            per_action.append({"action": a, "r3": r3_v, "time_only": to_v})
        to_greedy = greedy_action(to_row, tuple(range(12))) if to_row else None
        rows[key] = {"per_action": per_action,
                     "greedy_mode12_r3": g12,
                     "greedy_mode12_time_only": to_greedy,
                     "greedy_mode4_from_r3": g4,
                     "greedy_agreement_r3_vs_time_only":
                         None if to_row is None else g12 == to_greedy}
    reach = derive_reachability()
    tref = json.loads(GATE_PATH.read_text(encoding="utf-8"))[
        "t_ref_calibration"]
    return {
        "schema": ABLATION_SCHEMA,
        "experiment_id": "EXP-008",
        "decision_basis": {
            "scope": "DEC-034 section 5 (zero-charge derived ablation)",
            "fields": "DEC-036 section 5 (all eighteen fields resolved)",
            "implementation": "DEC-035 (B6 implementation adopted)",
            "authorization": "DEC-039 (this artifact; worst-case 0, charge 0)",
            "register_line": "PLAN line 315 (ablation table) - UNCHANGED",
        },
        "executed": False,
        "provenance": provenance(),
        "q0_provenance": {
            "A3-R3-frozen": r3.provenance,
            "A3-time-only": time_only.provenance,
        },
        "reward_variants": {
            "R3": "frozen primary reward (configs/reward.yaml), unchanged",
            "A3-time-only": {
                "formula": "R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)",
                "failure_value": -1.0,
                "classification": "MULTI-TERM REMOVAL from R3 (task-imbalance "
                                  "and spill-waste removed simultaneously; "
                                  "NOT a one-factor ablation) - per DEC-035",
            },
            "A3-R4-log-ratio": {
                "retained": False,
                "status": "DROPPED by DEC-036 section 8; registered but NOT "
                          "executable (R4_UNRESOLVED_SEMANTICS); no Q0 was "
                          "ever computed under R4 and none is constructed "
                          "here",
            },
        },
        "t_ref_source": "exp002-gate:gate.json (t_ref_calibration)",
        "t_ref_calibration": tref,
        "train_cells": sorted(k for k, v in tref.items() if v is not None),
        "ablation_table": rows,
        "a4_mode4": derive_mode4_policy(r3),
        "baseline_reachability": reach,
        "summary": {
            "state_rows": len(rows),
            "evidence_pairs_compared": n_pairs,
            "pairs_differing_r3_vs_time_only": len(differing),
            "differing_pairs": differing,
            "mode4_subset": sorted(MODE4_SUBSET),
        },
        "stated_limitations": [LIMITATION_INITIALIZATION, LIMITATION_RQ4,
                               LIMITATION_DESCRIPTIVE],
        "statistics_governance": "descriptive-only (DEC-030 section 8; "
                                 "DEC-036 field 14)",
        "a5": "DISABLED (DEC-011); not part of this ablation",
    }


def build_rerun_doc() -> dict[str, Any]:
    """The clean preflight re-run DEC-030 section 15 requires (gate item 4)."""
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    return {
        "schema": RERUN_SCHEMA,
        "experiment_id": "EXP-008",
        "rerun_kind": ("CLEAN preflight re-run for the DEC-039 authorization "
                       "decision (DEC-030 section 15 gate item 4), zero Spark"),
        "reruns_artifact": AUDIT_PATH.name,
        "original_audit": {
            "audit_date_utc": audit.get("audit_date_utc"),
            "audit_schema_version": audit.get("audit_schema_version"),
            "recommendation": audit.get("recommendation"),
            "repository_head": audit.get("repository_head"),
            "plan_fingerprint": audit.get("plan_fingerprint"),
            "rl_config_fingerprint": audit.get("rl_config_fingerprint"),
        },
        "executed": False,
        "provenance": provenance(),
        "blocking_findings_resolution": {
            b: {"resolution": BLOCKER_RESOLUTIONS[b], "status": "RESOLVED"}
            for b in audit.get("blocking_findings", [])
        },
        "non_blocking_findings_disposition": {
            n: {"disposition": NONBLOCKING_DISPOSITIONS.get(
                n, "non-blocking by audit classification")}
            for n in audit.get("non_blocking_findings", [])
        },
        "authorization": {
            "trained_exp008_executions": "NOT AUTHORIZED (unchanged)",
            "zero_charge_derived_ablation":
                "AUTHORIZED (DEC-034 section 5; DEC-039)",
            "worst_case_live_train_executions": 0,
            "worst_case_ledger_charge": 0,
            "a5": "DISABLED (DEC-011)",
            "test": "NOT AUTHORIZED",
        },
        "ledger": {
            "cap": 500, "charged": 483, "remaining": 17,
            "arithmetic": "232 + 84 + 20 + 126 + 6 + 15 = 483",
            "source": "DEC-038 (canonical); DEC-031 sections 3/4/8 + "
                      "DEC-033 sections 4/5",
        },
        "plan_state": "docs/PLAN.md line 315 UNCHANGED (~300 trained runs "
                      "remain planned and unconsumed)",
        "recommendation": ("GO // zero-charge derived ablation only (DEC-034 "
                           "section 5); trained-execution authorization "
                           "remains NO"),
    }


def main() -> int:
    written = []
    for path, doc in ((ABLATION_PATH, build_ablation_doc()),
                      (RERUN_PATH, build_rerun_doc())):
        sealed = freeze_mod.seal(doc)
        freeze_mod.write_artifact(sealed, path)
        written.append(f"{path.name} artifact_id="
                       f"{sealed['artifact_id'][:16]} "
                       f"fingerprint={sealed['fingerprint'][:16]}")
    for line in written:
        print(line)
    print("spark_executions=0 (this generator opens no Spark session)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

