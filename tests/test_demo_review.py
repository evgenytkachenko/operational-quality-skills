import json
from pathlib import Path
import pytest
from operational_quality.pharmacy_demo import run_demo,summarize
from operational_quality.demo_review import render_report,verify_directory
from operational_quality.control_validation import digest

def write(directory,a,report=True):
 directory.mkdir()
 for n,v in a.items():(directory/n).write_text(json.dumps(v))
 if report:(directory/'REPORT.md').write_text(render_report(a))
 return directory

@pytest.mark.parametrize('scenario',['nominal','missing-evidence'])
def test_readable_and_verified_without_network_or_model(tmp_path,monkeypatch,scenario):
 def deny(*args,**kwargs):raise AssertionError('model not allowed')
 monkeypatch.setattr('operational_quality.pharmacy_demo.local_review',deny)
 a=run_demo(scenario);d=write(tmp_path/'demo',a);before={p.name:p.read_bytes() for p in d.iterdir()}
 got,text=verify_directory(d)
 assert got==a and before=={p.name:p.read_bytes() for p in d.iterdir()}
 assert 'not proof' in text or 'not supported' in text
 if scenario=='nominal':assert '84/700 (12.0%)' in text and '28/700 (4.0%)' in text and '8.0 percentage-point decrease' in text
 else:assert 'No supported improvement estimate' in text and '8.0 percentage-point' not in text and '7 unknown' in text

@pytest.mark.parametrize('change',['artifact','summary','rehash','missing','extra','traversal','report','symlink','oversize'])
def test_changed_or_unsafe_saved_run_rejected(tmp_path,change):
 a=run_demo();d=write(tmp_path/'demo',a)
 if change in ('artifact','rehash'):
  a['05-validation.json']['recommendation']='stop';(d/'05-validation.json').write_text(json.dumps(a['05-validation.json']))
  if change=='rehash':
   a['00-summary.json']['artifact_hashes']['05-validation.json']=digest(a['05-validation.json']);(d/'00-summary.json').write_text(json.dumps(a['00-summary.json']))
 elif change=='summary':a['00-summary.json']['validation_recommendation']='stop';(d/'00-summary.json').write_text(json.dumps(a['00-summary.json']))
 elif change=='missing':(d/'03-evidence.json').unlink()
 elif change=='extra':(d/'unrelated.json').write_text('{}')
 elif change=='traversal':a['00-summary.json']['artifact_hashes']['../private.json']='0'*64;(d/'00-summary.json').write_text(json.dumps(a['00-summary.json']))
 elif change=='report':(d/'REPORT.md').write_text('Misleading approval')
 elif change=='symlink':
  target=tmp_path/'private';target.write_text('SECRET');(d/'03-evidence.json').unlink();(d/'03-evidence.json').symlink_to(target)
 elif change=='oversize':(d/'03-evidence.json').write_text('x'*1000001)
 with pytest.raises((ValueError,OSError)):verify_directory(d)

def test_older_demo_without_report_can_be_reviewed(tmp_path):
 a=run_demo();d=write(tmp_path/'legacy',a,False)
 assert verify_directory(d)[0]==a
 assert not (d/'REPORT.md').exists()

def test_optional_candidate_is_revalidated_not_executed(tmp_path,monkeypatch):
 from operational_quality.pharmacy_demo import load
 class Client:
  def chat(self,**kwargs):return {'message':{'content':json.dumps(load('scripted_assessment'))}}
 a=run_demo(model='fixture:small',client=Client());d=write(tmp_path/'demo',a)
 def deny(*a,**kw):raise AssertionError('no model during verification')
 monkeypatch.setattr('operational_quality.pharmacy_demo.local_review',deny)
 _,text=verify_directory(d);assert 'remains unapproved' in text
 a['03-local-candidate.json']['review']['assessment']['observations'][0]['links'][0]['quote']='invented quote'
 (d/'03-local-candidate.json').write_text(json.dumps(a['03-local-candidate.json']))
 with pytest.raises(ValueError):verify_directory(d)

def test_report_escapes_markup():
 a=run_demo();a['05-validation.json']['segments'][0]['reasons']=['<script>alert(1)</script> [execute](https://example.invalid) | injected\nheading']
 text=render_report(a)
 assert '<script>' not in text and '[execute]' not in text and '| injected' not in text and '\nheading' not in text

def test_cli_failure_does_not_echo_payload(tmp_path,monkeypatch,capsys):
 from operational_quality.demo_review import main
 d=write(tmp_path/'demo',run_demo());(d/'00-summary.json').write_text('PRIVATE SECRET INVALID JSON')
 monkeypatch.setattr('sys.argv',['ops-pharmacy-demo-review','--directory',str(d)])
 with pytest.raises(SystemExit):main()
 captured=capsys.readouterr();assert 'PRIVATE SECRET' not in captured.out+captured.err

@pytest.mark.parametrize('target',['artifact','summary'])
def test_json_boolean_numeric_substitutions_rejected(tmp_path,target):
 a=run_demo();d=write(tmp_path/'demo',a)
 name='05-validation.json' if target=='artifact' else '00-summary.json'
 a[name]['actions_executed']=0
 (d/name).write_text(json.dumps(a[name]))
 with pytest.raises(ValueError):verify_directory(d)
