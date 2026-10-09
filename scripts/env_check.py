#!/usr/bin/env python
"""Run all AdaSpark environment checks; optionally regenerate the environment report.

Usage (inside the project venv, from the repository root):
    python scripts/env_check.py                  # check this machine; writes nothing
    python scripts/env_check.py --write-report   # also rewrite docs/ENVIRONMENT_REPORT.md
                                                 # and docs/environment_report.json

The committed report records the study machine, so it is rewritten only on request.
Exit code 0 unless a check FAILED (verdict BLOCKED).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sparkrl.utils import envcheck  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write-report", action="store_true",
                    help="overwrite the committed environment report under docs/ with this machine's results")
    args = ap.parse_args()
    report = envcheck.run_all(write_report=args.write_report)
    sys.exit(0 if report["verdict"] != "BLOCKED" else 1)
