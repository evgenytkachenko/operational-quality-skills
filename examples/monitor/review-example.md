# Fictional monitoring review

This is a hand-authored illustration, not a live finding or an executed model's assessment.

Current window: October 1–7, 2026 (UTC daily buckets). Baseline: September 24–30.
All 56 expected daily metric/cohort buckets are present, finalized and asserted complete
by the synthetic source. Missing outcomes are zero. Completeness flags are not independent
verification of the underlying eligible population.

| Cohort / metric | Baseline | Current | Change | Priority |
| --- | --- | --- | --- | --- |
| EU invoices / late completion | 56/700 = 8% | 175/700 = 25% | +17 pp | High |
| EU invoices / approval returns | 21/700 = 3% | 98/700 = 14% | +11 pp | High |
| Domestic invoices / late completion | 56/700 = 8% | 56/700 = 8% | 0 pp | No configured signal |
| Domestic invoices / approval returns | 21/700 = 3% | 21/700 = 3% | 0 pp | No configured signal |

EU late completions exceed the 15% threshold and the configured five-point deterioration
trigger. Each of the seven current daily buckets also breaches the threshold with adequate
daily denominators. Evidence refs are
`workflow_metrics:late_completion-invoices_eu-7` through
`workflow_metrics:late_completion-invoices_eu-13`; baseline refs end in `-0` through `-6`.

The approval-return guardrail also deteriorated and exceeded its 8% threshold; current refs
are `workflow_metrics:approval_returns-invoices_eu-7` through `-13`, with baseline `-0` through
`-6`. These exact full refs appear in `monitor.json`. Outcome and guardrail movement warrant
review together, but do not establish that returned approvals caused delays.

Before attributing deterioration, check cohort composition, business-calendar effects,
metric eligibility and concurrent operational changes. A two-window difference is not a
statistical trend or control-effectiveness estimate. Domestic stability does not prove the
EU workflow's cause and is not a causal control group.

Suggested next step: a human should resolve an authorized sample of affected EU invoice
case IDs from the approved workflow source, document selection limitations, and invoke
`operations-root-cause` with the seven-day current window. No case IDs can be inferred from
these aggregate row IDs. No RCA run, notification or source-system change has been performed.
