"""Traceability and bounded execution for JYRM 1BNCF v3.1.0.

The ten attached phase archives are retained byte-for-byte under ``onebitflow``.
They are engineering instructions, not executable shell text.  This runner
verifies source identity, preserves all 275,000 prompt/workflow IDs, and runs a
scoped local containership adaptation.  It never converts local test success
into source-task or phase promotion.
"""
from __future__ import annotations
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
from . import Refusal, UC_RELEASE, engines as E, safety as SAFE

SCHEMA='UC/1BIT_WORKFLOW_APPLICATION/1'
TASK_RE=re.compile(r'PW-(\d{3})-(\d{3})-(\d{2})\Z')
STATES={'IN_PROGRESS','BLOCKED','PASS','FAIL','NOT_APPLICABLE'}
MAX_LEDGER_COMPRESSED=128*1024*1024


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def base(root):return Path(SAFE.contained_path(str(root),'onebitflow'))


def load(root):
    b=base(root);m=json.loads((b/'APPLICATION.json').read_text(encoding='utf-8'))
    if m.get('schema')!=SCHEMA:raise Refusal('unsupported 1-bit workflow application schema')
    return b,m


def status(root):
    _,m=load(root)
    return {'schema':'UC/1BIT_WORKFLOW_STATUS/1','candidate':m['candidate'],'source_version':m['source_version'],
            'source_phases':10,'components':m['component_count'],'prompt_workflows':m['prompt_workflow_count'],
            'counts':m['task_status_counts'],'local_component_coverage':m['local_component_coverage'],
            'phase_gates':{p['phase']:p['source_gate'] for p in m['phases']},'phase_gates_closed':0,
            'full_series_complete':False,'rule':'1-bit communication, not 1-bit cognition',
            'note':'Local adaptation evidence is separate from source-task promotion; JYRM/external adapter phases remain unqualified.'}


def _ledger_records(path):
    if path.stat().st_size>MAX_LEDGER_COMPRESSED:raise Refusal('1-bit workflow ledger exceeds compressed byte budget')
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:
            if len(line)>8192:raise Refusal('1-bit workflow ledger line exceeds bound')
            yield json.loads(line)


def check(root,deep=False):
    b,m=load(root);errors=[]
    ledger=b/'ledger.jsonl.gz'
    if sha(ledger)!=m['ledger_sha256']:errors.append('ledger digest mismatch')
    # Source archives are the primary immutable provenance anchor.
    for p in m['source_phases']:
        path=b/'source'/p['file']
        if not path.is_file() or sha(path)!=p['sha256']:errors.append(f"{p['phase']}: source archive digest mismatch")
        else:
            with zipfile.ZipFile(path) as z:
                names=z.namelist();man=[n for n in names if n.endswith('/MANIFEST.json')]
                if len(man)!=1:errors.append(f"{p['phase']}: missing/ambiguous manifest")
                else:
                    src=json.loads(z.read(man[0]));
                    if src.get('phase')!=p['number'] or src.get('component_count')!=11 or src.get('prompts')!=27500:
                        errors.append(f"{p['phase']}: source manifest identity/count mismatch")
    counts=collections.Counter();components=collections.Counter();seen=set()
    for r in _ledger_records(ledger):
        tid=r.get('id');mm=TASK_RE.fullmatch(tid or '')
        if not mm or tid in seen:errors.append('invalid or duplicate task id');break
        comp=int(mm.group(1));parent=int(mm.group(2));nested=int(mm.group(3))
        if not (1<=comp<=110 and 1<=parent<=100 and 1<=nested<=25):errors.append(tid+': id outside source bounds');break
        if r.get('component')!=comp or r.get('phase')!=f'P{(comp-1)//11+1:02d}':errors.append(tid+': trace mismatch');break
        if r.get('status') not in STATES or r.get('status') in {'PASS','FAIL','NOT_APPLICABLE'}:errors.append(tid+': unsubstantiated promoted/final state');break
        if not r.get('reason'):errors.append(tid+': missing disposition reason');break
        seen.add(tid);counts[r['status']]+=1;components[comp]+=1
    if len(seen)!=275000 or len(components)!=110 or set(components.values())!={2500}:
        errors.append('incomplete 275,000-task coverage')
    if dict(counts)!=m['task_status_counts']:errors.append('task status counts differ from application manifest')
    if deep and not errors:
        cmap=json.loads((b/'COMPONENTS.json').read_text(encoding='utf-8'))
        checked=0
        for key,rec in sorted(cmap.items()):
            path=b/'source'/rec['archive']
            with zipfile.ZipFile(path) as z:
                raw=z.read(rec['entry']);checked+=1
                if hashlib.sha256(raw).hexdigest()!=rec['source_sha256']:
                    errors.append(key+': component source bytes changed');continue
                text=raw.decode('utf-8')
                ids=re.findall(r'^### (PW-\d{3}-\d{3}-\d{2})$',text,re.M)
                parents=re.findall(r'^## Parent \d{3} — ',text,re.M)
                if len(ids)!=2500 or len(set(ids))!=2500 or len(parents)!=100:
                    errors.append(key+': source prompt/parent coverage mismatch')
        if checked!=110:errors.append('deep source component count mismatch')
    if errors:raise Refusal('1-bit workflow traceability verification failed',{'errors':errors[:50],'error_count':len(errors)})
    return {'schema':'UC/1BIT_WORKFLOW_CHECK/1','integrity':'PASS','tasks':len(seen),'components':len(components),
            'counts':dict(counts),'source_archives_verified':10,'source_components_verified':110 if deep else 0,
            'phase_gates_closed':0,'engineering_completion_verified':False,'deep':bool(deep)}


