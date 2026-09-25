"""Pinned TIFF v1.6.0 source, complete dispositions, and scoped test execution.

This runner does not synthesize arbitrary implementations or declare 325,000
engineering tasks complete. Full phase promotion remains independently gated.
"""
from __future__ import annotations
import collections
import csv
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
from . import Refusal, engines as E, safety as SAFE


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def source_hash(row):return hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()


def load(root):
    base=Path(root)/'tifflow';m=json.loads((base/'APPLICATION.json').read_text(encoding='utf-8'));return base,m


def status(root):
    _,m=load(root)
    return {'schema':'UC/TIFF_WORKFLOW_STATUS/1','candidate':'UC-2.5.0','source_version':'1.6.0',
            'components':m['component_count'],'tasks':m['task_count'],'counts':m['counts'],
            'scoped_component_evidence':m['scoped_component_evidence'],'phase_gates':m['phase_gates'],
            'all_work_complete':False,'note':'Local implementation/test evidence is not full source-task closure. Independent ownership/review and unimplemented source features remain blocked.'}


def check(root,deep=False):
    base,m=load(root);errors=[]
    for name,key in [('series.zip','source_sha256'),('ledger.jsonl.gz','ledger_sha256'),('COMPONENTS.json','components_sha256')]:
        if sha(base/name)!=m[key]:raise Refusal('TIFF workflow integrity mismatch: '+name)
    comps=json.loads((base/'COMPONENTS.json').read_text())
    with zipfile.ZipFile(base/'series.zip') as z,gzip.open(base/'ledger.jsonl.gz','rt',encoding='utf-8') as ledger:
        prefix=m['source_prefix'];original=json.loads(z.read(prefix+'MANIFEST.json'))
        if original['version']!='1.6.0' or len(original['components'])!=325:raise Refusal('wrong original TIFF series')
        if set(comps)!=set(c['canonical_component_id'] for c in original['components']):raise Refusal('TIFF component identity set differs')
        count=0;counts=collections.Counter();phase_counts=collections.Counter();seen=set()
        for phase in range(1,10):
            with z.open(prefix+f'LEDGERS/P{phase:02d}.csv') as raw:
                for source in csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline='')):
                    line=next(ledger,None)
                    if line is None:raise Refusal('TIFF execution ledger truncated')
                    row=json.loads(line);r=row['record'];tid=source['task_id'];cid=source['component_id']
                    if tid in seen:raise Refusal('duplicate canonical TIFF task')
                    seen.add(tid)
                    if row['source_row_sha256']!=source_hash(source) or r['task_id']!=tid or r['component_id']!=cid or r['phase']!=phase:raise Refusal('source identity changed: '+tid)
                    if r['schema_version']!='1.6.0' or r['status']!='BLOCKED' or r['reviewer']!='UNASSIGNED':raise Refusal('unsupported task promotion: '+tid)
                    if r['evidence_sha256']!=m['components_sha256'] or r['artifact_ref']!='tifflow/COMPONENTS.json#'+cid:raise Refusal('task evidence binding mismatch: '+tid)
                    for key in ('owner','verification_command','verification_result','updated_utc','blocker_or_na_rationale','next_action'):
                        if not isinstance(r.get(key),str) or not r[key]:raise Refusal('missing evidence field '+key+': '+tid)
                    count+=1;counts[r['status']]+=1;phase_counts[phase]+=1
        if next(ledger,None) is not None:raise Refusal('extra TIFF ledger rows')
        if count!=325000 or count!=m['task_count'] or dict(counts)!=m['counts']:raise Refusal('TIFF ledger totals differ')
        if m['phase_gates']!={f'P{i:02d}':'BLOCKED' for i in range(1,10)}:raise Refusal('unsubstantiated phase promotion')
        if deep:
            for c in original['components']:
                h=hashlib.sha256()
                with z.open(prefix+c['path']) as f:
                    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
                if h.hexdigest()!=c['sha256']:raise Refusal('original component bytes changed: '+c['canonical_component_id'])
    return {'schema':'UC/TIFF_WORKFLOW_CHECK/1','integrity':'PASS','canonical_tasks_checked':count,
            'components':325,'source_component_hashes_checked':325 if deep else 0,'counts':dict(counts),
            'phase_gates_closed':0,'source_archive_sha256':m['source_sha256'],'full_series_complete':False}


