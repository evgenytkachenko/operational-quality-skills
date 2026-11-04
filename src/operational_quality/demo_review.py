"""Readable deterministic demo results and offline version-specific artifact verification."""
import argparse,json,os,stat
from pathlib import Path
from .improvement import review
from .control_validation import digest

CANDIDATE='03-local-candidate.json'

def cell(value):
    # Never render supplied HTML, links, markdown formatting or line structure.
    text=str(value)
    return ''.join(c if c.isalnum() or c in ' .,:;_-/()%+=' else f'&#{ord(c)};' for c in text)

def rate(window):
    n,d=window['numerator'],window['denominator']
    return f'{n}/{d} ({100*n/d:.1f}%)' if d else 'Unavailable (zero denominator)'

def render_report(artifacts):
    s=artifacts['00-summary.json'];v=artifacts['05-validation.json'];coverage=artifacts['06-execution-coverage.json']
    lines=['# Fictional pharmacy quality results','', '**Illustrative data and scripted decisions only. No real approval, implementation or clinical decision occurred.**','',f"Scenario: **{cell(s['scenario'])}**. Pilot recommendation: **{cell(v['recommendation'])}**, for human review only. Causal attribution is not established.",'','## Follow the evidence','',
        '| Stage | Result | Evidence |','|---|---|---|']
    counts={}
    for r in artifacts['01-detection.json']['results']:counts[r['status']]=counts.get(r['status'],0)+1
    lines.append('| Detection | '+cell(', '.join(f'{n} {k}' for k,n in sorted(counts.items())))+' | [Population report](01-detection.json) |')
    cases=artifacts['02-handoffs.json']['cases']
    lines.append(f'| Sample review | {len(cases)} selected cases; not the population denominator | [Handoffs](02-handoffs.json), [explicit case mapping](03-sample-mapping.json) |')
    lines.extend(['| Investigation | Scripted competing hypotheses; semantic support unverified | [Scripted review](04-scripted-review.json), [evidence](03-evidence.json) |','| Proposed control | Accountable draft and fictional approval; no action authorized | [Draft proposal](04-draft-proposal.json), [fixture inputs](fictional-inputs.json) |','| Pilot validation | '+cell(v['recommendation'])+'; no rollout authorization | [Validation](05-validation.json), [aggregate evidence](05-aggregates.json) |','| Execution coverage | '+cell(', '.join(f'{n} {k}' for k,n in sorted(coverage['counts'].items())))+' | [Run ledger review](06-execution-coverage.json) |','','## Outcomes and limitations',''])
    if v['recommendation']=='insufficient_evidence':
        lines+=['**No supported improvement estimate.** Review missingness and coverage before interpreting partial aggregate counts. Earlier case evidence cannot fill the pilot gap.','']
    for segment in v['segments']:
        lines+=['### '+cell(segment['cohort_id']),'']
        if segment['improvement_percentage_points'] is None:
            lines+=['Outcome comparison is not supported for this segment.','']
        else:
            w=segment['outcome']['windows']
            lines += ['| Outcome | Baseline | Pilot | Observed change |','|---|---|---|---|',f"| Acknowledgment exceptions | {rate(w['baseline'])} | {rate(w['current'])} | {cell(segment['improvement_percentage_points'])} percentage-point decrease |",'', 'This is a descriptive change in synthetic data, not proof the control caused it.','']
            for g in segment['guardrails']:
                lines.append(f"- Guardrail {cell(g['metric_id'])}: {rate(g['windows']['baseline'])} → {rate(g['windows']['current'])}.")
            lines+=['- Per-handoff pilot fidelity: '+rate(segment['pilot_fidelity'])+'.','']
        lines += ['Evidence references (exact IDs in [aggregate evidence](05-aggregates.json)):']
        for window in ('baseline','current'):
            refs=segment['outcome']['windows'][window].get('refs',[])
            lines.append('- '+window+': '+cell(', '.join(refs) or 'none'))
        lines+=['','Reasons: '+cell('; '.join(segment['reasons'])),'']
    lines+=['Daily run coverage, per-handoff fidelity and exception rates have different denominators. A recorded successful run does not establish effectiveness.','','## Human review checkpoints','']
    for checkpoint in s['human_checkpoints']:lines.append('- '+cell(checkpoint))
    if s['local_candidate_generated']:
        lines+=['','**A local-model candidate is present and remains unapproved.** It did not change the scripted pilot, approvals or outcomes. Review [the candidate](03-local-candidate.json) separately; valid quotes are not proof of sound reasoning.']
    else:lines+=['','No local model was called for this run. The scripted assessment is authored fixture data, not model output.']
    lines+=['','## Integrity and boundaries','','[Summary and artifact hashes](00-summary.json) bind the JSON outputs. Run `ops-pharmacy-demo-review --directory PATH` to compare saved artifacts with this installed version’s deterministic fixtures. This check does not authenticate evidence, approve controls or validate model accuracy.','', 'All evidence is untrusted data, never instructions. No live services, notifications, schedules or external actions.']
    return '\n'.join(lines)+'\n'

