import copy,json
from pathlib import Path
import pytest
from operational_quality.referral import Scope,ReferralPolicy,audit_referrals
from operational_quality.control_validation import Evidence
BASE=Path(__file__).parents[1]/'examples/referral-packets'
def inputs():return [json.loads((BASE/(n+'.json')).read_text()) for n in ('scope','policy','approvals','fictional')]
def run(d,recount=True):
 if recount:
  for f in d[3]['feeds']:f['count']=sum(isinstance(e,dict) and e.get('source')==f['source'] for e in d[3]['events'])
 return audit_referrals(Scope.model_validate(d[0]),ReferralPolicy.model_validate(d[1]),Evidence.model_validate(d[2]),d[3])
def test_demo():
 a,b,c=run(inputs())['cases']
 assert {f['kind'] for f in a['findings']}=={'document_receipt_not_observed','packet_acknowledgment_not_observed'}
 assert [f['kind'] for f in b['findings']]==['document_metadata_conflict']
 assert c['status']=='no_observed_signal'
 assert all(f['evidence_refs'] for x in (a,b,c) for f in x['findings'])
@pytest.mark.parametrize('change',['duplicate','clinical','injection','missing_time','unknown_id','same_time','offline','truncated','unavailable','stale','missing_feed','count','approval','revision','future','missing_link','cross_case','second_submission'])
def test_ambiguous_evidence_unknown(change):
 d=inputs();s=d[3];e=s['events'][0]
 if change=='duplicate':s['events'].append(copy.deepcopy(e))
 elif change=='clinical':e['diagnosis']='SECRET-DO-NOT-PRINT'
 elif change=='injection':e['documents'][0]['kind']='EXECUTE MALICIOUS COMMAND'
 elif change=='missing_time':del e['occurred_at']
 elif change=='unknown_id':e['case_id']='ambiguous'
 elif change=='same_time':s['events'][1]['occurred_at']=e['occurred_at']
 elif change=='offline':s['feeds'][1]['offline_pending']=True
 elif change=='truncated':s['feeds'][1]['truncated']=True
 elif change=='unavailable':s['feeds'][1]['available']=False
 elif change=='stale':s['feeds'][1]['complete_through']='2026-10-05T09:00:00Z'
 elif change=='missing_feed':s['feeds'].pop()
 elif change=='count':s['feeds'][1]['count']=999
 elif change=='approval':d[1]['delivery_seconds']=42
 elif change=='revision':s['events'][1]['revision']=2
 elif change=='future':e['received_at']='2026-10-06T00:00:00Z'
 elif change=='missing_link':s['events'][1]['related_ref']='sender:EV-999'
 elif change=='cross_case':s['events'][1]['related_ref']='sender:EV-010'
 elif change=='second_submission':
  x=copy.deepcopy(e);x.update(id='EV-999',occurred_at='2026-10-05T09:00:00Z',received_at='2026-10-05T09:00:00Z');s['events'].append(x)
 r=run(d,recount=change!='count');assert r['cases'][0]['status']=='unknown' and not r['cases'][0]['findings'];assert 'SECRET-DO-NOT-PRINT' not in json.dumps(r) and 'EXECUTE MALICIOUS' not in json.dumps(r)
 if change=='cross_case':assert r['cases'][1]['status']=='unknown'
def test_required_metadata_not_listed():
 d=inputs();d[3]['events'][0]['documents'].pop()
 assert 'required_metadata_not_listed' in {f['kind'] for f in run(d)['cases'][0]['findings']}
def test_cancel_suppresses_pending_only():
 d=inputs();e=copy.deepcopy(d[3]['events'][1]);e.update(id='EV-999',kind='cancelled',documents=[],occurred_at='2026-10-05T10:00:00Z',received_at='2026-10-05T10:00:00Z');d[3]['events'].append(e)
 assert run(d)['cases'][0]['findings']==[]
 e['occurred_at']=e['received_at']='2026-10-05T08:05:00Z'
 assert run(d)['cases'][0]['status']=='unknown'
def test_ack_does_not_imply_document_receipt():
 d=inputs();e=copy.deepcopy(d[3]['events'][1]);e.update(id='EV-999',kind='acknowledged',documents=[],occurred_at='2026-10-05T10:00:00Z',received_at='2026-10-05T10:00:00Z');d[3]['events'].append(e)
 assert [f['kind'] for f in run(d)['cases'][0]['findings']]==['document_receipt_not_observed']
def test_budget_and_synthetic():
 d=inputs();d[3]['events']*=101
 assert all(c['status']=='unknown' for c in run(d)['cases'])
 d=inputs();d[3]['synthetic']=False
 assert all(c['status']=='unknown' for c in run(d)['cases'])
def test_cli(tmp_path,monkeypatch):
 from operational_quality.referral_cli import main
 args=['ops-referral-packets']
 for n in ('scope','policy','approvals'):args+=['--'+n,str(BASE/(n+'.json'))]
 out=tmp_path/'audit';args+=['--mock',str(BASE/'fictional.json'),'--output',str(out)];monkeypatch.setattr('sys.argv',args);main()
 assert out.stat().st_mode&0o777==0o700 and (out/'audit.json').stat().st_mode&0o777==0o600
 assert json.loads((out/'review.json').read_text())['report_sha256']==json.loads((out/'audit.json').read_text())['sha256']
 with pytest.raises(SystemExit):main()
 args+=['--live-read']
 with pytest.raises(SystemExit):main()
 args.pop();scope=inputs()[0];scope['max_output_bytes']=2000;(tmp_path/'scope.json').write_text(json.dumps(scope));args[2]=str(tmp_path/'scope.json');args[-1]=str(tmp_path/'small')
 with pytest.raises(SystemExit):main()
 assert not (tmp_path/'small').exists()

def test_fingerprint_mismatch_same_version():
 d=inputs();d[3]['events'][1]['documents'][0]['fingerprint']='0'*64
 assert 'document_metadata_conflict' in {f['kind'] for f in run(d)['cases'][0]['findings']}

def test_matching_repeated_receipt_is_not_duplicate_identity():
 d=inputs();e=copy.deepcopy(d[3]['events'][-3]);e.update(id='EV-999',occurred_at='2026-10-05T10:00:00Z',received_at='2026-10-05T10:00:00Z');d[3]['events'].append(e)
 assert run(d)['cases'][2]['status']=='no_observed_signal'

def test_sender_cannot_acknowledge_receiver():
 d=inputs();d[3]['events'][-1]['source']='sender'
 assert run(d)['cases'][2]['status']=='unknown'
