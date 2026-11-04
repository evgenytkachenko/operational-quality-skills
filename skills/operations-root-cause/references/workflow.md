# Execution and review

Install the repository package once with `python -m pip install -e '.[integrations]'`.
Use the repository's `examples/config.json` as the operator configuration template; replace
fictional IDs, time range and field mappings for the approved sources. Investigations do not
require raw-file uploads. Synthetic fixture files exist only for offline demonstration/testing.

Offline example from the repository root:

```sh
ops-rca --config examples/config.json --mock examples/fictional.json --output output/demo
```

The command creates private `evidence.json` and `inquiry.json`. Read the latter with your
host agent, follow its system instruction/schema, and draft a structured assessment.
Validate a host draft against the saved immutable evidence packet:

```sh
ops-rca-review --packet output/demo/evidence.json --assessment examples/assessment.json --output output/review
```

For live reads, explicitly replace `--mock ...` with `--live-read` only when authorized.
Re-fetching live data can change the packet; use `ops-rca-review` to validate against
the saved packet without further retrieval. Never relabel a new
packet as the original. Each accepted report records the packet's SHA-256 and quote ledger.
The SHA records integrity linkage, not source authenticity or a cryptographic signature.

Optional: install `.[local-model]`, then add `--local-model INSTALLED_MODEL`. This calls an
already running Ollama at `127.0.0.1:11434`; it never pulls or starts a model.
Recognizable `:cloud` and `-cloud` selectors are rejected. A loopback destination does
not guarantee offline inference: the operator must verify a local model and disable
server-side cloud/proxy features; aliases and custom servers cannot be certified by this CLI. It performs one
60-second request with 3,000 output tokens and a 24,000-character evidence input cap.
Tokenization varies by model; this conservative cap does not guarantee context fit. No tools or autonomous model retrieval are
available. Model semantics and instruction adherence are not mechanically guaranteed.
The host agent supports iterative inquiry within the same total retrieval budget; the
local path is a single-pass draft and returns proposed discriminating checks for review.

Validate every observation's source/part/quote; reject any invalid companion citation.
The reused provenance checker deliberately does not certify semantic support. A faithful
quote can contradict the proposed claim. Final review must assess mechanism, alternative
explanations, knowledge at decision time, control feasibility and measurable outcomes.
No automated validator can establish causation from these records alone.

When no usable evidence exists, the schema permits empty observations and controls,
with unknown hypotheses and explicit gaps. Never fabricate a fact to satisfy a schema.
Evidence links can cite exact normalized message, case_id, timestamp, activity or queue
fields; part names and quotes must match the saved packet.
