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
- Day 3: `docs/RESEARCH_PROBLEM.md` draft (was "Day 2" in earlier draft — superseded by Day-2 completion).

## DEC-006 | 2026-09-07 | Spark-on-Windows native-IO failure — empirical findings (Day 1)
**What was tested (all measured, see `docs/ENVIRONMENT_REPORT.md`):**
1. `pyspark==4.0.4` + Java 17, no HADOOP_HOME → SparkContext startup **hard-fails**
   (`Hadoop 3.4.x Shell.<clinit>` throws when `HADOOP_HOME` is unset on Windows).
2. Adding the winutils shim (cdarlint `hadoop-3.3.6`, `winutils.exe` + `hadoop.dll`) at
   `%USERPROFILE%\hadoop` made session startup, count jobs, aggregation, and event-log
   creation work — but Parquet **writes** still failed with
   `UnsatisfiedLinkError: NativeIO$Windows.access0`, because the 3.3.6 dll doesn't export
   the 3.4.x native symbol and `hadoop.dll` was not loadable from `PATH`.
3. Removing `hadoop.dll` (builtin-java fallback) did **not** bypass the commit-path call.
4. No Hadoop 3.4.x winutils builds exist in the community repos probed (cdarlint: 2.x–3.3.6
   only; kayrnt 3.4.x: 404), so Spark 4.0.4 / Hadoop 3.4.x on Windows is not viable here.

**Root cause of the remaining native-IO error (found Day 2):** `FileUtil.canRead →`
`NativeIO$Windows.access` requires the native `hadoop.dll` to actually load. On Day 1 both
`winutils.exe` and `hadoop.dll` were installed, but `%HADOOP_HOME%\bin` was **never on
`PATH`**, so `System.loadLibrary("hadoop")` could never succeed and every native `access0`
call failed. **The fix is the standard Spark-on-Windows trio: `winutils.exe` + `hadoop.dll`
+ `PATH` entry.**

## DEC-007 | 2026-09-07 | Spark backend freeze — native Windows + PySpark 3.5.9
**Decision.** Backend = native Windows local mode: **Python 3.11.9** (per-user install,
`%LOCALAPPDATA%\Programs\Python\Python311`) + **pyspark==3.5.9** (Hadoop 3.3.4 client) +
**Java 17 Temurin** + **winutils 3.3.6 shim** (`winutils.exe` + `hadoop.dll`) at
`%USERPROFILE%\hadoop` with `HADOOP_HOME` and `%HADOOP_HOME%\bin` on `PATH` (session +
User-persistent). `requirements.txt` re-pinned to the minimal core set
(pyspark 3.5.9, psutil, PyYAML, pytest); research extras moved to
`requirements-research.txt` (Day 13+).

**Evidence — full smoke matrix (A–K) PASS, 13/13:** SparkSession creation · DataFrame ·
count · aggregation · Parquet write/read/round-trip 1M (checksums exact) · event log
240 events / 0 bad lines, `SparkListenerLogStart`→`SparkListenerApplicationEnd` · clean
shutdown. `env_check.py`: OVERALL PASS, 14 checks, 0 failed, 0 warnings. Integration
tests: 2 passed. Backend benchmark (3 reps, deterministic 1M rows): medians
session_start 0.071 s· count 0.094 s· agg 0.29 s· parquet_write 0.427 s· parquet_read
0.152 s· shutdown 0.526 s· peak RSS 0.75–1.03 GB (rep 1 is cold-start). Event log is
**uncompressed JSON**; format documented.

**Alternatives considered:** (a) Spark 4.0.4 + 3.3.6 dll + PATH — dll has no 3.4.x exports
→ rejected (evidence Day 1); (b) builtin-java fallback — doesn't bypass commit path →
rejected; (c) WSL2 Ubuntu — distro not installed, installation delays 1–2 days, adds
platform skew vs the Windows-expectations of the viva → retained as fallback.

