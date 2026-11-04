"""Prepare, review and bind a fictional corrective-action proposal; no automated implementation."""
import argparse,json
from pathlib import Path
from .cli import read_json,save
from .improvement import Settings,Snapshot,Accountability,prepare,review,local_review,proposal,inquiry

def main():
    p=argparse.ArgumentParser(description='Fictional pharmacy administrative improvement workbench')
    for n in ('settings','mock','output'):p.add_argument('--'+n,required=True)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--assessment');mode.add_argument('--local-model',help='Explicit already-installed local Ollama model; never downloads')
    p.add_argument('--accountability',help='Human-authored plan bound to validated review hash')
    a=p.parse_args()
    try:
        if a.accountability and not (a.assessment or a.local_model):raise ValueError('review required')
        out=Path(a.output)
        if out.exists():raise ValueError('output already exists')
        packet=prepare(Settings.model_validate(read_json(a.settings)),Snapshot.model_validate(read_json(a.mock)))
        artifacts={'evidence.json':packet,'inquiry.json':inquiry(packet)}
        if a.assessment:artifacts['review.json']=review(json.dumps(read_json(a.assessment)),packet)
        if a.local_model:artifacts['review.json']=local_review(packet,a.local_model)
        if a.accountability:artifacts['proposal.json']=proposal(artifacts['review.json'],Accountability.model_validate(read_json(a.accountability)))
        if sum(len((json.dumps(v,indent=2)+'\n').encode()) for v in artifacts.values())>250000:raise ValueError('output budget')
        out.mkdir(mode=0o700,parents=True,exist_ok=False)
        for n,v in artifacts.items():save(out,n,v)
        print(f'Fictional workbench saved to {out}; human review required; model accuracy and semantic support unverified.')
    except Exception as exc:p.exit(2,f'Workbench failed ({type(exc).__name__}); payload omitted.\n')

if __name__=='__main__':main()
