# Fictional control coverage review

From a Python 3.11+ checkout, install into a virtual environment with `python -m pip install .`, then:

```sh
ops-control-coverage --register examples/control-coverage/register.json --evidence examples/control-coverage/evidence.json --mock examples/control-coverage/fictional.json --output /tmp/control-coverage-demo
```

Use a fresh output directory. Files are mode 0600, directory 0700; overwrite is rejected. No services, credentials or models are required. The wheel contains the CLI and skill directory under `share/operational-quality-skills/skills`; examples remain in the checkout. Copy the skill directory into the host's supported location if needed; no remote personal-skill installation is implied.

The fictional register selects six administrative obligations with an example five-minute grace period. These are not recommended pharmacy thresholds:

1. Successful run recorded within its window.
2. Successful run recorded after its deadline and grace.
3. Failed run recorded.
4. Explicit skip bound to an exact obligation hash and pre-window approval quote.
5. No run observed in complete asserted ledgers beyond the due/grace boundary.
6. Failed attempt followed by an explicitly linked non-overlapping successful retry, with both retained.

`coverage.json` contains the register, approval provenance, ledgers, per-obligation conclusions and counts including unknowns/skips. `review.json` supplies trusted host-review instructions and report hash. Counts summarize only the selected approved register, not overall control coverage or effectiveness.

The register and skip are content-bound by canonical digests (`operational_quality.control_validation.digest`). Changing the register requires a new approved quote containing its ID and hash. A skip quote must contain skip ID and hash of its content excluding links; the skip also binds the exact typed obligation digest. Approval is source-asserted, not authenticated. Reconciliation never creates approval or executes an obligation.

Use the existing improvement workbench for human-reviewed hypotheses and accountable proposals, and existing Control Validation for baseline/pilot outcomes, guardrails and fidelity. This skill only checks whether expected execution evidence is observed; it does not duplicate either workflow or transform a missing record into a causal conclusion.
