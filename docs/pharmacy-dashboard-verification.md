# Portfolio dashboard verification

Base: verified remote main `1e250df9807c3e00913ee5a9c98099fb5bbb0491`. New work is isolated on `feat/pharmacy-control-dashboard`; no push, merge or deployment was performed.

Implemented a loopback-only Python launch command, packaged local HTML/CSS/JS, a responsive review/evaluation interface, 13 fictional cases and a strict confusion-matrix calculation. Existing Referral Packet Auditor performs document metadata checks; existing Control Validation blocks an effectiveness verdict because no approved or implemented pilot is supplied. No new model adapter or vendor connector. Simulated human reviews are browser-memory changes only; ground truth and detector metrics are immutable fixtures.

Verification in the virtual environment:

- Full suite: 365 tests passed, including five dashboard calculation/provenance/route tests. All nine skill packages validate.
- Independent review verified counts, denominators, unknown exclusion, hashes, ground-truth separation, browser-only decisions and fixed read-only routes. It found an inconsistent sidebar control label, now sourced from dataset.control_id. Reviewer independently passed all five unit tests and mobile Chromium checks; no remaining significant issues.
- Browser automation ran in local system Chromium on desktop 1440×1100, mobile 390×844 and narrow 320×740. Both review and evaluation views had zero axe-core violations for tested WCAG 2 A/AA and 2.1 AA tags, no horizontal overflow and no page errors.
- Tested keyboard skip link and focus on case selection, radio/submit interactions, review announcement, answer-key filter, unknown-case decision restrictions, reset/reload behavior and unchanged metrics after review. Browser requests remained loopback GET only. Screenshots were visually inspected for desktop and mobile.
- Clean wheel build and non-editable installation passed. The installed server launched from `/tmp` on an ephemeral loopback port, served packaged assets/data with CSP/no-store headers, rejected POST with 501, and passed the same responsive/accessibility browser script. The smoke server was stopped after testing.

Development browser setup initially attempted a Playwright browser download, which was blocked by the download host (403). Testing instead used the already installed `/usr/bin/chromium`. axe-core was installed as a temporary test dependency, not added to runtime assets. No model was downloaded or run, and no live business service or production data was accessed.

Reproduce unit checks with `.venv/bin/python -m pytest -q`. For optional browser checks, launch the dashboard locally, use an environment with Playwright and Chromium, install axe-core locally (for example `npm install --prefix /tmp/dashboard-checks --cache /tmp/dashboard-cache axe-core`), then run:

```sh
python scripts/check_dashboard_browser.py --url http://127.0.0.1:8765 --chromium /usr/bin/chromium --axe /tmp/dashboard-checks/node_modules/axe-core/axe.min.js
```

The browser script rejects non-loopback target URLs. Automated checks are not a WCAG certification or assistive-technology/user study; Safari/Firefox, other OSes, high-contrast modes and production deployment are unvalidated. Local Python HTTP serving is for a trusted single-user demo, not public hosting or an authenticated system. Fixed synthetic truth does not establish real-world detector performance. Recorded completion is replayed, never operationally blocked/reversed. Accuracy is not operational effectiveness, clinical safety or model accuracy; no such result is claimed. Human oversight and all prior read-only/clinical/privacy limits remain intact.
