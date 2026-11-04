# Running and scheduling integration

Install the repository package in the host environment:

```sh
python -m pip install -e '.[integrations]'
```

Copy `skills/operational-quality-monitor` (with references and metadata) into the host's
skills directory. A wheel also carries it under the environment's
`share/operational-quality-skills/skills/operational-quality-monitor` directory.

## Offline examples

From the repository root:

```sh
ops-monitor --config examples/monitor/config.json --mock examples/monitor/deterioration.json --output output/monitor-demo
ops-monitor --config examples/monitor/config.json --mock examples/monitor/insufficient.json --output output/monitor-insufficient
ops-monitor --config examples/monitor/config.json --mock examples/monitor/unavailable.json --output output/monitor-unavailable
```

The fictional invoice example has two cohorts, one business-outcome rate (late completion)
and one guardrail rate (approval returns). The EU cohort deteriorates in both; the domestic
cohort is stable. It establishes signals to investigate, not a cause. Missing outcomes and
missing buckets in the second fixture withhold affected comparisons. The unavailable fixture
produces an insufficient-data report without printing exception payloads or credentials.
These are synthetic daily aggregates, not live vendor/service results or a model benchmark.

`monitor.json` contains deterministic results/evidence. `review.json` provides a host-agent
review prompt, exact report hash and a reference to `monitor.json` as untrusted data.
`run.json` records completion time and synthetic/live-read mode. The total serialized
size of all three files, including formatting, must fit max_output_bytes before any
output directory is created. The host agent performs the
qualitative review; the CLI never calls a model, scheduler, notification service or RCA.
Files are private (0600) in a new directory (0700); existing runs are never overwritten.
Exit 0 means a report was produced, including insufficient-data reports; exit 2 means a
configuration/execution error. A scheduler must inspect statuses, not treat exit 0 as health.

## Rolling windows and schedulers

The separate `rolling.json` example uses seven current days, seven baseline days and one day
of data-finalization lag. For a deterministic replay:

```sh
ops-monitor --config examples/monitor/rolling.json --mock examples/monitor/deterioration.json --as-of 2026-10-09T00:00:00Z --output output/monitor-replay
```

This resolves current `[2026-10-01, 2026-10-08)` and baseline `[2026-09-24, 2026-10-01)`.
Without `--as-of`, rolling configuration uses today's UTC midnight minus lag_days as current
window end. Each window is 1–90 days; the expected daily-cell count must fit the independent
aggregate budget. Windows cannot overlap or end in the future. Explicit configurations cannot use `--as-of`.

An existing operator-approved scheduler can invoke `ops-monitor` once per cadence with the
rolling configuration and a new private output path for each run. To use the configured
reporting view, replace `--mock ...` with `--live-read` only after source access is authorized.
The operator supplies runtime secrets through the existing secret store; never put them in
scheduler command text or configuration. Provide a unique run path, approved source config,
retention policy and human reviewer. Do not install a cron job or create an external task as
part of this skill's installation. Scheduling and sending notifications require separate
explicit authorization. No recurring tasks are created by this repository.

`--as-of` selects window boundaries; it does not reconstruct a database snapshot as it
existed on that date. Late corrections can change live rerun results. Preserve each saved
report and its run metadata. Repeated runs are independent snapshots. Persistent notification suppression, stateful alert
escalation and cross-run statistical trend detection are not implemented. Consecutive-day
logic works within the current window only. Do not describe repeated scheduled results as
independent corroborating evidence.

## Human-reviewed RCA handoff

Attention findings include a proposed RCA skill name, metric/cohort context and an empty case
list. Human review comes first. Resolve appropriate affected cases through the already approved
workflow source; retain cohort/window linkage and selection limitations. Then invoke the
existing RCA skill with explicit case IDs and an authorized window within its limits. Never
invent case IDs from aggregate record IDs or automatically run RCA merely because a threshold
was crossed. If the needed case source is unavailable, state that limitation.
