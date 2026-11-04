# Present the preventive-control portfolio

This four-minute demonstration asks: **Can an administrative documentation check find exceptions, and what evidence would justify a pilot?** It demonstrates evaluation discipline, not a deployed control or a particular company's workflow. Every case, label and review is fictional. No model, patient data or live service is used.

## Start and reset

Follow the [local installation and launch instructions](pharmacy-dashboard.md#launch-locally), then open http://127.0.0.1:8765. Use the dashboard reset button or refresh before each presentation to restore the authored initial review decisions. Keep this guide beside the browser. The review queue and Control evaluation are two views of the same fixed dataset.

## Four-minute narrative

| Time | Show | Say |
|---|---|---|
| 0:00–0:30 | Overview and synthetic notice | “This candidate control sends a recorded administrative completion for review when required receipt metadata is unobserved. We replay 13 fictional cases; we do not block a real handoff.” |
| 0:30–1:20 | Select REF-DEMO-003; inspect evidence and coverage | “The packet expects a routing sheet, but its receipt is unobserved in the available records. The completion is a separate event. Source references make the finding inspectable; feed assertions and hashes do not prove source completeness or authenticity.” |
| 1:20–1:50 | Record a simulated review for case 003 | “An operations-quality reviewer can confirm, dismiss or request evidence. This changes only this tab's review state. It is not a real approval, action or adjudication of ground truth.” |
| 1:50–2:40 | Under All, open the answer key for 005; switch to the missed-case filter and open 007 | “Case 005 is a false alert: the fictional answer key says an approved off-system record exists. Case 007 is a miss: a receipt appears to match, but the answer key says it belongs to another packet. The detector never reads these labels.” |
| 2:40–3:00 | Clear the missed-case filter by selecting All; select REF-DEMO-013 | “Coverage and adjudication are unavailable. Unknown is not cleared: only requesting more evidence is enabled. This case is excluded from accuracy denominators.” |
| 3:00–4:00 | Open Control evaluation | “Of 12 evaluable cases, four are true alerts, two false alerts, one missed exception and five true negatives. Review decisions do not change those counts. The validation engine returns insufficient evidence for effectiveness: there is no approved or implemented pilot.” |

Finish with the decision to **seek better evidence before considering a pilot**, not a rollout recommendation. A human would first assess receipt capture and packet matching, then approve a bounded pilot with outcome, reviewer-workload guardrail, implementation-fidelity measures and confounding review. No such approval or pilot occurs here.

## Evidence and answer-key ledger

“Missing” below means missing according to the **authored answer key**, not an inference from feed silence. These labels are separate from detector input but are not independently verified real adjudications.

| Case suffix (REF-DEMO-) | Detector | Answer key | Classification |
|---|---|---|---|
| 001, 002, 003, 004 | Flag | Missing | 4 true positives |
| 005 | Flag | Present: off-system record | 1 false positive |
| 006 | Flag | Present: delayed receipt feed | 1 false positive |
| 007 | No flag | Missing: receipt matched to wrong packet | 1 false negative |
| 008, 009, 010, 011, 012 | No flag | Present | 5 true negatives |
| 013 | Unknown | Unknown | Excluded; 1 of 13 records |

For case 003, inspect `sender:EV-030` (submission), `receiver:EV-031` (form receipt), `receiver:EV-033` (acknowledgment) and `workflow:COMP-DEMO-003` (recorded completion). The absent routing receipt has no source record to cite. `adjudication:DEMO-003` supplies the fictional missing label. For the miss, compare `receiver:EV-072` with `adjudication:DEMO-007`: apparently matching metadata is not authenticated document identity. The following command prints every case's original event references, completion reference and label reference directly from the existing dashboard dataset.

From the repository checkout after installation:

```sh
.venv/bin/python - <<'PY'
from operational_quality.dashboard import dataset, score

d = dataset()
for c in d['cases']:
    f, t = c['flag'], c['ground_truth_missing']
    kind = 'unknown' if f is None or t is None else (
        'tp' if f and t else 'fp' if f else 'fn' if t else 'tn')
    refs = ', '.join(e['source'] + ':' + e['id'] for e in c['evidence'])
    print(c['id'], kind, c['ground_truth']['label'],
          c['ground_truth']['ref'], c['completion']['ref'], refs)
m = score(d['cases'])
print({k: m[k] for k in ('tp', 'fp', 'fn', 'tn', 'unknown', 'evaluable', 'total')})
for name in ('precision', 'recall', 'false_positive_rate', 'miss_rate'):
    r = m[name]
    print(name, f"{r['numerator']}/{r['denominator']}", r['rate'])
print('Effectiveness:', d['effectiveness'])
PY
```

Expected counts: `tp=4, fp=2, fn=1, tn=5, unknown=1, evaluable=12, total=13`. Precision is **4/6 flags (66.7%)**; recall is **4/5 actual exceptions (80%)**; false-positive rate is **2/7 actual negatives (28.6%)**; miss rate is **1/5 actual exceptions (20%)**. Two of six alerts are false alerts; that fraction is not the false-positive rate. Zero denominators would be unavailable, not perfect performance.

## What this supports

The replay demonstrates traceable detection, explicit blind spots and reversible human review. Its tiny, deliberately constructed cohort supports no production performance, causal improvement, clinical safety or model-accuracy claim. Nothing here establishes documentation validity, dispensing readiness or an insurance determination. No model was run; this dashboard has no model invocation path.

For a broader scripted investigation and pilot illustration, use the separate [end-to-end quality demo](pharmacy-quality-demo.md). Its acknowledgment-control outcomes do not validate this documentation control. See [dashboard verification](pharmacy-dashboard-verification.md) for test coverage and accessibility limits.
