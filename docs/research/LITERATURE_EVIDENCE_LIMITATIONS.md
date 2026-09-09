# Literature Evidence Limitations

*AdaSpark · Day 10 (2026-09-09) · companion to `docs/LITERATURE_MATRIX.md` v1.0 and `docs/research/RESEARCH_GAP.md` · full per-row routes in `docs/research/LITERATURE_VERIFICATION_LOG.md`*

> **Purpose.** Research transparency: state exactly how far the verified evidence reaches, which claims rest on abstracts rather than full text, and what must be rechecked before any stronger claim is made. These limits are already flagged per row in each matrix row's Limitation field; this note collects them in one place.

## 1. Abstract/Title-Scoped Rows (full text not retrieved)

Full texts behind paywalls were not fetched. Claims for these rows are scoped to verified abstracts/titles:

- **A2** (Spark SQL): abstract-level; no performance figures quoted beyond the abstract.
- **C2** (multi-objective Spark tuning on clouds): title/venue scope.
- **C3** (BO acquisition functions for Spark): title/venue scope.
- **C4** (BestConfig): abstract-level (cost/expertise framing).
- **C6** (deep-RL Spark job scheduling): title/venue scope.
- **D1** (deep-RL resource management): title/abstract scope.
- **E1** (CherryPick): title/abstract scope.
- **F1** (self-adaptive taxonomy): title/venue scope.
- **F2** (Second Research Roadmap chapter): title/venue scope.
- **G1** (MAPE-K vision): title/venue scope.
- **G2** (autonomic survey): abstract verbatim via CrossRef — abstract-level, not full-text.
- **H1** (Bao): abstract-level.
- **H2** (Neo): abstract verbatim via CrossRef — abstract-level.
- **I1** (learned indexes): title/venue scope.
- **I2** (SkinnerDB): abstract verbatim via CrossRef — abstract-level.
- **J1** (OtterTune): title/venue scope.
- **J2** (SMAC): title/venue scope.
- **J3** (few-shot BO): arXiv abstract page — abstract-level (conference paper per arXiv comment).
Fully abstract-read rows (stronger footing, still not full text): A1, A3, A4, A5, A6, B3, C1, C4, C5, C7, E2, G2, H2, I2, J3. Implementation-facts scope: B1 (Databricks blog + official Spark docs — explicitly non-peer-reviewed). B2 verified via OpenAlex/CrossRef DOI record.

## 2. What This Constrains

1. **Quantitative comparisons across papers are not licensed.** Effect sizes, trial counts, and head-to-head numbers live in full texts; the gap note therefore cites only abstract-stated figures (A1 10x, A5 order-of-magnitude, A6 100X-vs-Hive, C1 22.8–40.0%) and otherwise argues from problem framings and method classes.
2. **The "absence" part of the gap is scoped.** "The surveyed approaches do not, at verified scope, jointly demonstrate…" is an absence claim bounded by the 30-row corpus at abstract level. A full text in the queue (especially C2/C3/C4/C6/E1/J1/J2) could qualify it — which is why the gap note uses "predominantly", "at verified scope", and "within the literature corpus examined".
3. **No method detail beyond the abstract is asserted.** State/action/reward/algorithm decompositions for D1/E2/I2 and transfer protocols for J1/J3 are stated only where the abstract supplies them; anything deeper is deferred to full-text inspection.
4. **B1 is not peer-reviewed evidence.** AQE behaviors are documented from the vendor blog + official docs; the matrix labels this explicitly and the gap note never treats AQE figures as paper claims.

## 3. What Must Be Rechecked Later (if needed)

- Before any Tier-3-adjacent venue claim: fetch full texts of C2, C3, C4, C6, E1, J1, J2 (the load-bearing tuning/transfer rows) and confirm the gap-combination reading.
- Before quoting any number beyond the four abstract-stated figures above: fetch the source full text.
- C7 author-list caveat (Semantic Scholar "Jia-geng Feng" vs OpenAlex "Jiadong Feng") — check against IEEE Xplore when convenient; bibliographic only, does not affect the gap.
- If new papers are added later, route them through the verification log with the same ID/source/route/biblio/claim/full-text/decision/notes schema (controlled change, not silent append).
