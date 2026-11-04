import copy,json
from pathlib import Path
import pytest
from operational_quality.improvement import Settings,Snapshot,Accountability,prepare,review,local_review,proposal
from operational_quality.control_validation import digest
BASE=Path(__file__).parents[1]/'examples/pharmacy-improvement'
def inputs():return [json.loads((BASE/(n+'.json')).read_text()) for n in ('settings','fictional','assessment','accountability')]
def packet(d):return prepare(Settings.model_validate(d[0]),Snapshot.model_validate(d[1]))
def test_end_to_end_draft():
 d=inputs();p=packet(d);r=review(json.dumps(d[2]),p);result=proposal(r,Accountability.model_validate(d[3]))
 assert p['selected_case_patterns'][0]['distinct_cases']==2
 assert result['status']=='DRAFT_HUMAN_REVIEW_REQUIRED' and not result['approval_granted'] and not result['actions_executed']
 assert result['next_skill']=='operations-control-validation'
 assert r['semantic_support']=='UNVERIFIED'

@pytest.mark.parametrize('change',['partial','duplicate','out_of_scope','order','missing_case'])
def test_uncertain_selection_suppresses_inquiry(change):
 d=inputs()
 if change=='partial':d[1]['complete']=False
 elif change=='duplicate':d[1]['events'].append(copy.deepcopy(d[1]['events'][0]))
 elif change=='out_of_scope':d[1]['events'][0]['case_id']='RX-DEMO-999'
 elif change=='order':d[1]['events'][1]['timestamp']=d[1]['events'][0]['timestamp']
 elif change=='missing_case':d[1]['events']=d[1]['events'][:3]
 p=packet(d);assert not p['events'] and not p['selected_case_patterns']
 with pytest.raises(ValueError):review(json.dumps(d[2]),p)
 a=d[2];a['observations']=[];a['controls']=[]
 for h in a['hypotheses']:h.update(status='unknown',supporting=[],contradicting=[])
 assert review(json.dumps(a),p)['review_status']=='HUMAN_REVIEW_REQUIRED'

def test_recurrence_counts_cases_not_events():
 d=inputs();e=copy.deepcopy(d[1]['events'][1]);e.update(id='EV-099',timestamp='2026-10-05T11:00:00Z');d[1]['events'].append(e)
 assert packet(d)['selected_case_patterns'][0]['distinct_cases']==2

def test_schema_blocks_raw_instructions_and_phi():
 for key in ('diagnosis','instructions','patient_name'):
  d=inputs();d[1]['events'][0][key]='DO NOT COPY'
  with pytest.raises(ValueError):packet(d)

@pytest.mark.parametrize('change',['quote','invented_source','duplicate_hypothesis','sensitive_text'])
def test_assessment_validation(change):
 d=inputs();p=packet(d)
 if change=='quote':d[2]['observations'][0]['links'][0]['quote']='not in evidence'
 elif change=='invented_source':d[2]['observations'][0]['links'][0]['source_id']='invented'
 elif change=='duplicate_hypothesis':d[2]['hypotheses'][1]['explanation']=d[2]['hypotheses'][0]['explanation']
 elif change=='sensitive_text':d[2]['unknowns']=['secret=sample-credential']
 with pytest.raises(ValueError):review(json.dumps(d[2]),p)

@pytest.mark.parametrize('change',['hash','index','owner','deadline','hypothesis','rejected'])
def test_accountability_binding(change):
 d=inputs();p=packet(d)
 if change=='rejected':d[2]['hypotheses'][0]['status']='rejected'
 r=review(json.dumps(d[2]),p);d[3]['review_sha256']=digest(r)
 if change=='hash':d[3]['review_sha256']='0'*64
 elif change=='index':d[3]['actions'][0]['control_index']=3
 elif change=='owner':d[3]['actions'][0]['owner_role']='intake_lead'
 elif change=='deadline':d[3]['actions'][0]['review_by']=d[3]['prepared_at']
 elif change=='hypothesis':d[3]['actions'][0]['hypothesis_indices']=[-1]
 with pytest.raises(ValueError):proposal(r,Accountability.model_validate(d[3]))

class MockClient:
 def __init__(self,assessment):self.raw=json.dumps(assessment);self.calls=[]
 def chat(self,**kwargs):self.calls.append(kwargs);return {'message':{'content':self.raw}}

def test_optional_local_adapter_one_bounded_call():
 d=inputs();p=packet(d);client=MockClient(d[2]);r=local_review(p,'fictional-installed:small',client)
 assert r['semantic_support']=='UNVERIFIED' and len(client.calls)==1
 call=client.calls[0]
 assert call['stream'] is False and call['options']['num_ctx']==16384 and call['options']['num_predict']==3000
 assert 'tools' not in call

def test_local_rejects_cloud_tampered_or_oversized_before_call():
 d=inputs();client=MockClient(d[2]);p=packet(d)
 for model in ('example:cloud','example-cloud',''):
  with pytest.raises(ValueError):local_review(p,model,client)
 bad=copy.deepcopy(p);bad['limitations'].append('tampering')
 with pytest.raises(ValueError):local_review(bad,'local',client)
 bad['limitations'].append('x'*16001)
 with pytest.raises(ValueError):local_review(bad,'local',client)
 assert not client.calls

def test_mock_server_invalid_output_and_unavailable():
 d=inputs();p=packet(d);client=MockClient(d[2]);client.raw='x'*100001
 with pytest.raises(ValueError):local_review(p,'local',client)
 client.raw='not json'
 with pytest.raises(ValueError):local_review(p,'local',client)


def test_cli_no_model_by_default_and_private_dossier(tmp_path,monkeypatch):
 from operational_quality.improvement_cli import main
 def deny(*args,**kwargs):raise AssertionError('model must not be called')
 monkeypatch.setattr('operational_quality.improvement_cli.local_review',deny)
 out=tmp_path/'review';args=['ops-improvement','--settings',str(BASE/'settings.json'),'--mock',str(BASE/'fictional.json'),'--assessment',str(BASE/'assessment.json'),'--accountability',str(BASE/'accountability.json'),'--output',str(out)]
 monkeypatch.setattr('sys.argv',args);main()
 assert (out/'proposal.json').exists() and out.stat().st_mode&0o777==0o700
 assert (out/'review.json').stat().st_mode&0o777==0o600
 with pytest.raises(SystemExit):main()

def test_trusted_domain_boundary_for_host_and_local():
 from operational_quality.improvement import inquiry,PHARMACY_SYSTEM
 d=inputs();p=packet(d);client=MockClient(d[2]);local_review(p,'local',client)
 assert client.calls[0]['messages'][0]['content']==inquiry(p)['system']==PHARMACY_SYSTEM
 assert 'Never assess clinical' in PHARMACY_SYSTEM
