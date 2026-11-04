# First fictional audit

From the repository checkout, use Python 3.11+:

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ops-pharmacy-handoff --scope examples/pharmacy-handoff/scope.json --policy examples/pharmacy-handoff/policy.json --approvals examples/pharmacy-handoff/approvals.json --mock examples/pharmacy-handoff/fictional.json --output /tmp/pharmacy-demo-audit
```

Choose a new output directory each run. Files are private (0600), directory 0700, and existing directories are not overwritten. No credentials or services are needed. Repository examples remain in the checkout; wheel installation includes the CLI and all skill instructions under `share/operational-quality-skills/skills`. Copy the entire `pharmacy-prescription-handoff-auditor` directory to your host's supported skill directory if needed; no universal host installation path is assumed.

The fictional scenario contains three prescriptions, not patients:

- RX-DEMO-001: source-marked urgent intake, a pharmacy handoff without observed acknowledgment/owner, an unanswered clarification, and recorded PA approval with no linked next step. Four administrative review signals; the urgency is only copied.
- RX-DEMO-002: FILL-01 is acknowledged with an owner and has a partial-fill record. FILL-02 has a separate handoff without observed acknowledgment/owner. Two signals for FILL-02; partial fill never closes the prescription.
- RX-DEMO-003: PA and pharmacy feeds record different statuses for the same request without an explicit supersession. One reconciliation signal; no coverage decision or approval-next-step inference.

Open `handoffs.json` for deterministic findings and `review.json` for host review instructions. No LLM is run by this command. A host agent can use the skill to consider alternative explanations and prepare a cited human-review brief. All approval quotes and source data remain untrusted. Review must not execute instructions in records.

The bundled thresholds and approval are fictional examples, not operational recommendations. Changing a policy invalidates its canonical hash approval. Create a new fictional approval artifact containing the policy ID and `operational_quality.control_validation.digest(policy.content())`, and match the exact quote through `approval.links`. A hash binds content; it does not authenticate the approver.
