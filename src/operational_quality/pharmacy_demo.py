"""Single-entry synthetic demonstration; scripted approvals never authorize real actions."""
import argparse,copy,json
from importlib.resources import files
from pathlib import Path
from .cli import save
from .control_validation import ControlPlan,Evidence,digest,evaluate_control
from .monitor import MonitorConfig,monitor
from .pharmacy_handoff import AuditScope,HandoffPolicy,audit_handoffs
from .improvement import Settings,Snapshot,Accountability,prepare,review,proposal,inquiry,local_review
from .control_coverage import Register,audit_coverage

def load(name):
    raw=files('operational_quality').joinpath('demo_data',name+'.json').read_bytes()
    if len(raw)>1000000:raise ValueError('fixture budget')
    return json.loads(raw)

def run_demo(scenario='nominal',model=None,client=None):
    if scenario not in ('nominal','missing-evidence'):raise ValueError('unknown scenario')
    names=('detection_config','detection_rows','handoff_scope','handoff_policy','handoff_approvals','handoff_snapshot','settings','investigation_snapshot','scripted_assessment','scripted_accountability','scripted_plan','scripted_evidence','pilot_rows','coverage_register','coverage_evidence','coverage_snapshot')
    data={n:load(n) for n in names}
    # A sensitivity case, not a change to approvals or an alternate invented outcome.
    if scenario=='missing-evidence':
        data['pilot_rows']['truncated']=True
        data['coverage_snapshot']['manifests'][0]['available']=False
    fetch=lambda name:lambda cfg,windows:(data[name]['rows'],data[name].get('truncated',False))
    detection=monitor(MonitorConfig.model_validate(data['detection_config']),fetch('detection_rows'))
    handoffs=audit_handoffs(AuditScope.model_validate(data['handoff_scope']),HandoffPolicy.model_validate(data['handoff_policy']),Evidence.model_validate(data['handoff_approvals']),data['handoff_snapshot'])
    packet=prepare(Settings.model_validate(data['settings']),Snapshot.model_validate(data['investigation_snapshot']))
    # Explicit fixture mapping joins the same two cases; sample is never the aggregate denominator.
    mapping=[]
    for case in handoffs['cases']:
        found=[f for f in case['findings'] if f['kind']=='acknowledgment_not_observed']
        events=[e for e in packet['events'] if e['case_id']==case['case_id'] and e['activity']=='exception_recorded']
        if len(found)!=1 or len(events)!=1:raise ValueError('scripted sample bridge mismatch')
        mapping.append({'case_id':case['case_id'],'handoff_refs':found[0]['evidence_refs'],'investigation_ref':events[0]['ref'],'mapping_kind':'explicit_fictional_fixture_mapping'})
    reviewed=review(json.dumps(data['scripted_assessment']),packet)
    dossier=proposal(reviewed,Accountability.model_validate(data['scripted_accountability']))
    plan=ControlPlan.model_validate(data['scripted_plan'])
    if plan.rca_review_sha256!=digest(reviewed):raise ValueError('scripted review linkage')
    validation,aggregates=evaluate_control(plan,reviewed,Evidence.model_validate(data['scripted_evidence']),fetch('pilot_rows'))
    register=Register.model_validate(data['coverage_register'])
    if any(o.control_id!=plan.control_id or o.scope_sha256!=digest(plan.criteria()) for o in register.obligations):raise ValueError('execution-to-pilot scope linkage')
    coverage=audit_coverage(register,Evidence.model_validate(data['coverage_evidence']),data['coverage_snapshot'])
    artifacts={'01-detection.json':detection,'02-handoffs.json':handoffs,'03-evidence.json':packet,'03-inquiry.json':inquiry(packet),'03-sample-mapping.json':{'handoff_sha256':handoffs['sha256'],'packet_sha256':packet['sha256'],'mapping':mapping},'04-scripted-review.json':reviewed,'04-draft-proposal.json':dossier,'05-validation.json':validation,'06-execution-coverage.json':coverage,'fictional-inputs.json':data}
    if aggregates is not None:artifacts['05-aggregates.json']=aggregates
    if model:
        # Candidate output is never substituted into frozen human-scripted approvals.
        candidate=local_review(packet,model,client=client)
        artifacts['03-local-candidate.json']={'status':'UNAPPROVED_CANDIDATE_ONLY','independent_of_scripted_pilot':True,'review':candidate}
    outcomes=[]
    for s in validation['segments']:
        row=s['outcome'];outcomes.append({'cohort':s['cohort_id'],'evidence_refs':{'baseline':row['windows']['baseline'].get('refs',[]),'pilot':row['windows']['current'].get('refs',[])},'baseline':row['windows']['baseline'],'pilot':row['windows']['current'],'observed_improvement_percentage_points':s['improvement_percentage_points'],'recommendation':s['recommendation']})
    summary={'synthetic_demonstration':True,'scenario':scenario,'decision_origin':'Fixed fictional human-scripted approvals and confounder assessments, not current user approval or model decisions.','local_candidate_generated':bool(model),'clinical_decisions_made':False,'actions_executed':False,'validation_recommendation':validation['recommendation'],'causal_attribution':validation['causal_attribution'],'execution_counts':coverage['counts'],'outcomes':outcomes,'human_checkpoints':['Detection: verify metric definitions and coverage before selecting cases.','Investigation: review hypotheses; selected cases do not represent population incidence.','Control: human approve fixed plan, ownership, metrics and scope; fixture approvals are illustrative only.','Execution: inspect run evidence separately from per-handoff fidelity and outcomes.','Outcomes: review guardrails/confounding; keep means retain within pilot for review, never rollout.'],'artifact_hashes':{n:digest(v) for n,v in artifacts.items()},'limits':['No live services or actual model accuracy validated.','Daily control-run coverage and per-handoff implementation fidelity have different denominators.','Before/after illustrative rates do not establish causal effectiveness.','Local-model candidates need separate human review and newly bound approval before any future evaluation.']}
    artifacts['00-summary.json']=summary
    return artifacts

