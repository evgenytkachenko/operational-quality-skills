# End-to-end pharmacy demo verification

Base: verified main `40a0db80dca32f1fad607250217ab2da51f4742b`. Work is isolated on `feat/pharmacy-quality-demo`; no remote push or merge is authorized for this new work.

The `ops-pharmacy-demo` entrypoint composes existing Monitor, Pharmacy Handoff Auditor, Improvement Workbench/RCA, Control Validation and Control Execution Coverage functions. It introduces orchestration, explicit fixture links, a narrative summary and sixteen packaged synthetic JSON fixtures, not a new domain engine or connector. The existing optional Ollama adapter/provider schema is used unchanged. No source implementation outside the new demo was changed; pyproject adds the entrypoint and package data.

The scripted walkthrough represents one fictional administrative acknowledgment issue. Detection uses population aggregates; two explicit sample cases illustrate the issue without becoming a denominator. A checked fixture mapping binds handoff refs to investigation refs. The frozen scripted review is hash-bound to accountability and an illustrative approved ControlPlan. Daily execution scopes bind to that plan's criteria hash. The optional model response is a separate unapproved candidate, never substituted into frozen approval or outcome artifacts. The missing-evidence replay keeps missingness visible and prevents an improvement conclusion.

Verification in Python 3.12 virtual environment:

- Full suite: 326 passed, including nine end-to-end demo tests; tests block socket connections.
- All nine existing skills validate.
- Independent review found a timeline inconsistency (proposal preparation preceding detection-window closure). Fixture preparation was moved after detection and before registration, with review deadline after pilot close. Regression added; independent reviewer passed all nine demo tests and found no remaining significant issues.
- Tests verify exact illustrative counts, artifact/review/criteria links, selected-case mapping, default no-model behavior, missing-evidence suppression, candidate isolation, changed-control hash rejection, execution-scope mismatch, cloud-name rejection, private output and no-overwrite, plus coherent review/approval/implementation timing.
- Clean wheel build and non-editable installation passed. Nominal and missing-evidence commands ran from `/tmp`, using installed site-packages code and all sixteen packaged fixtures. All eleven installed CLI entrypoints passed `--help`.
- Nominal synthetic outcome: 84/700 versus 28/700 acknowledgment exceptions, an observed decrease of eight percentage points. Guardrail remains 21/700, pilot fidelity is 686/700 and seven daily run records are successful. Those distinct denominators are explicitly documented. The existing validator recommends keep for human review within the fictional pilot only, with causal attribution NOT_ESTABLISHED.
- Missing-evidence replay yields insufficient_evidence and seven unknown execution obligations; no supported improvement estimate.

Only fixture data and mocked model responses were used. No PHI, actual approvals/implementation, clinical/insurance decisions, live services, credentials, model execution/downloads, notifications or schedules. Optional model availability, accuracy, semantic support, prompt-injection resistance, memory fit and server privacy configuration remain unvalidated. Shared context/output budgets were not increased; server memory is not mechanically bounded by request limits. Hashes/quotes bind supplied artifacts, not authentic authority or causality. No effect on real operational errors has been established.

Reproduce using the commands in [the walkthrough](pharmacy-quality-demo.md). Default execution requires neither Ollama nor live connectors. The fixture generator is development-only and creates fictional records, never real approvals. Human interpretation and approval remain separate from scripted demonstrations and automated validation.
