# Quality desk: fictional pharmacy control portfolio

A desktop/mobile portfolio demonstration of one administrative control: **review a recorded completion when required document receipt metadata is unobserved**. This is a replay that illustrates a possible preventive checkpoint. It never blocks, reverses or completes a real handoff. All records, document fingerprints, answer-key labels and initial review decisions are authored synthetic fixtures.

## Launch locally

From a Python 3.11+ repository checkout:

```sh
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ops-pharmacy-dashboard
```

Open **http://127.0.0.1:8765** in a browser. Stop the server with Ctrl+C. If the port is occupied, use `--port 8766`; `--port 0` chooses an available port and prints its address. The server binds only to `127.0.0.1`. No credentials, Node build step, external fonts, model or service are required. The installed wheel includes the HTML, CSS and JavaScript, so launch works outside the checkout.

This is a local Python demonstration server, not a production deployment or authenticated application. Do not expose it through a public tunnel, bind a public listener, supply real data or use its decisions operationally. There are no write endpoints or uploaded-data inputs.

## Preview

![Desktop review workspace](images/dashboard-desktop.png)

[Mobile screenshot](images/dashboard-mobile.png)

## Five-minute walkthrough

1. **Orient.** The overview shows 13 screened records, six flags, one missed case and 80% recall. Read the synthetic-replay notice. These are classifier replay metrics, not production results or error reduction.
2. **Inspect an alert.** Select REF-DEMO-003. Follow the packet → receipts → recorded completion → review path. The routing-sheet receipt is unobserved. Inspect source record IDs, timestamps, coverage and audit hash. Absence from a feed is not proof of absent documentation.
3. **Simulate a decision.** Choose confirm, dismiss or request more evidence, then record the simulated review. The designated role is operations quality, not a real account or authorization. Choices change only memory in this tab. No POST/request, source write, approval or notification occurs. Refresh or reset restores the fictional initial decisions.
4. **Find the blind spot.** Filter “Missed · answer key” and select REF-DEMO-007. The source feed appears complete; the authored adjudication says a receipt belongs to the wrong packet. The detector does not read ground truth. Open the answer key to see why this case is a miss.
5. **Understand false alerts.** REF-DEMO-005 has an approved off-system record absent from the feed; REF-DEMO-006 has a delayed receipt feed. Both are false alerts relative to the fictional adjudication. Dismissing an alert does not change its fixed answer-key classification.
6. **Keep unknown separate.** REF-DEMO-013 lacks usable coverage and adjudication. It is not treated as a cleared case or included in accuracy denominators. Only “request more evidence” is enabled for simulated review.
7. **Evaluate the control.** Open Control evaluation. Inspect the confusion matrix, denominators and model limits. The existing Control Validation engine returns insufficient evidence because there is no approved/implemented pilot and confounders are unresolved. A future preventive deployment needs separate approval and outcome measurement.

## Fixed synthetic ground truth and calculations

| Count | Value | Meaning |
|---|---:|---|
| True positives | 4 | Flagged and documentation actually missing in the authored answer key |
| False positives | 2 | Flagged, but documentation present according to the answer key |
| False negatives | 1 | No flag despite missing documentation in the answer key |
| True negatives | 5 | No flag and documentation present in the answer key |
| Unknown | 1 | Unusable coverage/adjudication; excluded from all four rates |

Precision = 4/6 = **66.7%**. Recall = 4/5 = **80%**. False-positive rate = 2/7 actual negatives = **28.6%** (not 2/6 flags). Miss rate = 1/5 actual exceptions = **20%**. Counts are explicitly labeled synthetic and remain unchanged by simulated reviewer decisions. Zero denominators produce unavailable rates, not zero accuracy.

The 12-case evaluable cohort is hand-authored, not randomly sampled or representative. The truth labels are neither independent real adjudication nor clinical judgments. Unknown exclusion is displayed, not hidden. No statistical confidence, generalization, real-world performance or improvement claim is made.

## Architecture and reuse

`dashboard.py` builds bounded fictional metadata and calls the existing **Referral Packet Auditor** for administrative form/routing-sheet receipt checks. The candidate control gates review on those findings at an authored recorded-completion point. Original mock source IDs, receipt metadata, completion refs, manifest assertions and report digests remain inspectable. Source metadata and supplied fingerprints are not authenticated document contents. The answer key is added separately after detector evaluation, never supplied to the control.

The existing **Control Validation** contract evaluates an unapproved, unimplemented proposal and returns insufficient evidence without aggregate retrieval. That output is shown separately from classifier accuracy. This dashboard complements `ops-pharmacy-demo`; it does not reuse that acknowledgment pilot's favorable rates for this different documentation control. Existing demo/validation architecture supplies evidence, hashes and human-review boundaries; no new provider, connector or clinical logic is invented.

The UI uses local static assets, native controls, semantic headings/tables, explicit labels, visible focus, a skip link, announced review status and responsive layouts. Browser state is ephemeral; there is no localStorage, cookie, external resource or analytics. All data is inserted via textContent rather than HTML interpretation. The server exposes exact fixed GET routes, a restrictive content-security policy and no source-write API.

## Verification and limitations

See [verification details](pharmacy-dashboard-verification.md). Calculations and route security have automated tests. Desktop/mobile Chromium, keyboard flows and automated accessibility checks were exercised. Automated checks do not establish full WCAG conformance or replace assistive-technology/user testing.

No model was run or downloaded. There is no dashboard model invocation path, and detector rates are not LLM accuracy. No PHI, document contents, clinical appropriateness, dosing, dispensing, urgency, consent-validity or insurance decisions are supported. Source mapping/completeness and ground truth remain fictional assertions. No real control was implemented, no clinical safety was established, and no operational outcomes were measured.
