"""Unit tests: EXP-008 scope, Q0 policy, guards and provenance. NO Spark.

These tests defend the boundary DEC-030/DEC-031 drew around EXP-008: the
methodology is frozen in intent, UNFROZEN in detail and UNAUTHORIZED in
execution. Concretely they prove that

* every DEC-030 section-12 field is required-but-unset and fails CLOSED -
  nothing is defaulted into the frozen research design;
* no Q0 is projected, pooled, collapsed or invented, the primary-study Q0 is
  untouched, and an unsupported Q0 source is refused deterministically;
* TEST and VALIDATION cells/metrics can never enter an A3/A4 configuration;
* A5 stays blocked (no arm, no multi-step, no gamma != 0.0);
* run provenance records every required field with no fabricated value;
* the module exposes NO path that authorizes execution.
"""
from __future__ import annotations

import dataclasses

import pytest

from sparkrl.agent.q0 import Q0_NEUTRAL_VERSION, Q0_VERSION
from sparkrl.experiments.spec import TEST, TRAIN, VALIDATION
from sparkrl.rl.action import MODE4, MODE12
from sparkrl.rl.reward import (FORMULA_A3_R4_LOG_RATIO, FORMULA_A3_TIME_ONLY,
                               FORMULA_ID, IncompleteFormulaError)
from sparkrl.training import exp008
from sparkrl.training.exp008 import (A3_ARMS, A4_ARMS, A5_ARM_ID, ALL_ARMS,
                                     ARM_A3_R3, ARM_A3_R4_LOG_RATIO,
                                     ARM_A3_TIME_ONLY, ARM_A4_MODE4,
                                     CONFIG_SCHEMA, EXECUTION_AUTHORIZATION,
                                     EXECUTION_AUTHORIZED, EXP008_ID,
                                     FROZEN_DATASET_SEED, Q0_ROWS_WIDE,
                                     A5DisabledError, Exp008ArmConfig,
                                     Exp008ConfigError, Exp008Error,
                                     Exp008IncompleteError, Exp008Q0Error,
                                     Exp008ScopeError, all_arm_configs,
                                     arm_config_from_mapping,
                                     arm_config_from_yaml, arm_scope_summary,
                                     build_reward_calculator, guard_a5,
                                     guard_agent_seeds, guard_arm, guard_cell,
                                     guard_metrics, guard_q0_for_mode,
                                     guard_q0_projection, guard_q0_rows,
                                     guard_q0_source, guard_reward_variant,
                                     guard_split, guard_train_cells,
                                     load_exp008_config, q0_policy,
                                     required_fields)

pytestmark = [pytest.mark.unit]

TRAIN_CELLS = ("F1_agg|small", "F2_join|medium")


def complete_a4_config(**overrides) -> Exp008ArmConfig:
    """A hypothetical fully-supplied A4 config, for guard tests only.

    Supplying these values here is a TEST FIXTURE, never a freeze: DEC-030
    section 12 leaves each of them unresolved and the shipped
    ``configs/exp008.yaml`` keeps every one of them ``null``.
    """
    base = dict(
        arm=ARM_A4_MODE4, action_mode=MODE4, reward_variant=FORMULA_ID,
        state_schema="state-v1.5", q0_source=Q0_VERSION,
        agent_seeds=(0, 1), train_cells=TRAIN_CELLS,
        t_ref_source="exp002-train-b0-median", episode_horizon=35,
        early_stop_rule={"rule": "fixture"}, aqe_condition="aqe_enabled=false",
        warm_up_behavior="fixture", cache_behavior="fixture", alpha=0.2,
        gamma=0.0, epsilon_schedule={"start": 1.0},
        live_execution_charging_rule="fixture")
    base.update(overrides)
    return Exp008ArmConfig(**base)


# --- arms ----------------------------------------------------------------------
def test_arms_are_exactly_the_dec030_set():
    assert A3_ARMS == (ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A3_R4_LOG_RATIO)
    assert A4_ARMS == (ARM_A4_MODE4,)
    assert ALL_ARMS == A3_ARMS + A4_ARMS
    for arm in ALL_ARMS:
        guard_arm(arm)
    with pytest.raises(Exp008ScopeError):
        guard_arm("A3-something-else")


def test_each_a3_arm_is_bound_to_its_own_frozen_reward():
    assert exp008.ARM_REWARD_FORMULA == {
        ARM_A3_R3: FORMULA_ID,
        ARM_A3_TIME_ONLY: FORMULA_A3_TIME_ONLY,
        ARM_A3_R4_LOG_RATIO: FORMULA_A3_R4_LOG_RATIO,
    }
    # A4's reward is the control-pairing field: UNFROZEN, so never set here.
    assert ARM_A4_MODE4 not in exp008.ARM_REWARD_FORMULA
    assert "reward_variant" in required_fields(ARM_A4_MODE4)
    assert "reward_variant" not in required_fields(ARM_A3_R3)


