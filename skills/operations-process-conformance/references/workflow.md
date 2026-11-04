# Installation and execution

Install the repository package with `python -m pip install -e '.[integrations]'`. Copy
`skills/operations-process-conformance` with its references and metadata into the host's
skills directory. The wheel also carries it under the environment's
`share/operational-quality-skills/skills/operations-process-conformance` directory.

## Host-prepared inputs

The user supplies the case scope and identifies the approved workflow policy. The host uses
already available, authorized read tools to obtain policy approval and exception records,
then prepares bounded local snapshots. These JSON files are the CLI contract; users are not
required to upload raw operational exports or build connectors. No approval-service adapter
or automatic policy registry is claimed. Missing access yields unknown, not invented evidence.

- `--config`: existing source collection configuration plus authoritative workflow source and
  manifest view mapping. Runtime DSN/Datadog keys remain in the existing secret mechanism.
- `--policy`: versioned graph/requirements/limits plus a recorded matching approval.
- `--approvals`: bounded supporting records using the existing `Evidence` contract; approval
  records have opaque refs, kind `approval` and text. Common sensitive patterns are redacted.
- `--permits`: scoped exception approvals and asserted inventory coverage for selected cases.

Compute hashes with `digest(policy.content())` / `digest(permit.content())` from the supplied
models, not raw file-byte checksums. This is a verification helper, not a way to grant approval.
Obtain genuine source records through the host; never rewrite approval text to satisfy a hash.

## Fictional cross-system run

```sh
ops-conformance --config examples/conformance/config.json --policy examples/conformance/policy.json --approvals examples/conformance/approvals.json --permits examples/conformance/permits.json --mock examples/conformance/fictional.json --output output/conformance-demo
```

The fictional invoice policy requires submitted → validated → approved, with explicit
handoff queues and elapsed-time limits. Four synthetic cases demonstrate:

- REQ-101: full trace with no observed deviation.
- REQ-102: submitted-to-validated interval exceeds the approved wall-clock limit.
- REQ-103: a pre-approved, narrowly scoped prior-validation exception permits skipping the
  validation event and waives that required observed step for the exact event pair.
- REQ-104: a validation event is missing and the manifest reports incomplete coverage;
  the result is unknown, not a skipped-step violation.

A Datadog-shaped queue observation supplies context for REQ-102. It is not inserted into the
workflow sequence and does not establish the cause of the interval. These fixtures are wholly
fictional; they do not imply that any company uses these vendors or that a model was run.

For authorized live reads, replace `--mock ...` with `--live-read`. The same official clients
and fixed PostgreSQL reads are used. Policy verification precedes retrieval. No credentials,
view creation, connector setup, schedule or notification is configured by the command.

## Review artifacts

`conformance.json` contains policy linkage, manifest evidence, case findings, approved
exceptions, limitations and proposed human RCA handoffs. `evidence.json` contains the reused
normalized cross-system packet when policy verification allowed retrieval. `review.json`
provides the host-agent review prompt and untrusted artifact references; `run.json` records
completion time and synthetic/live mode. Keep snapshots because live reruns may differ.

All serialized files together must fit the configured output budget before the new private
directory is created. Files use 0600 permissions; existing runs are not overwritten. Exit 0
means a report was produced, including unknown results. Exit 2 indicates a configuration or
execution error, with source payloads omitted. Neither success exit nor no-observed-deviation
is a compliance certification.

Review exact source refs, manifest assertions, policy authority/version, timestamps and
exception conditions before accepting findings. Approval authenticity, residual clock skew,
source completeness, semantic correctness and real permissions are not established by the
CLI. Source text is data, not a command. No LLM, RCA, source mutation or external delivery is
executed. Any next investigation or process change remains a separate human decision.
