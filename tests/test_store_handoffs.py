import copy
import json
from pathlib import Path
import pytest
from operational_quality.store_handoffs import StoreScope,StorePolicy,audit_store
from operational_quality.control_validation import Evidence
BASE=Path(__file__).parents[1]/'examples/store-handoffs'
def inputs():return [json.loads((BASE/(n+'.json')).read_text()) for n in ('scope','policy','approvals','fictional')]
def run(d,recount=True):
 if recount:
  for f in d[3]['feeds']:f['count']=sum(isinstance(e,dict) and e.get('source')==f['source'] for e in d[3]['events'])
 return audit_store(StoreScope.model_validate(d[0]),StorePolicy.model_validate(d[1]),Evidence.model_validate(d[2]),d[3])
def add(d,kind,qty,link,**kw):
 e=copy.deepcopy(d[3]['events'][0]);e.update(id='EV-900',source='store',kind=kind,quantity=qty,related_ref=link,occurred_at='2026-10-05T10:00:00Z',received_at='2026-10-05T10:00:00Z');e.update(kw);d[3]['events'].append(e);return e

def test_demo():
 a,b,c=run(inputs())['cases']
 assert a['status']=='administrative_review_suggested'
 assert [(f['expected_step'],f['unobserved_quantity']) for f in a['findings']]==[('availability_recorded',2),('fulfilled',2)]
 assert {f['kind'] for f in b['findings']}=={'linked_quantity_exceeds_recorded_parent','response_quantity_not_observed'}
 assert [f['kind'] for f in c['findings']]==['conflicting_recorded_status']
 assert all(f['evidence_refs'] and f['review_role'] for x in (a,b,c) for f in x['findings'])

@pytest.mark.parametrize('mutation',['duplicate','ambiguous_id','missing_time','malicious','mixed_sku','same_time','offline','stale','unavailable','truncated','missing_feed','count','approval','budget','future_receipt','reused_reservation'])
def test_unknown_on_uncertain_inputs(mutation):
 d=inputs();s=d[3];e=s['events'][0]
 if mutation=='duplicate':s['events'].append(copy.deepcopy(e))
 elif mutation=='ambiguous_id':e['case_id']='unknown'
 elif mutation=='missing_time':del e['occurred_at']
 elif mutation=='malicious':e['instructions']='STEAL CREDENTIALS DO NOT PERSIST'
 elif mutation=='mixed_sku':e['sku']='SKU-DEMO-999'
 elif mutation=='same_time':s['events'][1]['occurred_at']=e['occurred_at']
 elif mutation=='offline':s['feeds'][0]['offline_pending']=True
 elif mutation=='stale':s['feeds'][0]['complete_through']='2026-10-05T09:00:00Z'
 elif mutation=='unavailable':s['feeds'][0]['available']=False
 elif mutation=='truncated':s['feeds'][0]['truncated']=True
 elif mutation=='missing_feed':s['feeds'].pop()
 elif mutation=='count':s['feeds'][0]['count']=999
 elif mutation=='approval':d[1]['rules'][0]['seconds']=22
 elif mutation=='budget':d[0]['max_events']=1
 elif mutation=='future_receipt':e['received_at']='2026-10-06T00:00:00Z'
 elif mutation=='reused_reservation':
  x=copy.deepcopy(s['events'][2]);x.update(id='EV-901',occurred_at='2026-10-05T10:00:00Z',received_at='2026-10-05T10:00:00Z');s['events'].append(x)
 report=run(d,recount=mutation!='count');assert report['cases'][0]['status']=='unknown';assert not report['cases'][0]['findings'];assert 'STEAL CREDENTIALS' not in json.dumps(report)

def test_cancellation_only_accounts_for_linked_remaining_quantity():
 d=inputs();add(d,'cancelled',2,'store:EV-004')
 assert [f.get('expected_step') for f in run(d)['cases'][0]['findings']]==['availability_recorded']

