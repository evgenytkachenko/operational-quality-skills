# Operational Quality Skills

Four read-only agent skills for business-process delays, routing errors, rework and
recurring exceptions. They combine deterministic evidence processing with host-agent
review and explicit human decisions.

| Skill | Purpose |
| --- | --- |
| [Operational Quality Monitor](skills/operational-quality-monitor/SKILL.md) | Assess population-level outcome/guardrail rates and prioritize emerging signals |
| [Operations Root-Cause](skills/operations-root-cause/SKILL.md) | Investigate affected cases, compare causal hypotheses and propose preventive controls |
| [Operations Control Validation](skills/operations-control-validation/SKILL.md) | Evaluate an approved pilot against outcomes, fidelity, guardrails and confounding |
| [Operations Process Conformance](skills/operations-process-conformance/SKILL.md) | Review workflow transitions, handoffs and exceptions against an approved policy |

## Install

Python 3.11+:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,integrations]'
```

Copy the desired folders under `skills/` into your host's configured skills directory
(for Codex, `~/.codex/skills/`), keeping each folder's references and agents metadata together.
Install the CLI in the same environment the host uses. The skill is independently readable;
the helper provides deterministic enforcement. No credentials or model installation occurs.
This repository does not automatically install into a personal ChatGPT skill service.

## Try the fictional case

```sh
ops-rca --config examples/config.json --mock examples/fictional.json --output output/demo
ops-rca-review --packet output/demo/evidence.json --assessment examples/assessment.json --output output/review
python -m pytest -q
```

The fictional invoice-approval case combines workflow history with Datadog-shaped logs,
span evidence and an event. The example assessment is a hand-authored demonstration,
not a claim of an actual model run. Read `evidence.json`, then use `inquiry.json` with the
host agent to test competing explanations. `review.json` carries citation checks and
explicit human-review/semantic-support limitations.

Production profiles are predefined: official Datadog SDK reads and a configurable
PostgreSQL reporting view via psycopg. Scope, source field mappings and budgets live in
JSON configuration. An operator configures approved sources once; an investigator supplies
case IDs and dates, without raw-file exports or new connector code. `--live-read` is an
explicit opt-in; development and tests use only synthetic responses.

See the [skill](skills/operations-root-cause/SKILL.md),
[integration and security limits](skills/operations-root-cause/references/integrations.md),
[execution modes](skills/operations-root-cause/references/workflow.md), and
[reuse/license decisions](docs/reuse.md).

## Verification limits

Tests cover synthetic integration contracts, pagination, boundaries, quote validation,
redaction, malformed data and CLI flow. No real Datadog/PostgreSQL instance or LLM is
contacted in the test suite. Tenant schemas, authentication, row-level permissions and
real model reasoning still need an authorized deployment trial. SDKs load response bodies
before local caps; host-agent tools are governed by host permissions, not CLI enforcement.
Redaction is best-effort, and quote validity cannot prove causality. Review before use.

## Operational Quality Monitor

```sh
ops-monitor --config examples/monitor/config.json --mock examples/monitor/deterioration.json --output output/monitor-demo
ops-monitor --config examples/monitor/rolling.json --mock examples/monitor/deterioration.json --as-of 2026-10-09T00:00:00Z --output output/monitor-replay
```

The monitor has independent aggregate budgets and daily cohort contracts rather than RCA's
case-ID limits. It calculates weighted rates, missingness, coverage, threshold breaches and
descriptive window differences. It withholds comparisons for insufficient data, produces
a host-agent review handoff and recommends human-reviewed RCA only when warranted.

Its live profile reads an existing approved PostgreSQL aggregate reporting view through
psycopg; sampled Datadog incident logs are not treated as a business population. See the
[aggregate contract](skills/operational-quality-monitor/references/contracts.md),
[one-shot/scheduled execution interface](skills/operational-quality-monitor/references/execution.md),
[fictional review example](examples/monitor/review-example.md) and
[monitor verification](docs/monitor-verification.md). No external schedules or notifications
are created. The CLI performs no LLM calls; the installed skill guides host-agent review.

## Operations Control Validation

```sh
ops-control-validate --plan examples/control-validation/plan.json --rca-review examples/control-validation/rca-review.json --evidence examples/control-validation/evidence.json --mock examples/control-validation/pilot.json --output output/control-demo
```

This skill links the exact RCA-proposed control to a recorded pilot approval and fixed
evaluation criteria. It reuses bounded aggregate evidence, checks pilot implementation
fidelity and guardrails, reviews confounding and recommends keep/change/stop/insufficient
evidence for human review. An approval hash is not an authenticated permission grant; no
rollout, stopping action, schedule or notification is executed.

See the [evaluation contract](skills/operations-control-validation/references/contract.md),
[host preparation and CLI workflow](skills/operations-control-validation/references/workflow.md),
and [verification limits](docs/control-validation-verification.md). The fictional scenario
includes both favorable observed results and an unresolved-confounding alternative.

## Operations Process Conformance

```sh
ops-conformance --config examples/conformance/config.json --policy examples/conformance/policy.json --approvals examples/conformance/approvals.json --permits examples/conformance/permits.json --mock examples/conformance/fictional.json --output output/conformance-demo
```

This skill reviews selected case traces against a versioned approved workflow policy. It
reuses existing source profiles, adds a bounded manifest lookup, applies narrowly scoped
exceptions and accounts for incomplete evidence and timestamp uncertainty. Datadog supplies
context, not authoritative business steps. Findings are potential deviations or unknowns,
not compliance certification or root causes. RCA handoffs require human review.

See the [policy/trace contract](skills/operations-process-conformance/references/contract.md),
[execution workflow](skills/operations-process-conformance/references/workflow.md) and
[verification limits](docs/conformance-verification.md).

## Pharmacy Prescription Handoff Auditor (synthetic profile)

The [Pharmacy Prescription Handoff Auditor](skills/pharmacy-prescription-handoff-auditor/SKILL.md), reconstructs fictional administrative intake, clarification, PA and pharmacy handoffs. It reports evidence-linked possible missing acknowledgments, owners, responses and next steps, recorded-status conflicts and repeated handoffs. Ambiguous identities and incomplete coverage yield unknown, and partial fills remain separate from case closure.

Install with `python -m pip install .`, then follow the [first-run guide](skills/pharmacy-prescription-handoff-auditor/references/first-run.md) for `ops-pharmacy-handoff`. This profile is mock-only: no PHI, live pharmacy integration, clinical or payer decisions, model runs or external actions. Existing urgency labels are preserved without assigning urgency. See [verification and limits](docs/pharmacy-handoff-verification.md).

## Store Inventory and Fulfillment Handoff Auditor

The [store auditor](skills/store-inventory-handoff-auditor/SKILL.md) reconstructs fictional receiving, receipt-specific availability postings, reservations, picks, fulfillment and acknowledgment. It flags linked quantity discrepancies and unobserved remaining quantities while keeping returns separate and treating incomplete/offline feeds or ambiguous matches as unknown. No stock balance, loss or fault is inferred.

Install with `python -m pip install .` and follow the [first-run guide](skills/store-inventory-handoff-auditor/references/first-run.md) for `ops-store-handoffs`. This separate profile is mock-only; no live vendor connector, stock adjustments, fulfillment actions, messages, schedules or model runs. See [verification](docs/store-handoffs-verification.md).

## Referral Packet Auditor

The [Referral Packet Auditor](skills/referral-packet-auditor/SKILL.md) reconciles fictional administrative document metadata and receiving-desk acknowledgment for an explicitly selected immutable referral packet revision. It flags checklist omissions, unobserved receipts and acknowledgments, and version/fingerprint conflicts; uncertain coverage or identity yields unknown.

Use `ops-referral-packets` with the [first-run guide](skills/referral-packet-auditor/references/first-run.md). It never reads clinical contents or makes consent, clinical, urgency, scheduling or insurance decisions. This profile is mock-only, without external actions or a live medical connector. See [verification](docs/referral-verification.md).

## Pharmacy Improvement Workbench (optional local LLM)

The [workbench](skills/pharmacy-improvement-workbench/SKILL.md) bridges evidence-backed hypotheses and approved control evaluation: detect repeated recorded administrative exception categories across selected fictional cases, draft competing explanations and controls using host review or an explicitly requested installed local Ollama model, then bind each proposal to an accountable role, deadline and closure-evidence requirement. Drafts are not approved or implemented actions.

Follow the [workflow](skills/pharmacy-improvement-workbench/references/workflow.md) for `ops-improvement`. Default mode makes no model calls; development tests use mocked responses only. The existing Control Validation skill remains responsible for approved pilots, guardrails, fidelity and measured outcomes. Read [execution limits](skills/pharmacy-improvement-workbench/references/limits.md) and [verification](docs/improvement-verification.md); no model accuracy, memory fit or real-company integration is claimed.

## Control Execution Coverage

The [coverage auditor](skills/control-execution-coverage/SKILL.md) reconciles an approved finite register of expected fictional administrative controls against run and skip ledgers. It distinguishes recorded success, late execution, failure, approved skip, unobserved execution and unknown coverage. It preserves retries and never treats successful execution as proof of effectiveness.

Use `ops-control-coverage` with the [workflow guide](skills/control-execution-coverage/references/workflow.md). It complements the improvement workbench's draft proposals and Control Validation's outcome evaluation. No live services, control execution, schedules, notifications or model runs occur. See [verification and branch assessment](docs/control-coverage-verification.md).

## End-to-end fictional pharmacy demonstration

After installation, run `ops-pharmacy-demo --output /tmp/pharmacy-quality-demo` and open the generated `START-HERE.md`. The [walkthrough](docs/pharmacy-quality-demo.md) connects detection, handoff evidence, scripted or optional local-model hypotheses, a fictional human-reviewed control, pilot validation, execution coverage and descriptive outcomes using existing components. Approvals are illustrative fixtures, never actual authorization; optional model proposals remain separate unapproved candidates. Use `--scenario missing-evidence` to see insufficient-evidence handling. No live services or model calls occur by default.

For a readable result, open the demo's `REPORT.md`. Run `ops-pharmacy-demo-review --directory /tmp/pharmacy-quality-demo` for a read-only, offline consistency check and printed report. It detects changed/missing/mixed JSON artifacts against the installed scripted fixtures without running a model; it does not authenticate evidence or approve controls. See the [verification guide](docs/pharmacy-quality-demo.md#readable-results-and-offline-verification).

Verification failures now identify the blocking check and a safe next step without echoing record contents. Add `--json` to `ops-pharmacy-demo-review` for structured results (exit 0 for consistency verified, 2 for failure). See [troubleshooting](docs/pharmacy-quality-demo.md#troubleshoot-a-saved-run-without-changing-it); the checker never repairs evidence or runs a model.
