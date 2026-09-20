"""Collection gate for the live-Spark integration suite (DEC-037 section 4).

WHY THIS EXISTS. These tests execute REAL Spark and several of them write a
training manifest under ``results/training/smoke/`` carrying a non-zero
``budget.live_executions``. At the ledger level that is indistinguishable
from a training run, so ``pytest`` over this directory SPENDS the frozen SC6
research budget (PLAN line 45, cap 500). It has happened twice:

  * DEC-033 - six live TRAIN executions on 2026-09-19, charged, unauthorized;
  * DEC-038 - fifteen more on 2026-09-20, charged, unauthorized.

Twenty-one of five hundred executions were consumed by test invocations that
nobody intended as experiments, and an execution record cannot be deleted
once written - it can only be disclosed and charged.

THE GATE. Collection here is SKIPPED by default and runs only when
``SPARKRL_ALLOW_SPARK=1`` is set, in the same explicit-opt-in shape as the
``--allow-spark`` flag that ``scripts/run_exp005.py`` and
``scripts/run_exp006.py`` already require before they touch Spark.

This deliberately INVERTS the older ``SPARKRL_SKIP_SPARK=1`` convention in
``tests/integration/test_spark_smoke.py``, which is opt-OUT: under opt-out
the default spends budget and you must remember to say no. Under opt-in the
default costs nothing and spending is a thing you say yes to. The older
variable still works and still forces a skip; setting both skips.

WHAT THIS MUST NOT BREAK. ``pytest tests/unit`` is what every validator's
own test gate runs (``scripts/validate_day30.py`` check 23,
``scripts/validate_day31.py`` check 35). This file lives in
``tests/integration/`` and is not loaded for ``tests/unit``, so that path is
untouched. Nothing here changes what the integration tests assert - only
whether they are collected at all.

To run them deliberately, from the canonical venv (DEC-007: sparkrl_env311):

    SPARKRL_ALLOW_SPARK=1 python -m pytest tests/integration

and expect the ledger to move. Check with ``scripts/validate_day31.py``
check 22 before and after, and record any charge by decision.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

ALLOW_ENV = "SPARKRL_ALLOW_SPARK"
LEGACY_SKIP_ENV = "SPARKRL_SKIP_SPARK"
HERE = Path(__file__).resolve().parent


def _spark_allowed() -> bool:
    """True only on an explicit opt-in that no legacy skip overrides."""
    if os.environ.get(LEGACY_SKIP_ENV) == "1":
        return False
    return os.environ.get(ALLOW_ENV) == "1"


def _under_this_directory(item) -> bool:
    """True only for items collected from THIS directory tree.

    pytest hands ``pytest_collection_modifyitems`` the WHOLE session's item
    list, not just the items under the conftest that defines the hook. An
    unfiltered loop therefore skips tests/unit too, which is far worse than
    the footgun it was written to close: ``pytest tests`` would report a
    green, fully-skipped run and the validators' own unit gate would be
    satisfied by a suite that asserted nothing. Filter by path.
    """
    path = getattr(item, "path", None) or getattr(item, "fspath", None)
    if path is None:
        return False
    try:
        return HERE == Path(str(path)).parent or HERE in Path(str(path)).parents
    except (OSError, ValueError):       # pragma: no cover - defensive
        return False


def pytest_collection_modifyitems(config, items):
    """Skip the live-Spark integration items unless explicitly allowed.

    A skip (not a deselect) so the reason is reported rather than silent:
    a run that spends nothing should say so out loud.
    """
    if _spark_allowed():
        return
    skip = pytest.mark.skip(reason=(
        f"live-Spark integration suite gated by DEC-037 section 4: these "
        f"tests execute real Spark and write training manifests that CHARGE "
        f"the frozen SC6 budget. Set {ALLOW_ENV}=1 to run them deliberately "
        f"and record the charge by decision."))
    for item in items:
        if _under_this_directory(item):
            item.add_marker(skip)


def demo() -> None:
    """Self-check: the gate is closed by default and opens only on 1."""
    saved = {k: os.environ.get(k) for k in (ALLOW_ENV, LEGACY_SKIP_ENV)}
    try:
        os.environ.pop(ALLOW_ENV, None)
        os.environ.pop(LEGACY_SKIP_ENV, None)
        assert not _spark_allowed(), "default must be CLOSED"

        os.environ[ALLOW_ENV] = "1"
        assert _spark_allowed(), "explicit opt-in must open the gate"

        os.environ[ALLOW_ENV] = "true"
        assert not _spark_allowed(), "only the exact string '1' opens it"

        os.environ[ALLOW_ENV] = "1"
        os.environ[LEGACY_SKIP_ENV] = "1"
        assert not _spark_allowed(), "legacy skip must still win"
        print("conftest gate self-check: OK")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


if __name__ == "__main__":
    demo()
