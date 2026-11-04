# Reuse and architecture boundary

Inspected the existing cloud Hyper Agile engine at commit
`bbccd49cad3b796b5eb5b515140c4cf6388a26f9`: evidence.py, guards.py,
providers/base.py, providers/ollama.py and methodology/SKILL.md. The checkout has no root
license, so no engine implementation or private case content was copied.

Inspected public `evgenytkachenko/hyper-agile-quality-skill` at
`9140a0bba0fc2db29d8ff8d4706176c7faaf0955`, including its MIT license,
claim_evidence.py and causal-model reference. Reused the standalone claim-evidence module
verbatim as `src/operational_quality/provenance.py`; license retained under `third_party/`.
It has no vendor, software-release or private-data dependencies (only Pydantic).

Reused the architectural ideas of stable evidence references, explicit uncertainty,
quote-presence versus semantic-support separation and human review. Did not import
release escape categories, QE lifecycle scoring, private prompts, cases or configuration.
Model providers remain outside deterministic analysis; Ollama uses its maintained SDK.

Evaluated SQL needs: bounded case timelines require sorting/grouping only. Python's
standard library is adequate; DuckDB/pandas would add dependencies without a current
query requirement. The optional PostgreSQL profile uses psycopg composition, not a SQL
engine or LLM-generated SQL. SQL is not mandatory for host-agent or synthetic operation.

The repository is the requested deliverable, not an installation into personal remote-skills.
No personal skill service, publishing workflow or remote write is part of this build.
