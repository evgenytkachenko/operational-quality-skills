# Execution workflow

Install the repository package (`python -m pip install -e '.[integrations]'`) in the host's
environment and copy `skills/operations-control-validation` with its references/metadata into
the host's skill directory. Wheels also include the skill under the environment's
`share/operational-quality-skills/skills/operations-control-validation` path.

## Inputs prepared by the host

The investigator selects a saved RCA proposal and pilot approval. The host uses already
configured, authorized read tools to obtain the approval, implementation and context records,
then prepares local plan/evidence snapshots. These JSON inputs are a tool contract, not a
requirement for the user to upload raw operational exports or invent connectors. No custom
approval-system adapter is claimed. If an approved source is unavailable, record the missing
evidence and stop at an insufficient recommendation; never invent an approval.

Use the existing RCA `review.json` as `--rca-review`; it contains `assessment.controls`.
Hash the parsed JSON with `digest()` and retain the selected control index/proposal. The
plan's `rca_reference` identifies the source review for a human. After specifying the fixed
criteria, `digest(ControlPlan.model_validate(plan).criteria())` yields the criteria hash for
comparison with an already recorded approval. A plan may omit approval while being prepared,
but evaluation then returns insufficient evidence. This helper does not obtain approval.

The nested aggregate configuration uses the existing approved PostgreSQL reporting view.
No live source is contacted unless `--live-read` is explicitly selected and context validation
passes. Read-only SQL, bound parameters, source limits and privacy behaviors are inherited
from the monitor. No credentials are put in plan, evidence or CLI command arguments.

## Fictional example

```sh
ops-control-validate --plan examples/control-validation/plan.json --rca-review examples/control-validation/rca-review.json --evidence examples/control-validation/evidence.json --mock examples/control-validation/pilot.json --output output/control-demo
ops-control-validate --plan examples/control-validation/confounded-plan.json --rca-review examples/control-validation/rca-review.json --evidence examples/control-validation/evidence.json --mock examples/control-validation/pilot.json --output output/control-confounded
```

The selected proposal is the existing fictional RCA recommendation to route invoices with
missing region to a review queue instead of defaulting to domestic approval. A fictional
approval specifies a seven-day baseline, a transition day and a seven-day pilot, separately
for standard and complex EU invoices. This approved evaluation plan supersedes the RCA's
suggested measurement duration; the change is explicit, not a retrospectively changed threshold.

In each segment, returns fall from 20% to 8%, late completion changes from 8% to 9% (below
the 20% guardrail threshold and five-point deterioration criterion), and pilot fidelity is
98% against a 95% criterion. The baseline includes 700 observed cases and the pilot 700 per
metric/segment, with no missing outcomes. All context checks are fictional, and both segments
meet keep criteria. This is an observed association, not evidence that the control caused it.
The second plan leaves a concurrent change unresolved and produces insufficient evidence.
No model was run to produce these fixtures or expected conclusions.

## Outputs and interpretation

- `validation.json`: selected proposal/approval/criteria linkage when valid, supporting
  quote ledger, segment results, recommendation, evidence hashes and limitations.
- `aggregate.json`: reused deterministic monitor evidence when context passed. Absent when
  context validation blocks retrieval; its absence must not be interpreted as no activity.
- `review.json`: host-agent qualitative-review prompt and references to the untrusted files.
- `run.json`: completion time and synthetic/live-read mode, without source credentials.

All artifacts together must fit the nested monitor output-byte budget. They are written to a
new private directory with private files, never over an existing run. Exit 0 means a report
was produced, including insufficient-evidence reports. Exit 2 means a configuration/execution
error; no source payload is printed. Inspect the recommendation and limitations, not just the
exit code. Keep saved snapshots: live late corrections can change a rerun's counts.

The host agent must review exact quotes, approver authority, implementation evidence, metric
semantics, population coverage, confounding and tradeoffs. Present keep/change/stop as a
proposed human decision and identify what would alter the recommendation. Do not grant new
rollout authority, extend the pilot, stop a system, alter a control, create schedules or send
external notifications. This skill creates only local review artifacts.
