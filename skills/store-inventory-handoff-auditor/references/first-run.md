# First fictional store audit

From this repository checkout with Python 3.11+:

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ops-store-handoffs --scope examples/store-handoffs/scope.json --policy examples/store-handoffs/policy.json --approvals examples/store-handoffs/approvals.json --mock examples/store-handoffs/fictional.json --output /tmp/store-demo-audit
```

Use a new output directory. Outputs are private (directory 0700, files 0600); existing directories are refused. No credentials, services or model are needed. Wheel installation includes CLI and skill instructions in `share/operational-quality-skills/skills`; examples are in the checkout. Copy the full skill directory into your host's supported skill location if needed; this does not install into any remote personal skill directory automatically.

The fictional demo illustrates three selected store/SKU line cycles:

- RETAIL-DEMO-001: ten units received, eight explicitly posted against that receipt. Four reserved/picked, two fulfilled and acknowledged; one of those two later returned. Review two unobserved posted units and two unobserved fulfilled units. The return does not reopen fulfillment or establish restocking.
- RETAIL-DEMO-002: three reserved but four recorded picked; four fulfilled and sent with no acknowledgment observed. Review the recorded quantity discrepancy and four unobserved acknowledgments; do not conclude stock loss.
- RETAIL-DEMO-003: conflicting open/complete statuses without explicit supersession. Reconcile records; pending-step inference is suppressed until the conflict is resolved.

`audit.json` contains deterministic findings, timelines, coverage, approval provenance and hash. `review.json` provides host review instructions. A host can read these using the skill to prepare an evidence-linked human-review brief; the CLI does not invoke an LLM or perform any external action.

The one-hour thresholds are fictional examples, not a recommended store service level. To change them, create a new version with an approved content hash using `operational_quality.control_validation.digest(policy.content())`; match its exact approval quote through `approval.links` as in the fixture. Approval must precede scope start. A digest binds content but does not authenticate the approver. Policy applicability and role access remain human checks.