# --- reward variant guards ------------------------------------------------------
def test_reward_variant_guard_accepts_implemented_and_refuses_r4():
    build_reward_calculator(FORMULA_ID)
    build_reward_calculator(FORMULA_A3_TIME_ONLY)
    with pytest.raises(IncompleteFormulaError):
        build_reward_calculator(FORMULA_A3_R4_LOG_RATIO)
    with pytest.raises(Exp008ScopeError):
        build_reward_calculator("R5-invented")


def test_missing_a4_reward_variant_is_required_but_unset():
    with pytest.raises(Exp008IncompleteError):
        guard_reward_variant(None, arm=ARM_A4_MODE4)


def test_r4_arm_can_never_become_configuration_complete():
    cfg = complete_a4_config(arm=ARM_A3_R4_LOG_RATIO, action_mode=MODE12,
                             reward_variant=None, q0_source=None)
    with pytest.raises(IncompleteFormulaError):
        cfg.validate_configuration()
    with pytest.raises(IncompleteFormulaError):
        cfg.arm_runtime_kwargs()


def test_an_arm_cannot_be_given_a_contradicting_reward():
    cfg = complete_a4_config(arm=ARM_A3_R3, action_mode=MODE12,
                             reward_variant=FORMULA_A3_TIME_ONLY)
    with pytest.raises(Exp008ScopeError):
        cfg.validate_configuration()


# --- fail-closed on every unresolved DEC-030 field ------------------------------
@pytest.mark.parametrize("arm", [ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A4_MODE4])
def test_shipped_config_is_incomplete_for_every_executable_arm(arm):
    cfg = arm_config_from_yaml(arm)
    assert cfg.unresolved_fields()          # nothing was silently defaulted
    with pytest.raises(Exp008IncompleteError):
        cfg.validate_configuration()


@pytest.mark.parametrize("field", sorted(set(required_fields(ARM_A4_MODE4))))
def test_dropping_any_single_required_field_fails_closed(field):
    cfg = complete_a4_config(**{field: None})
    with pytest.raises(Exp008Error):        # incomplete / scope / Q0 refusal
        cfg.validate_configuration()


def test_a_fixture_complete_config_validates_without_authorizing_anything():
    cfg = complete_a4_config()
    cfg.validate_configuration()
    kwargs = cfg.arm_runtime_kwargs()
    assert kwargs["action_mode"] == MODE4
    assert kwargs["action_subset"] == (0, 3, 6, 9)
    assert kwargs["split"] == TRAIN
    # Passing validation is NOT authorization.
    assert EXECUTION_AUTHORIZED is False
    assert cfg.to_provenance()["execution_authorized"] is False


# --- Q0 policy ------------------------------------------------------------------
def test_q0_projection_is_always_forbidden():
    guard_q0_projection(False)
    with pytest.raises(Exp008Q0Error):
        guard_q0_projection(True)
    for arm in ALL_ARMS:
        assert q0_policy(arm)["projection"] is False
    with pytest.raises(Exp008Q0Error):
        complete_a4_config(q0_projection=True).validate_configuration()


def test_q0_sources_are_the_existing_frozen_ones_only():
    for arm in (ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A4_MODE4):
        policy = q0_policy(arm)
        assert policy["allowed_sources"] == [Q0_VERSION, Q0_NEUTRAL_VERSION]
        assert policy["required_explicit"] is True
        guard_q0_source(arm, Q0_VERSION)
        guard_q0_source(arm, Q0_NEUTRAL_VERSION)
        with pytest.raises(Exp008Q0Error):
            guard_q0_source(arm, "q0-exp008-projected/v1")
        with pytest.raises(Exp008IncompleteError):
            guard_q0_source(arm, None)


def test_r4_admits_no_q0_at_all():
    policy = q0_policy(ARM_A3_R4_LOG_RATIO)
    assert policy["allowed_sources"] == []
    with pytest.raises(Exp008Q0Error):
        guard_q0_source(ARM_A3_R4_LOG_RATIO, Q0_VERSION)


def test_q0_rows_must_stay_twelve_wide_under_mode4():
    assert Q0_ROWS_WIDE == 12
    good = {"state-v1.5|agg|S|le0": [0.5] * 12}
    guard_q0_rows(good)
    guard_q0_for_mode(good, MODE4)
    guard_q0_for_mode(good, MODE12)
    # A 4-wide "projected" table is exactly what must never be constructed.
    with pytest.raises(Exp008Q0Error):
        guard_q0_for_mode({"state-v1.5|agg|S|le0": [0.5] * 4}, MODE4)
    with pytest.raises(Exp008ConfigError):
        guard_q0_rows({})


