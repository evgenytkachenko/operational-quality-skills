"""Bounded fictional retail workflow audit; never an inventory ledger."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import Field, StrictBool, StrictInt, model_validator
from .core import Strict, instant, redact
from .control_validation import digest
from .conformance import PolicyApproval, verify_quote_record

KINDS=('received','availability_recorded','reserved','picked','fulfilled','handoff_sent','acknowledged','cancelled','returned','status_recorded')
SOURCES=('receiving','inventory','orders','store')
PARENTS={'availability_recorded':'received','picked':'reserved','fulfilled':'picked','handoff_sent':'fulfilled','acknowledged':'handoff_sent','returned':'fulfilled'}
ROLES={'received':'inventory_team','availability_recorded':'inventory_team','reserved':'pick_team','picked':'fulfillment_team','fulfilled':'handoff_team','handoff_sent':'handoff_team'}

class Rule(Strict):
    trigger: Literal['received','reserved','picked','fulfilled','handoff_sent']
    response: Literal['availability_recorded','picked','fulfilled','handoff_sent','acknowledged']
    seconds: StrictInt = Field(ge=1,le=604800)
    @model_validator(mode='after')
    def check(self):
        if PARENTS[self.response]!=self.trigger:raise ValueError('unsupported rule pair')
        return self

class StorePolicy(Strict):
    id: Literal['STORE-DEMO-POLICY']='STORE-DEMO-POLICY'
    version: str = Field(pattern=r'^v[0-9]+$')
    rules: list[Rule] = Field(min_length=1,max_length=5)
    max_feed_lag_seconds: StrictInt = Field(ge=0,le=86400)
    approval: PolicyApproval | None = None
    def content(self):return self.model_dump(mode='json',exclude={'approval'})
    @model_validator(mode='after')
    def check(self):
        if len({r.trigger for r in self.rules})!=len(self.rules):raise ValueError('duplicate rule')
        if self.approval:self.approval.approved_at=instant(self.approval.approved_at)
        return self

class StoreScope(Strict):
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
        if not 0<(self.as_of-self.start).total_seconds()<=604800 or self.as_of>datetime.now(timezone.utc):raise ValueError('invalid window')
        if len(set(self.case_ids))!=len(self.case_ids) or any(not re.fullmatch(r'RETAIL-DEMO-[0-9]{3}',c) for c in self.case_ids):raise ValueError('ambiguous demo IDs')
        return self

class Feed(Strict):
    source: Literal['receiving','inventory','orders','store']
    cases: list[str]
    complete_through: datetime
    count: StrictInt = Field(ge=0,le=1000)
    available: StrictBool
    truncated: StrictBool
    offline_pending: StrictBool
    clock_uncertainty_seconds: StrictInt = Field(ge=0,le=3600)

class Record(Strict):
    id: str = Field(pattern=r'^EV-[0-9]{3,6}$')
    source: Literal['receiving','inventory','orders','store']
    case_id: str = Field(pattern=r'^RETAIL-DEMO-[0-9]{3}$')
    store_id: str = Field(pattern=r'^STORE-DEMO-[0-9]{3}$')
    sku: str = Field(pattern=r'^SKU-DEMO-[0-9]{3}$')
    kind: Literal['received','availability_recorded','reserved','picked','fulfilled','handoff_sent','acknowledged','cancelled','returned','status_recorded']
    occurred_at: datetime
    received_at: datetime
    quantity: StrictInt = Field(ge=0,le=100000)
    unit: Literal['each']='each'
    related_ref: str | None = Field(default=None,pattern=r'^(receiving|inventory|orders|store):EV-[0-9]{3,6}$')
    status: Literal['open','complete','cancelled'] | None = None
    supersedes_ref: str | None = Field(default=None,pattern=r'^(receiving|inventory|orders|store):EV-[0-9]{3,6}$')
    @model_validator(mode='after')
    def check(self):
        self.occurred_at,self.received_at=instant(self.occurred_at),instant(self.received_at)
        if self.kind in PARENTS or self.kind=='cancelled':
            if not self.related_ref:raise ValueError('explicit link required')
        elif self.related_ref:raise ValueError('unexpected link')
        if self.kind=='status_recorded':
            if self.status is None or self.quantity!=0:raise ValueError('status needs label and zero quantity')
        elif self.status or self.supersedes_ref:raise ValueError('unexpected status fields')
        if self.kind!='status_recorded' and self.quantity==0:raise ValueError('positive quantity required')
        return self
    @property
    def ref(self):return f'{self.source}:{self.id}'


def audit_store(scope,policy,evidence,snapshot):
    checksum=digest(policy.content());approval=policy.approval
    sources={a.ref:{'text':redact(a.text)} for a in evidence.artifacts if approval and a.ref in {l.source_id for l in approval.links}}
    kinds={a.ref:a.kind for a in evidence.artifacts}
    valid,ledger=verify_quote_record(policy.id,checksum,approval.links,sources,kinds) if approval else (False,None)
    valid=bool(valid and approval.decision=='approved' and approval.policy_sha256==checksum and approval.approved_at<=scope.start)
    issues=[];events=[];feeds={};blocked={c:[] for c in scope.case_ids};quarantine=[]
    if not valid:issues.append('unverified_policy_approval')
    elif not isinstance(snapshot,dict) or set(snapshot)!={'synthetic','feeds','events'} or snapshot['synthetic'] is not True or not isinstance(snapshot['events'],list):issues.append('invalid_mock_snapshot')
    else:
        rows=snapshot['events']
        if len(rows)>scope.max_events:issues.append('event_budget_exceeded')
        try:
            if not isinstance(snapshot['feeds'],list) or len(snapshot['feeds'])!=4:raise ValueError('four feeds required')
            for raw in snapshot['feeds']:
                f=Feed.model_validate(raw);f.complete_through=instant(f.complete_through)
                if f.source in feeds or sorted(f.cases)!=sorted(scope.case_ids):raise ValueError('ambiguous manifest')
                feeds[f.source]=f
                if not f.available or f.truncated or f.offline_pending:issues.append('coverage_partial_or_offline')
                if not scope.start<=f.complete_through<=scope.as_of or (scope.as_of-f.complete_through).total_seconds()>policy.max_feed_lag_seconds:issues.append('delayed_sync_or_invalid_watermark')
                if f.count!=sum(isinstance(r,dict) and r.get('source')==f.source for r in rows):issues.append('source_count_mismatch')
        except (ValueError,TypeError):issues.append('invalid_feed_manifest')
        for i,raw in enumerate(rows[:scope.max_events]):
            try:
                e=Record.model_validate(raw)
                if e.case_id not in blocked or e.source not in feeds:raise ValueError('unknown identity')
                u=feeds[e.source].clock_uncertainty_seconds
                if (e.occurred_at-scope.start).total_seconds()<u or (scope.as_of-e.occurred_at).total_seconds()<u or e.received_at>scope.as_of or (e.received_at-e.occurred_at).total_seconds() < -u:raise ValueError('incoherent times')
                events.append(e)
            except (ValueError,TypeError):
                quarantine.append({'row':i,'reason':'invalid_or_ambiguous_record; payload omitted'})
                c=raw.get('case_id') if isinstance(raw,dict) else None
                if isinstance(c,str) and c in blocked:blocked[c].append('quarantined_record')
                else:issues.append('ambiguous_identity')
    refs={};u=max((f.clock_uncertainty_seconds for f in feeds.values()),default=0)
    cutoff=min([scope.as_of,*[f.complete_through for f in feeds.values()]])
    for e in events:
        if e.ref in refs:
            blocked[e.case_id].append('duplicate_source_id');blocked[refs[e.ref].case_id].append('duplicate_source_id')
        refs[e.ref]=e
    for e in events:
        for link in [e.related_ref,e.supersedes_ref]:
            if not link:continue
            old=refs.get(link)
            if old is None or (old.case_id,old.store_id,old.sku)!=(e.case_id,e.store_id,e.sku) or (e.occurred_at-old.occurred_at).total_seconds()<=2*u:
                blocked[e.case_id].append('unresolved_or_ambiguous_link')
                if old:blocked[old.case_id].append('ambiguous_link_target')
            elif link==e.supersedes_ref and old.kind!='status_recorded':blocked[e.case_id].append('invalid_status_supersession')
            elif link==e.related_ref and (e.kind=='cancelled' and old.kind not in {'reserved','picked'} or e.kind in PARENTS and old.kind!=PARENTS[e.kind]):blocked[e.case_id].append('invalid_workflow_link')
    result={'schema_version':1,'synthetic_only':True,'review_status':'HUMAN_REVIEW_REQUIRED','actions_executed':False,'root_cause_established':False,'policy_sha256':checksum,'scope':scope.model_dump(mode='json'),'cases':[],'quarantined_rows':quarantine,'feed_coverage':[feeds[k].model_dump(mode='json') for k in sorted(feeds)]}
    if valid:result.update(policy=policy.content(),approval_provenance=ledger,supporting_evidence=sources)
    for c in scope.case_ids:
        trace=sorted([e for e in events if e.case_id==c],key=lambda e:(e.occurred_at,e.ref));reasons=issues+blocked[c]
        if not trace:reasons.append('no_usable_records')
        if len({(e.store_id,e.sku) for e in trace})>1:reasons.append('ambiguous_line_identity')
        if any((b.occurred_at-a.occurred_at).total_seconds()<=2*u for a,b in zip(trace,trace[1:])):reasons.append('ambiguous_order')
        # One reservation/receiving cycle per selected line; reopened work requires a new ID.
        if any(sum(e.kind==kind for e in trace)>1 for kind in ('received','reserved')):reasons.append('ambiguous_reused_cycle')
        superseded={e.supersedes_ref for e in trace if e.supersedes_ref}
        statuses=[e for e in trace if e.kind=='status_recorded' and e.ref not in superseded]
        case={'case_id':c,'status':'unknown' if reasons else 'no_observed_signal','reasons':sorted(set(reasons)),'findings':[],'timeline':[{'ref':e.ref,**e.model_dump(mode='json')} for e in trace],'evidence_through':cutoff.isoformat()}
        def finding(kind,ev,role,**details):
            case['findings'].append({'kind':kind,'evidence_refs':[e.ref for e in ev],'review_role':role,'next_check':'Review cited source records and documented exceptions within your authorized role; do not change stock or fulfill orders.',**details})
        if not reasons:
            conflict=len({e.status for e in statuses})>1
            if conflict:finding('conflicting_recorded_status',statuses,'store_supervisor')
            for parent in trace:
                children=[e for e in trace if e.related_ref==parent.ref]
                # Quantities are incremental movements, except availability, a receipt-specific posted quantity.
                for kind in sorted({e.kind for e in children}):
                    group=[e for e in children if e.kind==kind]
                    if sum(e.quantity for e in group)>parent.quantity:
                        finding('linked_quantity_exceeds_recorded_parent',[parent,*group],ROLES.get(parent.kind,'store_supervisor'),recorded_parent=parent.quantity,recorded_child_total=sum(e.quantity for e in group),note='Possible mapping or record discrepancy; not proof of stock loss.')
                successor={'reserved':'picked','picked':'fulfilled'}.get(parent.kind)
                allocations=[e for e in children if e.kind in {successor,'cancelled'}]
                if successor and sum(e.quantity for e in allocations)>parent.quantity and any(e.kind=='cancelled' for e in allocations) and any(e.kind==successor for e in allocations):
                    finding('conflicting_completed_and_cancelled_quantities',[parent,*allocations],'store_supervisor')
                for rule in policy.rules:
                    if parent.kind!=rule.trigger or conflict:continue
                    responses=[e for e in children if e.kind==rule.response]
                    cancellations=[e for e in children if e.kind=='cancelled']
                    accounted=sum(e.quantity for e in responses+cancellations)
                    if accounted>parent.quantity:
                        continue
                    if (cutoff-parent.occurred_at).total_seconds()-2*u>rule.seconds and accounted<parent.quantity:
                        finding('response_quantity_not_observed',[parent,*responses,*cancellations],ROLES[parent.kind],expected_step=rule.response,unobserved_quantity=parent.quantity-accounted,threshold_seconds=rule.seconds,note='Unobserved in available records, not proof the action did not happen.')
            if case['findings']:case['status']='administrative_review_suggested'
        result['cases'].append(case)
    result['limitations']=['Fictional selected line cycles only; not an inventory balance, stock-loss conclusion or population audit.', 'Coverage and policy approval are supplied assertions, not authenticated guarantees.', 'Returns are separate linked movements, never evidence of restocking or reversal of prior fulfillment.', 'No live retail adapter, external actions, automatic RCA, model, schedule or notification.']
    result['sha256']=digest(result)
    return result
