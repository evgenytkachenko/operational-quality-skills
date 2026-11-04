"""Fictional expected-control execution reconciliation; no effectiveness certification."""
from datetime import datetime,timezone
from typing import Literal
from pydantic import Field,StrictBool,StrictInt,model_validator
from .core import Strict,instant,redact
from .control_validation import digest,Link
from .conformance import PolicyApproval,verify_quote_record

class Obligation(Strict):
    id: str = Field(pattern=r'^OB-DEMO-[0-9]{3}$')
    control_id: str = Field(pattern=r'^CONTROL-DEMO-[0-9]{3}$')
    version: StrictInt = Field(ge=1,le=99)
    scope_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    earliest_start: datetime
    due: datetime
    owner_role: Literal['operations_quality','intake_lead','pharmacy_operations_lead']
    @model_validator(mode='after')
    def check(self):
        self.earliest_start,self.due=instant(self.earliest_start),instant(self.due)
        if self.earliest_start>=self.due:raise ValueError('invalid obligation window')
        return self

class Register(Strict):
    synthetic: Literal[True]
    id: Literal['CONTROL-DEMO-REGISTER']='CONTROL-DEMO-REGISTER'
    version: StrictInt = Field(ge=1,le=99)
    start: datetime
    as_of: datetime
    grace_seconds: StrictInt = Field(ge=0,le=86400)
    max_feed_lag_seconds: StrictInt = Field(ge=0,le=3600)
    obligations: list[Obligation] = Field(min_length=1,max_length=50)
    approval: PolicyApproval | None = None
    def content(self):return self.model_dump(mode='json',exclude={'approval'})
    @model_validator(mode='after')
    def check(self):
        self.start,self.as_of=instant(self.start),instant(self.as_of)
        if not 0<(self.as_of-self.start).total_seconds()<=604800 or self.as_of>datetime.now(timezone.utc):raise ValueError('invalid audit window')
        if len({o.id for o in self.obligations})!=len(self.obligations):raise ValueError('duplicate obligation')
        if any(not self.start<=o.earliest_start<o.due<=self.as_of for o in self.obligations):raise ValueError('obligation outside audit window')
        # Distinct IDs cannot silently duplicate a scheduled obligation.
        if len({(o.control_id,o.version,o.scope_sha256,o.earliest_start,o.due) for o in self.obligations})!=len(self.obligations):raise ValueError('duplicate semantic obligation')
        if self.approval:self.approval.approved_at=instant(self.approval.approved_at)
        return self

class Run(Strict):
    id: str = Field(pattern=r'^RUN-DEMO-[0-9]{3}$')
    obligation_id: str = Field(pattern=r'^OB-DEMO-[0-9]{3}$')
    control_id: str = Field(pattern=r'^CONTROL-DEMO-[0-9]{3}$')
    version: StrictInt = Field(ge=1,le=99)
    scope_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    started_at: datetime
    finished_at: datetime
    recorded_at: datetime
    result: Literal['success','failed']
    previous_run_id: str | None = Field(default=None,pattern=r'^RUN-DEMO-[0-9]{3}$')
    @model_validator(mode='after')
    def check(self):
        self.started_at,self.finished_at,self.recorded_at=map(instant,(self.started_at,self.finished_at,self.recorded_at))
        if self.started_at>self.finished_at or self.finished_at>self.recorded_at:raise ValueError('incoherent run times')
        return self

class Skip(Strict):
    id: str = Field(pattern=r'^SKIP-DEMO-[0-9]{3}$')
    obligation_id: str = Field(pattern=r'^OB-DEMO-[0-9]{3}$')
    obligation_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    decision: Literal['approved_skip','revoked']
    approved_at: datetime
    links: list[Link] = Field(min_length=1,max_length=5)
    def content(self):return self.model_dump(mode='json',exclude={'links'})
    @model_validator(mode='after')
    def check(self):self.approved_at=instant(self.approved_at);return self

class Manifest(Strict):
    source: Literal['runs','skips']
    obligation_ids: list[str]
    complete_from: datetime
    complete_through: datetime
    available: StrictBool
    truncated: StrictBool
    count: StrictInt = Field(ge=0,le=200)
    clock_uncertainty_seconds: StrictInt = Field(ge=0,le=300)


