# Control-validation contract

## Proposal, approval and evidence

`ControlPlan` selects a control by index from the saved RCA review's `assessment.controls`.
The proposal string must match exactly and the canonical SHA-256 of the entire parsed review
must match `rca_review_sha256`. This links a proposed control; it does not assert the RCA cause
or proposal was proved correct. Use `digest()` from `operational_quality.control_validation`
for canonical hashes, not a raw file-byte checksum.

The criteria hash binds the selected control/report, proposal, registration timestamp,
fixed windows, source mapping, metric versions/roles/thresholds, pilot segments and optional
comparators. Budgets and runtime credentials are not evaluation criteria. The approval must
name the same control/cohorts/pilot window/hash, record `approved_pilot`, and be dated after
criteria registration and no later than pilot start. The exact approval quote must contain
both control ID and criteria hash. Changing a criterion requires a newly recorded approval;
do not edit an old record merely to make the validator pass.

Implementation must be recorded after approval, no earlier than baseline end and no later
than pilot start. Otherwise the stable baseline/pilot comparison is not supported. Use a
separate transition/ramp period between windows if appropriate. This is declared timing;
the validator cannot prove an actual rollout date from quote presence alone.

The evidence snapshot contains bounded records with opaque refs, kind (`approval`,
`implementation`, `context`) and text. Cite exact `source_id`, `part: text` and sanitized
quote. Required claims use the reused Hyper Agile quote/provenance checker. Every citation,
including companion citations, must resolve to the appropriate artifact kind. Common secret
patterns are redacted before matching; sensitive plan/citation text is rejected without being
persisted in an insufficient result. No source error payload is printed. Prompt-like text is
retained as untrusted evidence and never executed.

**Authority boundary:** an artifact kind, approver-role string, date, matching quote or SHA-256
is not a signature, authenticated identity, permission grant or semantic verification. A
trusted host/operator must obtain records from authorized sources and verify actual approval.
`source_authenticity` remains `UNVERIFIED`, quote semantic support remains `UNVERIFIED`, and
causal attribution remains `NOT_ESTABLISHED` on every recommendation.

## Aggregate and segmentation contract

Reuse the Operational Quality Monitor's daily aggregate reporting-view contract and existing
psycopg read-only client. The nested `monitoring` configuration requires explicit, nonoverlapping,
closed UTC baseline/pilot windows (1–90 days each), explicit cohorts and the existing aggregate
row/output/time budgets. No incident-case limits or new vendor connector is introduced.

A rate uses summed outcome numerator / summed observed denominator. Missing eligible outcomes
are counted separately and lower coverage. Require all daily buckets, adequate counts, consistent
versions and source-asserted census/finalization. No zero-denominator rate is inferred. Counts,
versions and completeness flags are upstream assertions, not independently verified population
truth. Keep the metric unit, eligibility, status timing, cancellations/reopenings and cohort
assignment consistent across windows. Definitions must be documented in the approved plan's
underlying source records. Do not sum overlapping segments or assume distinct IDs mean disjoint
people/cases. The evaluator does not pool segments, avoiding a misleading pooled improvement.

Roles:

- Exactly one primary outcome rate: configured target and minimum absolute improvement.
- One or more distinct guardrail rates: pilot threshold is the stop-review boundary; a
  baseline-to-pilot deterioration at the configured minimum change prompts change review.
- One distinct fidelity rate, higher-is-better: intended control applications / eligible
  observable applications during the pilot, with missing observations counted separately.

Both windows are required for pilot outcomes and guardrail-change comparisons. Fidelity is
required only for the pilot: do not fabricate baseline data for a control that did not exist.
The reused aggregate collector calculates the full metric/cohort grid; baseline fidelity can
therefore show an unused insufficient comparison in `aggregate.json`. Control validation
explicitly evaluates only its pilot window and records current fidelity issues. Its retrieval
budget conservatively allows for the full grid. Available pilot-baseline fidelity records are checked: any recorded exposure, missing
outcome, unfinalized/non-census flag or definition mismatch blocks the untreated-baseline
assumption. Absent baseline fidelity is not proof of non-exposure; implementation/context
evidence remains necessary.

Optional comparator cohorts require primary outcome and control-exposure/fidelity records
in both windows. The exposure evidence must be complete and usable, with zero exposure
and zero missing outcomes. Missing exposure records do not mean untreated. Do not fabricate
zeroes; withhold the comparison if genuine exposure evidence is unavailable. Comparator
guardrail rows are not used by this version.

A one-to-one comparator mapping must cover every pilot segment, use distinct non-pilot IDs,
and have adequate outcome and unexposed-population evidence in both windows. The evaluator subtracts comparator
improvement from pilot improvement for a descriptive adjusted change. To recommend keep,
both raw and adjusted improvements must meet the worthwhile-change criterion. This does not
validate exchangeability, parallel trends, statistical significance or a causal effect.

## Confounding and recommendations

Review five domains explicitly: case mix, seasonality, concurrent changes, measurement and
spillover. `assessed_not_material` needs exact context evidence; `material` or `unresolved`
prevents an effectiveness keep/change conclusion. Absence from a log is not proof of no
concurrent change. Even a complete review cannot rule out residual confounding.

Apply these rules to every pilot segment:

1. A reliable pilot guardrail threshold breach yields **stop** for human safety review,
   even when another outcome/comparator is insufficient or confounding is unresolved.
   The result does not claim the control caused the breach.
2. Inadequate required aggregate evidence, exposed/ambiguous baseline evidence or an
   unverified untreated comparator yields **insufficient_evidence**. Material or
   unresolved confounding also yields insufficient evidence for effectiveness.
3. Pilot fidelity below its criterion yields **change**; it does not establish that a fully
   implemented control would be ineffective.
4. A guardrail's deterioration criterion met below its stop threshold yields **change**.
5. Outcome target and worthwhile improvement met, with adequate fidelity and guardrails,
   yields **keep** for human review within the current approval. With comparators, require
   raw and adjusted improvement. Otherwise recommend **change**, without claiming proof
   of ineffectiveness.

Overall priority is stop, then insufficient evidence, then change, then keep. No favorable
segment can hide another's stop/insufficient result. Threshold breach is strict; equality at
a target is acceptable. Worthwhile change is inclusive at the configured minimum. Exact
fraction arithmetic avoids floating-point boundary errors. Statistical power, significance,
time-to-event outcomes, duration percentiles, randomization and causal identification are
outside this version. All decisions remain recommendations, never actions.
