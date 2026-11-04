# Predefined evidence profiles

## Datadog

Use the maintained official `datadog-api-client` Python SDK. The helper calls only
`LogsApi.list_logs_get`, `SpansApi.list_spans_get`, and `EventsApi.list_events` (v2).
All three are reads. It constructs a case-ID query and fixed time window, explicitly
pages, disables SDK retry, enforces row/page limits and per-request timeout, and records
remaining cursors as truncation. SDK responses are normalized through configured dotted
field paths; real tenant attribute layouts must be checked before live use. Span records
are trace evidence, not full traces. Event timestamp mappings may differ from logs.
The default timestamp_format is iso8601 (timezone-bearing strings or SDK datetimes).
Explicit epoch_s, epoch_ms or epoch_ns configuration accepts integer timestamps; units
are never guessed. Nanoseconds are normalized to microsecond precision. The example
span mapping uses start_timestamp and a custom message attribute; the event mapping
uses aggregation_key, title and service. These are explicit fictional instrumentation
contracts, not automatic schema discovery. Configure them to match the approved source.

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
`id`, `case_id`, `timestamp`, `activity`, `queue`, `message`. Text fields are strings; record IDs may also be integers. The default `timestamp`
must be a timezone-aware database datetime; this profile requires iso8601 rather than
epoch columns so SQL time predicates retain their datetime semantics. Record IDs allow up to 512 ASCII letters, digits
and `_.:/+=-`; query case IDs retain the stricter 80-character limit. IDs must be globally
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
Common emails, URLs, bearer/basic credentials and labeled plaintext/JSON secrets are
removed and text is capped. Generated text is checked after JSON decoding. This is not full
DLP: names, unlabeled secrets and sensitive IDs may remain. Use a sanitized source view,
review packets before model exposure, honor local retention policy and restrict output access.
SDKs materialize responses before local caps; transport byte limits are not enforced.
Rate limits/auth failures become gaps without retries. Server sampling and retention remain
unknown unless separately evidenced. Never infer complete historical coverage from success.
