"""Synthetic exception review to accountable proposal; no pilot approval or outcome evaluation."""
import json,re
from datetime import datetime
from pydantic import Field,StrictInt,StrictBool,model_validator
from typing import Literal
from .core import Strict,Config,analyze,instant,redact
from .control_validation import digest
from .inquiry import SYSTEM,handoff,validate_assessment,local_assessment

PHARMACY_SYSTEM=SYSTEM+"""
This workflow is fictional pharmacy administrative improvement only. Never assess clinical
appropriateness, dosing, dispensing, substitution, safety, urgency, consent validity or insurance.
Never contact people, modify systems, schedule or implement controls. No tools are available.
Recorded categories are not verified process failures. Recurrence in selected cases is not a
population trend or causal result. Controls are proposals requiring human review. Unknown
or unavailable evidence permits only unknown hypotheses and empty observations/controls.
"""

def inquiry(packet):
    request=handoff(packet)
    request['system']=PHARMACY_SYSTEM
    return request

class Event(Strict):
    id: str = Field(pattern=r'^EV-[0-9]{3}$')
    case_id: str = Field(pattern=r'^RX-DEMO-[0-9]{3}$')
    timestamp: datetime
    activity: Literal['handoff_sent','acknowledged','exception_recorded','exception_resolved']
    queue: Literal['intake','clarification','pharmacy']
    exception: Literal['none','owner_unrecorded','ack_unrecorded','routing_return']
    @model_validator(mode='after')
    def check(self):
        self.timestamp=instant(self.timestamp)
        if (self.activity in {'exception_recorded','exception_resolved'})!=(self.exception!='none'):raise ValueError('exception label mismatch')
        return self

class Snapshot(Strict):
    synthetic: Literal[True]
    complete: StrictBool
    events: list[Event] = Field(max_length=40)

class Settings(Strict):
    synthetic: Literal[True]
    case_ids: list[str] = Field(min_length=1,max_length=10)
    start: datetime
    end: datetime
    @model_validator(mode='after')
    def check(self):
        if len(set(self.case_ids))!=len(self.case_ids) or any(not re.fullmatch(r'RX-DEMO-[0-9]{3}',c) for c in self.case_ids):raise ValueError('synthetic cases required')
        self.start,self.end=instant(self.start),instant(self.end)
        if not 0<(self.end-self.start).total_seconds()<=604800:raise ValueError('invalid window')
        from datetime import timezone
        if self.end>datetime.now(timezone.utc):raise ValueError('future window')
        return self

class Action(Strict):
    control_index: StrictInt = Field(ge=0,le=9)
    hypothesis_indices: list[StrictInt] = Field(min_length=1,max_length=6)
    owner_role: Literal['operations_quality','intake_lead','pharmacy_operations_lead']
    review_by: datetime
    closure_evidence_required: str = Field(min_length=10,max_length=800)
    @model_validator(mode='after')
    def check(self):
        self.review_by=instant(self.review_by)
        if len(set(self.hypothesis_indices))!=len(self.hypothesis_indices):raise ValueError('duplicate hypotheses')
        return self

class Accountability(Strict):
    review_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    prepared_at: datetime
    actions: list[Action] = Field(min_length=1,max_length=10)
    @model_validator(mode='after')
    def check(self):
        self.prepared_at=instant(self.prepared_at)
        if len({a.control_index for a in self.actions})!=len(self.actions):raise ValueError('duplicate control accountability')
        if any(a.review_by<=self.prepared_at for a in self.actions):raise ValueError('review deadline must follow preparation')
        return self


