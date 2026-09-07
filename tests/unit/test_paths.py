"""Unit tests for path resolution (no Spark required).

Run with:  python -m pytest -m unit
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sparkrl.utils import paths

pytestmark = [pytest.mark.unit]


def test_project_root_contains_pyproject():
    root = paths.project_root()
    assert (root / "pyproject.toml").exists()
    assert (root / "src").is_dir()


def test_data_root_defaults_outside_repo(monkeypatch):
    monkeypatch.delenv(paths.DATA_ROOT_ENV, raising=False)
    root = paths.resolve_data_root(create=False)
    assert root == Path.home() / "sparkrl_data"
    assert root.resolve() != paths.project_root().resolve()


def test_data_root_env_override_and_creation(monkeypatch, tmp_path):
    fake = tmp_path / "dataroot"
    monkeypatch.setenv(paths.DATA_ROOT_ENV, str(fake))
    root = paths.resolve_data_root(create=True)
    for sub in ("raw", "processed", "generated", "eventlogs", "tmp"):
        assert (root / sub).is_dir()


def test_eventlog_and_tmp_dirs_are_under_data_root(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.DATA_ROOT_ENV, str(tmp_path / "dr"))
    assert paths.eventlog_dir().parent == paths.resolve_data_root()
    assert paths.tmp_dir().name == "tmp"
