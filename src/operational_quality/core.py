"""Bounded normalization and correlation; correlation never establishes causation."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

TOKEN = r"[A-Za-z0-9_-]{1,80}"
FIELDS = {"id", "case_id", "timestamp", "activity", "queue", "message"}


def instant(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Strict):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    kind: Literal["datadog_logs", "datadog_spans", "datadog_events", "postgres"]
    fields: dict[str, str]
    case_field: str = "@case_id"
    timestamp_format: Literal["iso8601", "epoch_s", "epoch_ms", "epoch_ns"] = "iso8601"
    site: Literal["datadoghq.com", "datadoghq.eu", "us3.datadoghq.com", "us5.datadoghq.com", "ap1.datadoghq.com", "ap2.datadoghq.com", "ddog-gov.com"] = "datadoghq.com"
    schema_name: str = "reporting"
    view: str = "operation_events"
    dsn_env: str = "OPS_DATABASE_DSN"

    @model_validator(mode="after")
    def check(self):
        if set(self.fields) != FIELDS:
            raise ValueError("fields must map id, case_id, timestamp, activity, queue, message")
        if not re.fullmatch(r"@?[A-Za-z_][A-Za-z0-9_.]*", self.case_field):
            raise ValueError("invalid Datadog case field")
        for value in [self.schema_name, self.view, self.dsn_env]:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
                raise ValueError("invalid identifier")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", v) for v in self.fields.values()):
            raise ValueError("invalid field mapping")
        if self.kind == "postgres" and self.timestamp_format != "iso8601":
            raise ValueError("PostgreSQL profile requires a timezone-aware timestamp column")
        if self.kind == "postgres" and any('.' in v for v in self.fields.values()):
            raise ValueError("Postgres fields must be column names")
        return self


class Config(Strict):
    case_ids: list[str] = Field(min_length=1, max_length=20)
    start: datetime
    end: datetime
    sources: list[Source] = Field(min_length=1, max_length=6)
    max_rows: int = Field(default=200, ge=1, le=1000)
    page_size: int = Field(default=100, ge=1, le=1000)
    max_pages: int = Field(default=3, ge=1, le=10)
    timeout_seconds: int = Field(default=15, ge=1, le=60)
    max_text: int = Field(default=500, ge=40, le=2000)
    max_packet_bytes: int = Field(default=200000, ge=1000, le=1000000)

    @model_validator(mode="after")
    def check(self):
        self.start, self.end = instant(self.start), instant(self.end)
        if not 0 < (self.end - self.start).total_seconds() <= 7 * 86400:
            raise ValueError("window must be positive and at most seven days")
        if any(not re.fullmatch(TOKEN, c) for c in self.case_ids):
            raise ValueError("case IDs must be opaque alphanumeric identifiers")
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("duplicate case IDs")
        if len({s.name for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate source names")
        return self


def redact(value):
    text = str(value)
    # Consume the whole credential including the authentication scheme.
    text = re.sub(r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", "[CREDENTIAL_REMOVED]", text)
    key = r"(?:token|password|secret|api[_-]?key|authorization)"
    # Common JSON log values, including escaped quotes inside the secret.
    text = re.sub(r'(?i)("' + key + r'"\s*:\s*)"(?:\\.|[^"\\])*"', r'\1"[REDACTED]"', text)
    text = re.sub(r"(?i)\b(" + key + r")\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", text)
    text = re.sub(r"https?://\S+", "[URL REMOVED]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL REMOVED]", text)
    return ''.join(c for c in text if c >= ' ' or c == '\n')


def source_instant(value, encoding):
    if encoding == 'iso8601':
        return instant(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError('explicit epoch encoding requires an integer')
    scale = {'epoch_s': 1, 'epoch_ms': 1000, 'epoch_ns': 1000000000}[encoding]
    seconds, remainder = divmod(value, scale)
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds, microseconds=remainder * 1000000 // scale)


def get_path(row, path):
    for part in path.split('.'):
        row = row[part]
    return row


def normalize(config, source, rows):
    events, notes = [], []
    for index, row in enumerate(rows):
        try:
            item = {key: get_path(row, path) for key, path in source.fields.items()}
            if isinstance(item['id'], int) and not isinstance(item['id'], bool):
                item['id'] = str(item['id'])
            if not all(isinstance(item[k], str) and item[k].strip() for k in FIELDS - {"timestamp"}):
                raise ValueError("non-string or empty field")
            if not re.fullmatch(r'[A-Za-z0-9_.:/+=-]{1,512}', item['id']) or not re.fullmatch(TOKEN, item['case_id']):
                raise ValueError("invalid identifier")
            when = source_instant(item['timestamp'], source.timestamp_format)
            if item['case_id'] not in config.case_ids or not config.start <= when < config.end:
                notes.append(f"{source.name}: row {index} outside requested scope")
                continue
            item['timestamp'] = when.isoformat()
            for key in ('message', 'queue', 'activity'):
                clean = redact(item[key])
                if clean != item[key]:
                    notes.append(f"{source.name}: row {index} {key} redacted")
                if len(clean) > config.max_text:
                    notes.append(f"{source.name}: row {index} {key} truncated")
                item[key] = clean[:config.max_text]
            item['source'] = source.name
            item['ref'] = f"{source.name}:{item.pop('id')}"
            events.append(item)
        except (KeyError, TypeError, ValueError, OverflowError):
            notes.append(f"{source.name}: row {index} missing, ambiguous or invalid fields; excluded")
    return events, notes


def analyze(config, fetch):
    events, limitations, coverage = [], [], []
    for source in config.sources:
        try:
            rows, notes = fetch(source, config)
            if not isinstance(rows, list):
                raise ValueError("invalid response")
            if len(rows) >= config.max_rows:
                notes = [*notes, "row cap reached; coverage may be incomplete"]
            normalized, issues = normalize(config, source, rows[:config.max_rows])
            events.extend(normalized)
            limitations.extend(f"{source.name}: {n}" for n in notes)
            limitations.extend(issues)
            coverage.append({'source': source.name, 'kind': source.kind, 'retrieved': len(rows[:config.max_rows]), 'accepted': len(normalized), 'status': 'partial' if notes or issues else 'bounded'})
            if not normalized:
                limitations.append(f"{source.name}: no usable evidence; absence is not proof of no activity")
        except Exception as exc:
            # Never persist vendor exception text: it can contain credentials and raw payloads.
            limitations.append(f"{source.name}: retrieval failed ({type(exc).__name__}); evidence unavailable")
            coverage.append({'source': source.name, 'status': 'unavailable'})
    unique, conflicts = {}, set()
    for event in events:
        ref = event['ref']
        if ref in unique and unique[ref] != event:
            conflicts.add(ref)
        unique[ref] = event
    for ref in sorted(conflicts):
        unique.pop(ref)
        limitations.append(f"{ref}: conflicting duplicate ID excluded")
    events = sorted(unique.values(), key=lambda e: (e['timestamp'], e['ref']))
    cases = []
    for case_id in config.case_ids:
        selected = [e for e in events if e['case_id'] == case_id]
        gaps = [{'from': a['ref'], 'to': b['ref'], 'seconds': (instant(b['timestamp']) - instant(a['timestamp'])).total_seconds()} for a, b in zip(selected, selected[1:])]
        workflow = [e for e in selected if next(s.kind for s in config.sources if s.name == e['source']) == 'postgres']
        repeats = sorted({e['activity'] for e in workflow if sum(x['activity'] == e['activity'] for x in workflow) > 1})
        cases.append({'case_id': case_id, 'refs': [e['ref'] for e in selected], 'observed_gaps': gaps, 'repeated_workflow_activities': repeats})
        if not selected:
            limitations.append(f"{case_id}: no evidence")
    packet = {'schema_version': 1, 'scope': {'case_ids': config.case_ids, 'start': config.start.isoformat(), 'end': config.end.isoformat()}, 'coverage': coverage, 'events': events, 'cases': cases, 'limitations': limitations, 'interpretation': 'Exact case-ID joins only. Gaps are observed event intervals, not proven waiting times. Repeated activities are not proven rework. No causal verdict.'}
    if len(json.dumps(packet).encode()) > config.max_packet_bytes:
        raise ValueError("packet budget exceeded; narrow scope or reduce row/text limits")
    packet['sha256'] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
    return packet
