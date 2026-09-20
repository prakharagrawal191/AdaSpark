"""DEC-030 deterministic artifact generator (zero-Spark; read-only).

Regenerates ``results/evaluation/exp008_methodology_freeze.json`` byte-identically
on rerun (sorted keys, fixed values, no timestamps). Touches no governance source.

Methodology freeze for EXP-008 A3/A4 per DEC-030. Execution is NOT authorized.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

PROJECT = pathlib.Path(__file__).resolve().parents[1]
MD_PATH = PROJECT / "docs" / "research" / "DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md"
OUT_PATH = PROJECT / "results" / "evaluation" / "exp008_methodology_freeze.json"

HEAD = "5cf0cf850f022750fa7df734328f6807e3546ee9"

SOURCE_FILES = [
    "DECISIONS.md",
    "configs/reward.yaml",
    "configs/rl.yaml",
    "docs/PLAN.md",
    "docs/architecture/ARCHITECTURE_FREEZE.md",
    "docs/architecture/COMPONENT_CONTRACTS.md",
    "docs/research/DAY37_EXP008_PREFLIGHT_AUDIT.md",
    "experiments/registry.csv",
    "src/sparkrl/agent/q0.py",
    "src/sparkrl/agent/q_learning.py",
    "src/sparkrl/rl/action.py",
    "src/sparkrl/rl/env.py",
    "src/sparkrl/rl/reward.py",
    "src/sparkrl/rl/state.py",
    "src/sparkrl/training/ablation.py",
    "src/sparkrl/training/loop.py",
]


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


U = "UNFROZEN - SEPARATE DECISION REQUIRED"
U_B3 = "REQUIRES EXPLICIT DECISION (B3: Q0 provenance)"
U_B4 = "UNFROZEN - REQUIRES DECISION (B4)"
U_B5 = "UNFROZEN - REQUIRES SEPARATE BUDGET DECISION (B5)"
PRESUMED = "presumed from frozen main-study value; NOT separately frozen for this arm"


def common_controls(q0_status: str) -> dict:
    return {
        "aqe_condition": "aqe_enabled=false (frozen main-study control) - " + U_B4,
        "alpha": "0.2 (frozen main-study value) - " + U_B4,
        "action_schema": "mode12 (12 actions) - " + U_B4,
        "cache_behavior": U_B4,
        "dataset_seed": "0 (frozen: T_ref calibrated for dataset seed 0 only)",
        "early_stop_rule": U_B4,
        "episode_horizon": U_B4,
        "epsilon_schedule": (
            "start 1.0, floor 0.05, decay 0.95 per episode "
            "(frozen main-study values) - " + U_B4
        ),
        "gamma": "0.0 (frozen main-study value; DEC-011 bandit lock) - " + U_B4,
        "live_execution_charging_rule": U_B5,
        "q0": q0_status,
        "state_schema": "state-v1.5 (30 states) - " + U_B4,
        "train_cells": U_B4,
        "training_seeds": U_B4,
        "warm_up_behavior": U_B4,
    }


A3_TIME_ONLY = {
    "arm_identifier": "A3-time-only",
    "registered_intent_source": "PLAN section 24 (line 188): time-only (1, 0, 0)",
    "classification": (
        "MULTI-TERM REMOVAL from R3 - NOT a pure one-factor ablation: "
        "task-imbalance AND spill-waste removed simultaneously"
    ),
    "removed_terms": ["task-imbalance (0.2)", "spill-waste (0.2)"],
    "retained_terms": ["time improvement (1.0, clipped)", "failure penalty (-1.0)"],
    "reward_formula": "R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)",
    "coefficients": {
        "clip_high": 1.0,
        "clip_low": -1.0,
        "w_failure": 1.0,
        "w_spill_waste": 0.0,
        "w_task_imbalance": 0.0,
        "w_time_improvement": 1.0,
    },
    "failure_behavior": "R = -1.0 exactly (DEC-010; retained from frozen R3)",
    "clipping": "time delta clipped to [-1, +1] (retained from frozen R3)",
    "t_ref_source": "EXP-002 TRAIN records, B0 median, dataset seed 0 - " + PRESUMED,
    **common_controls(U_B3),
}

A3_R3_FROZEN = {
    "arm_identifier": "A3-R3-frozen",
    "registered_intent_source": (
        "PLAN section 24 (line 188): final/frozen R3 (1, 0.2, 0.2)"
    ),
    "classification": "R3 remains exactly the frozen primary reward - unchanged",
    "reward_formula": (
        "1.0*clip((T_ref-T)/T_ref,-1,+1) + 0.2*(1-min(1,CV/0.5)) "
        "- 0.2*min(1,(spill/input)/0.10) - 1.0*1[fail]"
    ),
    "coefficients": {
        "clip_high": 1.0,
        "clip_low": -1.0,
        "spill_ratio_reference": 0.10,
        "task_cv_reference": 0.5,
        "w_failure": 1.0,
        "w_spill_waste": 0.2,
        "w_task_imbalance": 0.2,
        "w_time_improvement": 1.0,
    },
    "failure_behavior": "R = -1.0 exactly (DEC-010, frozen R3)",
    "clipping": "[-1, +1] on the time delta (frozen R3)",
    "missing_input_rule": (
        "missing CV/spill inputs contribute 0.0 and are recorded, never guessed "
        "(frozen reward.py)"
    ),
    "t_ref_source": (
        "EXP-002 TRAIN records, B0 median, dataset seed 0 (frozen TRefStore gate)"
    ),
    **common_controls(U_B3),
}

A3_R4_LOG_RATIO = {
    "arm_identifier": "A3-R4-log-ratio",
    "registered_intent_source": (
        "PLAN section 24 (line 188): R4 log-ratio -ln(T/T_ref)"
    ),
    "classification": (
        "INCOMPLETE - R4 is UNIMPLEMENTED; every missing semantic requires "
        "a separate explicit decision"
    ),
    "registered_formula": "R4 = -ln(T / T_ref)",
    "implementation_status": "UNIMPLEMENTED (no weights, no validator, no tests)",
    "unfrozen_semantics": {
        "clipping": U,
        "coefficients": U,
        "edge_T_le_0": U,
        "edge_T_ref_le_0": U,
        "edge_failures_timeouts": U,
        "edge_missing_execution_time": U,
        "failure_rule": U,
        "term_structure_vs_time_only": U,
    },
    "t_ref_source": "EXP-002 TRAIN records, B0 median, dataset seed 0 - " + PRESUMED,
    **common_controls(U_B3),
}


A4_MODE4 = {
    "arm_identifier": "A4-mode4",
    "registered_intent_source": (
        "PLAN section 24: 4-action minimization / action-space ablation"
    ),
    "classification": (
        "ACTION AVAILABILITY ONLY - mode4 subset of mode12; every other factor "
        "must equal its control arm"
    ),
    "action_space": {
        "frozen_source": (
            "ARCHITECTURE_FREEZE section 9 / COMP-RL-07 / "
            "action.py MODE4_SUBSET = frozenset({0, 3, 6, 9})"
        ),
        "mode": "mode4",
        "subset": [0, 3, 6, 9],
    },
    "primary_comparison": "mode12 (all 12 frozen actions)",
    "exact_four_configurations": [
        {
            "action_index": 0,
            "config": (
                "local[2]; spark.sql.shuffle.partitions=16; "
                "spark.default.parallelism=2"
            ),
            "parallelism": 2,
            "shuffle_partitions": 16,
        },
        {
            "action_index": 3,
            "config": (
                "local[2]; spark.sql.shuffle.partitions=128; "
                "spark.default.parallelism=2"
            ),
            "parallelism": 2,
            "shuffle_partitions": 128,
        },
        {
            "action_index": 6,
            "config": (
                "local[4]; spark.sql.shuffle.partitions=64; "
                "spark.default.parallelism=4"
            ),
            "parallelism": 4,
            "shuffle_partitions": 64,
        },
        {
            "action_index": 9,
            "config": (
                "local[8]; spark.sql.shuffle.partitions=32; "
                "spark.default.parallelism=8"
            ),
            "parallelism": 8,
            "shuffle_partitions": 32,
        },
    ],
    "verification": (
        "subset strictly contained in the frozen 12-grid "
        "(grid_index = parallelism_index*4 + shuffle_index); selection restriction "
        "pre-implemented and unit-validated; AQE guard preserved"
    ),
    "reward": "R3 presumed - " + U_B4 + "; must equal its control arm",
    "t_ref_source": "EXP-002 TRAIN, B0 median, dataset seed 0 - " + PRESUMED,
    **common_controls(
        "STRUCTURALLY COMPATIBLE (EXISTING FROZEN MAPPING) - rows remain "
        "12-wide; subset indices used as-is; Q0 SOURCE choice still " + U
    ),
}

Q0 = {
    "governing_rules": [
        "no TEST-derived information",
        "no post-hoc Q0 construction",
        "no invented state mapping",
        "no invented action mapping",
        "no pooling unless already frozen",
        "no silent change to the primary-study Q0",
        "no reuse of an incompatible Q0 merely for convenience",
    ],
    "per_arm": {
        "A3-R3-frozen": {
            "classification": "REQUIRES NEW DECISION",
            "note": (
                "same state/action space as primary; q0-exp002/v1 plausible; "
                "provenance UNFROZEN (B3)"
            ),
        },
        "A3-R4-log-ratio": {
            "classification": "REQUIRES NEW DECISION",
            "note": (
                "no Q0 ever computed under R4; constructing one now would be "
                "post-hoc construction (forbidden)"
            ),
        },
        "A3-time-only": {
            "classification": "REQUIRES NEW DECISION",
            "note": (
                "state/action space may stay identical; q0-exp002/v1 plausible; "
                "provenance UNFROZEN (B3)"
            ),
        },
        "A4-mode4": {
            "classification": "EXISTING FROZEN MAPPING",
            "note": (
                "rows 12-wide; indices {0, 3, 6, 9} used as-is; no projection; "
                "Q0 source choice still UNFROZEN"
            ),
        },
    },
    "projection_invented": False,
}

CONFOUNDS = {
    "A3": [
        {
            "confound": "multi-term reward removal",
            "description": (
                "time-only removes TWO terms simultaneously; not isolable per term"
            ),
            "severity": "HIGH",
            "resolution": "explicit classification; NOT repaired",
        },
        {
            "confound": "Q0 interaction",
            "description": (
                "differing Q0 sources confound reward effects with initialization"
            ),
            "severity": "MEDIUM",
            "resolution": U_B3,
        },
        {
            "confound": "R4 functional-form change",
            "description": (
                "-ln vs clipped-linear confounds functional form with "
                "coefficient/term differences; edge semantics unfrozen"
            ),
            "severity": "HIGH",
            "resolution": U,
        },
    ],
    "A4": [
        {
            "confound": "action-selection distribution differences",
            "description": (
                "epsilon-greedy over 4 vs 12 actions changes exploration coverage; "
                "inherent to the factor; report, do not repair"
            ),
            "severity": "MEDIUM",
            "resolution": "inherent; reported",
        },
        {
            "confound": "possible Q0 mismatch",
            "description": (
                "if A4 Q0 source differs from its control arm, action effects are "
                "confounded with initialization"
            ),
            "severity": "MEDIUM",
            "resolution": U_B3,
        },
    ],
}

UNRESOLVED = [
    "final arm set to execute (which A3 formulas; whether A3-R4 is retained)",
    "Q0 source per arm (A3 all arms; A4)",
    "state schema per arm (A3; A4)",
    "action schema for A3",
    "reward arm for A4 control pairing",
    "seeds (count + identities) (A3; A4)",
    "TRAIN cells (A3; A4)",
    "episode horizon (A3; A4)",
    "early-stop rule (A3; A4)",
    "AQE condition confirmation (A3; A4)",
    "warm-up behavior (A3; A4)",
    "cache behavior (A3; A4)",
    "whether A3 and A4 share seeds/cells/horizon",
    "statistical governance (descriptive vs inferential; thresholds)",
    "R4 complete specification (A3-R4)",
    "epsilon schedule / alpha / gamma if deviating from frozen values (A3; A4)",
    "live-execution charging rule and headroom (B5 - separate budget decision)",
    "implementation authorization (B6 - separate decision)",
]

A5 = {
    "disabled_by": "DEC-011 (2026-09-13, Day-30 mode gate = NO)",
    "gamma": 0.0,
    "gamma_0_9_implementation_or_execution": "FORBIDDEN under DEC-030",
    "multi_step_rl_opened": False,
    "part_of_this_decision": False,
    "status": "DISABLED",
}

BUDGET = {
    "b5_resolved_by_this_dec": False,
    "b5_status": "NOT RESOLVED BY DEC-030 - SEPARATE REQUIRED DECISION",
    "contradictory_figures_cited_not_selected": {
        "cumulative_live_executions_before_exp008": 379,
        "remaining_sc6_capacity_dec_chain_post007": -89,
        "remaining_sc6_capacity_nominal_train_only": 121,
        "remaining_sc6_capacity_validation_excluded_basis": 38,
        "sc6_cap_frozen": 500,
    },
    "explicit_dependency": (
        "EXP-008 execution remains unauthorized until a separate budget decision "
        "establishes a valid headroom calculation."
    ),
}

STATS = {
    "frozen_for_exp008": False,
    "frozen_machinery_main_study": (
        "PLAN 22/23/33: 5 reps, medians, Wilcoxon signed-rank (instance x seed), "
        "Mann-Whitney (unpaired), Cliff delta, Holm-Bonferroni (EXP-005 standard)"
    ),
    "inferential_analysis_performed": False,
    "separate_stats_dec_may_be_required_later": True,
    "thresholds_invented": False,
    "unfrozen_items": [
        "descriptive-only vs inferential choice",
        "effect-size threshold",
        "Holm family",
        "minimum successful cells",
        "multiple-testing correction scope",
        "p-value threshold",
        "superiority threshold",
    ],
}

GATES = {
    "A3_exact_intent_reconstructed": True,
    "A3_time_only_classified_as_multi_term_removal": True,
    "A4_exact_four_action_mapping_verified": True,
    "A4_exact_intent_reconstructed": True,
    "A4_Q0_compatibility_explicitly_resolved_or_marked_unresolved": True,
    "No_Q0_projection_invented": True,
    "R3_remains_unchanged": True,
    "R4_either_completely_frozen_or_marked_for_separate_decision": True,
    "budget_remains_separate_unresolved_decision": True,
    "control_variables_explicitly_recorded": True,
    "deterministic_json_rerun_passes": True,
    "execution_authorization_remains_NO": True,
    "hidden_confound_recorded": True,
    "historical_decisions_unchanged": True,
    "no_TEST_executed": True,
    "no_Spark_executed": True,
    "no_training_executed": True,
    "statistical_thresholds_not_invented": True,
}


def build() -> dict:
    decisions_sha = sha256_of(PROJECT / "DECISIONS.md")
    return {
        "a3_arms": {
            "r3_frozen": A3_R3_FROZEN,
            "r4_log_ratio": A3_R4_LOG_RATIO,
            "time_only": A3_TIME_ONLY,
        },
        "a4_arm": A4_MODE4,
        "acceptance_gates": GATES,
        "a5": A5,
        "budget_dependency": BUDGET,
        "confound_classifications": CONFOUNDS,
        "date": "2026-09-17",
        "decision_id": "DEC-030",
        "decision_state_fingerprint": f"DEC-026|{HEAD}|{decisions_sha}",
        "dec030_fingerprint": sha256_of(MD_PATH),
        "execution_authorized": False,
        "files_created": [
            "docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md",
            "results/evaluation/exp008_methodology_freeze.json",
        ],
        "files_modified": [],
        "no_TEST_executed": True,
        "no_Spark_executed": True,
        "no_training_executed": True,
        "q0": Q0,
        "repository": {
            "branch": "main",
            "head": HEAD,
            "latest_committed_dec": "DEC-026",
        },
        "schema_version": "exp008-methodology-freeze/v1",
        "scope": (
            "EXP-008 A3/A4 methodology only (reward variants A3; action-space "
            "ablation A4); resolves only methodological aspects of B1-B4; "
            "B5 and B6 remain separate"
        ),
        "source_document_fingerprints": {
            name: sha256_of(PROJECT / name) for name in SOURCE_FILES
        },
        "statistical_governance": STATS,
        "status": "DECIDED - methodology frozen; execution NOT authorized",
        "unresolved_methodological_fields": UNRESOLVED,
    }


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()

