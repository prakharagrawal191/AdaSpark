# Architecture Checklist — Day-12 Freeze

*Candidate C · verify each box against ARCHITECTURE_FREEZE.md / COMPONENT_CONTRACTS.md / DEC-009.*

- [x] selected architecture documented (FREEZE §2; CANDIDATES §10; DEC-008/009)
- [x] all component boundaries defined (12 components, §5; inventory rationale recorded)
- [x] all interfaces defined (CONTRACTS §1 + §3 signatures)
- [x] all data contracts defined (FREEZE §7; CONTRACTS §4 field tables)
- [x] config flow defined (system/experiment/RL layers, §8)
- [x] RL state contract defined (v1.5 + A1 variant, §9)
- [x] action contract defined (12 actions + 4-subset, §9/CONTRACTS)
- [x] reward contract defined (R2/R3/R4 + T_ref gate, §9)
- [x] cache contract defined (key/hit/miss/invalidation, §11)
- [x] offline initialization defined (grid→T_ref→Q-init + leakage guards, §10)
- [x] train/validation/test separation defined (split tags + Day-31 gate, §14)
- [x] baseline interface defined (B0/B0′/B1–B4/RL identical protocol, §12)
- [x] AQE control defined (flag-only off/on, §13)
- [x] failure behavior defined (per-component + F-FAIL invariant, §15)
- [x] Plan-B path defined (config selectors, no rewrite, §16)
- [x] experiment compatibility checked (11-EXP matrix, §17)
- [x] diagrams created (6 Mermaid sources, §18.1–18.6)
- [x] no unnecessary infrastructure (single-node, §19 mapping)
- [x] no new RQ/Hypothesis/SC/EXP IDs (drift audit clean)
- [x] implementation not started (src/ untouched; design files only)
