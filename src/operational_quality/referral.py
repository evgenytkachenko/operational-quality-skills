"""Synthetic referral packet metadata reconciliation, never clinical document assessment."""
from datetime import datetime,timezone
from typing import Literal
from pydantic import Field,StrictBool,StrictInt,model_validator
from .core import Strict,instant,redact
from .conformance import PolicyApproval,verify_quote_record
from .control_validation import digest
DOCS=Literal['administrative_form','consent_record','routing_sheet']

class ReferralPolicy(Strict):
    id: Literal['REFERRAL-DEMO-POLICY']='REFERRAL-DEMO-POLICY'
    version: str = Field(pattern=r'^v[0-9]+$')
    required_types: list[DOCS] = Field(min_length=1,max_length=3)
    acknowledgment_seconds: StrictInt = Field(ge=1,le=604800)
    delivery_seconds: StrictInt = Field(ge=1,le=604800)
    max_feed_lag_seconds: StrictInt = Field(ge=0,le=86400)
    approval: PolicyApproval | None = None
    def content(self):return self.model_dump(mode='json',exclude={'approval'})
    @model_validator(mode='after')
    def check(self):
        if len(set(self.required_types))!=len(self.required_types):raise ValueError('duplicate required type')
        if self.approval:self.approval.approved_at=instant(self.approval.approved_at)
        return self

class Scope(Strict):
    synthetic: Literal[True]
    cases: list[str] = Field(min_length=1,max_length=20)
    start: datetime
    as_of: datetime
    max_output_bytes: StrictInt = Field(default=1000000,ge=2000,le=5000000)
    @model_validator(mode='after')
    def check(self):
        import re
        self.start,self.as_of=instant(self.start),instant(self.as_of)
        if not 0<(self.as_of-self.start).total_seconds()<=604800 or self.as_of>datetime.now(timezone.utc):raise ValueError('invalid time scope')
        if len(set(self.cases))!=len(self.cases) or any(not re.fullmatch(r'REF-DEMO-[0-9]{3}',c) for c in self.cases):raise ValueError('ambiguous synthetic scope')
        return self

class Document(Strict):
    kind: DOCS
    version: StrictInt = Field(ge=1,le=999)
    fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')

class Record(Strict):
    id: str = Field(pattern=r'^EV-[0-9]{3,6}$')
    source: Literal['sender','receiver']
    case_id: str = Field(pattern=r'^REF-DEMO-[0-9]{3}$')
    revision: StrictInt = Field(ge=1,le=99)
    kind: Literal['submitted','document_received','acknowledged','cancelled']
    occurred_at: datetime
    received_at: datetime
    documents: list[Document] = Field(default_factory=list,max_length=3)
    related_ref: str | None = Field(default=None,pattern=r'^(sender|receiver):EV-[0-9]{3,6}$')
    @property
    def ref(self):return f'{self.source}:{self.id}'
    @model_validator(mode='after')
    def check(self):
        self.occurred_at,self.received_at=instant(self.occurred_at),instant(self.received_at)
        if self.kind=='submitted':
            if self.source!='sender' or self.related_ref or len({d.kind for d in self.documents})!=len(self.documents):raise ValueError('invalid submission')
        else:
            if not self.related_ref:raise ValueError('explicit submission link required')
            if self.kind=='document_received':
                if self.source!='receiver' or len(self.documents)!=1:raise ValueError('one received metadata item required')
            elif self.documents:raise ValueError('unexpected document metadata')
            if self.kind=='acknowledged' and self.source!='receiver':raise ValueError('receiver acknowledgment required')
        return self

class Feed(Strict):
    source: Literal['sender','receiver']
    cases: list[str]
    count: StrictInt = Field(ge=0,le=1000)
    complete_through: datetime
    available: StrictBool
    truncated: StrictBool
    offline_pending: StrictBool
    clock_uncertainty_seconds: StrictInt = Field(ge=0,le=3600)


