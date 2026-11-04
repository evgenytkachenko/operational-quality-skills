"""Loopback-only fictional portfolio dashboard. Fixed assets; no write endpoints."""
import argparse,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from importlib.resources import files
from .control_validation import Evidence,ControlPlan,digest,evaluate_control
from .referral import Scope,ReferralPolicy,audit_referrals

PROPOSAL='Review administrative completion when required document receipt metadata is unobserved.'

def dataset():
    policy=ReferralPolicy(version='v1',required_types=['administrative_form','routing_sheet'],delivery_seconds=1,acknowledgment_seconds=1,max_feed_lag_seconds=0)
    checksum=digest(policy.content());quote=f'FICTIONAL checklist approval REFERRAL-DEMO-POLICY {checksum}'
    policy=ReferralPolicy.model_validate({**policy.content(),'approval':{'decision':'approved','approved_at':'2026-10-01T00:00:00Z','policy_sha256':checksum,'links':[{'source_id':'demo:checklist','quote':quote}]}})
    evidence=Evidence.model_validate({'artifacts':[{'ref':'demo:checklist','kind':'approval','text':quote}]})
    cases=[]
    # 4 true alerts, 2 false alerts, 1 missed case, 5 true negatives, 1 unscorable.
    for n in range(1,14):
        case_id=f'REF-DEMO-{n:03d}'
        missing=n<=6;truth=n in (1,2,3,4,7);unknown=n==13
        explanation=('Required routing sheet was absent at completion in the fictional adjudication record.' if truth else 'Both required documents were present in the fictional adjudication record.')
        if n==5:explanation='Routing sheet was held in an approved off-system record; its receipt was absent from the feed.'
        if n==6:explanation='A delayed receipt feed hid a routing sheet already present at completion.'
        if n==7:explanation='The feed reported a matching receipt, but fictional adjudication found it associated with the wrong packet.'
        if unknown:explanation='Receiver coverage and adjudication are unavailable; exclude from all accuracy denominators.'
        docs=[{'kind':kind,'version':1,'fingerprint':digest({'case':case_id,'kind':kind})} for kind in ('administrative_form','routing_sheet')]
        submit=f'EV-{n*10:03d}'
        events=[{'id':submit,'source':'sender','case_id':case_id,'revision':1,'kind':'submitted','occurred_at':'2026-10-05T08:00:00Z','received_at':'2026-10-05T08:00:00Z','documents':docs}]
        for j,d in enumerate(docs):
            if missing and j==1:continue
            events.append({'id':f'EV-{n*10+j+1:03d}','source':'receiver','case_id':case_id,'revision':1,'kind':'document_received','occurred_at':f'2026-10-05T08:{10+j*5}:00Z','received_at':f'2026-10-05T08:{10+j*5}:00Z','documents':[d],'related_ref':'sender:'+submit})
        events.append({'id':f'EV-{n*10+3:03d}','source':'receiver','case_id':case_id,'revision':1,'kind':'acknowledged','occurred_at':'2026-10-05T08:20:00Z','received_at':'2026-10-05T08:20:00Z','documents':[],'related_ref':'sender:'+submit})
        scope=Scope(synthetic=True,cases=[case_id],start='2026-10-05T00:00:00Z',as_of='2026-10-05T08:30:00Z')
        manifests=[{'source':s,'cases':[case_id],'count':sum(e['source']==s for e in events),'complete_from':scope.start.isoformat(),'complete_through':scope.as_of.isoformat(),'available':not unknown,'truncated':False,'offline_pending':False,'clock_uncertainty_seconds':1} for s in ('sender','receiver')]
        # Referral manifest contract needs only complete-through; keep schema strict.
        for m in manifests:m.pop('complete_from')
        report=audit_referrals(scope,policy,evidence,{'synthetic':True,'feeds':manifests,'events':events})
        case=report['cases'][0];flag=None if case['status']=='unknown' else any(f['kind'] in {'document_receipt_not_observed','required_metadata_not_listed','document_metadata_conflict'} for f in case['findings'])
        completion={'ref':f'workflow:COMP-DEMO-{n:03d}','case_id':case_id,'state':'administrative_completion_recorded','at':'2026-10-05T08:30:00Z'}
        initial='confirm' if n in (1,2) else 'dismiss' if n==5 else None
        cases.append({'id':case_id,'queue':'Intake desk' if n%2 else 'Document review','flag':flag,'completion':completion,'initial_decision':initial,'observed_missing':['routing_sheet'] if missing else [],'ground_truth_missing':None if unknown else truth,'ground_truth':{'ref':f'adjudication:DEMO-{n:03d}','label':'unknown' if unknown else 'documentation_missing' if truth else 'documentation_present','explanation':explanation,'fictional':True},'audit':report,'evidence':events,'source_coverage':manifests})
    metrics=score(cases)
    # Reuse approved-pilot gate: a classifier replay is not implementation or effectiveness evidence.
    assessment={'observations':[],'hypotheses':[{'explanation':text,'status':'unknown','supporting':[],'contradicting':[],'discriminating_check':'Human review source mapping before considering a pilot.','counterfactual':'Cannot establish from this replay.'} for text in ('Receipt capture may be incomplete.','Packet matching may be incorrect.')],'controls':[{'proposal':PROPOSAL,'owner_role':'operations_quality','measure':'Define pilot outcome, false-alert guardrail and fidelity denominators before approval.','review_window':'Unapproved hypothetical pilot window.','tradeoff':'Reviewer workload and missed mismatches.'}],'unknowns':['No approved or implemented pilot evidence.']}
    review={'assessment':assessment}
    plan=ControlPlan(control_id='DOC-DEMO-CONTROL',rca_reference='dashboard:proposal',rca_review_sha256=digest(review),control_index=0,proposal=PROPOSAL,registered_at='2026-10-08T08:00:00Z',monitoring={'metrics':[{'id':k,'definition_version':'v1','role':role,'worse':worse,'threshold':threshold} for k,role,worse,threshold in [('documentation_exceptions','outcome','higher',.08),('false_alerts','guardrail','higher',.1),('control_applied','guardrail','lower',.95)]],'cohorts':['fictional_replay'],'windows':{'baseline':{'start':'2026-10-01T00:00:00Z','end':'2026-10-08T00:00:00Z'},'current':{'start':'2026-10-09T00:00:00Z','end':'2026-10-16T00:00:00Z'}}},pilot_cohorts=['fictional_replay'],outcome_metric='documentation_exceptions',guardrail_metrics=['false_alerts'],fidelity_metric='control_applied',approval=None,implemented_at=None,implementation_claim='No pilot was implemented; this is a fictional replay.',confounders=[{'domain':d,'status':'unresolved','explanation':'Not assessed by this synthetic classification replay.','links':[]} for d in ('case_mix','seasonality','concurrent_changes','measurement','spillover')])
    def no_fetch(*args):raise AssertionError('No aggregate retrieval without approval')
    validation,_=evaluate_control(plan,review,Evidence(artifacts=[]),no_fetch)
    result={'synthetic':True,'title':'Documentation completeness review','control_id':'DOC-DEMO-CONTROL','proposal':PROPOSAL,'cases':cases,'metrics':metrics,'effectiveness':validation,'policy_sha256':checksum,'limits':['No patient data, document contents, clinical or insurance decisions.','A recorded completion is replayed, not blocked or reversed.','All ground truth and reviewer decisions are authored synthetic fixtures.','No model was run; no model accuracy is claimed.','No writes, external integrations, notifications or schedules.']}
    result['sha256']=digest(result)
    return result

