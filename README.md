# Operational Quality Skills

An evidence-led agent skill for business-process delays, routing errors, rework and
recurring exceptions. It combines deterministic cross-system correlation with an LLM-led
investigation, competing hypotheses and preventive controls for human review.

## Install

Python 3.11+:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,integrations]'
```

Copy `skills/operations-root-cause` into your host's configured skills directory (for Codex,
`~/.codex/skills/operations-root-cause`), keeping its references and agents metadata together.
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
