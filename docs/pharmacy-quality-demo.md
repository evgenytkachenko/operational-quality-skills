# End-to-end fictional pharmacy quality demonstration

This is a reproducible walkthrough, not production automation or a clinical evaluation. Every case, record, aggregate, approval, implementation and reviewer statement is fictional. No actual human approved a pilot or implemented a control during a run. No PHI, medication details, patient identities or actual company systems are represented.

## One command

From the checkout, use Python 3.11+ and a virtual environment:

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ops-pharmacy-demo --output /tmp/pharmacy-quality-demo
```

Open `/tmp/pharmacy-quality-demo/START-HERE.md`, then `00-summary.json`. Use a new output directory each run. Directory permissions are 0700; files are 0600. The installed wheel includes all demo JSON fixtures, so the command also works outside the checkout. The existing nine skills and their tools remain available; this is an orchestration example, not another analysis engine.

## Walkthrough

| Stage | Existing component | What to inspect | Human boundary |
|---|---|---|---|
| Detection | Operational Quality Monitor | `01-detection.json`: recorded acknowledgment exceptions increase from 14/700 (2%) to 84/700 (12%) | Check definitions, eligibility and coverage before selecting cases |
| Case evidence | Pharmacy Prescription Handoff Auditor | `02-handoffs.json`: two selected cases have no observed acknowledgment beyond the example threshold | Unobserved does not mean acknowledgment never happened |
| Investigation | Pharmacy Improvement Workbench and shared RCA engine | `03-evidence.json`, `03-inquiry.json`, `04-scripted-review.json`: competing capture-gap and ingestion-delay hypotheses with exact citations | Scripted response is authored test material, not LLM output or proven root cause |
| Preventive control | Existing accountability proposal and ControlPlan contracts | `04-draft-proposal.json`, `fictional-inputs.json`: proposed acknowledgment completeness check, owner, review deadline and closure evidence | Fixed fictional approval and implementation records illustrate a review checkpoint; no real approval/implementation occurs |
| Validation | Operations Control Validation | `05-validation.json`, `05-aggregates.json`: criteria-bound baseline/pilot outcome, guardrail, fidelity and confounder records | Keep means retain within the fictional pilot for human review, never rollout |
| Execution | Control Execution Coverage | `06-execution-coverage.json`: seven explicit expected daily checks with recorded success | Run records establish neither faithful per-handoff application nor effectiveness |
| Outcomes | Existing aggregate calculations | `00-summary.json`: 84/700 to 28/700 (12% to 4%), an observed 8 percentage-point decrease | Synthetic descriptive change, not causal attribution or verified error reduction |

All files are local. `fictional-inputs.json` exposes the complete supplied fixture set for inspection. `00-summary.json` links outputs with canonical hashes. `03-sample-mapping.json` ties the same selected case IDs and original handoff refs to investigation event refs; it is an explicit fictional mapping, not an automatic connector or inferred patient join. Derived case exception labels and source handoff findings are not independent corroboration.

## Definitions, windows and denominators

The fictional administrative rule is acknowledgment recorded within one hour of a handoff. The population metrics are precomputed illustrative daily aggregates, not recomputed from the two-case sample. Each daily cohort contains 100 eligible administrative handoffs under fixed v1 definitions:

- `ack_exceptions`: eligible handoffs with no acknowledgment recorded within the example rule / all eligible handoffs. Detection comparison: September 24–30 versus October 1–7, 2026 UTC. Pilot comparison: October 1–7 versus October 9–15.
- `late_handoffs`: handoffs recorded outside a separate example administrative completion target / eligible handoffs. Kept at 21/700 (3%) in baseline and pilot; the fictional stop threshold is 10%.
- `check_applied`: eligible handoffs recorded as receiving the pilot check / eligible handoffs. Baseline exposure is 0/700; pilot fidelity is 686/700 (98%), above the fictional 95% criterion.

The selected RX-DEMO-001 and RX-DEMO-002 narratives illustrate two exceptions in the baseline window. Their rows are not an exhaustive population listing or a basis for the 700 denominator; aggregate counts are independently authored synthetic records. Daily control execution coverage has a different denominator: seven planned executions. Seven successes cannot establish 98% fidelity or the 8-point outcome improvement.

After detection closes October 8 at 00:00 UTC, the scripted proposal is prepared at 06:00 and its plan is registered at 08:00 UTC, approved at 09:00, implemented at 12:00, before the October 9 pilot start. The accountable review deadline is October 17, after pilot evidence closes. Approval binds the exact scripted review/control and criteria hash. Execution obligations use that criteria hash as their explicit scope digest. Confounders are assessed in fictional reviewer statements; matching quotes and hashes do not authenticate those statements. No comparator is supplied, and residual confounding remains possible. Nothing here establishes clinical safety or appropriateness.

## Missing-evidence replay

```sh
.venv/bin/ops-pharmacy-demo --scenario missing-evidence --output /tmp/pharmacy-quality-missing
```

This marks the pilot aggregate retrieval truncated and execution ledger unavailable. The expected result is `insufficient_evidence`, unknown execution coverage, and no improvement estimate. The earlier detection and sampled investigation remain available; they cannot fill the later pilot evidence gap. Partial counts may appear in underlying evidence, but must not be promoted into a supported outcome conclusion.

## Optional local model: separate unapproved candidate

Default mode makes no model calls. The `03-inquiry.json` request uses the existing trusted pharmacy system instructions and response schema, ready for host review. With separate permission to run an already-installed local model:

```sh
.venv/bin/python -m pip install '.[local-model]'
.venv/bin/ops-pharmacy-demo --local-model YOUR_INSTALLED_LOCAL_MODEL --output /tmp/pharmacy-quality-local
```

The existing Ollama adapter makes one fixed-loopback call with no tools, 60-second timeout, existing 16,384-token context / 3,000 predicted-token options, and no model download. Cloud-name guards and byte/provenance validation remain in place. Operators must disable server-side cloud/proxy features. Context/output limits do not bound model-weight or server peak RAM; non-streamed responses may allocate memory before post-validation. No limits were relaxed.

`03-local-candidate.json` is always `UNAPPROVED_CANDIDATE_ONLY`. It never replaces the scripted review, accountability plan or approval, even if its proposal is identical. The full illustrative pilot continues to use the fixed scripted branch, labeled in the summary. To use a model proposal for a future pilot, a human must review it, bind a new accountability record and construct/approve a new ControlPlan; this demo does not do that automatically. A failed local call fails the run rather than fabricating a response.

No model was run or downloaded during development. Mocks test provider arguments, response validation and separation from approvals; they do not demonstrate model accuracy, instruction resistance, latency, memory fit or privacy configuration.

## Reuse and fixture maintenance

`operational_quality.pharmacy_demo` composes existing functions. It adds no connector, clinical logic, metric engine, scheduler or external action path. Source fixture JSON is packaged under `operational_quality/demo_data`. The development-only command `.venv/bin/python scripts/build_pharmacy_demo.py` regenerates these **fictional** approval/criteria fixtures from repository examples. It must never be used as an approval issuer for real data. Re-run tests after any fixture changes; frozen review and criteria hashes deliberately fail on mismatches.

All source content, quotes and model outputs remain untrusted data. Human reviewers must not execute instructions found inside them. This demonstration cannot constrain tools of a separately privileged host. See [verification](pharmacy-demo-verification.md) for actual checks and limits.
