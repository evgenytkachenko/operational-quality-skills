# Operational Quality Monitor verification

The RCA branch was fast-forwarded to remote main at
`743a561965e2f73eba9cf8d64f6260f395a21253`, verified via `git ls-remote`, after its
54 tests passed. Monitor development starts from that commit on a separate branch.

## Implemented boundary

The new skill and `ops-monitor` executable perform one read-only aggregate evaluation.
It reuses the existing Pydantic configuration style, private bounded JSON artifact I/O,
credential-by-environment approach, fixed psycopg read-only queries, evidence refs and
human-review boundary. New metric/cohort models deliberately do not reuse RCA's incident
case-ID/window restrictions. No new vendor connector, SQL engine or model provider was built.

The current live profile is an operator-configured PostgreSQL daily aggregate reporting
view. No live view was queried or created. Datadog remains an RCA source rather than a
population denominator. The host-agent skill supplies interpretation and follow-up inquiry;
CLI results are deterministic evidence, not LLM-verified causal conclusions.

## Offline checks

All 94 tests pass, including the 54 existing RCA tests. Both skills pass the skill-creator
validator. The test suite covers prior RCA behavior and monitor weighted rates, exact threshold
boundaries, worsening direction, missing buckets, missing outcomes, low/zero denominators,
version changes, population/finalization assertions, malformed/duplicate/out-of-scope rows,
truncation, safe exception handling, input budgets, explicit and rolling windows, SQL
parameterization/read-only mode, no-overwrite/private outputs and CLI execution.

An independent reviewer confirmed the math and source boundaries and identified two issues:
future windows could emit findings, and the output budget counted compact rather than
serialized JSON. Both were fixed with regressions and passed independent follow-up review. Future-ending windows now fail before
retrieval. The CLI checks all serialized output files together before creating the directory.

## Verification limits

No live PostgreSQL source, credentials, model, external scheduler or notification service
was used. Mocks cannot validate tenant permissions, server functions, indexes, resource use,
view semantics, source reconciliation or actual eligible-population completeness. Counts and
flags remain upstream assertions. No transport-byte limit is enforced before client response
materialization. Source read failures yield insufficient-data reports, not a healthy verdict.

Minimum denominator is an inference gate, not anonymization. Small-cell counts and identifiers
may still be sensitive. Cohorts can overlap, observation windows can have different case mix,
and seasonality is not adjusted. No statistical significance, causal effect, persistent alert
suppression or cross-run trend model is implemented. An approved scheduler may invoke the
one-shot CLI, but no external schedules or delivery actions are configured by this work.

The four documented synthetic CLI scenarios (deterioration, insufficient evidence, source
unavailable and rolling replay) execute successfully without business-service access.

Wheel smoke test: installed the built wheel into an isolated, non-editable environment,
verified both packaged skill folders, and ran ops-monitor on the deterioration fixture.
The installed executable produced the expected two attention findings.
