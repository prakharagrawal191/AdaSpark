#!/usr/bin/env python
"""Run all AdaSpark environment checks and (re)generate the environment report.

Usage (inside the project venv, from the repository root):
    python scripts/env_check.py

Exit code 0 unless a check FAILED (verdict BLOCKED).
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sparkrl.utils import envcheck  # noqa: E402

if __name__ == "__main__":
    report = envcheck.run_all(write_report=True)
    sys.exit(0 if report["verdict"] != "BLOCKED" else 1)