def show(root,task):
    mm=TASK_RE.fullmatch(task or '')
    if not mm:raise Refusal('invalid 1-bit workflow task ID')
    comp=int(mm.group(1));b,m=load(root);cmap=json.loads((b/'COMPONENTS.json').read_text(encoding='utf-8'))
    rec=cmap.get(f'C{comp:03d}')
    if not rec:raise Refusal('1-bit component not found')
    with zipfile.ZipFile(b/'source'/rec['archive']) as z:
        text=z.read(rec['entry']).decode('utf-8')
    marker='### '+task+'\n';start=text.find(marker)
    if start<0:raise Refusal('source prompt/workflow ID not found')
    end=text.find('\n### PW-',start+len(marker));parent_end=text.find('\n## Parent ',start+len(marker))
    ends=[x for x in (end,parent_end) if x>=0];end=min(ends) if ends else len(text)
    disposition=None
    for r in _ledger_records(b/'ledger.jsonl.gz'):
        if r['id']==task:disposition=r;break
    if disposition is None:raise Refusal('task missing from disposition ledger')
    return {'schema':'UC/1BIT_WORKFLOW_TASK/1','source_component':rec,'source_prompt_workflow':text[start:end].strip(),
            'disposition':disposition}


PLAN={
  1:['EncodingTests','QuantizerTests','WarmupTests'],
  2:['IntegrityResidualTests'],
  3:['RoutingCollectiveTests'],
  4:['BackendAndTIFFTests'],
  5:['AdaptiveControlTests'],
  6:['CapabilityBoundaryTests'],
  7:['TransitionQualityTests'],
  8:['RecoveryReplayTests'],
  9:['EquivalenceTests'],
 10:['AccountingTests'],
}


def execute(root):
    check(root,deep=False)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=Path(SAFE.contained_path(str(root),f'_runs/onebitflow/{stamp}'));out.mkdir(parents=True)
    results=[]
    for phase,classes in PLAN.items():
        name=f'P{phase:02d}';log=out/(name+'.log')
        command=[sys.executable,'-B','-m','unittest','-v',*('test_onebit.'+c for c in classes)]
        with log.open('wb') as f:
            try:r=subprocess.run(command,cwd=Path(root)/'tests',stdout=f,stderr=subprocess.STDOUT,timeout=120,check=False);code=r.returncode
            except subprocess.TimeoutExpired:code=124
        raw=log.read_text(errors='replace');skipped='skipped=' in raw or ' ... skipped ' in raw
        results.append({'phase':name,'local_tests':'FAIL' if code else 'PASS_WITH_SKIPS' if skipped else 'PASS',
                        'exit':code,'command':command,'log':log.relative_to(root).as_posix(),'log_sha256':sha(log),
                        'source_phase_gate':'BLOCKED','scope':'Bounded local containership adaptation only; no JYRM/NCCL/JA21/QAM/FXSpot/Junkyard/model release promotion.'})
    value={'schema':'UC/1BIT_PROFILE_EXECUTION/1','candidate':UC_RELEASE,'source_version':'3.1.0','results':results,
           'local_test_failures':sum(r['local_tests']=='FAIL' for r in results),'phase_gates_closed':0,'full_series_complete':False,
           'rule':'1-bit communication, not 1-bit cognition'}
    SAFE.atomic_json(str(out/'RESULTS.json'),value);return value


def configure(sp):
    p=sp.add_parser('onebit-workflow',help='JYRM 1BNCF v3.1.0 traceability and bounded local execution')
    p.add_argument('verb',choices=('status','check','show','execute'));p.add_argument('task',nargs='?');p.add_argument('--deep',action='store_true');p.set_defaults(fn=run)


def run(a):
    root=E.ship_root()
    if a.verb=='show':value=show(root,a.task or '')
    elif a.verb=='check':value=check(root,a.deep)
    elif a.verb=='execute':value=execute(root)
    else:value=status(root)
    print(json.dumps(value,indent=2,sort_keys=True));return 1 if value.get('local_test_failures',0) else 0
