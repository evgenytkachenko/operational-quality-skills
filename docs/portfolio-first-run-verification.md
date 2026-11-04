# Portfolio first-run verification

Base: remote main and `docs/portfolio-evidence-walkthrough` verified at `6035c47b80913bd77afada52a4d597d894cfd4eb` after authorized push and fast-forward. Follow-on work is documentation-only on `docs/portfolio-first-run`, not pushed or deployed.

The README now leads with an evaluator overview, existing dashboard screenshot, minimum setup, concrete synthetic cases, a full-workflow command and an implementation/verification status table. The previous detailed commands remain in [the CLI reference](cli-reference.md), with links adjusted. No new skill, connector, metric or runtime component was added.

## Checks

- Full synthetic suite: 365 tests passed before the walkthrough merge; runtime code is unchanged in this follow-on.
- Fresh Python 3.12 virtual environment at `/tmp/ops-portfolio-first-run`: `pip install .` built a wheel and installed it non-editably with base dependencies only, without test, integration or model extras.
- Installed commands ran from `/tmp`, outside the checkout: the end-to-end demo generated START-HERE.md and REPORT.md; the offline verifier returned exit 0. Output was kept in a fresh temporary directory.
- Installed dashboard launched on an ephemeral loopback port. HTML, JS, CSS and JSON routes returned content; synthetic true positives equaled 4. The server was stopped after smoke testing.
- Relative documentation links were checked. Independent review checked overview claims, examples, setup and model/service boundaries; no significant issues were found. Its wording suggestion to call the existing source profiles “read-only integration profiles” was applied.

The installation used package-index access for dependencies. No live business service, real records, model download or model execution was used. This run tested Linux/Python 3.12; Windows path guidance was inspected but not executed. Existing browser/accessibility results are documented in [dashboard verification](pharmacy-dashboard-verification.md), not repeated or expanded by these documentation checks. No deployment, real-world performance, causal improvement or clinical safety is established.
