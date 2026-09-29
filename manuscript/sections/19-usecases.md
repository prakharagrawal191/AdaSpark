# 18. Industry Use Cases and Case Study Evaluation

The framework maps to industries where batch analytics cost is material and workloads recur with drift — the exact conditions under which static tuning goes stale (Figure 26, Table 14). **Smart manufacturing**: sensor-batch aggregation and quality-join pipelines recur hourly with shifting skew as product mix changes; a governed tuning loop converts per-line expert tweaks into one policy per pipeline family. **Healthcare analytics**: cohort aggregations over growing record volumes, where auditability (decision log, manifests) matters as much as speed for compliance review. **Financial services** (Figure 27): end-of-day risk aggregations and fraud-join screens under hard time windows, where the 3–5× gap between default and tuned configurations measured here translates directly into window headroom. **Telecom, retail, and smart-city** workloads share the pattern: recurring joins/aggregations over growing, skew-shifting data.

These mappings are prospective: no industry deployment was executed and no industry data measured. What transfers is the evaluated mechanism (sample-efficient tuning inside a counted budget with sealed evaluation) and the measured cost model (~57 wall-clock hours and commodity single-node compute for a full 4,842-run adjudication study), which bounds what a pilot would cost an adopting team.

## Table 14: Industry Use Cases Matrix (prospective)

| Industry | Workload pattern | Maps to | Expected benefit |
|---|---|---|---|
| Smart manufacturing | Sensor aggregation, quality joins | F1_agg, F2_join | Less per-line tuning; drift response |
| Healthcare analytics | Cohort aggregation over growth data | F1_agg (M→L) | Auditable tuning for review |
| Financial services | Risk aggregation, fraud joins, time windows | F1/F2, F5_mixed | Window headroom from 3–5× tuning gap |
| Telecom analytics | Call-record joins, skew by region | F4_ski | Skew-robust configs |
| Retail intelligence | Sales aggregation, inventory joins | F1_agg, F2_join | Seasonal-scale adaptation |
| Smart cities | Sensor-mixed pipelines | F5_mixed | Shared-host contention tolerance |