def test_mode4_addresses_the_same_columns_of_the_same_row():
    """No renumbering: mode4 reads indices 0/3/6/9 of the 12-wide row."""
    row = [float(i) for i in range(12)]
    table = {"state-v1.5|agg|S|le0": row}
    guard_q0_for_mode(table, MODE4)
    assert [row[i] for i in exp008.guard_q0_action_indices(MODE4)] == [
        0.0, 3.0, 6.0, 9.0]


def test_primary_study_q0_builder_is_untouched():
    """B6 adds no new Q0 constructor and renames none of the frozen ones."""
    from sparkrl.agent import q0 as q0_mod
    assert q0_mod.Q0_VERSION == Q0_VERSION
    assert hasattr(q0_mod, "build_q0_from_exp002")
    assert hasattr(q0_mod, "build_neutral_q0")
    exp008_builders = [n for n in dir(exp008)
                       if n.startswith("build_") and "q0" in n.lower()]
    assert exp008_builders == []


# --- TRAIN-only guards ----------------------------------------------------------
def test_train_split_is_the_only_admissible_split():
    guard_split(TRAIN)
    for split in (TEST, VALIDATION, "TRAIN", "", "anything"):
        with pytest.raises(Exp008ScopeError):
            guard_split(split)


def test_test_and_validation_cells_are_refused():
    guard_cell("F1_agg", "small", FROZEN_DATASET_SEED)
    guard_train_cells(TRAIN_CELLS)
    for family, scale, seed in (("F4_ski", "small", 0),     # unseen family
                                ("F1_agg", "large", 0),     # unseen scale
                                ("F1_agg", "small", 4),     # TEST seed
                                ("F1_agg", "small", 3)):    # VALIDATION seed
        with pytest.raises(Exp008ScopeError):
            guard_cell(family, scale, seed)
    with pytest.raises(Exp008ScopeError):
        guard_train_cells(("F4_ski|small",))
    with pytest.raises(Exp008ScopeError):
        guard_train_cells(("F1_agg|large",))


def test_malformed_or_unknown_cells_are_configuration_errors():
    for cells in ((), "F1_agg|small", ("F1_agg",), ("|small",),
                  ("NotAFamily|small",), ("F1_agg|huge",)):
        with pytest.raises(Exp008ConfigError):
            guard_train_cells(cells)


def test_test_metrics_can_never_enter_an_a3_a4_path():
    guard_metrics({"split": TRAIN, "execution_time_s": 1.0})
    for bad in ({"split": TEST}, {"split": VALIDATION},
                {"test_family": "F4_ski"}, {"test_scale": "large"},
                {"test_seed": 4}):
        with pytest.raises(Exp008ScopeError):
            guard_metrics(bad)


def test_a_config_cannot_declare_a_non_train_split_or_other_dataset_seed():
    with pytest.raises(Exp008ScopeError):
        complete_a4_config(split=TEST).validate_configuration()
    with pytest.raises(Exp008ScopeError):
        complete_a4_config(dataset_seed=4).validate_configuration()


# --- A5 lock --------------------------------------------------------------------
def test_a5_arm_is_refused():
    with pytest.raises(A5DisabledError):
        guard_arm(A5_ARM_ID)
    with pytest.raises(A5DisabledError):
        guard_a5(arm=A5_ARM_ID)
    with pytest.raises(A5DisabledError):
        arm_config_from_mapping(A5_ARM_ID, {})


def test_multi_step_and_non_zero_gamma_are_refused():
    guard_a5(gamma=0.0)
    with pytest.raises(A5DisabledError):
        guard_a5(multi_step=True)
    for gamma in (0.9, 0.5, 1.0, -0.1):
        with pytest.raises(A5DisabledError):
            guard_a5(gamma=gamma)
    with pytest.raises(A5DisabledError):
        complete_a4_config(gamma=0.9).validate_configuration()


def test_a5_is_absent_from_the_scope_summary_arms():
    summary = arm_scope_summary()
    assert A5_ARM_ID not in summary["arms"]
    assert "DISABLED" in summary["a5_status"]


# --- seeds ----------------------------------------------------------------------
def test_agent_seeds_are_structurally_validated_but_never_invented():
    guard_agent_seeds([0, 1])
    guard_agent_seeds([7])                        # no frozen seed set imposed
    with pytest.raises(Exp008IncompleteError):
        guard_agent_seeds(None)
    for bad in ([], [0, 0], ["0"], [True], 3):
        with pytest.raises(Exp008ConfigError):
            guard_agent_seeds(bad)