def audit_referrals(scope,policy,evidence,snapshot):
    approval=policy.approval;checksum=digest(policy.content())
    sources={a.ref:{'text':redact(a.text)} for a in evidence.artifacts if approval and a.ref in {l.source_id for l in approval.links}}
    kinds={a.ref:a.kind for a in evidence.artifacts}
    valid,ledger=verify_quote_record(policy.id,checksum,approval.links,sources,kinds) if approval else (False,None)
    valid=bool(valid and approval.decision=='approved' and approval.policy_sha256==checksum and approval.approved_at<=scope.start)
    issues=[];blocked={c:[] for c in scope.cases};events=[];feeds={};quarantine=[]
    if not valid:issues.append('unverified_administrative_policy')
    elif not isinstance(snapshot,dict) or set(snapshot)!={'synthetic','events','feeds'} or snapshot['synthetic'] is not True or not isinstance(snapshot['events'],list):issues.append('invalid_synthetic_snapshot')
    else:
        rows=snapshot['events']
        if len(rows)>1000:issues.append('event_budget_exceeded')
        try:
            if not isinstance(snapshot['feeds'],list) or len(snapshot['feeds'])!=2:raise ValueError('both feed manifests required')
            for raw in snapshot['feeds']:
                f=Feed.model_validate(raw);f.complete_through=instant(f.complete_through)
                if f.source in feeds or sorted(f.cases)!=sorted(scope.cases):raise ValueError('ambiguous manifest')
                feeds[f.source]=f
                if not f.available or f.truncated or f.offline_pending:issues.append('partial_or_unavailable_coverage')
                if not scope.start<=f.complete_through<=scope.as_of or (scope.as_of-f.complete_through).total_seconds()>policy.max_feed_lag_seconds:issues.append('stale_feed_watermark')
                if f.count!=sum(isinstance(r,dict) and r.get('source')==f.source for r in rows):issues.append('feed_count_mismatch')
        except (ValueError,TypeError):issues.append('invalid_feed_manifest')
        for i,raw in enumerate(rows[:1000]):
            try:
                e=Record.model_validate(raw)
                if e.case_id not in blocked or e.source not in feeds:raise ValueError('ambiguous identity')
                u=feeds[e.source].clock_uncertainty_seconds
                if (e.occurred_at-scope.start).total_seconds()<u or (scope.as_of-e.occurred_at).total_seconds()<u or e.received_at>scope.as_of or (e.received_at-e.occurred_at).total_seconds() < -u:raise ValueError('incoherent timestamps')
                events.append(e)
            except (ValueError,TypeError):
                quarantine.append({'row':i,'reason':'invalid metadata; payload omitted'})
                c=raw.get('case_id') if isinstance(raw,dict) else None
                if isinstance(c,str) and c in blocked:blocked[c].append('quarantined_record')
                else:issues.append('ambiguous_case_identity')
    refs={};u=max((f.clock_uncertainty_seconds for f in feeds.values()),default=0)
    cutoff=min([scope.as_of,*[f.complete_through for f in feeds.values()]])
    for e in events:
        if e.ref in refs:
            blocked[e.case_id].append('duplicate_source_id');blocked[refs[e.ref].case_id].append('duplicate_source_id')
        refs[e.ref]=e
    for e in events:
        if e.related_ref:
            parent=refs.get(e.related_ref)
            if parent is None or parent.kind!='submitted' or parent.case_id!=e.case_id or parent.revision!=e.revision or (e.occurred_at-parent.occurred_at).total_seconds()<=2*u:
                blocked[e.case_id].append('unresolved_or_ambiguous_submission_link')
                if parent:blocked[parent.case_id].append('ambiguous_link_target')
    report={'schema_version':1,'synthetic_only':True,'human_review_required':True,'clinical_decisions_made':False,'external_actions_executed':False,'policy_sha256':checksum,'scope':scope.model_dump(mode='json'),'cases':[],'quarantined_rows':quarantine,'feed_coverage':[feeds[k].model_dump(mode='json') for k in sorted(feeds)]}
    if valid:report.update(policy=policy.content(),approval_provenance=ledger,supporting_evidence=sources)
    for c in scope.cases:
        trace=sorted([e for e in events if e.case_id==c],key=lambda e:(e.occurred_at,e.ref));reasons=list(issues)+blocked[c]
        submissions=[e for e in trace if e.kind=='submitted']
        # A selected case is one immutable packet revision; revised packets require separate case IDs.
        if len(submissions)!=1 or len({e.revision for e in trace})!=1:reasons.append('ambiguous_or_missing_packet_revision')
        if any((b.occurred_at-a.occurred_at).total_seconds()<=2*u for a,b in zip(trace,trace[1:])):reasons.append('ambiguous_order')
        cancellations=[e for e in trace if e.kind=='cancelled']
        if len(cancellations)>1 or cancellations and any(e.occurred_at>cancellations[0].occurred_at for e in trace):reasons.append('conflicting_cancellation_or_post_cancellation_activity')
        case={'case_id':c,'status':'unknown' if reasons else 'no_observed_signal','reasons':sorted(set(reasons)),'findings':[],'timeline':[{'ref':e.ref,**e.model_dump(mode='json')} for e in trace],'evidence_through':cutoff.isoformat()}
        def finding(kind,items,**details):case['findings'].append({'kind':kind,'evidence_refs':[e.ref for e in items],'review_role':'referral_administration','next_check':'Review the cited metadata and documented administrative exceptions within authorized access; do not access clinical contents or contact parties automatically.',**details})
        if not reasons:
            sub=submissions[0];expected={d.kind:d for d in sub.documents};received={}
            for e in trace:
                if e.kind=='document_received':received.setdefault(e.documents[0].kind,[]).append(e)
            for kind,items in sorted(received.items()):
                if kind not in expected or any(e.documents[0]!=expected[kind] for e in items):finding('document_metadata_conflict',[sub,*items],document_type=kind,note='Version/fingerprint mismatch; not a judgment about document contents or validity.')
            if not cancellations:
                for kind in sorted(set(policy.required_types)-set(expected)):finding('required_metadata_not_listed',[sub],document_type=kind)
                age=(cutoff-sub.occurred_at).total_seconds()-2*u
                if age>policy.delivery_seconds:
                    for kind in sorted(set(expected)-set(received)):finding('document_receipt_not_observed',[sub],document_type=kind,threshold_seconds=policy.delivery_seconds)
                if age>policy.acknowledgment_seconds and not any(e.kind=='acknowledged' for e in trace):finding('packet_acknowledgment_not_observed',[sub],threshold_seconds=policy.acknowledgment_seconds)
            if case['findings']:case['status']='administrative_review_suggested'
        report['cases'].append(case)
    report['limitations']=['Fictional administrative metadata only; no clinical contents, suitability, consent validity, urgency, scheduling or insurance decisions.', 'Unobserved means absent from available source-asserted coverage, not that an action did not happen.', 'One explicitly selected immutable revision per case; no cross-case patient matching or automatic latest-version selection.', 'Source completeness and approval authenticity require human review. No live connector, model or external action path.']
    report['sha256']=digest(report)
    return report