def prepare(settings,snapshot):
    config=Config(case_ids=settings.case_ids,start=settings.start,end=settings.end,max_rows=50,max_packet_bytes=16000,sources=[{'name':'administrative','kind':'postgres','fields':{k:k for k in ('id','case_id','timestamp','activity','queue','message')}}])
    invalid=(len({e.id for e in snapshot.events})!=len(snapshot.events) or any(e.case_id not in settings.case_ids or not settings.start<=e.timestamp<settings.end for e in snapshot.events))
    if any(len({e.timestamp for e in snapshot.events if e.case_id==c})!=len([e for e in snapshot.events if e.case_id==c]) for c in settings.case_ids):invalid=True
    usable=snapshot.complete and not invalid and {e.case_id for e in snapshot.events}==set(settings.case_ids)
    rows=[{'id':e.id,'case_id':e.case_id,'timestamp':e.timestamp.isoformat(),'activity':e.activity,'queue':e.queue,'message':f'Recorded administrative exception category: {e.exception}.'} for e in snapshot.events] if usable else []
    packet=analyze(config,lambda s,c:(rows,[] if usable else ['Incomplete or ambiguous selected evidence; no causal inquiry permitted.']))
    packet.pop('sha256');packet['synthetic_only']=True
    packet['limitations']+=['Selected cases only; source completeness is asserted, not authenticated. Recorded exception labels are not independently verified failures.', 'No clinical, dispensing, urgency, insurance or safety decisions. No tools or external actions. No PHI or actual company data.', 'Repeated category across cases is a review candidate, not a population trend or causal result.']
    groups={}
    if usable:
        for e in snapshot.events:
            if e.activity=='exception_recorded':groups.setdefault((e.exception,e.queue),[]).append(e)
    recurrence=[{'exception':k[0],'queue':k[1],'distinct_cases':len({e.case_id for e in v}),'case_ids':sorted({e.case_id for e in v}),'evidence_refs':sorted('administrative:'+e.id for e in v)} for k,v in sorted(groups.items()) if len({e.case_id for e in v})>=2]
    packet['selected_case_patterns']=recurrence
    packet['sha256']=digest(packet)
    if len(json.dumps(packet).encode())>16000:raise ValueError('evidence budget exceeded; reduce selected cases')
    return packet


def review(raw,packet):
    result=validate_assessment(raw,packet)
    a=result['assessment']
    if not packet['events'] and (a['observations'] or a['controls'] or any(h['status']!='unknown' for h in a['hypotheses'])):raise ValueError('unavailable evidence requires unknown hypotheses and no controls')
    return result


def local_review(packet,model,client=None):
    if len(json.dumps(packet).encode())>16000:raise ValueError('evidence budget')
    # Validate packet integrity before contacting even a loopback model.
    if digest({k:v for k,v in packet.items() if k!='sha256'})!=packet.get('sha256'):raise ValueError('packet hash')
    result=local_assessment(packet,model,client=client,system=PHARMACY_SYSTEM)
    return review(json.dumps(result['assessment']),packet)


def proposal(reviewed,plan):
    if digest(reviewed)!=plan.review_sha256:raise ValueError('review hash mismatch')
    assessment=reviewed['assessment'];controls=assessment['controls'];hypotheses=assessment['hypotheses']
    if {a.control_index for a in plan.actions}!=set(range(len(controls))):raise ValueError('every proposed control needs one accountable review action')
    for a in plan.actions:
        if controls[a.control_index]['owner_role']!=a.owner_role:raise ValueError('control owner differs from accountable role')
        if any(i<0 or i>=len(hypotheses) or hypotheses[i]['status']=='rejected' for i in a.hypothesis_indices):raise ValueError('invalid or rejected hypothesis linkage')
        if redact(a.closure_evidence_required)!=a.closure_evidence_required:raise ValueError('sensitive action text')
    return {'status':'DRAFT_HUMAN_REVIEW_REQUIRED','approval_granted':False,'actions_executed':False,'review_sha256':plan.review_sha256,
        'accountability':plan.model_dump(mode='json'),'proposed_controls':controls,
        'next_skill':'operations-control-validation','handoff_requirements':['Human review causal hypotheses and proposed controls; this draft is not approval.', 'Construct existing ControlPlan with this review hash, selected control index, baseline/pilot cohorts and windows, outcome numerator/denominator, guardrail and fidelity metrics.', 'Record approval and implementation evidence, assess confounders; use bounded aggregates for evaluation. No error reduction is established here.']}