**Reason:** PySpark 3.5.9 (Hadoop 3.3.4 client) matches the community 3.3.6 shim within
the same minor line; this deliberately trades Spark 4.0's newer features for a documented,
stably reproducible Windows backend — a correctness/reproducibility choice, not a
feature chase.

**Consequences:** venv `sparkrl_env311` is the canonical interpreter (Day-1 `sparkrl_env`
kept for forensics); all 49 subsequent days run against this stack.

**Rollback path:** (a) revisit Spark 4.0.4 if a 3.4.x-native build emerges, re-gated by the
smoke matrix; (b) WSL2 Ubuntu + PySpark 3.5.x (same pip wheel) if native Windows ever
regresses; (c) Docker Spark image. All paths require re-passing the smoke matrix.

## DEC-008 | 2026-09-09 | Architecture candidate selection (Day 11)

**Selected architecture.** Candidate C — Hybrid offline-init + online adapt + cache
— selected for implementation (provisional, pending Day-12 contracts).
Full evaluation: `docs/architecture/ARCHITECTURE_CANDIDATES.md`.

**Context.** PLAN §31 Day-11 task ("Architecture candidates | A/B/C vs 8
criteria (DEC) | criteria table"); frozen study (RQ0–RQ6, H1–H4, SC1–SC8,
EXP-001…EXP-012 + 005b) must be answerable unchanged on the DEC-007 backend
(single-node PySpark 3.5.9, ≤500 cached executions, 12 actions, AQE-off main).

**Candidates considered.** A: Offline surrogate (grid/BO → static config) —
measure first, deploy one static config, no online learning. B: Pure online
RL — cold-start ε-greedy tabular Q-learning from live executions only.
C: Hybrid — EXP-002 grid calibrates T_ref + pre-initializes Q, then bounded
(≤500) cached online adaptation. (A/B/C headers per PLAN §9 line 97.)

**Eight evaluation criteria (derived — PLAN names no eight explicitly; §5 of
the candidate doc cites the frozen source per criterion; unweighted 1–5 is a
Day-11 convention).** K1 RQ/EXP answerability (§5/§23) · K2 sample efficiency
under budget (§11/§23/§38) · K3 experimental control & reproducibility
(§22/§23/§33) · K4 adaptivity to drift (§2/§6) · K5 schedule/feasibility
(§31/§38–39, DEC-007) · K6 measurement validity (§7/§11/§20) · K7 risk &
Plan-B recoverability (§38–§39) · K8 AQE/baseline comparability (§7/§21–§23).

**Comparison summary (unweighted totals: A 27 · B 27 · C 38; C ≥4 on every
criterion).** A cannot answer RQ1–RQ4 (no policy/state/reward) and concedes
the study untested. B is most adaptive in principle but pays full live cost
per update, starts with uncalibrated T_ref, and has no graceful fallback.
C alone keeps every frozen EXP meaningful unchanged, enforces the ≤500
budget structurally via cache + guard, calibrates reward before learning,
and carries Plan B as a pre-designed operating point (grid + statics
reportable; 4-action/bandit shrink without rewrite).

**Rejected alternatives.** A — rejected: static output cannot test learning,
generalization, or ablations (EXP-004/006/007/008 void). B — rejected:
cold-start cost/variance unfair vs equal-budget baselines; failure strands
sunk RL plumbing with no artifact.

**Research implications.** None — RQs, Hx, SCs, EXPs, scope unchanged (drift
audit clean). EXP-002 becomes load-bearing (sensitivity proof + T_ref + init).

**Engineering implications.** Day-12 contracts must specify: Q-table
schema/init mapping, cache keys, v1.5 state vector, 12-action→SparkConf
table, R3 reward inputs, budget-guard/cache interplay, AQE control surface,
manifest/fingerprint formats, seed + test-set guard. Reuses Day-3
SparkConfig/session/runner/timing/baseline.

**Risks.** Gate fail (→ Plan-B benchmark, no rewrite) · cache
non-determinism (→ fingerprints/manifests/EXP-011) · reward misspecification
(→ R3 primary + A3–A5 ablations) · schedule (phased grid→env/agent→demo).