def score(cases):
    counts={'tp':0,'fp':0,'fn':0,'tn':0,'unknown':0}
    for c in cases:
        flag,truth=c['flag'],c['ground_truth_missing']
        if any(v is not None and type(v) is not bool for v in (flag,truth)):raise ValueError('boolean classification required')
        if flag is None or truth is None:counts['unknown']+=1;continue
        counts['tp' if flag and truth else 'fp' if flag else 'fn' if truth else 'tn']+=1
    def ratio(n,d):return {'numerator':n,'denominator':d,'rate':n/d if d else None}
    return {**counts,'evaluable':sum(counts[k] for k in ('tp','fp','fn','tn')),'total':len(cases),'precision':ratio(counts['tp'],counts['tp']+counts['fp']),'recall':ratio(counts['tp'],counts['tp']+counts['fn']),'false_positive_rate':ratio(counts['fp'],counts['fp']+counts['tn']),'miss_rate':ratio(counts['fn'],counts['tp']+counts['fn'])}

def handler(payload):
    assets=files('operational_quality').joinpath('dashboard_assets')
    routes={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/data.json':data=payload;kind='application/json'
            elif self.path in routes:
                name,kind=routes[self.path];data=assets.joinpath(name).read_bytes()
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(data)
        def log_message(self,*args):pass
    return Handler

def main():
    p=argparse.ArgumentParser(description='Loopback-only synthetic pharmacy control portfolio; no external actions')
    p.add_argument('--port',type=int,default=8765)
    a=p.parse_args()
    if not 0<=a.port<=65535:p.error('port must be between 0 and 65535')
    try:
        server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(json.dumps(dataset()).encode()))
        print(f'Fictional dashboard: http://127.0.0.1:{server.server_port} — Ctrl+C to stop. No source writes or models.',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
    except OSError:p.exit(2,'Could not bind local port; choose another --port.\n')
if __name__=='__main__':main()
