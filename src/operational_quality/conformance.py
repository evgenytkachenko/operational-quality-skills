"""Evidence-bounded comparison with an approved workflow policy; no compliance verdicts."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Literal
import json
import re
from pydantic import Field, StrictBool, StrictInt, model_validator
from .core import Strict, Config, instant, analyze, redact
from .control_validation import Evidence, Link, digest
from .provenance import EvidenceLink, bind_claims, required_link_failures

TOKEN_PATTERN = r'^[A-Za-z0-9_-]{1,80}$'
REF_PATTERN = r'^[A-Za-z0-9_.:/+=-]{1,512}$'
MANIFEST_FIELDS = ('id', 'case_id', 'policy_id', 'policy_version', 'first_event_at', 'last_event_at',
                   'event_count', 'complete', 'closed', 'clock_uncertainty_seconds')


class Handoff(Strict):
    from_queue: str = Field(pattern=TOKEN_PATTERN)
    to_queue: str = Field(pattern=TOKEN_PATTERN)


class Edge(Strict):
    from_step: str = Field(pattern=TOKEN_PATTERN)
    to_step: str = Field(pattern=TOKEN_PATTERN)
    handoffs: list[Handoff] = Field(min_length=1, max_length=30)
    max_elapsed_seconds: int | None = Field(default=None, ge=1, le=604800)


class ExceptionRule(Edge):
    code: str = Field(pattern=TOKEN_PATTERN)
    waived_required_steps: list[str] = Field(default_factory=list, max_length=50)


class PolicyApproval(Strict):
    decision: Literal['approved', 'revoked']
    approved_at: datetime
    policy_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    links: list[Link] = Field(min_length=1, max_length=5)


class WorkflowPolicy(Strict):
    id: str = Field(pattern=TOKEN_PATTERN)
    version: str = Field(pattern=TOKEN_PATTERN)
    effective_from: datetime
    effective_to: datetime
    steps: list[str] = Field(min_length=1, max_length=50)
    initial_steps: list[str] = Field(min_length=1, max_length=10)
    terminal_steps: list[str] = Field(min_length=1, max_length=10)
    required_steps: list[str] = Field(max_length=50)
    edges: list[Edge] = Field(max_length=200)
    exceptions: list[ExceptionRule] = Field(default_factory=list, max_length=50)
    approval: PolicyApproval | None = None

    @model_validator(mode='after')
    def check(self):
        self.effective_from, self.effective_to = instant(self.effective_from), instant(self.effective_to)
        if self.effective_from >= self.effective_to:
            raise ValueError('invalid policy validity interval')
        if len(set(self.steps)) != len(self.steps) or any(not re.fullmatch(TOKEN_PATTERN, s) for s in self.steps):
            raise ValueError('steps must be unique safe identifiers')
        for group in [self.initial_steps, self.terminal_steps, self.required_steps]:
            if len(group) != len(set(group)) or not set(group) <= set(self.steps):
                raise ValueError('invalid or repeated step declaration')
        if len({(e.from_step, e.to_step) for e in self.edges}) != len(self.edges):
            raise ValueError('ambiguous policy edges')
        if len({e.code for e in self.exceptions}) != len(self.exceptions):
            raise ValueError('duplicate exception codes')
        for edge in [*self.edges, *self.exceptions]:
            if edge.from_step not in self.steps or edge.to_step not in self.steps:
                raise ValueError('edge refers to unknown step')
        for exception in self.exceptions:
            if not set(exception.waived_required_steps) <= set(self.required_steps):
                raise ValueError('exception can waive only declared required steps')
        if self.approval:
            self.approval.approved_at = instant(self.approval.approved_at)
        return self

    def content(self):
        return self.model_dump(mode='json', exclude={'approval'})


class Permit(Strict):
    id: str = Field(pattern=TOKEN_PATTERN)
    case_id: str = Field(pattern=TOKEN_PATTERN)
    policy_id: str = Field(pattern=TOKEN_PATTERN)
    policy_version: str = Field(pattern=TOKEN_PATTERN)
    code: str = Field(pattern=TOKEN_PATTERN)
    from_ref: str = Field(pattern=REF_PATTERN)
    to_ref: str = Field(pattern=REF_PATTERN)
    valid_from: datetime
    valid_to: datetime
    approved_at: datetime
    decision: Literal['approved', 'revoked']
    links: list[Link] = Field(min_length=1, max_length=5)

    @model_validator(mode='after')
    def check(self):
        self.valid_from, self.valid_to, self.approved_at = (instant(v) for v in (self.valid_from, self.valid_to, self.approved_at))
        if self.valid_from >= self.valid_to:
            raise ValueError('invalid permit interval')
        return self

    def content(self):
        return self.model_dump(mode='json', exclude={'links'})


class PermitInventory(Strict):
    permits: list[Permit] = Field(default_factory=list, max_length=100)
    complete_for_cases: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def check(self):
        if len({p.id for p in self.permits}) != len(self.permits):
            raise ValueError('duplicate permit IDs')
        if len(set(self.complete_for_cases)) != len(self.complete_for_cases) or any(not re.fullmatch(TOKEN_PATTERN, c) for c in self.complete_for_cases):
            raise ValueError('invalid exception inventory coverage')
        return self


class ManifestSource(Strict):
    schema_name: str = 'reporting'
    view: str = 'workflow_trace_manifest'
    fields: dict[str, str] = Field(default_factory=lambda: {k: k for k in MANIFEST_FIELDS})

    @model_validator(mode='after')
    def check(self):
        if set(self.fields) != set(MANIFEST_FIELDS) or len(set(self.fields.values())) != len(MANIFEST_FIELDS):
            raise ValueError('manifest mappings must be complete and distinct')
        if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for v in [self.schema_name, self.view, *self.fields.values()]):
            raise ValueError('invalid manifest identifier')
        return self


class ConformanceConfig(Strict):
    collection: Config
    workflow_source: str
    manifest_source: ManifestSource = Field(default_factory=ManifestSource)
    max_output_bytes: int = Field(default=1000000, ge=2000, le=5000000)

    @model_validator(mode='after')
    def check(self):
        matches = [s for s in self.collection.sources if s.name == self.workflow_source and s.kind == 'postgres']
        if len(matches) != 1:
            raise ValueError('choose one configured PostgreSQL workflow source as authoritative')
        return self


class TraceManifest(Strict):
    id: str = Field(pattern=REF_PATTERN)
    case_id: str = Field(pattern=TOKEN_PATTERN)
    policy_id: str = Field(pattern=TOKEN_PATTERN)
    policy_version: str = Field(pattern=TOKEN_PATTERN)
    first_event_at: datetime
    last_event_at: datetime
    event_count: StrictInt = Field(ge=1, le=10000)
    complete: StrictBool
    closed: StrictBool
    clock_uncertainty_seconds: StrictInt = Field(ge=0, le=86400)

    @model_validator(mode='after')
    def check(self):
        self.first_event_at, self.last_event_at = instant(self.first_event_at), instant(self.last_event_at)
        if self.first_event_at > self.last_event_at:
            raise ValueError('invalid trace boundaries')
        return self


def verify_quote_record(name, checksum, links, sources, kinds):
    ledger = bind_claims({name: f'{name} {checksum}'}, {name: [EvidenceLink(**link.model_dump()) for link in links]}, sources)
    valid = (not required_link_failures(ledger, (name,)) and all(kinds.get(l.source_id) == 'approval' for l in links)
             and any(name in l.quote and checksum in l.quote for l in links))
    return valid, ledger[name].model_dump() if valid else None


def evaluate_conformance(config, policy, inventory, evidence, fetch_events, fetch_manifest):
    collection = config.collection
    if collection.end > datetime.now(collection.end.tzinfo):
        raise ValueError('conformance window must not end in the future')
    referenced = {link.source_id for link in (policy.approval.links if policy.approval else [])}
    referenced.update(link.source_id for permit in inventory.permits
        if permit.case_id in collection.case_ids and permit.policy_id == policy.id and permit.policy_version == policy.version
        for link in permit.links)
    sources = {a.ref: {'text': redact(a.text)} for a in evidence.artifacts if a.ref in referenced}
    kinds = {a.ref: a.kind for a in evidence.artifacts if a.ref in referenced}
    checksum = digest(policy.content())
    approval = policy.approval
    valid_policy, policy_ledger = verify_quote_record(policy.id, checksum, approval.links, sources, kinds) if approval else (False, None)
    valid_policy = bool(valid_policy and approval.decision == 'approved' and approval.policy_sha256 == checksum and approval.approved_at <= policy.effective_from)
    result = {'schema_version': 1, 'policy_id': policy.id, 'policy_version': policy.version, 'policy_sha256': checksum,
        'review_status': 'HUMAN_REVIEW_REQUIRED', 'compliance_certified': False, 'root_cause_established': False,
        'population_scope': 'Only the explicitly selected case IDs; no population noncompliance rate is inferred.',
        'cases': [], 'limitations': [], 'actions_executed': False, 'notifications_sent': False, 'schedules_created': False}
    packet = None
    if not valid_policy:
        result['limitations'].append('Policy approval, version hash, timing or exact evidence linkage is missing/invalid; no retrieval performed.')
        result['cases'] = [{'case_id': c, 'status': 'unknown', 'findings': [], 'reasons': ['unverified_policy'], 'rca_handoff': None} for c in collection.case_ids]
    else:
        result['policy'] = policy.content()
        result['policy_approval_provenance'] = policy_ledger
        result['supporting_evidence'] = sources
        packet = analyze(collection, fetch_events)
        result['evidence_sha256'] = packet['sha256']
        result['limitations'] += packet['limitations']
        primary = [e for e in packet['events'] if e['source'] == config.workflow_source]
        coverage = next(c for c in packet['coverage'] if c['source'] == config.workflow_source)
        primary_ok = coverage['status'] == 'bounded' and coverage.get('accepted') == len(primary)
        manifests, metadata_ok = {}, True
        try:
            rows, truncated = fetch_manifest(config)
            if not isinstance(rows, list) or not isinstance(truncated, bool):
                raise ValueError('invalid manifest response')
            if truncated or len(rows) > len(collection.case_ids):
                metadata_ok = False
                result['limitations'].append('Manifest retrieval truncated or exceeded requested cases.')
            for raw in rows[:len(collection.case_ids)]:
                values = {k: raw[v] for k, v in config.manifest_source.fields.items()}
                if isinstance(values['id'], int) and not isinstance(values['id'], bool):
                    values['id'] = str(values['id'])
                manifest = TraceManifest.model_validate(values)
                if manifest.case_id not in collection.case_ids or manifest.case_id in manifests or any(m.id == manifest.id for m in manifests.values()):
                    raise ValueError('unexpected or duplicated manifest')
                manifests[manifest.case_id] = manifest
        except Exception as exc:
            metadata_ok = False
            result['limitations'].append(f'Manifest evidence unavailable/invalid ({type(exc).__name__}); payload omitted.')
        result['trace_manifests'] = [manifests[k].model_dump(mode='json') for k in sorted(manifests)]
        permit_records = {}
        for permit in inventory.permits:
            valid, ledger = verify_quote_record(permit.id, digest(permit.content()), permit.links, sources, kinds)
            if valid:
                permit_records[permit.id] = ledger
        base_edges = {(e.from_step, e.to_step): e for e in policy.edges}
        exception_rules = {r.code: r for r in policy.exceptions}
        for case_id in collection.case_ids:
            events = sorted([e for e in primary if e['case_id'] == case_id], key=lambda e: (e['timestamp'], e['ref']))
            manifest = manifests.get(case_id)
            case = {'case_id': case_id, 'status': 'unknown', 'reasons': [], 'findings': [], 'rca_handoff': None}
            if not primary_ok: case['reasons'].append('workflow_retrieval_partial_invalid_or_duplicated')
            if not metadata_ok or manifest is None: case['reasons'].append('manifest_unavailable_or_invalid')
            if manifest:
                case['manifest_ref'] = 'manifest:' + manifest.id
                if not manifest.complete or not manifest.closed: case['reasons'].append('trace_incomplete_or_open')
                if manifest.policy_id != policy.id or manifest.policy_version != policy.version: case['reasons'].append('policy_version_mismatch')
                clock_range = timedelta(seconds=manifest.clock_uncertainty_seconds)
                if not (collection.start <= manifest.first_event_at-clock_range and manifest.last_event_at+clock_range < collection.end): case['reasons'].append('trace_crosses_or_overlaps_collection_boundary')
                if not (policy.effective_from <= manifest.first_event_at-clock_range and manifest.last_event_at+clock_range < policy.effective_to): case['reasons'].append('trace_crosses_or_overlaps_policy_validity')
                if len(events) != manifest.event_count or not events: case['reasons'].append('event_count_mismatch')
                elif instant(events[0]['timestamp']) != manifest.first_event_at or instant(events[-1]['timestamp']) != manifest.last_event_at: case['reasons'].append('trace_boundary_mismatch')
                if any(e['activity'] not in policy.steps for e in events): case['reasons'].append('unmapped_workflow_step')
                if any((instant(b['timestamp'])-instant(a['timestamp'])).total_seconds() <= 2*manifest.clock_uncertainty_seconds for a,b in zip(events,events[1:])):
                    case['reasons'].append('ordering_ambiguous_within_clock_uncertainty')
            if not case['reasons']:
                waived, uncertain_waivers = set(), set()
                observed = {e['activity'] for e in events}
                missing_steps = set(policy.required_steps)-observed
                def finding(kind, status, refs, **details):
                    case['findings'].append({'kind': kind, 'status': status, 'evidence_refs': refs, 'policy_ref': f'{policy.id}:{policy.version}', **details})
                if events[0]['activity'] not in policy.initial_steps:
                    finding('unexpected_initial_step', 'potential_deviation', [events[0]['ref']])
                if events[-1]['activity'] not in policy.terminal_steps:
                    finding('unexpected_terminal_step', 'potential_deviation', [events[-1]['ref']])
                for a,b in zip(events,events[1:]):
                    edge = base_edges.get((a['activity'],b['activity']))
                    elapsed = (instant(b['timestamp'])-instant(a['timestamp'])).total_seconds()
                    uncertainty = 2*manifest.clock_uncertainty_seconds
                    def handoff_matches(rule):
                        return any(h.from_queue==a['queue'] and h.to_queue==b['queue'] for h in rule.handoffs)
                    def within_limit(rule):
                        return rule.max_elapsed_seconds is None or elapsed + uncertainty <= rule.max_elapsed_seconds
                    base_satisfied = edge is not None and handoff_matches(edge) and within_limit(edge)
                    possible_rules = [r for r in policy.exceptions if (r.from_step,r.to_step)==(a['activity'],b['activity'])
                                      and (not base_satisfied or missing_steps.intersection(r.waived_required_steps))]
                    applicable, uncertain_exception = [], False
                    for permit in inventory.permits:
                        rule = exception_rules.get(permit.code)
                        if not (permit.case_id==case_id and permit.policy_id==policy.id and permit.policy_version==policy.version
                                and permit.from_ref==a['ref'] and permit.to_ref==b['ref'] and rule in possible_rules and permit.decision=='approved'):
                            continue
                        if permit.id not in permit_records:
                            uncertain_exception = True
                            uncertain_waivers.update(rule.waived_required_steps)
                            continue
                        clock_range = timedelta(seconds=manifest.clock_uncertainty_seconds)
                        earliest_a, latest_a = instant(a['timestamp'])-clock_range, instant(a['timestamp'])+clock_range
                        earliest_b, latest_b = instant(b['timestamp'])-clock_range, instant(b['timestamp'])+clock_range
                        temporal_certain = permit.approved_at <= earliest_a and permit.valid_from <= earliest_a and latest_b < permit.valid_to
                        temporal_possible = permit.approved_at <= latest_a and permit.valid_from <= latest_a and earliest_b < permit.valid_to
                        timing_possible = rule.max_elapsed_seconds is None or elapsed-uncertainty <= rule.max_elapsed_seconds
                        if temporal_certain and handoff_matches(rule) and within_limit(rule):
                            applicable.append((permit,rule))
                        elif temporal_possible and handoff_matches(rule) and timing_possible:
                            uncertain_exception = True
                            uncertain_waivers.update(rule.waived_required_steps)
                    if len(applicable)>1:
                        finding('ambiguous_exception_approvals','unknown',[a['ref'],b['ref']])
                        for _,rule in applicable:
                            uncertain_waivers.update(rule.waived_required_steps)
                        continue
                    if applicable:
                        permit,edge = applicable[0]
                        waived.update(edge.waived_required_steps)
                        finding('permitted_exception','permitted_exception',[a['ref'],b['ref']],permit_id=permit.id,
                                permit_sha256=digest(permit.content()),permit_scope=permit.content(),approval_provenance=permit_records[permit.id],exception_code=edge.code)
                    unknown_exception = bool(possible_rules) and (case_id not in inventory.complete_for_cases or uncertain_exception) and not applicable
                    if edge is None:
                        finding('invalid_transition', 'unknown' if unknown_exception else 'potential_deviation', [a['ref'],b['ref']], from_step=a['activity'],to_step=b['activity'])
                        continue
                    if not any(h.from_queue==a['queue'] and h.to_queue==b['queue'] for h in edge.handoffs):
                        finding('unpermitted_handoff','unknown' if unknown_exception else 'potential_deviation',[a['ref'],b['ref']],from_queue=a['queue'],to_queue=b['queue'])
                    if edge.max_elapsed_seconds is not None:
                        elapsed = (instant(b['timestamp'])-instant(a['timestamp'])).total_seconds()
                        uncertainty = 2*manifest.clock_uncertainty_seconds
                        if elapsed - uncertainty > edge.max_elapsed_seconds:
                            finding('elapsed_interval_exceeds_policy','unknown' if unknown_exception else 'potential_deviation',[a['ref'],b['ref']],observed_seconds=elapsed,limit_seconds=edge.max_elapsed_seconds,uncertainty_seconds=uncertainty)
                        elif elapsed + uncertainty > edge.max_elapsed_seconds:
                            finding('elapsed_interval_near_policy_limit','unknown',[a['ref'],b['ref']],observed_seconds=elapsed,limit_seconds=edge.max_elapsed_seconds,uncertainty_seconds=uncertainty)
                observed = {e['activity'] for e in events}
                for step in sorted(set(policy.required_steps)-observed-waived):
                    unresolved = step in uncertain_waivers or (case_id not in inventory.complete_for_cases and any(step in r.waived_required_steps for r in policy.exceptions))
                    finding('required_step_not_observed','unknown' if unresolved else 'potential_deviation',[e['ref'] for e in events],step=step,trace_completeness='source_asserted')
                statuses = {f['status'] for f in case['findings']}
                case['status'] = ('unknown' if 'unknown' in statuses else 'potential_deviation' if 'potential_deviation' in statuses else 'permitted_exception' if 'permitted_exception' in statuses else 'no_observed_deviation')
                if 'potential_deviation' in statuses:
                    case['rca_handoff'] = {'skill':'operations-root-cause','case_ids':[case_id], 'start':collection.start.isoformat(), 'end':collection.end.isoformat(),
                        'instruction':'Human review policy applicability, source completeness and exceptions first; then consider RCA. Do not infer a cause or invoke it automatically.', 'automatic_invocation':False}
            result['cases'].append(case)
    result['limitations'] += ['Workflow/manifest completeness, policy approval and permit inventory are source assertions, not authenticated compliance evidence.',
        'Supporting Datadog records are context only and cannot fill authoritative workflow gaps or prove absent business steps.',
        'Timestamps may have residual skew/late arrival; equal or overlapping uncertainty intervals do not establish event order.',
        'Elapsed intervals are wall-clock policy checks, not working time or business-calendar calculations. No root cause is inferred.']
    result['sha256'] = digest(result)
    return result, packet