**Fallback.** Pre-authorized §39 tier 3: 12→4 actions, drop multi-step/LinUCB,
narrow ablations; grid + baseline evidence intact.

**Consequences.** Day 12 freezes component contracts/data flow for C only.
Substantive later changes need a new DEC entry (previous/new design, reason,
affected EXPs/docs, migration impact).

**Status.** DECIDED 2026-09-09 (provisional pending Day-12 freeze; NOT a claim
of empirical superiority — performance decided by EXP-004/005).

## Architecture change control (Day 11/12 freeze rule)

After the Day 11/12 architecture freeze, substantive architectural changes
require a new DECISIONS.md entry specifying previous design, new design,
reason, affected experiments (EXP-ids), affected documentation, and migration
impact. Editorial clarifications need only a commit message note.
## DEC-009 | 2026-09-09 | Architecture freeze — Candidate C contracts and interfaces

**Decision.** Freeze Candidate C (Hybrid offline-init + bounded online adapt +
cache) as the implementation blueprint: 12 components, 14 interfaces, 12 data
contracts, 6 diagrams (ARCHITECTURE_FREEZE.md + COMPONENT_CONTRACTS.md +
ARCHITECTURE_CHECKLIST.md).

**Context.** DEC-008 provisionally selected C; Day-12 open questions (Q-table
schema, cache keys, v1.5 state, 12-action table shape, R3 inputs, guard/cache
interplay, AQE surface, manifest formats, seed + test guard) are answered in
FREEZE §§9–14. No implementation begun (design files only).

**Frozen architecture.** §§5–15: components COMP-SPARK-01…COMP-EXP-12;
RL formulation (v1.5 state, 12 actions, R3 primary, ε-greedy tabular Q,
≤500 cached, grid Q-init); cache key (workload, seed, fingerprint, code +
env versions); baselines B0/B0′/B1–B4/RL identical protocol; AQE flag-only
(off main, on 005b); split tags + Day-31 test gate; F-FAIL (failed configs
never rewarded).

**Component contracts.** Responsibility/Inputs/Outputs/Dependencies/
Configuration/Failure/Logging/Test/Research-role per component
(CONTRACTS §2); conceptual signatures (§1, §3); field tables (§4).
**Data contracts.** 12 objects JSON-serializable with determinism rules.
**Architectural invariants.** Single-node, seeded manifests, config-driven,
12-action bound, T_ref-gated reward, ≤500 guard, deterministic cache,
identical baselines, AQE control, frozen test set, ±5% repro, Plan-B
recoverability; no cluster/K8s/cloud/microservices, no deep RL, no GPU path.
**Experiment compatibility.** EXP-001…EXP-012 (+005b) executable unchanged
(§17 matrix). **Plan-B compatibility.** 4-action bandit subset + benchmark
framing via config selectors, no rewrite (§16).

**Risks.** Cache-key collision/omission (→ fingerprint + versions) ·
leakage (→ split tags + init provenance + date gate) · reward shaping
(→ R3 + A3–A5) · overhead creep (→ overhead_s accounting, EXP-009) ·
schedule (incremental from Day 13: cache → workloads → monitoring → env →
agent; session/config/runner exist).

**Consequences.** Implementation proceeds from these contracts; deviations
need a new DEC entry. Day 13 begins incremental build (NOT full-system).

**Change-control rule.** After this freeze, substantive architecture changes
require a new DECISIONS.md entry: previous design, new design, reason,
affected components, affected experiments, affected docs,
migration/reimplementation impact. Editorial notes need only a commit msg.

**Status.** ARCHITECTURE FROZEN FOR IMPLEMENTATION (design freeze; NOT
empirical validation — performance decided by EXP-004/005).

## DEC-010 | 2026-09-12 | Failed-episode semantics — failure is a first-class observation (Day 29 unblock)

