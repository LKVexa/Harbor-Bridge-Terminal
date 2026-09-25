"""Integrity and honest status for the original VWS source and current dispositions."""
from __future__ import annotations
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import zipfile
from . import Refusal

STATES = {'OPEN','IN_PROGRESS','BLOCKED','PASS','FAIL','NOT_APPLICABLE'}
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def load(root):
    base=Path(root)/'vwsflow'
    manifest=json.loads((base/'APPLICATION.json').read_text(encoding='utf-8'))
    return base,manifest
def status(root):
    _,m=load(root)
    return {'schema':'UC/VWS_STATUS/1','release':m['release'],'source_packs':m['task_count'],'source_checklists':m['source_checklist_count'],'integration_packs':m['integration_pack_count'],'counts':m['counts'],'phase_gates':{p['phase']:p['status'] for p in m['phases']},'all_work_complete':False,'profile':m['profile'],'protocol':m['protocol'],'note':'Inventory coverage is not 6,360 completed engineering tasks. Native and public deployment gates remain blocked.'}
def records(base,m):
    if digest(base/'series.zip')!=m['source_archive_sha256']:raise Refusal('VWS original archive digest mismatch')
    if digest(base/'ledger.jsonl.gz')!=m['ledger_sha256']:raise Refusal('VWS disposition ledger digest mismatch')
    with gzip.open(base/'ledger.jsonl.gz','rt',encoding='utf-8') as f:
        ledger=[json.loads(line) for line in f]
    with zipfile.ZipFile(base/'series.zip') as z:
        with z.open('VWS200/ledger/TASKS.jsonl') as f:
            source=[(json.loads(line),hashlib.sha256(line).hexdigest()) for line in f]
    return ledger,source

def check(root):
    base,m=load(root);ledger,source=records(base,m);errors=[]
    if m.get('schema')!='UC/VWS_REAPPLICATION/1' or m.get('task_count')!=6360 or m.get('source_checklist_count')!=6300 or m.get('integration_pack_count')!=60:errors.append('invalid manifest identity/counts')
    if [p.get('phase') for p in m.get('phases',[])]!=[f'P{i:02d}' for i in range(12)]:errors.append('expected exactly twelve ordered phases')
    if len(ledger)!=6360 or len(source)!=6360:errors.append('expected 6360 original and current entries')
    by_id={r['id']:r for r in ledger};src={r['id']:r for r,_ in source}
    if len(by_id)!=len(ledger) or len(src)!=len(source):errors.append('duplicate IDs')
    if set(by_id)!=set(src):errors.append('missing or extra current IDs')
    for s,h in source:
        r=by_id.get(s['id'])
        if not r:continue
        if r.get('source_record_sha256')!=h:errors.append(s['id']+': original record identity mismatch')
        if r.get('requirement')!=s.get('requirement',s.get('title')):errors.append(s['id']+': original requirement changed')
        if 'requirement' in s and hashlib.sha256(s['requirement'].encode()).hexdigest()!=s.get('requirement_sha256'):errors.append(s['id']+': source requirement hash mismatch')
        if r.get('requirement_sha256')!=s.get('requirement_sha256'):errors.append(s['id']+': requirement hash changed')
        for k in ('kind','phase','dependencies'):
            if r.get(k)!=s.get(k):errors.append(s['id']+': '+k+' changed')
        if r.get('status') not in STATES:errors.append(s['id']+': invalid status')
        if any(d not in by_id and d not in {f'G{i:02d}' for i in range(12)} for d in r.get('dependencies',[])):errors.append(s['id']+': unknown dependency')
        if r.get('status')=='PASS':errors.append(s['id']+': this reapplication does not authorize per-item PASS promotion')
        if not r.get('reason') or not r.get('execution_home'):errors.append(s['id']+': missing disposition or execution home')
    counts=dict(collections.Counter(r['status'] for r in ledger))
    if counts!=m['counts']:errors.append('summary status counts differ')
    kinds=collections.Counter(s['kind'] for s,_ in source)
    if kinds!={'source_checklist':6300,'terminal_integration':60}:errors.append('source kind counts differ')
    for p in m['phases']:
        rr=[r for r in ledger if r['phase']==p['phase']]
        if p['packs']!=len(rr) or p['counts']!=dict(collections.Counter(r['status'] for r in rr)):errors.append(p['phase']+': phase summary differs')
        if p['status']!='BLOCKED':errors.append(p['phase']+': unsubstantiated phase promotion')
    if errors:raise Refusal('VWS traceability verification failed',{'errors':errors[:50],'error_count':len(errors)})
    return {'schema':'UC/VWS_CHECK/1','integrity':'PASS','engineering_completion':'NOT_COMPLETE','task_count':len(ledger),'source_requirement_hashes_verified':6300,'original_source_records_verified':6360,'counts':counts,'phase_gates_closed':0,'phase_count':12,'source_archive_sha256':m['source_archive_sha256']}

def show(root,task):
    if not re.fullmatch(r'(?:C\d{2}|ALT\d{2})-\d{3}|I\d{3}',task):raise Refusal('invalid VWS task ID')
    base,m=load(root);ledger,source=records(base,m)
    disposition=next((r for r in ledger if r['id']==task),None)
    original=next((r for r,_ in source if r['id']==task),None)
    if not disposition or not original:raise Refusal('VWS task not found')
    return {'source_workpack':original,'current_disposition':disposition}
