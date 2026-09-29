# 10. Explainability and Decision Intelligence Layer

A policy the operator cannot inspect is a liability, so AdaSpark treats explainability as a layer rather than a paragraph (Figures 15–16). Every decision is traceable: the acting policy is a named checkpoint in the policy store (e.g., `b801f4a7df200b04`, 84 episodes, ε = 0.05), its Q-table is a plain JSON mapping states to action values, and the manifest behind it records code version, seeds, and cell coverage. No decision is ever a black-box output — the greedy action for any state can be read off the table and checked against the evidence density behind it (episodes per state per seed).

Confidence is quantified, not asserted. Equation (2) defines the decision-confidence score as cross-seed greedy-policy agreement — the fraction of evidence-bearing states on which independently trained replicates choose the same action:

conf(s) = |{seeds agreeing on argmax_a Q_seed(s,a)}| / |seeds|,   C = mean over evidence-bearing states   (4)

Measured at C = 0.20 against a 0.70 threshold (M8, FAIL), this score did exactly what a confidence measure should do: it blocked the promotion of a single "winner" and forced the honest reporting of three replicate arms (DEC-015). Explainability here is therefore not visualization alone but decision intelligence — the system refusing to claim more than its evidence supports, with the refusal itself recorded.
