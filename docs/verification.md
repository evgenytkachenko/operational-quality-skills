# Verification record

Built in the cloud workspace using Python 3.12.14. Verified with Datadog API client
2.62.0, psycopg 3.3.8, Ollama client 0.6.3 and Pydantic 2.14.2.

- 36 pytest tests pass. Network connections are forbidden in the test process.
- Fictional CLI collection produces 11 normalized records across four sources and two
  invoice cases. Saved-packet review validates the hand-authored example assessment.
- Datadog contract tests execute the installed official SDK's generated parameter checks
  for logs, spans and events, replacing API dispatch before any HTTP request.
- PostgreSQL tests use psycopg's real SQL composition and a fake connection, verifying
  read-only mode, statement timeout, bound values and a fixed SELECT with LIMIT.
- Model tests use a fake client and validate output structure and every evidence quote;
  no inference model is downloaded or executed.
- Negative cases cover ambiguous/missing fields, duplicate/conflicting IDs, timezone and
  window boundaries, foreign cases, budget overflow, repeated pagination cursors, unsafe
  configuration, source failure privacy, malformed model results, invented citations,
  unsupported causal certainty, tampered packets and instruction-like evidence.
- The skill-creator quick validator passes; UI metadata was generated with its helper.
  The cloud bundle download returned HTTP 403, so the two helper scripts were read directly
  from the same cloud skill package. No personal-skill installation was attempted.
- Python wheel packaging includes the skill resources and both MIT license notices.

This is offline functional/contract verification, not a live integration certification or
a model-quality benchmark. SDK HTTP response parsing, tenant-specific Datadog field layouts,
actual database permissions, sampling/retention, model context handling and causal reasoning
need a separately authorized trial. Packet hashes detect accidental mismatch, not malicious
rewriting or source forgery. Best-effort redaction is not a data-loss prevention system.
