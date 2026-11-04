# Control execution coverage verification and branch assessment

Current verified main: `59aa7bd79478942358958020ac4f801439dcdb65` (workbench already merged). New development starts from that exact main on `feat/control-execution-coverage`. No remote branch or main updates were made for this task.

## Separate pharmacy handoff branch

Remote `feat/pharmacy-prescription-handoff` remains `c3b2d5ba1d249569bdf3e3ea1f7bd70b2aba5d0f`. Its merge base with current main is `49e9ba7dd874868a6f9fc07c54425b3b6121dbf0`; main has three unique commits and the pharmacy branch one. A non-worktree `git merge-tree --write-tree` preview found content conflicts in `README.md` and `pyproject.toml`. No merge was performed. No source-file conflicts were reported; pharmacy modules, fixtures, tests and skill are distinct from the newer store, referral and improvement files.

The pharmacy branch's standalone suite passed all 209 tests in an isolated detached checkout at `/tmp/pharmacy-readiness-c3b2d5b`, using the existing virtual environment with that checkout's source path. This establishes standalone readiness only. A future authorized integration must preserve all CLI entry points/skill package entries in pyproject and all README sections, resolve the two conflicts, run the combined suite, validate the additional skill and rebuild/install the combined wheel. Neither that integration nor combined-runtime verification was performed. Overlap is conceptual (administrative pharmacy evidence); the handoff auditor reconstructs individual cases, whereas the workbench investigates selected recorded exception categories and drafts accountable proposals. No replacement or automatic bridge is assumed.

## New capability

The gap addressed is finite expected-control execution coverage: reconcile a preapproved register with run and skip ledgers while retaining unknown obligations. The existing improvement workbench handles accountable proposals, and Control Validation evaluates approved pilot outcomes. This new skill does neither and never treats a run success as effectiveness or proof of error reduction. The workflow is company-agnostic, relevant to operational control oversight, and makes no claim about PHIL's systems, data or specific required processes.

Implemented `control_coverage.py`, `ops-control-coverage`, an installable skill, six fictional obligations, approval evidence and ledger fixtures, tests and first-run/contracts documentation. Reuses strict models, aware timestamps, canonical hashes, quote provenance, redaction, bounded input and private exclusive output. No new connector, model provider, query engine or third-party copied code. Host review instructions support interpretation; no new local adapter was needed, and no model is invoked.

Verification in Python 3.12 virtual environment:

- Full suite: 288 passed, including 29 coverage tests. Socket connections are blocked in tests.
- Eight skill packages validate. Clean wheel build/inspection includes eight skills and no unmerged pharmacy-auditor code. Non-editable install in a separate venv ran the fictional CLI from `/tmp` and imported site-packages code.
- Independent review reproduced two significant defects: rejected skip quotes were copied raw, and post-success retries could replace the earlier execution interpretation. Raw skip links are now omitted; only valid provenance is emitted. Post-success retries are unknown. Regression tests pass; reviewer independently ran all 29 tests and found no remaining significant defects.
- Tests cover on-time/late/failed/missing execution, explicit failed-to-success retries, overlapping/unlinked/cross-obligation attempts, post-success attempts, duplicate records, wrong scope/version, out-of-window/missing times, deadline uncertainty, malformed/injected fields, revoked/altered/duplicate skips, skip-plus-run conflicts, partial/stale/unavailable/count-mismatched ledgers, record budgets, private outputs, no overwrite and live-flag rejection.

Limits: entirely fictional metadata, no PHI, real services/credentials, model run/download, clinical/insurance decision, external action, notification or schedule. Approval, scope mapping, completeness and recorded outcomes are supplied assertions, not independently authenticated. Finite obligations must be explicitly supplied; no scheduler expansion, business calendar or population-wide assurance. A successful record does not validate control logic, implementation fidelity, effectiveness or safety. The CLI cannot constrain separate privileges of a host reviewing its output. New work remains locally committed and requires separate approval to push or merge.
