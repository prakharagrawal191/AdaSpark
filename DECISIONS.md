# Decision Log

Every architectural/environmental decision is recorded here with its rationale.
Format: `DEC-xxx | date | decision | rationale | alternatives rejected`.

## DEC-001 | 2026-09-07 | Virtual environment outside the repository
The venv lives at `%USERPROFILE%\sparkrl_env`, not `<repo>\.venv`.
**Rationale:** the repository sits in a OneDrive-synced folder (risk R9); thousands of
venv files under OneDrive cause sync churn and file locks. Activation is documented in
README.md. *Rejected alternative:* in-repo `.venv`.

## DEC-002 | 2026-09-07 | Bulk data root outside the repository
Datasets, Spark event logs, and Spark temp dirs default to `%USERPROFILE%\sparkrl_data`,
overridable via `SPARKRL_DATA_ROOT`. Resolution is implemented in
`src/sparkrl/utils/paths.py` (no absolute paths hard-coded in code).
**Rationale:** risk R9 (OneDrive interference with bulk IO); keeps the repo lightweight.
The repo `data/` subfolders remain as conventional placeholders (`.gitkeep`).

## DEC-003 | 2026-09-07 | PySpark pinned to 4.0.4
PyPI offers 4.0.0–4.2.0 and the 3.5.x line. Spark 4.0 officially supports Python 3.12 and
Java 17 — both present on this machine. The 4.0.x line is a mature patch series; 4.1/4.2
are newer minors with less ecosystem mileage. **Fallback** if the Day-2 smoke matrix fails
on Windows: Python 3.11 venv + `pyspark==3.5.x`, or WSL2 (per approved plan §39).

## DEC-004 | 2026-09-07 | Source layout: `src/sparkrl/` package
Maps the approved architecture (planning doc §28) onto the Day-1 instruction tree:
- `sparkrl.spark` + `sparkrl.workloads` + `sparkrl.datagen`  ↔ `src/spark/`
- `sparkrl.monitoring` ↔ `src/monitoring/`
- `sparkrl.env` (RL environment) ↔ `src/environment/`
- `sparkrl.agent` ↔ `src/rl/`
- `sparkrl.runner` + `sparkrl.analysis` ↔ `src/optimization/` + `src/evaluation/`
- `sparkrl.utils` ↔ `src/utils/`
Top-level `experiments/` holds the experiment registry and per-experiment YAML configs;
`configs/` holds cross-cutting configuration.

## DEC-005 | 2026-09-07 | Execution backend: native Windows local-mode (PROVISIONAL)
Priority chain: native Windows → WSL2 Ubuntu → Docker. Native Windows is chosen
provisionally (Java 17 + PySpark pip wheel present). Final confirmation happens in the
**Day-2 smoke-test matrix** (Parquet IO, event logs, winutils/Hadoop-native warnings).

## Open items
- Day 2: commit the approved planning document as `docs/PLAN.md`.
- Day 2: winutils / Hadoop-native assessment on real Parquet workloads (smoke matrix).

## DEC-006 | 2026-09-07 | Spark-on-Windows native-IO failure — empirical findings (Day 1)
**What was tested (all measured, see `docs/ENVIRONMENT_REPORT.md`):**
1. `pyspark==4.0.4` + Java 17, no HADOOP_HOME → SparkContext startup **hard-fails**
   (`Hadoop 3.4.x Shell.<clinit>` throws when `HADOOP_HOME` is unset on Windows).
2. Added winutils shim (cdarlint `hadoop-3.3.6`: `winutils.exe` + `hadoop.dll`) at
   `%USERPROFILE%\hadoop` → session startup, count jobs, and event-log creation **work**.
3. Parquet **write** fails in `ParquetOutputCommitter.commitJob` with
   `UnsatisfiedLinkError: NativeIO$Windows.access0` — Hadoop 3.4.x jars call a native
   export the 3.3.6 dll does not provide; removing `hadoop.dll` (builtin-java fallback)
   does **not** bypass the commit-path native call.
4. No Hadoop 3.4.x winutils builds exist in the community repos probed
   (cdarlint: 2.x–3.3.6 only; kayrnt 3.4.x: 404).

**Provisional backend decision for Day 2 (primary):** keep native Windows but switch the
pinned stack to the battle-tested Spark-on-Windows combination — **Python 3.11 venv +
`pyspark==3.5.x` (Hadoop 3.3.x client) + the 3.3.6 winutils shim already installed**
(documented fallback per DEC-003 / plan §39). Fallback-of-fallback: WSL2 Ubuntu + Spark
(current WSL2 has no Linux distro installed; `wsl --install -d Ubuntu-24.04` would be
required). Docker remains last resort. **Nothing is final until the Day-2 smoke matrix
passes end-to-end (Parquet write/read + event log) on the chosen stack.**

**Known secondary issue (Day-18 scope):** event-log parsing needs robustness work — the
envcheck event-log probe hit `JSONDecodeError` on a partially-flushed log after a failed
run. Parser hardening with fixture tests is already scheduled (Day 18).

**Environment actions taken today (persisted):** `HADOOP_HOME=%USERPROFILE%\hadoop` set as
a Windows **User** environment variable; shim files in `%USERPROFILE%\hadoop\bin`.

