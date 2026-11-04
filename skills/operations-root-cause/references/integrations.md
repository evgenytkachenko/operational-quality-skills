# Predefined evidence profiles

## Datadog

Use the maintained official `datadog-api-client` Python SDK. The helper calls only
`LogsApi.list_logs_get`, `SpansApi.list_spans_get`, and `EventsApi.list_events` (v2).
All three are reads. It constructs a case-ID query and fixed time window, explicitly
pages, disables SDK retry, enforces row/page limits and per-request timeout, and records
remaining cursors as truncation. SDK responses are normalized through configured dotted
field paths; real tenant attribute layouts must be checked before live use. Span records
are trace evidence, not full traces. Event timestamp mappings may differ from logs.
The adapter expects timezone-bearing timestamps, not guessed units or local times.

Use `DD_API_KEY` and `DD_APP_KEY` in the existing runtime secret store, with only the
permissions needed for these reads. Select the approved Datadog site in config. Never
put credentials in config or evidence. This skill neither creates nor configures credentials.
The official MCP server is an alternative through the host agent: discover its current
schemas, allow only read searches for logs/spans/events, preserve IDs and pagination
metadata, and apply the same scope. CLI budgets do not mechanically constrain host tools.
Do not enable MCP workflow/write tools as part of investigation.

Sources: [official Python SDK](https://datadoghq.dev/datadog-api-client-python/),
[API method reference](https://datadoghq.dev/datadog-api-client-python/datadog_api_client.v2.api.html),
[official MCP server](https://docs.datadoghq.com/mcp_server/).

## Business workflow: PostgreSQL reporting view

Use the existing `psycopg` client against an approved reporting replica/view, such as
order fulfillment, invoice approvals, claims handling or service-request history.
This is an explicitly chosen generic profile, not a claim about a company's systems.
An operator selects schema, view, DSN environment-variable name and six column mappings:
`id`, `case_id`, `timestamp`, `activity`, `queue`, `message`. All are strings except
`timestamp`, which is a timezone-aware database datetime. IDs must be opaque and globally
unique within a source; case IDs must share the same namespace across selected sources.
Provide a pseudonymized, least-privilege view with an index on case ID and timestamp.

No SQL authoring is required for an investigation. The helper composes one fixed SELECT
using psycopg identifiers and bound parameters, with a read-only transaction, statement
timeout, row limit and stable timestamp/ID ordering. Operator-approved views must not
call side-effecting functions; read-only transactions are not a defense against arbitrary
unsafe database functions. Use a dedicated SELECT-only role and server-side resource limits.
Database administration/view creation is outside this skill. Missing view or access is
reported as unavailable; never create tables or relax permissions automatically.

Source: [psycopg transaction characteristics](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

## Host-agent business tools

If an approved workflow integration already exists, use its bounded read/search operations
and map returned fields to the same six-field contract plus source and retrieval limitations.
Preserve source record IDs rather than creating unsupported joins. Do not invent or build a
vendor connector mid-investigation. The CLI currently ships only the two profiles above;
other host-tool retrieval is supervised by the host and is not a built-in CLI adapter.

## Limits and sensitive content

Only mapped fields reach the packet; raw responses and exception text are not persisted.
Common emails, URLs and labeled secrets are removed and text is capped. This is not full
DLP: names, unlabeled secrets and sensitive IDs may remain. Use a sanitized source view,
review packets before model exposure, honor local retention policy and restrict output access.
SDKs materialize responses before local caps; transport byte limits are not enforced.
Rate limits/auth failures become gaps without retries. Server sampling and retention remain
unknown unless separately evidenced. Never infer complete historical coverage from success.