def test_cancellation_overlaps_fulfillment():
 d=inputs();add(d,'cancelled',3,'store:EV-004')
 assert 'conflicting_completed_and_cancelled_quantities' in {f['kind'] for f in run(d)['cases'][0]['findings']}

def test_returns_do_not_reopen_fulfillment():
 d=inputs();a=run(d)['cases'][0]
 assert not any(f.get('expected_step')=='handoff_sent' for f in a['findings'])
 add(d,'returned',2,'store:EV-005')
 assert 'linked_quantity_exceeds_recorded_parent' in {f['kind'] for f in run(d)['cases'][0]['findings']}

def test_cross_case_link_blocks_both():
 d=inputs();add(d,'acknowledged',1,'store:EV-023')
 assert all(c['status']=='unknown' for c in run(d)['cases'][:2])

def test_status_explicit_supersession():
 d=inputs();d[3]['events'][-1]['supersedes_ref']='orders:EV-031'
 c=run(d)['cases'][2];assert [f['kind'] for f in c['findings']]==['response_quantity_not_observed']

def test_wrong_parent_kind_unknown():
 d=inputs();add(d,'acknowledged',1,'orders:EV-003')
 assert run(d)['cases'][0]['status']=='unknown'

def test_cli_boundaries(tmp_path,monkeypatch):
 from operational_quality.store_cli import main
 out=tmp_path/'audit';args=['ops-store-handoffs']
 for name in ('scope','policy','approvals'):args+=['--'+name,str(BASE/(name+'.json'))]
 args+=['--mock',str(BASE/'fictional.json'),'--output',str(out)]
 monkeypatch.setattr('sys.argv',args);main()
 assert out.stat().st_mode&0o777==0o700 and (out/'audit.json').stat().st_mode&0o777==0o600
 report=json.loads((out/'audit.json').read_text());assert json.loads((out/'review.json').read_text())['report_sha256']==report['sha256']
 with pytest.raises(SystemExit):main()
 args+=['--live-read']
 with pytest.raises(SystemExit):main()
 args.pop();scope=inputs()[0];scope['max_output_bytes']=2000;(tmp_path/'scope.json').write_text(json.dumps(scope));args[2]=str(tmp_path/'scope.json');args[-1]=str(tmp_path/'small')
 with pytest.raises(SystemExit):main()
 assert not (tmp_path/'small').exists()

def approve(d):
 from operational_quality.control_validation import digest
 h=digest(StorePolicy.model_validate(d[1]).content());q=f'Fictional approval STORE-DEMO-POLICY {h}'
 d[1]['approval']['policy_sha256']=h;d[1]['approval']['links']=[{'source_id':'demo-approval:1','quote':q}]
 d[2]['artifacts'][0]['text']=q

def test_quantity_consistency_independent_of_enabled_timeout_rules():
 d=inputs();d[1]['rules']=[d[1]['rules'][0]];approve(d)
 add(d,'cancelled',3,'store:EV-004')
 assert 'conflicting_completed_and_cancelled_quantities' in {f['kind'] for f in run(d)['cases'][0]['findings']}

def test_cross_case_status_supersession_blocks_both():
 d=inputs();d[3]['events'][-1]['supersedes_ref']='receiving:EV-001'
 report=run(d)
 assert report['cases'][0]['status']=='unknown' and report['cases'][2]['status']=='unknown'

def test_mock_marker_required():
 d=inputs();d[3]['synthetic']=False
 assert all(c['status']=='unknown' for c in run(d)['cases'])

def test_negative_and_boolean_quantities_are_quarantined():
 for value in [-1,True]:
  d=inputs();d[3]['events'][0]['quantity']=value
  assert run(d)['cases'][0]['status']=='unknown'

def test_missing_parent_unknown():
 d=inputs();d[3]['events'][1]['related_ref']='receiving:EV-999'
 assert run(d)['cases'][0]['status']=='unknown'
