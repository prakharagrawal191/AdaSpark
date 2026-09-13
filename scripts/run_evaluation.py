#!/usr/bin/env python
"""Day-31 evaluation harness CLI (PLAN line 277).

    | 31 | Eval harness + B1/B2 | frozen test set; static baselines tuned on
    validation | configs frozen |

No-Spark paths (safe to run on Day 31):

    --project-cost            project the EXP-003 / B1 / B2 execution cost
    --write-evaluation-spec   declare what a later day WILL run
    --freeze-test             freeze the TEST-split IDENTITY (no measurement)
    --verify                  re-verify every stored artifact fingerprint

Spark path (refused unless explicitly enabled):

    --select-baselines        execute the validation selection grid and freeze
                              B1/B2. Requires --allow-spark; without it the
                              projection is printed and NOTHING is executed.

This CLI never touches the TEST split: EXP-005 is Day 32-33 and EXP-006 is
Day 34 (PLAN lines 312-313). It makes no research claim about any strategy.

Usage:
    python scripts/run_evaluation.py --project-cost
    python scripts/run_evaluation.py --write-evaluation-spec --freeze-test
    python scripts/run_evaluation.py --verify
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.evaluation import freeze as freeze_mod          # noqa: E402
from sparkrl.evaluation import orchestration, spec           # noqa: E402
from sparkrl.evaluation.selection import select_baselines    # noqa: E402
from sparkrl.spark.config import SparkConfig                 # noqa: E402

B0_CONFIG = PROJECT / "configs" / "baseline_b0.yaml"
ARTIFACT_DIR = PROJECT / "results" / "evaluation"

ARTIFACTS = ("evaluation_spec.json", "baseline_selection.json", "test_freeze.json")


def _rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def cmd_project_cost(args: argparse.Namespace) -> int:
    projection = spec.project_cost(args.repetitions)
    _rule("COST PROJECTION (no Spark, nothing executed)")
    print(spec.summarize_projection(projection))
    blockers = orchestration.preflight_blockers()
    if blockers:
        print("\n  EXECUTION PRECONDITION NOT MET:")
        for item in blockers:
            print("    - " + item)
    if args.json:
        print(json.dumps(projection, indent=2, sort_keys=True))
    return 0


def cmd_write_evaluation_spec(args: argparse.Namespace) -> int:
    base_config = SparkConfig.from_yaml(B0_CONFIG)
    artifact = freeze_mod.build_evaluation_spec_artifact(
        base_config, args.repetitions)
    path = freeze_mod.write_artifact(
        artifact, freeze_mod.artifact_path("evaluation_spec.json", ARTIFACT_DIR))
    _rule("EVALUATION SPECIFICATION (declaration only, nothing executed)")
    print(f"  path        : {path}")
    print(f"  schema      : {artifact['schema_version']}")
    print(f"  artifact_id : {artifact['artifact_id'][:16]}")
    print(f"  repetitions : {artifact['repetitions']}")
    print(f"  candidates  : {artifact['frozen_configurations']['candidate_count']}")
    print(f"  val cells   : {len(artifact['validation_cells'])}")
    return 0


def cmd_freeze_test(args: argparse.Namespace) -> int:
    artifact = freeze_mod.build_test_freeze()
    path = freeze_mod.write_artifact(
        artifact, freeze_mod.artifact_path("test_freeze.json", ARTIFACT_DIR))
    _rule("TEST-SPLIT FREEZE (identity only - no measurement, no metric)")
    print(f"  path                 : {path}")
    print(f"  schema               : {artifact['schema_version']}")
    print(f"  artifact_id          : {artifact['artifact_id'][:16]}")
    print(f"  test cells           : {artifact['cell_count']}")
    print(f"  manifest_fingerprint : {artifact['manifest_fingerprint'][:16]}")
    print(f"  execution status     : {artifact['test_execution_status']}")
    for item in artifact["declared_components_not_materialized"]:
        print(f"  declared, not materialized: {item}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    _rule("ARTIFACT VERIFICATION")
    missing = 0
    for name in ARTIFACTS:
        path = freeze_mod.artifact_path(name, ARTIFACT_DIR)
        if not path.exists():
            print(f"  {name:26s} ABSENT")
            missing += 1
            continue
        artifact = freeze_mod.verify_artifact(path)
        print(f"  {name:26s} OK  {artifact['artifact_id'][:16]}")
    return 1 if missing == len(ARTIFACTS) else 0


def cmd_select_baselines(args: argparse.Namespace) -> int:
    if not args.allow_spark:
        _rule("SELECT BASELINES: REFUSED (would execute Spark)")
        print("  --select-baselines executes the validation selection grid and")
        print("  therefore needs Spark. It is refused without --allow-spark.")
        print("  Projection printed instead; NOTHING was executed.\n")
        return cmd_project_cost(args)

    blockers = orchestration.preflight_blockers()
    if blockers:
        _rule("SELECT BASELINES: BLOCKED (nothing executed)")
        for item in blockers:
            print("  - " + item)
        return 2

    base_config = SparkConfig.from_yaml(B0_CONFIG)
    plan = orchestration.validation_run_plan(base_config, args.repetitions)
    records = []
    for run_spec in plan:
        metrics, provenance = orchestration.execute_validation_run(
            run_spec, base_config)
        records.append({"run_spec": run_spec.to_dict(),
                        "metrics": metrics.to_dict(),
                        "provenance": provenance})
    observations = orchestration.observations_from_records(records)
    selection = select_baselines(observations)
    artifact = freeze_mod.build_baseline_selection_artifact(selection)
    path = freeze_mod.write_artifact(
        artifact, freeze_mod.artifact_path("baseline_selection.json", ARTIFACT_DIR))
    _rule("BASELINE SELECTION (validation split only)")
    print(f"  path : {path}")
    print(f"  B1   : {selection.b1_config_name}")
    for family, name in sorted(selection.b2_config_names.items()):
        print(f"  B2   : {family} -> {name}")
    print(json.dumps(orchestration.summarize_observations(observations),
                     indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Day-31 evaluation harness (EXP-003 / B1 / B2).")
    parser.add_argument("--project-cost", action="store_true",
                        help="project the execution cost; runs no Spark")
    parser.add_argument("--write-evaluation-spec", action="store_true",
                        help="write results/evaluation/evaluation_spec.json")
    parser.add_argument("--freeze-test", action="store_true",
                        help="write results/evaluation/test_freeze.json (identity only)")
    parser.add_argument("--verify", action="store_true",
                        help="re-verify stored artifact fingerprints")
    parser.add_argument("--select-baselines", action="store_true",
                        help="execute the validation grid and freeze B1/B2 "
                             "(needs Spark; refused without --allow-spark)")
    parser.add_argument("--allow-spark", action="store_true",
                        help="explicitly permit Spark execution")
    parser.add_argument("--repetitions", type=int,
                        default=spec.EVALUATION_REPETITIONS,
                        help="repetitions per cell (PLAN section 23 freezes 5)")
    parser.add_argument("--json", action="store_true",
                        help="also dump the projection as JSON")
    args = parser.parse_args(argv)

    if not any((args.project_cost, args.write_evaluation_spec, args.freeze_test,
                args.verify, args.select_baselines)):
        parser.error("choose at least one action (see --help)")

    status = 0
    if args.write_evaluation_spec:
        status = max(status, cmd_write_evaluation_spec(args))
    if args.freeze_test:
        status = max(status, cmd_freeze_test(args))
    if args.select_baselines:
        status = max(status, cmd_select_baselines(args))
    elif args.project_cost:
        status = max(status, cmd_project_cost(args))
    if args.verify:
        status = max(status, cmd_verify(args))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