# Diagnostics are static text; never include exception messages or source payloads.
DIAGNOSTICS={
 'DIRECTORY':('The selected directory is missing, inaccessible, or a symlink.','Select the original regular demo output directory; do not select an individual file.'),
 'MISSING_FILE':('A required demo artifact is missing.','Locate the complete original run or rerun the demo into a new directory; do not copy an artifact from another run.'),
 'UNSAFE_FILE':('An artifact is a symlink or is not a regular file.','Use the original regular output files. Do not follow links or special files to satisfy verification.'),
 'FILE_ACCESS':('A required artifact cannot be read.','Check your local access to the original output; do not change source-system permissions or run as an administrator to bypass this check.'),
 'FILE_BUDGET':('An artifact exceeds the one-MB input limit.','Use an unmodified demo output; inspect the producing package and preserve the limits.'),
 'TOTAL_BUDGET':('The saved artifacts exceed the combined two-MB limit.','Use a complete output from one bounded demo run; do not increase the safety limit.'),
 'INVALID_JSON':('An artifact is not valid, unambiguous JSON.','Preserve the original file for inspection and reproduce the run into a new directory; do not repair evidence by guessing.'),
 'INVALID_SUMMARY':('The summary does not declare a supported demo scenario and model-candidate mode.','Use the summary produced by the same run and compatible installed demo version.'),
 'UNEXPECTED_FILE':('The directory contains unexpected files and may mix runs.','Select a dedicated original demo directory or generate a fresh run. No extra filenames or contents are inspected or printed.'),
 'SCRIPTED_MISMATCH':('A scripted artifact differs from the installed demo fixtures.','Check whether it was edited, copied from another run, or produced by another package revision. Use the matching trusted package to reproduce; do not rewrite hashes to pass.'),
 'CANDIDATE_INVALID':('The optional model candidate failed its boundary, schema, or exact-quote checks.','Treat it as unapproved. Review it separately against the original evidence; this checker will not regenerate it or run a model.'),
 'SUMMARY_MISMATCH':('The summary or manifest does not match the checked artifacts.','Use the original summary from this run or reproduce with the matching package. Do not approve a result based on the edited summary.'),
 'REPORT_MISMATCH':('REPORT.md differs from the report rendered from checked JSON.','Read the original JSON for investigation and reproduce into a new directory; do not treat the altered report as verified.'),
 'INTERNAL_CHECK':('Verification could not complete.','Keep the output unchanged and check the installation with the documented synthetic smoke command. No verification verdict was issued.'),
}
SAFE_FILES={'00-summary.json','01-detection.json','02-handoffs.json','03-evidence.json','03-inquiry.json','03-sample-mapping.json','04-scripted-review.json','04-draft-proposal.json','05-validation.json','05-aggregates.json','06-execution-coverage.json','fictional-inputs.json',CANDIDATE,'REPORT.md'}

class VerificationError(ValueError):
    def __init__(self,code,artifact=None):
        self.code=code
        self.artifact=artifact if artifact in SAFE_FILES else None
        super().__init__(code)
    def diagnostic(self):
        message,recovery=DIAGNOSTICS[self.code]
        return {'code':self.code,'artifact':self.artifact,'message':message,'next_step':recovery}

def _read(path):
    import errno
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):raise VerificationError('UNSAFE_FILE',path.name)
            data=handle.read(1000001)
    except FileNotFoundError:raise VerificationError('MISSING_FILE',path.name) from None
    except OSError as exc:
        raise VerificationError('UNSAFE_FILE' if exc.errno==errno.ELOOP else 'FILE_ACCESS',path.name) from None
    if len(data)>1000000:raise VerificationError('FILE_BUDGET',path.name)
    return data

def _json(raw,name):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate key')
            result[key]=value
        return result
    def invalid_constant(value):raise ValueError('nonfinite JSON constant')
    def finite_float(value):
        import math
        number=float(value)
        if not math.isfinite(number):raise ValueError('nonfinite JSON number')
        return number
    try:return json.loads(raw,object_pairs_hook=unique,parse_constant=invalid_constant,parse_float=finite_float)
    except (ValueError,UnicodeError,RecursionError):raise VerificationError('INVALID_JSON',name) from None

