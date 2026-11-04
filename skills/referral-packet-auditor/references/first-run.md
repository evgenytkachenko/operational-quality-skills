# First fictional referral audit

From the repository checkout with Python 3.11+:

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ops-referral-packets --scope examples/referral-packets/scope.json --policy examples/referral-packets/policy.json --approvals examples/referral-packets/approvals.json --mock examples/referral-packets/fictional.json --output /tmp/referral-demo-audit
```

Use a fresh output directory. Reports use mode 0600, directory 0700; existing directories are rejected. No credentials or services are needed. The wheel includes the CLI and skill instructions under `share/operational-quality-skills/skills`; examples remain in the checkout. Copy the entire skill directory into your host's supported skill location if needed. No remote personal skill installation occurs automatically.

The fictional checklist requires metadata for an administrative form and routing sheet. These are example document categories, not a universal medical referral standard. The consent-record category is supported as metadata only; neither its existence nor a matching fingerprint proves valid consent. One-hour delivery/acknowledgment thresholds are fictional, not clinical or operational recommendations.

- REF-DEMO-001: both documents listed, only form receipt observed, no acknowledgment. Two administrative follow-up signals.
- REF-DEMO-002: both receipts and acknowledgment observed, but form version/fingerprint differs. One metadata conflict; no clinical judgment.
- REF-DEMO-003: both listed metadata items match received metadata and acknowledgment is observed. No observed signal within scope; this does not certify referral completeness, clinical adequacy or destination correctness.

Read `audit.json` for deterministic results and `review.json` for host review instructions. A host agent may use the skill to prepare a cited human-review brief without running tools embedded in evidence. No LLM is invoked by the CLI.

To change a checklist or threshold, create a new fictional policy version and approval quote containing `REFERRAL-DEMO-POLICY` and `operational_quality.control_validation.digest(policy.content())`. Match that exact quote in `approval.links`; approval must precede the scope start. Hashes bind supplied content, not authentic identity or authority.