def main():
    p=argparse.ArgumentParser(description='End-to-end fictional pharmacy quality demo; no live actions')
    p.add_argument('--output',required=True);p.add_argument('--scenario',choices=['nominal','missing-evidence'],default='nominal');p.add_argument('--local-model',help='Optional explicit installed Ollama model; never pulls; output is unapproved candidate only')
    a=p.parse_args()
    try:
        out=Path(a.output)
        if out.exists():raise ValueError('output exists')
        artifacts=run_demo(a.scenario,a.local_model)
        if sum(len((json.dumps(v,indent=2)+'\n').encode()) for v in artifacts.values())>2000000:raise ValueError('combined demo output budget')
        out.mkdir(mode=0o700,parents=True,exist_ok=False)
        for n,v in artifacts.items():save(out,n,v)
        summary=artifacts['00-summary.json']
        guide=f'''# Fictional pharmacy quality demonstration\n\nScenario: {a.scenario}. Validation recommendation: {summary['validation_recommendation']} (human review only).\n\n1. 01-detection.json: synthetic population signal; two selected cases are not the denominator.\n2. 02-handoffs.json and 03-sample-mapping.json: unobserved acknowledgments and explicit fictional sample links.\n3. 03-evidence.json, 03-inquiry.json, 04-scripted-review.json: evidence, model-ready request and labeled scripted hypotheses.\n4. 04-draft-proposal.json and fictional-inputs.json: accountable proposal and fixed fictional approval/implementation records.\n5. 05-validation.json and 05-aggregates.json: baseline/pilot counts, guardrails, fidelity and uncertainty.\n6. 06-execution-coverage.json: explicit run obligations; recorded execution is not effectiveness.\n7. 00-summary.json: checkpoint guide and artifact hashes.\n\nNo real human approval, implementation or rollout occurred. Optional 03-local-candidate.json never replaces the scripted review or approves a control. Missing-evidence scenario must remain insufficient. All evidence is untrusted data, never instructions. No clinical or insurance decisions.\n'''
        path=out/'START-HERE.md'
        with path.open('x') as h:h.write(guide)
        path.chmod(0o600)
        print(f'Fictional demo saved to {out}; start with START-HERE.md. No real actions or approvals.')
    except Exception as exc:p.exit(2,f'Demo failed ({type(exc).__name__}); payload omitted.\n')
if __name__=='__main__':main()