# --- configuration artifact -----------------------------------------------------
def test_shipped_config_declares_every_unresolved_field_as_null():
    raw = load_exp008_config()
    assert raw["experiment_id"] == EXP008_ID
    assert raw["schema_version"] == CONFIG_SCHEMA
    assert raw["authorization"]["execution_authorized"] is False
    assert set(raw["arms"]) == set(ALL_ARMS)
    for arm, block in raw["arms"].items():
        assert block["q0_projection"] is False
        assert block["dataset_seed"] == FROZEN_DATASET_SEED
        assert block["split"] == TRAIN
        assert block["q0_source"] is None
        assert block["agent_seeds"] is None
        assert block["train_cells"] is None
        assert block["episode_horizon"] is None
        assert block["early_stop_rule"] is None
        assert block["execution_budget"] is None
        assert block["live_execution_charging_rule"] is None
    # only the A4 arm carries the one frozen execution-control field
    assert raw["arms"][ARM_A4_MODE4]["action_mode"] == MODE4
    assert raw["arms"][ARM_A4_MODE4]["reward_variant"] is None
    for arm in A3_ARMS:
        assert raw["arms"][arm]["action_mode"] is None


def test_config_schema_is_closed():
    with pytest.raises(Exp008ConfigError):
        arm_config_from_mapping(ARM_A4_MODE4, {"unknown_key": 1})
    with pytest.raises(Exp008ConfigError):
        arm_config_from_mapping(ARM_A4_MODE4, {"alpha": "fast"})
    with pytest.raises(Exp008ConfigError):
        arm_config_from_mapping(ARM_A4_MODE4, {"agent_seeds": "0,1"})


def test_all_arm_configs_load_deterministically():
    a, b = all_arm_configs(), all_arm_configs()
    assert list(a) == list(ALL_ARMS)
    assert a == b


# --- provenance -----------------------------------------------------------------
def test_provenance_records_every_required_manifest_field():
    record = complete_a4_config().to_provenance()
    for key in ("experiment", "arm", "reward_variant", "action_mode",
                "action_subset", "state_schema", "q0_source", "q0_variant",
                "q0_projection", "agent_seeds", "dataset_seed", "split",
                "train_cells", "t_ref_fingerprint", "alpha", "gamma",
                "epsilon_schedule", "early_stop", "execution_budget",
                "aqe_condition", "implementation_fingerprint",
                "unresolved_fields", "execution_authorized"):
        assert key in record
    assert record["experiment"] == EXP008_ID
    assert record["action_subset"] == [0, 3, 6, 9]
    assert record["q0_projection"] is False
    assert record["q0_rows_wide"] == 12


def test_provenance_never_fabricates_an_unresolved_value():
    cfg = arm_config_from_yaml(ARM_A3_TIME_ONLY)
    record = cfg.to_provenance()
    unresolved = set(record["unresolved_fields"])
    assert unresolved == set(required_fields(ARM_A3_TIME_ONLY))
    # every unresolved field is carried as an explicit null, never a guess
    # ('early_stop_rule' is the manifest key 'early_stop').
    for field in unresolved:
        key = "early_stop" if field == "early_stop_rule" else field
        assert record[key] is None
    assert record["reward_variant"] == FORMULA_A3_TIME_ONLY   # fixed by the arm
    assert record["execution_authorization"] == EXECUTION_AUTHORIZATION


def test_arm_config_is_frozen_and_immutable():
    cfg = arm_config_from_yaml(ARM_A4_MODE4)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.arm = ARM_A3_R3                       # type: ignore[misc]


# --- non-authorization firewall -------------------------------------------------
def test_module_declares_zero_executions_and_no_authorization_path():
    assert EXECUTION_AUTHORIZED is False
    assert EXECUTION_AUTHORIZATION == "NO"
    assert (exp008.SPARK_EXECUTIONS, exp008.TRAINING_EXECUTIONS,
            exp008.TEST_EXECUTIONS) == (0, 0, 0)
    summary = arm_scope_summary()
    assert summary["execution_authorized"] is False
    assert (summary["spark_executions"], summary["training_executions"],
            summary["test_executions"]) == (0, 0, 0)


def test_module_never_imports_spark_or_a_runner():
    source = exp008.__file__
    text = open(source, encoding="utf-8").read()
    for forbidden in ("pyspark", "SparkSession", "sparkrl.spark",
                      "sparkrl.rl.env", "run_training", "subprocess"):
        assert forbidden not in text


def test_scope_summary_marks_r4_non_executable():
    arms = arm_scope_summary()["arms"]
    assert arms[ARM_A3_R4_LOG_RATIO]["executable"] is False
    assert arms[ARM_A3_R4_LOG_RATIO]["incomplete_reason"]
    for arm in (ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A4_MODE4):
        assert arms[arm]["executable"] is True     # executable IN KIND only
        assert arms[arm]["incomplete_reason"] is None
        assert arms[arm]["required_but_unset"]     # ...never in configuration