def show(root,task):
    if not re.fullmatch(r'C(?:00[1-9]|0[1-9][0-9]|[12][0-9]{2}|3[01][0-9]|32[0-5])-T(?:00[1-9]|0[1-9][0-9]|100)\.(?:0[1-9]|10)',task):raise Refusal('invalid canonical TIFF task ID')
    base,m=load(root);cid=task[:4]
    if sha(base/'series.zip')!=m['source_sha256']:raise Refusal('TIFF original archive mismatch')
    with zipfile.ZipFile(base/'series.zip') as z:
        src=json.loads(z.read(m['source_prefix']+'MANIFEST.json'));c=next(c for c in src['components'] if c['canonical_component_id']==cid)
        text=z.read(m['source_prefix']+c['path']).decode('utf-8')
    start=text.index('    **Prompt '+task+'**');end=text.find('\n  - [ ]',start)
    with gzip.open(base/'ledger.jsonl.gz','rt',encoding='utf-8') as f:
        record=next(json.loads(line)['record'] for line in f if '"task_id":"'+task+'"' in line)
    return {'source_path':c['path'],'source_prompt_workflow':text[start:end if end!=-1 else None].strip(),
            'disposition':record,'component_scope':json.loads((base/'COMPONENTS.json').read_text())[cid]}


PLAN={
  1:['BlobTests','AdmissionTests'],
  2:['HistoryTests.test_grid_matrix','KernelTests.test_coordinates','AdmissionTests.test_associated_alpha'],
  3:['HistoryTests.test_compression_matrix','AdmissionTests.test_lossy_compression'],
  4:['KernelTests.test_batch_atomic','KernelTests.test_native_limit','KernelTests.test_operation_budget'],
  5:['PixelCLITests','HistoryTests.test_replace_failure_preserves_old','HistoryTests.test_stale_commit'],
  6:['IndependentInteropTests'],
  7:['AdmissionTests.test_unknown_sidecar_fields','AdmissionTests.test_nonfinite_json'],
  8:[],
  9:['GifTests','KernelTests'],
}


def execute(root):
    """Run bounded local-profile tests in phase order; never close source gates."""
    check(root)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=Path(SAFE.contained_path(str(root),'_runs/tifflow/'+stamp));out.mkdir(parents=True)
    results=[]
    for phase,tests in PLAN.items():
        name=f'P{phase:02d}';log=out/(name+'.log')
        if not tests:
            results.append({'phase':name,'local_tests':'NOT_RUN','source_phase_gate':'BLOCKED',
                            'reason':'Cloud, COG and Zarr implementations are absent; no credentialed/network work attempted.'});continue
        command=[sys.executable,'-B','-m','unittest','-v',*('test_pixel_fabric.'+t for t in tests)]
        with log.open('wb') as f:
            try:r=subprocess.run(command,cwd=Path(root)/'tests',stdout=f,stderr=subprocess.STDOUT,timeout=120,check=False);code=r.returncode
            except subprocess.TimeoutExpired:code=124
        raw=log.read_text(errors='replace');skipped='skipped=' in raw or '... skipped ' in raw
        results.append({'phase':name,'local_tests':'FAIL' if code else 'PASS_WITH_SKIPS' if skipped else 'PASS',
                        'exit':code,'command':command,'log':log.relative_to(root).as_posix(),'log_sha256':sha(log),
                        'source_phase_gate':'BLOCKED','scope':'Local profile only; see tifflow/COMPONENTS.json. No source-task approvals implied.'})
    value={'schema':'UC/TIFF_PROFILE_EXECUTION/1','candidate':'UC-2.5.0','source_version':'1.6.0',
           'results':results,'phase_gates_closed':0,'full_series_complete':False,
           'local_test_failures':sum(r['local_tests']=='FAIL' for r in results)}
    SAFE.atomic_json(str(out/'RESULTS.json'),value)
    return value


def configure(sp):
    p=sp.add_parser('tiff-workflow',help='TIFF v1.6.0 traceability and scoped local qualification (not all-task automation)')
    p.add_argument('verb',choices=('status','check','show','execute'));p.add_argument('task',nargs='?');p.add_argument('--deep',action='store_true');p.set_defaults(fn=run)


def run(a):
    root=E.ship_root()
    if a.verb=='show':value=show(root,a.task or '')
    elif a.verb=='check':value=check(root,a.deep)
    elif a.verb=='execute':value=execute(root)
    else:value=status(root)
    print(json.dumps(value,indent=2,sort_keys=True));return 1 if value.get('local_test_failures',0) else 0