def audit_coverage(register,evidence,snapshot):
    a=register.approval;checksum=digest(register.content())
    sources={x.ref:{'text':redact(x.text)} for x in evidence.artifacts};kinds={x.ref:x.kind for x in evidence.artifacts}
    valid,ledger=verify_quote_record(register.id,checksum,a.links,sources,kinds) if a else (False,None)
    valid=bool(valid and a.decision=='approved' and a.policy_sha256==checksum and a.approved_at<=register.start)
    expected={o.id:o for o in register.obligations};blocked={k:[] for k in expected};issues=[];runs=[];skips=[];manifests={};quarantine=[]
    if not valid:issues.append('unverified_expected_register')
    elif not isinstance(snapshot,dict) or set(snapshot)!={'synthetic','runs','skips','manifests'} or snapshot['synthetic'] is not True:issues.append('invalid_snapshot')
    else:
        try:
            if not all(isinstance(snapshot[k],list) and len(snapshot[k])<=200 for k in ('runs','skips')):raise ValueError('record budget')
            if not isinstance(snapshot['manifests'],list) or len(snapshot['manifests'])!=2:raise ValueError('manifest required')
            for raw in snapshot['manifests']:
                m=Manifest.model_validate(raw);m.complete_from,m.complete_through=instant(m.complete_from),instant(m.complete_through)
                if m.source in manifests or sorted(m.obligation_ids)!=sorted(expected):raise ValueError('ambiguous manifest')
                manifests[m.source]=m
                if not m.available or m.truncated or m.complete_from>register.start or not register.start<=m.complete_through<=register.as_of or (register.as_of-m.complete_through).total_seconds()>register.max_feed_lag_seconds or m.count!=len(snapshot[m.source]):issues.append('incomplete_or_stale_ledger')
            for key,model,items in [('runs',Run,runs),('skips',Skip,skips)]:
                for n,raw in enumerate(snapshot[key]):
                    try:
                        item=model.model_validate(raw)
                        if item.obligation_id not in expected:raise ValueError('outside obligation scope')
                        items.append(item)
                    except (ValueError,TypeError):
                        quarantine.append({'source':key,'row':n,'reason':'invalid record; payload omitted'})
                        oid=raw.get('obligation_id') if isinstance(raw,dict) else None
                        if isinstance(oid,str) and oid in blocked:blocked[oid].append('quarantined_record')
                        else:issues.append('ambiguous_obligation_identity')
        except (ValueError,TypeError):issues.append('invalid_or_over_budget_ledger')
    u=max((m.clock_uncertainty_seconds for m in manifests.values()),default=0)
    cutoff=min([register.as_of,*[m.complete_through for m in manifests.values()]])
    for items in (runs,skips):
        ids={}
        for item in items:
            if item.id in ids:
                blocked[item.obligation_id].append('duplicate_record_id');blocked[ids[item.id].obligation_id].append('duplicate_record_id')
            ids[item.id]=item
    run_ids={r.id:r for r in runs}
    for r in runs:
        o=expected[r.obligation_id]
        if (r.control_id,r.version,r.scope_sha256)!=(o.control_id,o.version,o.scope_sha256):blocked[o.id].append('control_version_or_scope_mismatch')
        if (r.started_at-o.earliest_start).total_seconds()<u or (register.as_of-r.recorded_at).total_seconds()<u:blocked[o.id].append('run_outside_certain_window')
        if r.previous_run_id:
            prev=run_ids.get(r.previous_run_id)
            if prev is None or prev.obligation_id!=r.obligation_id or (r.started_at-prev.finished_at).total_seconds()<=2*u:
                blocked[o.id].append('ambiguous_retry_link')
                if prev:blocked[prev.obligation_id].append('ambiguous_retry_target')
    report={'schema_version':1,'synthetic_only':True,'human_review_required':True,'effectiveness_certified':False,'actions_executed':False,'register_sha256':checksum,'obligations':[],'quarantined_rows':quarantine,'coverage':[manifests[k].model_dump(mode='json') for k in sorted(manifests)]}
    if valid:report.update(register=register.content(),approval_provenance=ledger)
    for oid,o in expected.items():
        trace=sorted([r for r in runs if r.obligation_id==oid],key=lambda r:(r.started_at,r.id));permits=[s for s in skips if s.obligation_id==oid];reasons=issues+blocked[oid];state='unknown';links=[]
        if trace and (trace[0].previous_run_id is not None or any(b.previous_run_id!=a.id or (b.started_at-a.finished_at).total_seconds()<=2*u for a,b in zip(trace,trace[1:]))):reasons.append('unlinked_or_overlapping_attempts')
        if any(r.result=='success' for r in trace[:-1]):reasons.append('retry_after_success_without_invalidation')
        if len(permits)>1:reasons.append('ambiguous_skip_history')
        skip_valid=False
        if len(permits)==1:
            s=permits[0];ok,entry=verify_quote_record(s.id,digest(s.content()),s.links,sources,kinds)
            skip_valid=bool(ok and s.decision=='approved_skip' and s.obligation_sha256==digest(o.model_dump(mode='json')) and s.approved_at<=o.earliest_start)
            if skip_valid:links.append(entry)
            else:reasons.append('unverified_or_revoked_skip')
        if permits and trace:reasons.append('skip_and_execution_conflict')
        if not reasons:
            if skip_valid:state='approved_skip_recorded'
            elif trace:
                last=trace[-1]
                if last.result=='failed':state='failed_run_recorded'
                elif (last.finished_at-o.due).total_seconds()-u>register.grace_seconds:state='success_recorded_late'
                elif (last.finished_at-o.due).total_seconds()+u>register.grace_seconds:state='unknown';reasons.append('completion_near_deadline')
                else:state='success_recorded_within_window'
            elif (cutoff-o.due).total_seconds()-u>register.grace_seconds:state='execution_not_observed'
            else:state='unknown';reasons.append('coverage_not_beyond_due_and_grace')
        report['obligations'].append({'id':oid,'state':state,'reasons':sorted(set(reasons)),'owner_role':o.owner_role,'evidence_through':cutoff.isoformat(),'runs':[r.model_dump(mode='json') for r in trace],'skips':[s.content() for s in permits],'skip_provenance':links,'evidence_refs':[r.id for r in trace]+[s.id for s in permits], 'next_check':'Human review register applicability, ledger coverage and cited records; never execute or close a control automatically.'})
    report['counts']={s:sum(o['state']==s for o in report['obligations']) for s in sorted({o['state'] for o in report['obligations']})}
    report['limitations']=['Explicit expected obligations only; no schedules created and no inference beyond the approved selected register.', 'Not observed in available records does not prove a control did not run. Coverage and approval are source assertions.', 'A success record proves neither correct execution nor control effectiveness, error reduction or clinical safety.', 'No clinical or insurance decisions, live services, models, external actions or automatic corrective-action closure.']
    report['sha256']=digest(report)
    return report
