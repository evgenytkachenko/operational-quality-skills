import copy,io,json
import pytest
from operational_quality.dashboard import dataset,score,handler
from operational_quality.control_validation import digest

def test_fixed_ground_truth_calculations_and_limits():
 d=dataset();m=d['metrics']
 assert (m['tp'],m['fp'],m['fn'],m['tn'],m['unknown'],m['evaluable'],m['total'])==(4,2,1,5,1,12,13)
 assert m['precision']=={'numerator':4,'denominator':6,'rate':4/6}
 assert m['recall']['rate']==.8 and m['miss_rate']['rate']==.2
 assert m['false_positive_rate']['denominator']==7
 assert d['effectiveness']['recommendation']=='insufficient_evidence'
 assert not d['effectiveness']['actions_executed'] and not d['effectiveness']['rollout_authorized']
 assert d['sha256']==digest({k:v for k,v in d.items() if k!='sha256'})

def test_audit_findings_have_source_refs_and_control_does_not_read_truth():
 d=dataset()
 for c in d['cases']:
  refs={f"{e['source']}:{e['id']}" for e in c['evidence']}
  for f in c['audit']['cases'][0]['findings']:assert set(f['evidence_refs'])<=refs
  assert c['completion']['case_id']==c['id']
 assert d['cases'][6]['flag'] is False and d['cases'][6]['ground_truth_missing'] is True
 assert d['cases'][12]['flag'] is None
 # Review decisions cannot alter classifier or truth counts.
 before=score(d['cases'])
 for c in d['cases']:c['initial_decision']='dismiss'
 assert score(d['cases'])==before

def test_zero_denominators_are_unavailable():
 m=score([])
 assert all(m[k]['rate'] is None for k in ('precision','recall','false_positive_rate','miss_rate'))
 assert score([{'flag':None,'ground_truth_missing':True}])['unknown']==1
 with pytest.raises(ValueError):score([{'flag':1,'ground_truth_missing':True}])

def request(path):
 cls=handler(b'{"synthetic":true}');instance=cls.__new__(cls);instance.path=path;instance.wfile=io.BytesIO();codes=[];headers={}
 instance.send_response=codes.append;instance.send_error=codes.append;instance.send_header=lambda k,v:headers.update({k:v});instance.end_headers=lambda:None
 instance.do_GET();return codes,headers,instance.wfile.getvalue(),cls

def test_server_exact_read_only_routes_and_security_headers():
 for path in ('/','/app.js','/style.css','/data.json'):
  codes,headers,data,cls=request(path)
  assert codes==[200] and data and headers['Cache-Control']=='no-store'
  assert "connect-src 'self'" in headers['Content-Security-Policy']
  assert not hasattr(cls,'do_POST') and not hasattr(cls,'do_PUT') and not hasattr(cls,'do_DELETE')
 for path in ('/../pyproject.toml','/data.json?x=1','/private','//data.json'):
  assert request(path)[0]==[404]

def test_no_persistent_browser_state_or_html_injection_sink():
 js=request('/app.js')[2].decode()
 assert all(s not in js for s in ('innerHTML','localStorage','sessionStorage','document.cookie','eval('))
 assert js.count("fetch(")==1 and "fetch('/data.json')" in js
