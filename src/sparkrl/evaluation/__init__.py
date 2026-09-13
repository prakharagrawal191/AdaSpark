"""Day-31 evaluation harness: specification, split authorization, B1/B2, freeze.

Orchestration over already-frozen infrastructure. It owns no Spark session, no
timing clock, no event-log parser, no metrics merge and no configuration
fingerprint - all of those exist and are imported, never re-implemented.

Day 31 builds and declares; it executes no test run (EXP-005/006 are Days 32-34)
and it makes no research claim about any strategy.
"""
from sparkrl.evaluation.freeze import (ArtifactCorrupt, ArtifactExistsError,
                                       DEFAULT_ARTIFACT_DIR,
                                       artifact_fingerprint, artifact_path,
                                       build_baseline_selection_artifact,
                                       build_evaluation_spec_artifact,
                                       build_test_freeze, manifest_fingerprint,
                                       seal, verify_artifact, write_artifact,)
from sparkrl.evaluation.orchestration import (EvaluationExecutionBlocked,
                                              execute_test_run,
                                              execute_validation_run,
                                              observations_from_records,
                                              preflight_blockers,
                                              summarize_observations,
                                              validation_run_plan,)
from sparkrl.evaluation.selection import (BaselineSelection, CandidateResult,
                                          NoEligibleCandidate,
                                          ValidationObservation,
                                          resolve_baseline_config,
                                          select_baselines,)
from sparkrl.evaluation.spec import (BASELINES_IN_SCOPE, EVAL_SPEC_VERSION,
                                     EVALUATION_REPETITIONS, EXPERIMENT_ID,
                                     SELECTION_METRIC, SELECTION_STATISTIC,
                                     TIE_BREAK_NOTE, TIE_BREAK_RULE,
                                     SplitAuthorizationError, TestSplitSealed,
                                     assert_test_execution_permitted,
                                     authorize_cell, authorize_test_cell,
                                     authorize_validation_cell,
                                     build_evaluation_spec, project_cost,
                                     selection_candidates, summarize_projection,
                                     test_cells, validation_cells,
                                     validation_families,)

__all__ = [
    "ArtifactCorrupt", "ArtifactExistsError", "BASELINES_IN_SCOPE",
    "BaselineSelection", "CandidateResult", "DEFAULT_ARTIFACT_DIR",
    "EVALUATION_REPETITIONS", "EVAL_SPEC_VERSION", "EXPERIMENT_ID",
    "EvaluationExecutionBlocked", "NoEligibleCandidate", "SELECTION_METRIC",
    "SELECTION_STATISTIC", "SplitAuthorizationError", "TIE_BREAK_NOTE",
    "TIE_BREAK_RULE", "TestSplitSealed", "ValidationObservation",
    "artifact_fingerprint", "artifact_path", "assert_test_execution_permitted",
    "authorize_cell", "authorize_test_cell", "authorize_validation_cell",
    "build_baseline_selection_artifact", "build_evaluation_spec",
    "build_evaluation_spec_artifact", "build_test_freeze", "execute_test_run",
    "execute_validation_run", "manifest_fingerprint",
    "observations_from_records", "preflight_blockers", "project_cost",
    "resolve_baseline_config", "seal", "select_baselines",
    "selection_candidates", "summarize_observations", "summarize_projection",
    "test_cells", "validation_cells", "validation_families",
    "validation_run_plan", "verify_artifact", "write_artifact",
]
