# 18. Industry Use Cases and Case Study Evaluation

The framework maps to industries where batch analytics cost is material and workloads recur with drift — the exact conditions under which static tuning goes stale (Figure 26, Table 14). **Smart manufacturing**: sensor-batch aggregation and quality-join pipelines recur hourly with shifting skew as product mix changes; a governed tuning loop converts per-line expert tweaks into one policy per pipeline family. **Healthcare analytics**: cohort aggregations over growing record volumes, where auditability (decision log, manifests) matters as much as speed for compliance review. **Financial services** (Figure 27): end-of-day risk aggregations and fraud-join screens under hard time windows, where the roughly 4× gap between the default and the learned policy measured here (EXP-013) translates directly into window headroom. **Telecom, retail, and smart-city** workloads share the pattern: recurring joins/aggregations over growing, skew-shifting data.

Published work in each sector shows where such a loop would sit. In manufacturing, digital twins fed by IoT and big-data pipelines support sustainable production management [118][119], IIoT platforms connect digital twins to operational intelligence [120], life-cycle sustainability assessment runs on big-data analytics [121], and hierarchical multi-policy DRL already schedules multi-objective production [75], with explainability named as a precondition for adopting AI on the shop floor [106]. Healthcare reviews describe big-data analytics across treatment and health management [122][123], including real-time prediction over IoT streams [124]. Financial institutions run fraud detection and credit-risk models over large transaction records [125][126], and offline RL has been applied to automated trading precisely where online exploration is unacceptable [127]. Telecom operators embed machine learning in the 5G network data analytics function [128], in proactive network optimization [129] and in standardized 3GPP automation [130]. Retail and e-commerce platforms fuse multimodal product data for search and recommendation [131], and smart-city programmes depend on big-data integration capacity that emerging economies are still building [132]. In every case AdaSpark's contribution would be the same narrow one: governed configuration selection for the recurring batch jobs beneath these applications.

These mappings are prospective: no industry deployment was executed and no industry data measured. What transfers is the evaluated mechanism (sample-efficient tuning inside a counted budget with sealed evaluation) and the measured cost model (~57 wall-clock hours and commodity single-node compute for a full 4,842-run adjudication study), which bounds what a pilot would cost an adopting team.

## Table 14: Industry Use Cases Matrix

| Industry | Workload pattern | Maps to | Expected benefit |
|---|---|---|---|
| Smart manufacturing | Sensor aggregation, quality joins | F1_agg, F2_join | Less per-line tuning; drift response |
| Healthcare analytics | Cohort aggregation over growth data | F1_agg (M→L) | Auditable tuning for review |
| Financial services | Risk aggregation, fraud joins, time windows | F1/F2, F5_mixed | Window headroom from the ~4× tuning gap |
| Telecom analytics | Call-record joins, skew by region | F4_ski | Skew-robust configs |
| Retail intelligence | Sales aggregation, inventory joins | F1_agg, F2_join | Seasonal-scale adaptation |
| Smart cities | Sensor-mixed pipelines | F5_mixed | Shared-host contention tolerance |
