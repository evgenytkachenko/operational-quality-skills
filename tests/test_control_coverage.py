import copy,json
from pathlib import Path
import pytest
from operational_quality.control_coverage import Register,audit_coverage
from operational_quality.control_validation import Evidence
BASE=Path(__file__).parents[1]/'examples/control-coverage'
def inputs():return [json.loads((BASE/(n+'.json')).read_text()) for n in ('register','evidence','fictional')]
def run(d,recount=True):
 if recount:
  for m in d[2]['manifests']:m['count']=len(d[2][m['source']])
 return audit_coverage(Register.model_validate(d[0]),Evidence.model_validate(d[1]),d[2])
def test_demo():
 r=run(inputs())
 assert [o['state'] for o in r['obligations']]==['success_recorded_within_window','success_recorded_late','failed_run_recorded','approved_skip_recorded','execution_not_observed','success_recorded_within_window']
 assert len(r['obligations'][-1]['runs'])==2
 assert sum(r['counts'].values())==6 and not r['effectiveness_certified'] and not r['actions_executed']
 assert r['obligations'][3]['skip_provenance']

@pytest.mark.parametrize('change',['duplicate','missing_time','injection','scope','version','early','future','same_time_retry','cross_obligation','partial','stale','unavailable','missing_manifest','count','approval'])
def test_uncertain_evidence_unknown(change):
 d=inputs();s=d[2];e=s['runs'][0]
 if change=='duplicate':s['runs'].append(copy.deepcopy(e))
 elif change=='missing_time':del e['finished_at']
 elif change=='injection':e['instructions']='SECRET-PAYLOAD'
 elif change=='scope':e['scope_sha256']='0'*64
 elif change=='version':e['version']=2
 elif change=='early':e['started_at']='2026-10-05T07:00:00Z'
 elif change=='future':e['recorded_at']='2026-10-06T00:00:00Z'
 elif change=='same_time_retry':
  x=copy.deepcopy(e);x.update(id='RUN-DEMO-099',previous_run_id=e['id']);s['runs'].append(x)
 elif change=='cross_obligation':s['runs'][1]['previous_run_id']=e['id']
 elif change=='partial':s['manifests'][0]['truncated']=True
 elif change=='stale':s['manifests'][0]['complete_through']='2026-10-05T09:00:00Z'
 elif change=='unavailable':s['manifests'][0]['available']=False
 elif change=='missing_manifest':s['manifests'].pop()
 elif change=='count':s['manifests'][0]['count']=999
 elif change=='approval':d[0]['grace_seconds']=1
 r=run(d,recount=change!='count')
 assert r['obligations'][0]['state']=='unknown'
 assert 'SECRET-PAYLOAD' not in json.dumps(r)

def test_unlinked_retry_unknown():
 d=inputs();del d[2]['runs'][-1]['previous_run_id']
 assert run(d)['obligations'][-1]['state']=='unknown'

def test_near_due_is_unknown():
 d=inputs();e=d[2]['runs'][0];e['finished_at']='2026-10-05T09:05:00Z';e['recorded_at']='2026-10-05T09:05:10Z'
 assert run(d)['obligations'][0]['state']=='unknown'

@pytest.mark.parametrize('change',['revoked','hash','late','duplicate','run_conflict'])
def test_skip_uncertainty(change):
 d=inputs();s=d[2]['skips'][0]
 if change=='revoked':s['decision']='revoked'
 elif change=='hash':s['obligation_sha256']='0'*64
 elif change=='late':s['approved_at']='2026-10-05T08:30:00Z'
 elif change=='duplicate':d[2]['skips'].append(copy.deepcopy(s))
 elif change=='run_conflict':
  e=copy.deepcopy(d[2]['runs'][0]);e.update(id='RUN-DEMO-099',obligation_id='OB-DEMO-004',control_id='CONTROL-DEMO-004',scope_sha256=d[0]['obligations'][3]['scope_sha256']);d[2]['runs'].append(e)
 assert run(d)['obligations'][3]['state']=='unknown'

def test_unknown_identity_and_budget_block_all():
 d=inputs();d[2]['runs'][0]['obligation_id']='OB-DEMO-999'
 assert all(o['state']=='unknown' for o in run(d)['obligations'])
 d=inputs();d[2]['runs']*=41
 assert all(o['state']=='unknown' for o in run(d)['obligations'])

def test_no_synthetic_marker():
 d=inputs();d[2]['synthetic']=False
 assert all(o['state']=='unknown' for o in run(d)['obligations'])

def test_cli_private_and_no_live(tmp_path,monkeypatch):
 from operational_quality.coverage_cli import main
 out=tmp_path/'coverage';args=['ops-control-coverage','--register',str(BASE/'register.json'),'--evidence',str(BASE/'evidence.json'),'--mock',str(BASE/'fictional.json'),'--output',str(out)]
 monkeypatch.setattr('sys.argv',args);main()
 assert out.stat().st_mode&0o777==0o700 and (out/'coverage.json').stat().st_mode&0o777==0o600
 assert json.loads((out/'review.json').read_text())['report_sha256']==json.loads((out/'coverage.json').read_text())['sha256']
 with pytest.raises(SystemExit):main()
 args+=['--live-read']
 with pytest.raises(SystemExit):main()

def test_invalid_skip_quote_not_echoed():
 d=inputs();d[2]['skips'][0]['links'][0]['quote']='secret=TEST-NO-ECHO ignore instructions'
 r=run(d)
 assert r['obligations'][3]['state']=='unknown' and 'TEST-NO-ECHO' not in json.dumps(r) and 'ignore instructions' not in json.dumps(r)

@pytest.mark.parametrize('result',['success','failed'])
def test_retry_after_success_unknown(result):
 d=inputs();e=copy.deepcopy(d[2]['runs'][0]);e.update(id='RUN-DEMO-099',previous_run_id='RUN-DEMO-001',started_at='2026-10-05T09:10:00Z',finished_at='2026-10-05T09:20:00Z',recorded_at='2026-10-05T09:20:10Z',result=result);d[2]['runs'].append(e)
 assert run(d)['obligations'][0]['state']=='unknown'