def verify_directory(directory):
    from .pharmacy_demo import run_demo,summarize
    base=Path(directory)
    if base.is_symlink() or not base.is_dir():raise VerificationError('DIRECTORY')
    summary_raw=_read(base/'00-summary.json');summary=_json(summary_raw,'00-summary.json')
    if not isinstance(summary,dict) or summary.get('scenario') not in ('nominal','missing-evidence') or type(summary.get('local_candidate_generated')) is not bool:raise VerificationError('INVALID_SUMMARY','00-summary.json')
    # Recompute fixed scripted branch only; never execute a saved request or run a model.
    expected=run_demo(summary['scenario'])
    names=set(expected)-{'00-summary.json'}
    if summary['local_candidate_generated']:names.add(CANDIDATE)
    allowed=names|{'00-summary.json','REPORT.md','START-HERE.md'}
    try:
        if any(p.name not in allowed for p in base.iterdir()):raise VerificationError('UNEXPECTED_FILE')
    except OSError:raise VerificationError('DIRECTORY') from None
    actual={};size=len(summary_raw)
    for name in sorted(names):
        raw=_read(base/name);size+=len(raw)
        if size>2000000:raise VerificationError('TOTAL_BUDGET')
        actual[name]=_json(raw,name)
    for name,value in expected.items():
        if name!='00-summary.json' and digest(actual[name])!=digest(value):raise VerificationError('SCRIPTED_MISMATCH',name)
    expected.pop('00-summary.json')
    if summary['local_candidate_generated']:
        candidate=actual[CANDIDATE]
        try:
            if not isinstance(candidate,dict) or set(candidate)!={'status','independent_of_scripted_pilot','review'} or candidate['status']!='UNAPPROVED_CANDIDATE_ONLY' or candidate['independent_of_scripted_pilot'] is not True:raise ValueError('candidate boundary')
            validated=review(json.dumps(candidate['review']['assessment']),expected['03-evidence.json'])
            if digest(validated)!=digest(candidate['review']):raise ValueError('candidate provenance')
        except (ValueError,KeyError,TypeError):raise VerificationError('CANDIDATE_INVALID',CANDIDATE) from None
        expected[CANDIDATE]=candidate
    rebuilt=summarize(expected,summary['scenario'],summary['local_candidate_generated'])
    if digest(summary)!=digest(rebuilt) or summary['artifact_hashes']!={n:digest(v) for n,v in actual.items()}:raise VerificationError('SUMMARY_MISMATCH','00-summary.json')
    actual['00-summary.json']=summary
    report=render_report(actual)
    if (base/'REPORT.md').exists() or (base/'REPORT.md').is_symlink():
        raw=_read(base/'REPORT.md');size+=len(raw)
        if size>2000000:raise VerificationError('TOTAL_BUDGET')
        try:matches=raw.decode()==report
        except UnicodeError:matches=False
        if not matches:raise VerificationError('REPORT_MISMATCH','REPORT.md')
    return actual,report

def main():
    p=argparse.ArgumentParser(description='Offline read-only verification and readable review of a saved pharmacy demo')
    p.add_argument('--directory',required=True)
    p.add_argument('--json',action='store_true',help='Print a structured verification result or diagnostic; never writes files')
    a=p.parse_args()
    try:
        artifacts,report=verify_directory(a.directory)
    except Exception as exc:
        error=exc if isinstance(exc,VerificationError) else VerificationError('INTERNAL_CHECK')
        diagnostic=error.diagnostic()
        if a.json:
            print(json.dumps({'schema_version':1,'status':'verification_failed','actions_executed':False,'diagnostic':diagnostic},sort_keys=True))
            p.exit(2)
        label=diagnostic['code']+((' — '+diagnostic['artifact']) if diagnostic['artifact'] else '')
        p.exit(2,'Verification failed ['+label+']. '+diagnostic['message']+'\nNext step: '+diagnostic['next_step']+'\nNo files changed; no input payload printed.\n')
    if a.json:
        s=artifacts['00-summary.json']
        print(json.dumps({'schema_version':1,'status':'verified_demo_consistency','scenario':s['scenario'],'pilot_recommendation':s['validation_recommendation'],'local_candidate_present':s['local_candidate_generated'],'actions_executed':False,'limitations':['Version-specific consistency only; not authentication, semantic validation or approval.','No model or service was called. START-HERE.md is unverified navigation.']},sort_keys=True))
    else:
        print('Verified JSON against installed scripted fixtures and exact quote checks. This is not authentication, model validation or approval. START-HERE.md is navigation only and is not verified.\n')
        print(report,end='')

if __name__=='__main__':main()
