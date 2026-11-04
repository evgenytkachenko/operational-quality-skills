"""Regenerate ONLY fictional packaged demonstration fixtures; never real approval records."""
import copy,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from operational_quality.control_validation import digest,ControlPlan
from operational_quality.improvement import Settings,Snapshot,prepare,review
from operational_quality.pharmacy_handoff import HandoffPolicy
from operational_quality.control_coverage import Register
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'src/operational_quality/demo_data'
def read(p):return json.loads((ROOT/p).read_text())
def write(n,v):(out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
# Same fictional two-case handoff issue; no clinical, PA or medication fields.
scope=read('examples/pharmacy-handoff/scope.json');scope['case_ids']=scope['case_ids'][:2]
policy=read('examples/pharmacy-handoff/policy.json');approval=read('examples/pharmacy-handoff/approvals.json')
rows=[]
for n in (1,2):
 for j,kind in enumerate(('intake_received','handoff_sent')):
  e=dict(id=f'EV-{n*10+j:03d}',source='intake_feed',case_id=f'RX-DEMO-{n:03d}',episode_id='EP-01',occurred_at=f'2026-10-05T08:{j*10:02d}:00Z',received_at=f'2026-10-05T08:{j*10:02d}:00Z',kind=kind,queue='intake')
  if j:e.update(to_queue='pharmacy',owner_role='pharmacy_team')
  rows.append(e)
feeds=[dict(source=s,scope_case_ids=scope['case_ids'],complete_through=scope['as_of'],available=True,truncated=False,event_count=sum(e['source']==s for e in rows),clock_uncertainty_seconds=1) for s in ('intake_feed','pa_feed','pharmacy_feed')]
for n,v in [('handoff_scope',scope),('handoff_policy',policy),('handoff_approvals',approval),('handoff_snapshot',dict(synthetic=True,feeds=feeds,events=rows))]:write(n,v)
settings=read('examples/pharmacy-improvement/settings.json');snapshot=read('examples/pharmacy-improvement/fictional.json');snapshot['events']=[e for e in snapshot['events'] if e['activity']!='exception_resolved']
for e in snapshot['events']:
 e['timestamp']='2026-10-05T08:10:00Z' if e['activity']=='handoff_sent' else '2026-10-05T11:00:00Z'
assessment=read('examples/pharmacy-improvement/assessment.json');assessment['observations'][0]['claim']='Two selected fictional cases contain recorded acknowledgment exceptions; actual acknowledgment occurrence is unverified.';assessment['observations'][0]['links']=assessment['observations'][0]['links'][:2]
packet=prepare(Settings.model_validate(settings),Snapshot.model_validate(snapshot));reviewed=review(json.dumps(assessment),packet)
account=read('examples/pharmacy-improvement/accountability.json');account['review_sha256']=digest(reviewed);account['prepared_at']='2026-10-08T06:00:00Z';account['actions'][0]['review_by']='2026-10-17T00:00:00Z'
for n,v in [('settings',settings),('investigation_snapshot',snapshot),('scripted_assessment',assessment),('scripted_accountability',account)]:write(n,v)
# Explicit population aggregates; selected case sample is not the denominator.
metric=lambda id,role,threshold,worse='higher':dict(id=id,definition_version='v1',role=role,worse=worse,threshold=threshold,min_change=.05)
metrics=[metric('ack_exceptions','outcome',.08),metric('late_handoffs','guardrail',.10),metric('check_applied','guardrail',.95,'lower')]
windows=dict(baseline=dict(start='2026-10-01T00:00:00Z',end='2026-10-08T00:00:00Z'),current=dict(start='2026-10-09T00:00:00Z',end='2026-10-16T00:00:00Z'))
monitoring=dict(metrics=metrics,cohorts=['pharmacy_standard'],windows=windows)
def aggregates(wins,values):
 result=[]
 for label,w in wins.items():
  start=datetime.fromisoformat(w['start'].replace('Z','+00:00'))
  for m,val in values[label].items():
   for day in range(7):
    a=start+timedelta(days=day);b=a+timedelta(days=1)
    result.append(dict(id=f'{m}-{a.date()}',metric_id=m,cohort_id='pharmacy_standard',bucket_start=a.isoformat(),bucket_end=b.isoformat(),numerator=val,denominator=100,missing=0,definition_version='v1',population_complete=True,finalized=True))
 return dict(rows=result,truncated=False)
detection=dict(metrics=metrics[:2],cohorts=['pharmacy_standard'],windows=dict(baseline=dict(start='2026-09-24T00:00:00Z',end='2026-10-01T00:00:00Z'),current=windows['baseline']))
write('detection_config',detection);write('detection_rows',aggregates(detection['windows'],dict(baseline=dict(ack_exceptions=2,late_handoffs=3),current=dict(ack_exceptions=12,late_handoffs=3))))
write('pilot_rows',aggregates(windows,dict(baseline=dict(ack_exceptions=12,late_handoffs=3,check_applied=0),current=dict(ack_exceptions=4,late_handoffs=3,check_applied=98))))
plan=read('examples/control-validation/plan.json');plan.update(control_id='CONTROL-DEMO-001',rca_reference='demo:scripted-review',rca_review_sha256=digest(reviewed),proposal=reviewed['assessment']['controls'][0]['proposal'],monitoring=monitoring,pilot_cohorts=['pharmacy_standard'],outcome_metric='ack_exceptions',guardrail_metrics=['late_handoffs'],fidelity_metric='check_applied')
claim='FICTIONAL SCRIPT: CONTROL-DEMO-001 administrative acknowledgment check enabled for pharmacy_standard at 2026-10-08T12:00:00Z.'
plan['implementation_claim']=claim;plan['implementation_links']=[dict(source_id='demo:implementation',quote=claim)]
artifacts=[dict(ref='demo:implementation',kind='implementation',text=claim)]
for c in plan['confounders']:
 q=f"FICTIONAL SCRIPT: reviewer assessed {c['domain']} as not material for this illustrative pharmacy pilot; residual confounding is possible."
 c.update(explanation=q,links=[dict(source_id='demo:'+c['domain'],quote=q)]);artifacts.append(dict(ref='demo:'+c['domain'],kind='context',text=q))
plan['approval']=None
p=ControlPlan.model_validate(plan);criteria=digest(p.criteria());q=f'FICTIONAL SCRIPT: approved pilot CONTROL-DEMO-001 under criteria {criteria}; this is illustrative approval, not user authorization.'
plan['approval']=dict(control_id='CONTROL-DEMO-001',decision='approved_pilot',approver_role='Fictional operations quality owner',approved_at='2026-10-08T09:00:00Z',pilot_cohorts=['pharmacy_standard'],window=windows['current'],criteria_sha256=criteria,links=[dict(source_id='demo:pilot-approval',quote=q)])
artifacts.append(dict(ref='demo:pilot-approval',kind='approval',text=q));write('scripted_plan',plan);write('scripted_evidence',dict(artifacts=artifacts))
# Daily execution obligations refer to the exact pilot criteria; no schedules are created.
obs=[];runs=[]
for d in range(7):
 date=f'2026-10-{9+d:02d}';oid=f'OB-DEMO-{d+1:03d}'
 obs.append(dict(id=oid,control_id='CONTROL-DEMO-001',version=1,scope_sha256=criteria,earliest_start=date+'T08:00:00Z',due=date+'T09:00:00Z',owner_role='operations_quality'))
 runs.append(dict(id=f'RUN-DEMO-{d+1:03d}',obligation_id=oid,control_id='CONTROL-DEMO-001',version=1,scope_sha256=criteria,started_at=date+'T08:10:00Z',finished_at=date+'T08:20:00Z',recorded_at=date+'T08:21:00Z',result='success'))
register=dict(synthetic=True,version=1,start=windows['current']['start'],as_of=windows['current']['end'],grace_seconds=300,max_feed_lag_seconds=600,obligations=obs)
r=Register.model_validate(register);q=f'FICTIONAL SCRIPT: approved CONTROL-DEMO-REGISTER {digest(r.content())} for seven explicit checks, not an executable schedule.'
register['approval']=dict(decision='approved',approved_at='2026-10-08T09:00:00Z',policy_sha256=digest(r.content()),links=[dict(source_id='demo:register',quote=q)])
write('coverage_register',register);write('coverage_evidence',dict(artifacts=[dict(ref='demo:register',kind='approval',text=q)]))
write('coverage_snapshot',dict(synthetic=True,runs=runs,skips=[],manifests=[dict(source=s,obligation_ids=[o['id'] for o in obs],complete_from=register['start'],complete_through=register['as_of'],available=True,truncated=False,count=7 if s=='runs' else 0,clock_uncertainty_seconds=1) for s in ('runs','skips')]))
