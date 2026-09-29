# 12. Security, Reliability, and Governance Layer

Governance is what makes the loop deployable rather than merely interesting (Figure 18). Cluster security is simplified by the single-node deployment (no new network services; the sampler is a local daemon thread), while policy enforcement is where the layer is strictest: the 500-execution budget is an environment-owned guard counted across manifests, the F-FAIL invariant forbids failed configurations from ever yielding positive reward, and the TEST seal is a code-level authorization boundary verified by 36 gate checks — not a convention. Access control maps to these same guards: training, validation, and test splits each admit only their authorized entry points, and any crossing needs a named decision before a single run.

Reliability mechanisms operate at three levels: run level (timeouts convert pathological configs into −1 rewards instead of hangs), training level (checkpoints every 25 episodes, early stopping, smoke-test gates), and program level (pre-designed Plan-B scope rungs; 52 decision-log entries recording every authorization, reconciliation, and negative outcome). The result is fault tolerance with a paper trail: when the mode gate resolved NO or the agreement gate failed, the project degraded gracefully along planned paths instead of improvising.

## Table 8: Reliability and Governance Controls

| Control | Mechanism | Verifier |
|---|---|---|
| Budget guard (≤500) | Environment-owned counter, manifests summed | SC6 ledger 483/500 |
| F-FAIL (failures never rewarded) | r = −1 + Q-update applied | Unit test pins behavior |
| TEST seal | Authorization guards per split | Day-31 gate 36/36 |
| Deterministic analysis | Seeded resampling, frozen code | 16/16 corroboration |
| Immutable record | Content hashes, no-overwrite artifacts | Reproducibility harness |
| Scope discipline | Pre-designed Plan-B rungs | DEC-011 consumed rung 1 |
| Negative-outcome reporting | Decision log entries | M8 FAIL, H2/H3 open |