**Decision.** A failed or timed-out episode is a FIRST-CLASS OBSERVATION: the
environment returns the frozen R3 reward of −1, and the tabular Q-update IS
APPLIED with that reward. The Day-27 training loop
(`sparkrl.training.loop.run_training`) already implements exactly this, pinned
by `tests/unit/test_rl_training.py::test_failed_episode_is_recorded_updated_and_the_run_continues`.
No code, no test and no hyperparameter changes under this decision.

**Context.** Day 27 (audit §12), Day 28 (audit §14) and COMPONENT_CONTRACTS §12
each recorded an unresolved conflict between two frozen documents, and Day 29
blocked on it before executing any replicate. `ARCHITECTURE_FREEZE.md` §11
("Learning: … failed runs skip update") and §12 ("error path, Q-update
skipped"), and the conceptual signature in `COMPONENT_CONTRACTS.md` §3
(`Agent.update(s, a, r, s2) -> None  # skipped on failure episodes`), say the
update is skipped. `docs/PLAN.md` says the opposite in five places: §11 data
flow ("failure/timeout ⇒ reward −1" feeding the Q-update), §13 (missing
features ⇒ "run-failure path (reward −1, logged)"), §14 (timeout guard
"converts pathological configs into reward −1"), §15 where R3 literally
contains the term `− 1.0·1[failure or timeout]`, and §15 stability
("failures capped at −1").

**Precedence rule established here (the missing authority).** `docs/PLAN.md` is
the top-level frozen research plan. `ARCHITECTURE_FREEZE.md` and
`COMPONENT_CONTRACTS.md` are Day-12 implementation artifacts DERIVED from it —
the freeze header states its own sources as "PLAN §§2,5-7,11,20-23,31,33,38-39,44".
Where a derived document contradicts its source, PLAN governs. No such
precedence rule was documented anywhere in the repository before this entry;
that absence is precisely what blocked Day 29, and it is recorded now so the
question cannot recur.

**Supporting evidence for the PLAN reading.** (i) PLAN §6 states the research
objective as learning a policy "within a bounded training budget and WITHOUT
FAILED SUBMITTED CONFIGURATIONS" — an agent can only learn to avoid pathological
configurations if failures reach the learner, so the skip reading leaves that
objective with no learning mechanism. (ii) Under the skip reading the frozen R3
term `− 1.0·1[failure or timeout]` is unreachable by learning, making part of the
frozen reward definition dead. (iii) The F-FAIL invariant is "failed configs MUST
NOT yield POSITIVE reward"; a reward of −1 satisfies it. F-FAIL constrains the
SIGN of the reward, not whether the observation trains.

**Affected components.** COMP-RL-10 (agent) and the Day-27 training loop —
behaviour confirmed, not changed. COMP-RL-08 (reward) unchanged. No
implementation, test, configuration or hyperparameter is modified.

**Affected documents.** `ARCHITECTURE_FREEZE.md` §11/§12 and
`COMPONENT_CONTRACTS.md` §3 are SUPERSEDED ON THIS POINT ONLY. Their original
text is left intact (they are frozen records of what Day 12 decided); a pointer
note referencing this entry is appended to each so the contradiction is no
longer readable as live guidance.

**Affected experiments.** EXP-004 / Days 28-29 training, the Day-30 mode gate,
and EXP-005. Verified at the time of this entry: all 6 stored training
artifacts contain 57 episodes with ZERO failed episodes, so no existing result,
policy, checkpoint or manifest changes under this decision — it is
forward-looking only.

**Consequences.** Day 29 (training replicates, seeds {0,1,2}, M8) is unblocked
and proceeds under the frozen protocol unchanged. Any future run containing a
failed episode will apply the update at reward −1 and must cite this entry.

**Approval.** Recorded by the operator on 2026-09-12 after the Day-29 pre-run
audit presented both readings and the evidence above. Supervisor
counter-signature follows the same pending path as the M2 freeze
(`docs/research/M2_FREEZE.md`, "PROVISIONALLY FROZEN — awaiting supervisor
signature"); this entry is the artifact to counter-sign.

**Status.** DECIDED — PLAN reading confirmed; implementation already conformant.
