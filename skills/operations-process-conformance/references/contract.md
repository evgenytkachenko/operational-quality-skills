# Policy, trace and exception contract

## Approved policy

A policy has an opaque ID/version, half-open validity interval, known step names, acceptable
initial/final steps, required observed steps and permitted directed edges. Every edge declares
allowed queue-to-queue handoffs and optionally a maximum elapsed wall-clock interval. Step and
queue values must match normalized workflow fields exactly. A human must verify that these
fields represent business transitions rather than technical log activity.

The policy's canonical SHA-256 excludes its approval wrapper. The approval must be recorded
no later than policy effective time, have decision `approved`, match the policy hash, and cite
an exact sanitized approval quote containing policy ID and hash. Policy changes require a new
version/approval record; do not edit a quote to manufacture authorization. The reused quote
checker establishes string presence, not authority, semantics or source authenticity.

One policy version is evaluated per invocation. A trace assigned to another version, spanning
validity boundaries, or requiring unmodeled grandfathering is unknown; split/review it with the
correct approved policy. This version does not implement a BPMN engine, concurrent branches,
conditional rule expressions, automatic policy discovery or business-calendar calculations.
Initial/final-step rules are independent of required-step waivers.

## Authoritative events and bounded sources

Reuse the existing RCA `Config`, source mappings, clients, redaction and normalization:
20 explicitly selected case IDs, seven-day collection window, at most six sources, bounded
pages/rows/time/text. This is deliberately a case-trace audit, not population monitoring.
For population-level outcome rates, use Operational Quality Monitor's aggregate contract.
No population noncompliance denominator or prevalence is inferred here.

Choose one existing PostgreSQL workflow profile as authoritative (`workflow_source`). It
supplies `id`, `case_id`, timezone-bearing `timestamp`, `activity`, `queue`, `message` through
the existing fixed SELECT. Datadog logs/spans/events and other configured sources supply
context only. Their missingness is disclosed but cannot establish missing business steps.
A context-source outage does not by itself invalidate a complete authoritative trace.

An additional operator-approved manifest view on the **same configured PostgreSQL connection**
is queried with fixed quoted identifiers, bound case IDs, a read-only transaction, statement
timeout and a case-count-plus-one row cap. No custom vendor connector or new credential store
is added. Configure only schema/view/column mappings; no arbitrary SQL or table creation.
Approved views must not call unsafe side-effecting functions; use a dedicated SELECT-only role.

The manifest supplies one record per requested case:

| Field | Meaning |
| --- | --- |
| id, case_id | Stable manifest reference and exact workflow case ID |
| policy_id, policy_version | Policy assigned to this whole trace |
| first_event_at, last_event_at | Expected full-trace boundaries, inclusive timestamps |
| event_count | Expected unique canonical workflow event count, at least one |
| complete, closed | Source asserts full lifecycle coverage and a closed case |
| clock_uncertainty_seconds | Nonnegative bound on each event timestamp's uncertainty |

Counts and flags are upstream assertions, not independent proof of completeness. Missing,
truncated, duplicated, invalid or out-of-scope manifests conservatively withhold conclusions.
Actual event count/boundaries must agree. The full trace, including each boundary event's declared timestamp uncertainty, must fit
inside the collection and policy validity intervals. Boundary overlap yields unknown. Open cases, unmapped steps, partial primary retrieval or duplicate
source IDs yield unknown. Exact duplicate events are not silently treated as harmless evidence.
The current collector conservatively treats any primary-source normalization warning as partial.

The event and manifest queries are **not an atomic cross-system snapshot**. Use stable closed
trace exports/views and reconcile upstream. Mismatches become unknown, but matching counts do
not prove that no concurrent mutation occurred. Response bodies are materialized before local
caps; use server limits and approved narrow views. The CLI never creates these views.

## Ordering, missing steps and delays

Events are compared by normalized UTC time only when every adjacent gap is greater than twice
the declared per-event uncertainty. Equal times and overlapping uncertainty intervals yield
unknown; record-ID sorting is never used as proof of temporal order. Residual skew, incorrect
uncertainty declarations and late arrivals remain verification limits.

For an adequate closed trace, an unlisted transition or handoff is a potential deviation.
A required step absent from the observed trace is reported as not observed under the source's
completeness assertion, not as proof of actual nonperformance. Requirements apply to each case;
conditional/branch-specific requirements need a suitable separate approved policy or explicit
exception rule. The evaluator does not invent hidden intermediate steps.

For a limit L and observed event gap D, with uncertainty U per event: D−2U > L is a potential
elapsed-time deviation; D+2U <= L is within the limit; overlap with L is unknown. These are
wall-clock intervals, not working time, labor effort, queue wait or calendar-adjusted durations.

## Scoped exceptions

The policy enumerates exception codes with an exact from/to step pair, permitted handoffs,
optional elapsed limit and explicitly waived required steps. A permit is scoped to a case,
policy/version, code, exact event refs and validity interval. Its decision/timing/scope hash
must be cited in an approval record: the quote must contain permit ID and hash, the permit
must be approved no later than the earliest possible first event, and the entire event pair
including timestamp uncertainty must fit the interval. Possible overlap with approval/validity
boundaries is unknown, not a permitted exception.
Multiple applicable permits yield unknown rather than an arbitrary choice.

A permit applies only when its handoff and elapsed-time conditions are satisfied despite clock
uncertainty. Only then are its listed required steps waived and the exception reported as
permitted. Failed/ambiguous conditions are findings, not automatic waivers. A satisfied base edge takes precedence over an unused alternative permission. A verified
permit is considered only when needed to justify the observed transition/handoff/timing or
a missing required step, and then can replace that edge. It does not authorize other
transitions; an unexercised alternative handoff does not invalidate the normal approved path.

`complete_for_cases` records which case exception inventories the host/source asserts complete.
An absent permit is not evidence of no permission when inventory is incomplete and a relevant
policy exception exists. An unverified supplied approval also leaves that event pair unknown.
Inventory declarations are not authenticated proof; a human must inspect underlying records.
No free-text log message can create an exception, extend validity or alter a policy.

## Output interpretation

Case states are `no_observed_deviation`, `permitted_exception`, `potential_deviation`, or
`unknown`. Unknowns take precedence over an overall deviation label, while all observable
findings remain listed. Context-gated cases have reasons without speculative findings.
Each finding cites workflow refs and policy/version; each adequate case cites its manifest.
Policy/permit quote ledgers and evidence hashes preserve traceability, not authenticity.
Human-reviewed RCA suggestions are never invoked automatically. No causal or compliance
certification, source-system write, notification or schedule is produced.
