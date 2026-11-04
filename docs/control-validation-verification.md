# Operations Control Validation verification

Remote main was safely fast-forwarded from the reviewed RCA version to the reviewed monitor
commit `191c3ba5920df3f0229ce00053981198ccb3d84f`, after its 94 tests passed. Remote main
was verified with `git ls-remote`. Control Validation begins from that commit on a new branch.

## Reuse and scope

The evaluator reuses MonitorConfig, monitor aggregation/coverage/budget logic, the existing
fixed psycopg SELECT profile, private JSON artifact I/O, redaction, the RCA Assessment schema
and the MIT-licensed exact-quote provenance checker. The original third-party notice remains
in place. No private case data, new vendor connector, custom SQL engine, model or production
write path was introduced. Approvals/context use bounded host-prepared snapshots from already
authorized sources; no approval-service integration is claimed.

The CLI produces deterministic evaluation evidence and a host-agent review handoff. It has
no LLM, rollout, schedule or messaging calls. Keep/change/stop are human-review recommendations.
The approved control is bound to the exact selected RCA review/proposal and criteria hash;
these are integrity links, not authenticated signatures or permission grants.

## Tests and review

The suite passes 141 tests, including all 94 pre-existing RCA/monitor tests. All three
skills pass the skill-creator validator. Tests cover proposal/report integrity, approval scope/revocation/timing, criteria changes,
implementation evidence/timing/fidelity, quote-presence checks and invalid companion quotes,
segmented weighted rates, guardrail stops, zero/small denominators, missingness/buckets,
source failures/truncation inherited from monitor, confounding, matched comparisons,
no-overwrite/private outputs and source/configuration safety. No-network fixtures prevent
service access in the test process; CLI smoke tests use synthetic inputs.

Independent review identified ignored contamination evidence: supplied baseline fidelity
could show prior exposure, or a comparison cohort could have received the control, without
blocking a favorable effectiveness recommendation. This was fixed. Available baseline
exposure/ambiguity now withholds effectiveness conclusions, and matched comparators require
usable, complete, zero-exposure evidence in both windows. Regressions cover these cases, and independent follow-up review found no significant
remaining defect.
No nonexistent baseline fidelity data is invented for a control that did not yet exist.

## Limits

No live service, credentials, real data, external scheduler or inference model was used.
Tests cannot authenticate human approval, determine whether a true quote supports a claim,
prove implementation, reconcile eligible populations, establish disjoint segments or validate
live database permissions/view semantics. Source completeness and context assessments remain
upstream assertions. Unknown confounders may remain even after a documented review.

The evaluator supports case proportions, not duration averages, survival analysis, causal
identification or statistical significance/power. Comparison adjustment is descriptive and
does not validate exchangeability or parallel trends. Small-cell counts/opaque IDs may remain
sensitive; denominator gates are not anonymization. Redaction is best-effort. Client response
materialization precedes local byte limits; server-side resource controls remain necessary.

All recommendations require human review. Keep does not authorize expansion; stop does not
execute a suspension. No rollout, source edit, irreversible action, external schedule,
notification or new-branch publication is part of this work.

Both documented synthetic CLI scenarios execute successfully: the complete pilot recommends
keep for human review and the unresolved-confounding plan recommends insufficient evidence.
The built wheel installs into an isolated non-editable environment, contains all three skill
folders, and its installed control-validation command produces the expected pilot result.
