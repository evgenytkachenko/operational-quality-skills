"""Synthetic-only administrative prescription handoff audit; no clinical decisions."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from pydantic import Field, StrictBool, StrictInt, model_validator
from .core import Strict, instant, redact
from .control_validation import Evidence, digest
from .conformance import PolicyApproval, verify_quote_record

Queue = Literal['intake', 'clarification', 'prior_auth', 'pharmacy']
Source = Literal['intake_feed', 'pa_feed', 'pharmacy_feed']
Role = Literal['intake_team', 'clarification_team', 'pa_team', 'pharmacy_team']
KINDS = Literal['intake_received', 'handoff_sent', 'handoff_acknowledged', 'owner_assigned',
    'clarification_requested', 'clarification_response_recorded', 'pa_status_recorded',
    'pharmacy_received', 'next_step_recorded', 'partial_fill_recorded', 'fill_completed_recorded',
    'fill_cancelled_recorded', 'case_cancelled', 'case_closed_recorded', 'case_reopened',
    'off_system_resolution_recorded']
TERMINAL = {'case_cancelled', 'case_closed_recorded'}
NEXT = {'pharmacy_received', 'next_step_recorded', 'partial_fill_recorded', 'fill_completed_recorded'}


class HandoffPolicy(Strict):
    id: Literal['PHARMACY-DEMO-HANDOFF'] = 'PHARMACY-DEMO-HANDOFF'
    version: str = Field(pattern=r'^v[0-9]+$')
    effective_from: datetime
    effective_to: datetime
    acknowledgment_seconds: StrictInt = Field(ge=1, le=604800)
    owner_seconds: StrictInt = Field(ge=1, le=604800)
    clarification_seconds: StrictInt = Field(ge=1, le=604800)
    approval_next_step_seconds: StrictInt = Field(ge=1, le=604800)
    max_feed_lag_seconds: StrictInt = Field(ge=0, le=86400)
    repeated_handoff_count: StrictInt = Field(ge=2, le=20)
    approval: PolicyApproval | None = None

    @model_validator(mode='after')
    def check(self):
        self.effective_from,self.effective_to=instant(self.effective_from),instant(self.effective_to)
        if self.effective_from>=self.effective_to:raise ValueError('invalid policy interval')
        if self.approval:self.approval.approved_at=instant(self.approval.approved_at)
        return self

    def content(self):return self.model_dump(mode='json',exclude={'approval'})


class AuditScope(Strict):
    synthetic: Literal[True]
    case_ids: list[str] = Field(min_length=1,max_length=20)
    start: datetime
    as_of: datetime
    max_events: StrictInt = Field(default=500,ge=1,le=1000)
    max_output_bytes: StrictInt = Field(default=1000000,ge=2000,le=5000000)

    @model_validator(mode='after')
    def check(self):
        import re
        self.start,self.as_of=instant(self.start),instant(self.as_of)
        if not 0<(self.as_of-self.start).total_seconds()<=7*86400:raise ValueError('scope must be within seven days')
        if self.as_of>datetime.now(timezone.utc):raise ValueError('future snapshots are unsupported')
        if len(set(self.case_ids))!=len(self.case_ids) or any(not re.fullmatch(r'RX-DEMO-[0-9]{3}',c) for c in self.case_ids):
            raise ValueError('only distinct synthetic prescription IDs are accepted')
        return self


class Feed(Strict):
    source: Source
    scope_case_ids: list[str]
    complete_through: datetime
    available: StrictBool
    truncated: StrictBool
    event_count: StrictInt = Field(ge=0,le=1000)
    clock_uncertainty_seconds: StrictInt = Field(ge=0,le=3600)


class AdminEvent(Strict):
    id: str = Field(pattern=r'^EV-[0-9]{3,6}$')
    source: Source
    case_id: str = Field(pattern=r'^RX-DEMO-[0-9]{3}$')
    episode_id: str = Field(pattern=r'^EP-[0-9]{2}$')
    fill_id: str | None = Field(default=None,pattern=r'^FILL-[0-9]{2}$')
    occurred_at: datetime
    received_at: datetime
    kind: KINDS
    queue: Queue
    to_queue: Queue | None = None
    owner_role: Role | None = None
    related_ref: str | None = Field(default=None,pattern=r'^(intake_feed|pa_feed|pharmacy_feed):EV-[0-9]{3,6}$')
    pa_request_id: str | None = Field(default=None,pattern=r'^PA-DEMO-[0-9]{3}$')
    pa_status: Literal['pending','approved','denied','cancelled','unknown'] | None = None
    supersedes_ref: str | None = Field(default=None,pattern=r'^(intake_feed|pa_feed|pharmacy_feed):EV-[0-9]{3,6}$')
    existing_urgency: Literal['source_marked_routine','source_marked_urgent','not_recorded'] = 'not_recorded'

    @model_validator(mode='after')
    def check(self):
        self.occurred_at,self.received_at=instant(self.occurred_at),instant(self.received_at)
        if self.kind=='handoff_sent' and self.to_queue is None:raise ValueError('handoff destination required')
        if self.kind in {'handoff_acknowledged','owner_assigned','clarification_response_recorded','case_reopened','off_system_resolution_recorded'}|NEXT and self.related_ref is None:
            # Fill records may be standalone state observations, never implicit resolutions.
            if self.kind not in {'partial_fill_recorded','fill_completed_recorded'}:raise ValueError('explicit relation required')
        if self.kind in {'partial_fill_recorded','fill_completed_recorded','fill_cancelled_recorded'} and self.fill_id is None:raise ValueError('fill ID required')
        if self.kind in TERMINAL|{'intake_received','case_reopened'} and self.fill_id is not None:raise ValueError('episode lifecycle is not a fill lifecycle')
        if self.kind=='pa_status_recorded':
            if self.pa_request_id is None or self.pa_status is None:raise ValueError('PA reference and recorded status required')
        elif self.pa_status is not None or self.pa_request_id is not None or self.supersedes_ref is not None:
            raise ValueError('PA fields only belong to PA status records')
        if self.kind=='owner_assigned' and self.owner_role is None:raise ValueError('recorded owner role required')
        return self

    @property
    def ref(self):return f'{self.source}:{self.id}'


def audit_handoffs(scope,policy,evidence,snapshot):
    sources={a.ref:{'text':redact(a.text)} for a in evidence.artifacts if policy.approval and a.ref in {l.source_id for l in policy.approval.links}}
    kinds={a.ref:a.kind for a in evidence.artifacts}
    checksum=digest(policy.content())
    approval=policy.approval
    verified,ledger=verify_quote_record(policy.id,checksum,approval.links,sources,kinds) if approval else (False,None)
    verified=bool(verified and approval.decision=='approved' and approval.policy_sha256==checksum and approval.approved_at<=policy.effective_from
        and policy.effective_from<=scope.start<scope.as_of<policy.effective_to)
    report={'schema_version':1,'synthetic_only':True,'review_status':'HUMAN_REVIEW_REQUIRED','clinical_decisions_made':False,
        'urgency_assigned':False,'external_actions_executed':False,'policy_sha256':checksum,'scope':scope.model_dump(mode='json'),
        'cases':[],'quarantined_rows':[],'limitations':[]}
    blocked={c:[] for c in scope.case_ids}
    global_issues=[]
    rows=[];feeds={};events=[]
    if not verified:global_issues.append('threshold_policy_approval_or_scope_unverified')
    elif not isinstance(snapshot,dict) or set(snapshot)!={'synthetic','feeds','events'} or snapshot['synthetic'] is not True or not isinstance(snapshot['events'],list):
        global_issues.append('invalid_synthetic_snapshot_contract')
    else:
        report['policy']=policy.content();report['approval_provenance']=ledger;report['supporting_evidence']=sources
        rows=snapshot['events']
        if len(rows)>scope.max_events:global_issues.append('event_budget_exceeded')
        try:
            if not isinstance(snapshot['feeds'],list) or len(snapshot['feeds'])!=3:raise ValueError('three source manifests required')
            for raw in snapshot['feeds']:
                feed=Feed.model_validate(raw);feed.complete_through=instant(feed.complete_through)
                if feed.source in feeds or set(feed.scope_case_ids)!=set(scope.case_ids) or len(feed.scope_case_ids)!=len(scope.case_ids):raise ValueError('ambiguous feed scope')
                feeds[feed.source]=feed
                if not feed.available or feed.truncated:global_issues.append('feed_unavailable_or_truncated')
                if not scope.start<=feed.complete_through<=scope.as_of or (scope.as_of-feed.complete_through).total_seconds()>policy.max_feed_lag_seconds:
                    global_issues.append('feed_watermark_missing_or_stale')
                if feed.event_count!=sum(isinstance(r,dict) and r.get('source')==feed.source for r in rows):global_issues.append('feed_count_mismatch')
        except (ValueError,TypeError):global_issues.append('invalid_feed_manifest')
        for index,raw in enumerate(rows[:scope.max_events]):
            try:
                event=AdminEvent.model_validate(raw)
                if event.case_id not in blocked or event.source not in feeds:raise ValueError('ambiguous event scope')
                u=timedelta(seconds=feeds[event.source].clock_uncertainty_seconds)
                if not scope.start<=event.occurred_at-u or not event.occurred_at+u<=scope.as_of or event.received_at>scope.as_of or event.received_at<event.occurred_at-u:
                    raise ValueError('timestamp missing/outside snapshot or delivery incoherent')
                events.append(event)
            except (ValueError,TypeError):
                report['quarantined_rows'].append({'row_index':index,'reason':'invalid_or_ambiguous_administrative_record; raw payload omitted'})
                case_id=raw.get('case_id') if isinstance(raw,dict) else None
                if isinstance(case_id,str) and case_id in blocked:blocked[case_id].append('quarantined_event')
                else:global_issues.append('ambiguous_case_identifier_quarantined')
    by_ref={}
    for event in events:
        if event.ref in by_ref:
            blocked[event.case_id].append('duplicate_source_record_id')
            blocked[by_ref[event.ref].case_id].append('duplicate_source_record_id')
        by_ref[event.ref]=event
    uncertainty=max((f.clock_uncertainty_seconds for f in feeds.values()),default=0)
    cutoff=min([scope.as_of,*[f.complete_through for f in feeds.values()]])
    def later(a,b):return (a.occurred_at-b.occurred_at).total_seconds()>2*uncertainty
    for e in events:
        if e.related_ref:
            target=by_ref.get(e.related_ref)
            if target is None or target.case_id!=e.case_id or not later(e,target):
                blocked[e.case_id].append('unresolved_or_ambiguous_record_link')
                if target is not None and target.case_id!=e.case_id:blocked[target.case_id].append('cross_case_identifier_conflict')
                continue
            if e.kind=='case_reopened':
                if target.kind not in TERMINAL or target.episode_id==e.episode_id:blocked[e.case_id].append('invalid_reopen_link')
            elif target.episode_id!=e.episode_id:blocked[e.case_id].append('cross_episode_link_quarantined')
            elif (e.kind in {'handoff_acknowledged','owner_assigned','clarification_response_recorded','off_system_resolution_recorded'} or e.kind in NEXT and target.fill_id is not None) and e.fill_id!=target.fill_id:
                blocked[e.case_id].append('cross_fill_resolution_quarantined')
            if e.kind=='handoff_acknowledged' and (target.kind!='handoff_sent' or e.queue!=target.to_queue):blocked[e.case_id].append('acknowledgment_target_mismatch')
            if e.kind=='owner_assigned' and (target.kind!='handoff_sent' or e.queue!=target.to_queue):blocked[e.case_id].append('owner_assignment_target_mismatch')
            if e.kind=='clarification_response_recorded' and target.kind!='clarification_requested':blocked[e.case_id].append('clarification_target_mismatch')
            if e.kind in NEXT and not (target.kind=='pa_status_recorded' and target.pa_status=='approved'):blocked[e.case_id].append('next_step_link_not_to_recorded_approval')
        if e.supersedes_ref:
            old=by_ref.get(e.supersedes_ref)
            if old is None or old.kind!='pa_status_recorded' or (old.case_id,old.episode_id,old.pa_request_id,old.fill_id)!=(e.case_id,e.episode_id,e.pa_request_id,e.fill_id) or not later(e,old):
                blocked[e.case_id].append('invalid_status_supersession')
                if old is not None and old.case_id!=e.case_id:blocked[old.case_id].append('cross_case_identifier_conflict')
    report['feed_coverage']=[f.model_dump(mode='json') for f in feeds.values()]
    for case_id in scope.case_ids:
        selected=sorted([e for e in events if e.case_id==case_id],key=lambda e:(e.occurred_at,e.ref))
        issues=list(global_issues)+blocked[case_id]
        if not selected:issues.append('no_usable_case_records')
        if any(not later(b,a) for a,b in zip(selected,selected[1:])):issues.append('ambiguous_event_order')
        episodes={}
        for e in selected:episodes.setdefault(e.episode_id,[]).append(e)
        active_pa={}
        superseded_refs={e.supersedes_ref for e in selected if e.supersedes_ref}
        for e in selected:
            if e.kind=='pa_status_recorded' and e.ref not in superseded_refs:
                active_pa.setdefault((e.episode_id,e.pa_request_id),[]).append(e)
        for records in active_pa.values():
            if len({e.fill_id for e in records})>1:issues.append('ambiguous_pa_fill_scope')
            if sum(e.pa_status=='approved' for e in records)>1:issues.append('ambiguous_repeated_active_approval')
        previous_terminal=None
        for number,(episode_id,trace) in enumerate(episodes.items()):
            first=trace[0]
            if sum(e.kind in {'intake_received','case_reopened'} for e in trace)!=1:issues.append('ambiguous_repeated_episode_start')
            if number==0 and first.kind!='intake_received':issues.append('episode_start_unobserved')
            if number>0 and (first.kind!='case_reopened' or first.related_ref!=previous_terminal):issues.append('ambiguous_episode_identity_or_reopen')
            terminals=[e for e in trace if e.kind in TERMINAL]
            if len(terminals)>1:issues.append('conflicting_episode_closures')
            previous_terminal=terminals[-1].ref if terminals else None
            if terminals and any(e.occurred_at>terminals[0].occurred_at and e.kind!='off_system_resolution_recorded' for e in trace):issues.append('post_closure_activity_without_new_episode')
        case={'case_id':case_id,'status':'unknown' if issues else 'no_observed_signal','reasons':sorted(set(issues)),
              'existing_urgency_labels':[{'source_ref':e.ref,'label':e.existing_urgency,'episode_id':e.episode_id} for e in selected if e.existing_urgency!='not_recorded'],
              'findings':[],'episodes':[],'timeline':[{'ref':e.ref,**e.model_dump(mode='json')} for e in selected],
              'evidence_through':cutoff.isoformat()}
        for episode_id,trace in episodes.items():
            terminated=any(e.kind in TERMINAL for e in trace)
            case['episodes'].append({'episode_id':episode_id,'state':'terminal_recorded' if terminated else 'open_in_available_records',
                'fill_states':[{'ref':e.ref,'fill_id':e.fill_id,'recorded_state':e.kind} for e in trace if e.kind in {'partial_fill_recorded','fill_completed_recorded','fill_cancelled_recorded'}]})
            if issues:continue
            def finding(kind,refs,**details):case['findings'].append({'kind':kind,'episode_id':episode_id,'evidence_refs':refs,'interpretation':'Administrative observation for human review; not a clinical or insurance decision.',**details})
            superseded={e.supersedes_ref for e in trace if e.supersedes_ref}
            statuses={}
            for e in trace:
                if e.kind=='pa_status_recorded' and e.ref not in superseded:statuses.setdefault(e.pa_request_id,[]).append(e)
            conflicts=set()
            for request,records in statuses.items():
                if len({e.pa_status for e in records})>1:
                    conflicts.add(request)
                    finding('conflicting_recorded_pa_status',[e.ref for e in records],pa_request_id=request,
                        recorded_statuses=sorted({e.pa_status for e in records}),note='May reflect updates or feed disagreement; reconcile source records rather than determine coverage.')
            if terminated:continue
            for e in trace:
                def resolved(kinds):
                    return any(x.kind in kinds|{'off_system_resolution_recorded'} and x.related_ref==e.ref for x in trace)
                cancelled_fill=e.fill_id is not None and any(x.kind=='fill_cancelled_recorded' and x.fill_id==e.fill_id and later(x,e) for x in trace)
                if cancelled_fill:continue
                age=(cutoff-e.occurred_at).total_seconds()-2*uncertainty
                if e.kind=='handoff_sent':
                    if age>policy.acknowledgment_seconds and not resolved({'handoff_acknowledged'}):finding('acknowledgment_not_observed',[e.ref],threshold_seconds=policy.acknowledgment_seconds)
                    if age>policy.owner_seconds and e.owner_role is None and not resolved({'owner_assigned'}) and not any(x.kind=='handoff_acknowledged' and x.related_ref==e.ref and x.owner_role is not None for x in trace):finding('owner_not_observed',[e.ref],threshold_seconds=policy.owner_seconds)
                if e.kind=='clarification_requested' and age>policy.clarification_seconds and not resolved({'clarification_response_recorded'}):
                    finding('clarification_response_not_observed',[e.ref],threshold_seconds=policy.clarification_seconds)
                if e.kind=='pa_status_recorded' and e.pa_status=='approved' and e.ref not in superseded and e.pa_request_id not in conflicts and age>policy.approval_next_step_seconds and not resolved(NEXT):
                    finding('approval_next_step_not_observed',[e.ref],threshold_seconds=policy.approval_next_step_seconds,note='Recorded approval is not independently verified; no dispensing or insurance conclusion.')
            for fill in sorted({e.fill_id for e in trace},key=lambda value:value or ''):
                handoffs=[e for e in trace if e.kind=='handoff_sent' and e.fill_id==fill]
                if len(handoffs)>=policy.repeated_handoff_count:finding('repeated_handoffs_observed',[e.ref for e in handoffs],fill_id=fill,count=len(handoffs),note='May be legitimate routing; no cause or noncompliance inferred.')
        if not issues and case['findings']:case['status']='administrative_review_suggested'
        report['cases'].append(case)
    report['limitations']=['Synthetic-only profile; no live connector, real prescription data or standards-conformance claim.',
        'Unobserved means absent from the available, source-asserted coverage through evidence_through, not that an action did not happen.',
        'Off-system resolutions require explicit linked documentation; partial/completed fills do not imply prescription completion.',
        'Urgency labels are copied from existing source records without priority calculation, triage or clinical interpretation.',
        'Approval authenticity, source completeness, policy suitability and timestamp guarantees require human verification.']
    report['sha256']=digest(report)
    return report
