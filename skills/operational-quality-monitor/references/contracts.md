# Aggregate and cohort contract

## Supported metrics

Version 1 supports **rates/proportions of cases**, such as late completions / evaluated
completions, approval returns / evaluated approvals, or on-time outcomes / evaluated outcomes.
`numerator <= denominator` is mandatory. Duration averages/percentiles, unbounded event counts
per case, control-effectiveness causal estimates and cross-cohort grand totals are unsupported.

Each configured metric has an opaque ID, definition version, role (`outcome` or `guardrail`),
worsening direction, rate threshold, minimum absolute rate change, minimum observed denominator,
minimum outcome coverage, and consecutive-day requirement. Thresholds are fractions, so 0.05
is five percentage points. Threshold breach is strict (> for higher-worse, < for lower-worse);
deterioration is inclusive at the configured minimum change. Exact rational comparisons avoid
floating-point threshold boundary errors. Rates are sum(numerator) / sum(denominator), not
averages of daily rates. Different-sized comparison windows are allowed but require context.

## PostgreSQL reporting-view profile

Use an operator-approved, existing reporting replica/view through the established psycopg
client and a dedicated SELECT-only role. Configure schema, view and column mappings, not SQL.
`OPS_DATABASE_DSN` (or a configured environment-variable name) is supplied through the existing
secret mechanism. This skill neither configures credentials nor creates database objects.

The view supplies exactly one row per metric/cohort/UTC day, including zero-population days:

| Column | Meaning |
| --- | --- |
| id | Stable unique source record ID; no names, emails or secret URLs |
| metric_id, cohort_id | Exact configured IDs; cohorts may overlap |
| bucket_start, bucket_end | Timezone-aware timestamps, exactly one UTC day, half-open interval |
| numerator | Cases exhibiting the defined outcome among the observed denominator |
| denominator | Eligible cases with an observed/classifiable outcome |
| missing | Eligible cases whose outcome is missing/unclassifiable |
| definition_version | Matches the configured definition, including eligibility and timing rules |
| population_complete | Source asserts the eligible population is fully enumerated, not sampled |
| finalized | Source asserts the daily bucket is finalized after the reporting lag |

Counts are nonnegative integers; booleans and fractional counts are rejected. `eligible` is
`denominator + missing`; outcome coverage is `denominator / eligible`. If no eligible cases
exist, coverage/rate cannot establish a signal. A finalized complete population can still have
missing outcomes, which must be counted in `missing`. **These flags are assertions, not proof
of census completeness.** Upstream reconciliation is the operator's responsibility.

Definitions must explain the counted case unit, eligible population, status/outcome timing,
business calendar/SLA, treatment of cancellations and reopenings, cohort assignment, and how
missing outcomes are enumerated. A case must not be double counted across days within the same
metric/cohort. Prefer outcome-date buckets or a documented fixed cohort observation cutoff;
never mix these definitions under one version. These semantics cannot be inferred from SQL.

The source query is a fixed SELECT, with psycopg-quoted identifiers, bound metric/cohort/time
values, read-only transaction, statement timeout, deterministic ordering and `max_rows + 1`
truncation detection. No generated SQL, temporary tables, arbitrary functions or source writes
are exposed. Approved views must not call side-effecting functions; SQL read-only mode alone
cannot guarantee safety of arbitrary unsafe server functions. SDK/database response bodies are
materialized before local caps; use server resource limits and narrow views.

The existing Datadog RCA profile remains available for a later case investigation. It is not
used for population monitoring in this version: sampled logs/spans and their query counts do
not establish eligible business cases or missing outcomes. No automatic CRM/ERP integration
or schema discovery is claimed. The reporting view is the explicit source prerequisite.

## Evidence gates and prioritization

- Missing daily buckets, inadequate denominators/coverage, unfinalized or non-census rows,
  or definition mismatches make the affected metric/cohort comparison insufficient.
- Retrieval failure/truncation, invalid rows, duplicates or out-of-scope rows conservatively
  withhold **all** comparisons for the configured source. Invalid content is not retained.
- Valid incomplete counts remain visible as observed totals, not estimated complete counts.
- A usable comparison becomes `attention` for a threshold breach, configured window
  deterioration, or a run of consecutive daily breaches. Each day in a run must itself meet
  denominator and coverage requirements. `no_signal` means no configured trigger, not proof
  of healthy operations. Data-review findings remain visible even alongside high priorities.
- `high`: threshold breach plus window deterioration. `medium`: another configured signal.
  `review_data`: insufficient evidence. `none`: no trigger. These are triage rules, not risk scores.

Reports retain normalized aggregate rows, exact refs, resolved windows, thresholds and a SHA-256
link for reproducibility. The hash is not a source signature and cannot certify source truth.
No row-level personal data or free-text event messages are requested. Still, small cohorts and
opaque IDs may be sensitive: use approved aggregate views, pseudonymous cohort IDs and private
output retention. Minimum denominator gates inference, not anonymization or cell suppression.
