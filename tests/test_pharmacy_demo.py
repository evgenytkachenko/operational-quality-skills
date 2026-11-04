import copy,json
import pytest
from operational_quality.pharmacy_demo import run_demo,load
from operational_quality.control_validation import digest

def test_complete_scripted_chain_and_hashes():
 a=run_demo();s=a['00-summary.json'];v=a['05-validation.json'];p=a['fictional-inputs.json']['scripted_plan']
 assert s['synthetic_demonstration'] and not s['actions_executed'] and not s['clinical_decisions_made']
 assert s['validation_recommendation']=='keep' and s['causal_attribution']=='NOT_ESTABLISHED'
 o=s['outcomes'][0];assert (o['baseline']['numerator'],o['baseline']['denominator'],o['pilot']['numerator'],o['pilot']['denominator'])==(84,700,28,700)
 assert o['observed_improvement_percentage_points']==8
 assert s['execution_counts']=={'success_recorded_within_window':7}
 assert p['rca_review_sha256']==digest(a['04-scripted-review.json'])==a['04-draft-proposal.json']['review_sha256']
 assert all(x['scope_sha256']==v['criteria_sha256'] for x in a['fictional-inputs.json']['coverage_register']['obligations'])
 assert all(digest(a[n])==h for n,h in s['artifact_hashes'].items())
 assert len(a['03-sample-mapping.json']['mapping'])==2
 assert len(a['03-evidence.json']['scope']['case_ids'])==2
 assert a['01-detection.json']['results'][0]['status']=='attention'

def test_missing_evidence_prevents_effectiveness_claim():
 a=run_demo('missing-evidence');s=a['00-summary.json']
 assert s['validation_recommendation']=='insufficient_evidence'
 assert s['execution_counts']=={'unknown':7}
 assert all(o['observed_improvement_percentage_points'] is None for o in s['outcomes'])
 assert not a['05-validation.json']['rollout_authorized']

class Client:
 def __init__(self):self.calls=[]
 def chat(self,**kwargs):
  self.calls.append(kwargs);draft=load('scripted_assessment');draft['controls'][0]['proposal']='Different unapproved fictional investigation proposal.'
  return {'message':{'content':json.dumps(draft)}}

def test_local_candidate_never_inherits_scripted_approval():
 c=Client();a=run_demo(model='fictional-installed:small',client=c)
 assert len(c.calls)==1 and c.calls[0]['options']['num_ctx']==16384
 assert 'Never assess clinical' in c.calls[0]['messages'][0]['content']
 candidate=a['03-local-candidate.json'];assert candidate['status']=='UNAPPROVED_CANDIDATE_ONLY'
 assert candidate['review']['assessment']['controls'][0]['proposal']!=a['04-scripted-review.json']['assessment']['controls'][0]['proposal']
 assert a['fictional-inputs.json']['scripted_plan']['rca_review_sha256']!=digest(candidate['review'])
 assert a['05-validation.json']['rca_review_sha256']==digest(a['04-scripted-review.json'])

def test_default_has_no_model_call(monkeypatch):
 def deny(*a,**k):raise AssertionError('no model')
 monkeypatch.setattr('operational_quality.pharmacy_demo.local_review',deny)
 assert not run_demo()['00-summary.json']['local_candidate_generated']

def test_changed_review_cannot_reuse_approval(monkeypatch):
 from operational_quality import pharmacy_demo as module
 original=module.load
 def altered(name):
  value=original(name)
  if name=='scripted_assessment':value['controls'][0]['proposal']='Different control with no approval.'
  return value
 monkeypatch.setattr(module,'load',altered)
 with pytest.raises(ValueError):run_demo()

def test_execution_scope_mismatch_rejected(monkeypatch):
 from operational_quality import pharmacy_demo as module
 original=module.load
 def altered(name):
  value=original(name)
  if name=='coverage_register':value['obligations'][0]['scope_sha256']='0'*64
  return value
 monkeypatch.setattr(module,'load',altered)
 with pytest.raises(ValueError):run_demo()

def test_unknown_scenario_and_cloud_model_rejected():
 with pytest.raises(ValueError):run_demo('unsupported')
 c=Client()
 with pytest.raises(ValueError):run_demo(model='model:cloud',client=c)
 assert not c.calls

def test_cli_private_reproducible_no_overwrite(tmp_path,monkeypatch):
 from operational_quality.pharmacy_demo import main
 out=tmp_path/'demo';args=['ops-pharmacy-demo','--output',str(out)]
 monkeypatch.setattr('sys.argv',args);main()
 assert (out/'START-HERE.md').exists() and out.stat().st_mode&0o777==0o700
 assert all(p.stat().st_mode&0o777==0o600 for p in out.iterdir())
 assert json.loads((out/'00-summary.json').read_text())==run_demo()['00-summary.json']
 with pytest.raises(SystemExit):main()
 args+=['--live-read']
 with pytest.raises(SystemExit):main()

def test_detection_precedes_proposal_and_pilot_review_deadline():
 from operational_quality.core import instant
 detection=load('detection_config');account=load('scripted_accountability');plan=load('scripted_plan')
 assert instant(detection['windows']['current']['end'])<=instant(account['prepared_at'])<=instant(plan['registered_at'])<instant(plan['approval']['approved_at'])<instant(plan['implemented_at'])<instant(plan['monitoring']['windows']['current']['start'])
 assert instant(account['actions'][0]['review_by'])>=instant(plan['monitoring']['windows']['current']['end'])
