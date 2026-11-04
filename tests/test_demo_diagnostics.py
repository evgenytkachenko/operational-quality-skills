import json
import pytest
from operational_quality.pharmacy_demo import run_demo
from operational_quality.demo_review import verify_directory,VerificationError,main

def directory(tmp_path):
 d=tmp_path/'demo';d.mkdir()
 for n,v in run_demo().items():(d/n).write_text(json.dumps(v))
 return d

@pytest.mark.parametrize('change,code,artifact',[
 ('missing','MISSING_FILE','03-evidence.json'),('malformed','INVALID_JSON','03-evidence.json'),
 ('summary_type','INVALID_SUMMARY','00-summary.json'),('duplicate_key','INVALID_JSON','00-summary.json'),
 ('nan','INVALID_JSON','03-evidence.json'),('symlink','UNSAFE_FILE','03-evidence.json'),
 ('oversize','FILE_BUDGET','03-evidence.json'),('extra','UNEXPECTED_FILE',None),
 ('changed','SCRIPTED_MISMATCH','05-validation.json'),('summary_changed','SUMMARY_MISMATCH','00-summary.json'),
 ('report_changed','REPORT_MISMATCH','REPORT.md')])
def test_specific_payload_safe_diagnostics(tmp_path,change,code,artifact):
 d=directory(tmp_path)
 if change=='missing':(d/'03-evidence.json').unlink()
 elif change=='malformed':(d/'03-evidence.json').write_text('secret=SENSITIVE-PAYLOAD')
 elif change=='summary_type':(d/'00-summary.json').write_text('[]')
 elif change=='duplicate_key':(d/'00-summary.json').write_text('{"scenario":"nominal","scenario":"missing-evidence"}')
 elif change=='nan':(d/'03-evidence.json').write_text('{"value":NaN}')
 elif change=='symlink':
  (d/'03-evidence.json').unlink();(d/'03-evidence.json').symlink_to(tmp_path/'SENSITIVE-PAYLOAD')
 elif change=='oversize':(d/'03-evidence.json').write_text('x'*1000001)
 elif change=='extra':(d/'SENSITIVE-PAYLOAD.json').write_text('sensitive')
 elif change=='changed':
  x=json.loads((d/'05-validation.json').read_text());x['recommendation']='SENSITIVE-PAYLOAD';(d/'05-validation.json').write_text(json.dumps(x))
 elif change=='summary_changed':
  x=json.loads((d/'00-summary.json').read_text());x['validation_recommendation']='SENSITIVE-PAYLOAD';(d/'00-summary.json').write_text(json.dumps(x))
 elif change=='report_changed':(d/'REPORT.md').write_text('SENSITIVE-PAYLOAD')
 with pytest.raises(VerificationError) as error:verify_directory(d)
 diagnostic=error.value.diagnostic()
 assert diagnostic['code']==code and diagnostic['artifact']==artifact and diagnostic['next_step']
 assert 'SENSITIVE-PAYLOAD' not in json.dumps(diagnostic)

def test_directory_failure_and_safe_name_filter(tmp_path):
 with pytest.raises(VerificationError) as e:verify_directory(tmp_path/'missing')
 assert e.value.code=='DIRECTORY'
 assert VerificationError('FILE_ACCESS','../../../private').diagnostic()['artifact'] is None

def test_structured_success_and_error_exit_codes(tmp_path,monkeypatch,capsys):
 d=directory(tmp_path);monkeypatch.setattr('sys.argv',['ops-pharmacy-demo-review','--directory',str(d),'--json'])
 main();out=json.loads(capsys.readouterr().out)
 assert out['status']=='verified_demo_consistency' and out['pilot_recommendation']=='keep' and not out['actions_executed']
 (d/'03-evidence.json').unlink()
 with pytest.raises(SystemExit) as e:main()
 assert e.value.code==2
 captured=capsys.readouterr();out=json.loads(captured.out)
 assert not captured.err and out['status']=='verification_failed' and out['diagnostic']['code']=='MISSING_FILE'

def test_text_error_next_step_and_no_repair(tmp_path,monkeypatch,capsys):
 d=directory(tmp_path);p=d/'05-validation.json';p.write_text('PRIVATE-PAYLOAD');before=p.read_bytes()
 monkeypatch.setattr('sys.argv',['ops-pharmacy-demo-review','--directory',str(d)])
 with pytest.raises(SystemExit):main()
 result=capsys.readouterr()
 assert 'INVALID_JSON' in result.err and 'Next step:' in result.err and 'PRIVATE-PAYLOAD' not in result.err
 assert p.read_bytes()==before

def test_internal_error_does_not_echo_exception(tmp_path,monkeypatch,capsys):
 import operational_quality.demo_review as module
 def fail(*a):raise RuntimeError('PRIVATE-PAYLOAD')
 monkeypatch.setattr(module,'verify_directory',fail);monkeypatch.setattr('sys.argv',['ops-pharmacy-demo-review','--directory',str(tmp_path),'--json'])
 with pytest.raises(SystemExit):main()
 text=capsys.readouterr().out
 assert json.loads(text)['diagnostic']['code']=='INTERNAL_CHECK' and 'PRIVATE-PAYLOAD' not in text

def test_exponent_overflow_is_invalid_json(tmp_path):
 d=directory(tmp_path);(d/'03-evidence.json').write_text('{"value":1e9999}')
 with pytest.raises(VerificationError) as e:verify_directory(d)
 assert e.value.code=='INVALID_JSON'

def test_candidate_boundary_diagnostic(tmp_path):
 d=directory(tmp_path);p=d/'00-summary.json';s=json.loads(p.read_text());s['local_candidate_generated']=True;p.write_text(json.dumps(s));(d/'03-local-candidate.json').write_text('[]')
 with pytest.raises(VerificationError) as e:verify_directory(d)
 assert e.value.code=='CANDIDATE_INVALID' and e.value.artifact=='03-local-candidate.json'
