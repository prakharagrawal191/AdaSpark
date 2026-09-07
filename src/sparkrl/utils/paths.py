"""Path resolution for AdaSpark.

Design rules (approved plan §27/§28, risks R9):
- No machine-specific absolute paths are hard-coded anywhere in the codebase.
- Heavy artifacts (datasets, Spark event logs, Spark temp dirs) live OUTSIDE the
  repository, because the repository may sit inside a OneDrive-synced folder;
  OneDrive sync on bulk IO causes file locks and slowdowns.

Resolution order for the data root:
1. ``SPARKRL_DATA_ROOT`` environment variable (set this to relocate everything).
2. ``<user home>/sparkrl_data``.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT_ENV = "SPARKRL_DATA_ROOT"

_SUBDIRS = ("raw", "processed", "generated", "eventlogs", "tmp")


def project_root() -> Path:
    """Return the repository root (the directory containing pyproject.toml)."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(
        "project root not found: no pyproject.toml above "
        f"{Path(__file__).resolve()}"
    )


def resolve_data_root(create: bool = True) -> Path:
    """Resolve (and optionally create) the external data root directory."""
    override = os.environ.get(DATA_ROOT_ENV, "").strip()
    root = Path(override) if override else Path.home() / "sparkrl_data"
    if create:
        for sub in _SUBDIRS:
            (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def eventlog_dir(create: bool = True) -> Path:
    """Directory for Spark event logs (one JSON file per application run)."""
    return resolve_data_root(create) / "eventlogs"


def tmp_dir(create: bool = True) -> Path:
    """Directory for Spark local temp dirs and scratch files."""
    return resolve_data_root(create) / "tmp"


def data_root_env_name() -> str:
    """Name of the environment variable that overrides the data root."""
    return DATA_ROOT_ENV
