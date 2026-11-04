# Run the bounded workflow

From a Python 3.11+ repository checkout, install `python -m pip install .` in a virtual environment. The wheel contains CLI and skill instructions; examples remain in the checkout. Default preparation performs no model or service calls:

```sh
ops-improvement --settings examples/pharmacy-improvement/settings.json --mock examples/pharmacy-improvement/fictional.json --output /tmp/improvement-prepared
```

The demo includes two fictional handoff cases with recorded acknowledgment exceptions followed by resolution labels. Deterministic grouping reports two distinct selected cases, not three occurrences in one case or a population rate. It does not establish whether acknowledgments actually failed or whether resolutions were effective. This profile complements the separate prescription handoff auditor; it does not depend on or merge that branch.

Review `inquiry.json` using the host agent, then validate its JSON assessment. The included assessment is human-authored synthetic test material, not an actual LLM output:

```sh
ops-improvement --settings examples/pharmacy-improvement/settings.json --mock examples/pharmacy-improvement/fictional.json --assessment examples/pharmacy-improvement/assessment.json --accountability examples/pharmacy-improvement/accountability.json --output /tmp/improvement-dossier
```

Outputs: deterministic `evidence.json`, host `inquiry.json`, validated `review.json`, and a draft `proposal.json` when accountability is supplied. All are private local artifacts in a new directory. Reusing a directory is rejected. Unknown evidence permits only unknown hypotheses and gaps, with empty observations and controls.

An accountability plan binds the canonical digest of the complete validated review (`operational_quality.control_validation.digest(review)`), one action per control index, hypothesis indices, matching role, preparation time, later review deadline and closure evidence required. Changing a review invalidates its plan. A new model result will generally need a new human-authored plan; do not reuse the fixture hash. First run without `--accountability`, review the result, author the bound plan, then validate the same assessment with that plan. No approval, task assignment, notification, implementation or closure is performed.

Optional local mode, only after explicit operator authorization to execute an already-installed model:

```sh
python -m pip install '.[local-model]'
ops-improvement --settings examples/pharmacy-improvement/settings.json --mock examples/pharmacy-improvement/fictional.json --local-model YOUR_INSTALLED_LOCAL_MODEL --output /tmp/improvement-local-review
```

This uses the existing official Ollama Python client and shared adapter. It fixes the endpoint to loopback, disables environment proxies, makes one chat call with a 60-second timeout, no tools, no streaming, 16,384-token context and at most 3,000 predicted tokens. It never pulls models. Cloud model suffixes are rejected; operators must also disable server-side cloud/proxy features. Client injection exists only for tests. No local model was run or downloaded during development.

After human review, use Operations Control Validation to construct its existing `ControlPlan` with review hash, selected proposal, registered criteria, outcome and guardrail/fidelity metrics, baseline and pilot scope, approval/implementation evidence and confounders. The dossier lists these requirements; it is deliberately not an approved executable pilot plan. Measure error reduction there, not from this selected-case sample.
