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

def _read(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):raise ValueError('regular file required')
        data=handle.read(1000001)
    if len(data)>1000000:raise ValueError('file budget')
    return data

def verify_directory(directory):
    from .pharmacy_demo import run_demo,summarize
    base=Path(directory)
    if base.is_symlink() or not base.is_dir():raise ValueError('regular directory required')
    summary_raw=_read(base/'00-summary.json');summary=json.loads(summary_raw)
    if summary.get('scenario') not in ('nominal','missing-evidence'):raise ValueError('invalid scenario')
    if type(summary.get('local_candidate_generated')) is not bool:raise ValueError('invalid mode')
    # Recompute fixed scripted branch only; never execute a saved request or run a model.
    expected=run_demo(summary['scenario'])
    names=set(expected)-{'00-summary.json'}
    if summary['local_candidate_generated']:names.add(CANDIDATE)
    allowed=names|{'00-summary.json','REPORT.md','START-HERE.md'}
    if any(p.name not in allowed for p in base.iterdir()):raise ValueError('unexpected files; possible mixed runs')
    actual={};size=len(summary_raw)
    for name in sorted(names):
        raw=_read(base/name);size+=len(raw)
        if size>2000000:raise ValueError('combined budget')
        actual[name]=json.loads(raw)
    for name,value in expected.items():
        if name!='00-summary.json' and digest(actual[name])!=digest(value):raise ValueError('artifact mismatch with installed demo version')
    expected.pop('00-summary.json')
    if summary['local_candidate_generated']:
        candidate=actual[CANDIDATE]
        if set(candidate)!={'status','independent_of_scripted_pilot','review'} or candidate['status']!='UNAPPROVED_CANDIDATE_ONLY' or candidate['independent_of_scripted_pilot'] is not True:raise ValueError('candidate boundary')
        validated=review(json.dumps(candidate['review']['assessment']),expected['03-evidence.json'])
        if digest(validated)!=digest(candidate['review']):raise ValueError('candidate provenance mismatch')
        expected[CANDIDATE]=candidate
    rebuilt=summarize(expected,summary['scenario'],summary['local_candidate_generated'])
    if digest(summary)!=digest(rebuilt):raise ValueError('summary or hash mismatch')
    if summary['artifact_hashes']!={n:digest(v) for n,v in actual.items()}:raise ValueError('saved artifact hash mismatch')
    actual['00-summary.json']=summary
    report=render_report(actual)
    if (base/'REPORT.md').exists() or (base/'REPORT.md').is_symlink():
        raw=_read(base/'REPORT.md');size+=len(raw)
        if size>2000000 or raw.decode()!=report:raise ValueError('rendered report mismatch')
    return actual,report

def main():
    p=argparse.ArgumentParser(description='Offline read-only verification and readable review of a saved pharmacy demo')
    p.add_argument('--directory',required=True)
    a=p.parse_args()
    try:
        artifacts,report=verify_directory(a.directory)
        print('Verified JSON against installed scripted fixtures and exact quote checks. This is not authentication, model validation or approval. START-HERE.md is navigation only and is not verified.\n')
        print(report,end='')
    except Exception as exc:p.exit(2,f'Demo verification failed ({type(exc).__name__}); files may be missing, changed, mixed or from another version. No input payload printed.\n')

if __name__=='__main__':main()
