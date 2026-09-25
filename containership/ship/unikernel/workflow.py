"""Read-only traceability for the attached 96,000-task engineering series.

The source is data, not shell commands. Import/coverage checks never execute its
text and never turn TODO/BLOCKED/IN_PROGRESS into completed implementation.
"""
from __future__ import annotations
import gzip
import hashlib
import re
import zipfile
from collections import Counter
from pathlib import Path
from . import Refusal
from . import strictjson as J
from .safety import contained_path, inspect_zip

TASK_ID=re.compile(r'UC-M(?:0[1-9]|1[0-2])\.0[1-8]-C(?:00[1-9]|0[1-9][0-9]|100)-T(?:0[1-9]|10)\Z')
STATES={'TODO','IN_PROGRESS','BLOCKED','DONE','NOT_APPLICABLE'}

def _base(root):return Path(contained_path(str(root),'workflow'))

def status(root):
    r=J.read(_base(root)/'APPLICATION.json')
    if not isinstance(r,dict) or r.get('schema')!='UC/WORKFLOW_APPLICATION/1':raise Refusal('unsupported workflow application schema')
    return r

def _rows(handle):
    while True:
        line=handle.readline(65537)
        if not line:break
        if len(line)>65536 or not line.endswith(b'\n'):raise Refusal('workflow record line exceeds bounds or is truncated')
        yield J.loads(line,max_bytes=65536)

def _source(root):
    base=_base(root);meta=status(root);p=Path(contained_path(str(base),'series.zip'))
    h=hashlib.sha256()
    with p.open('rb') as fh:
        for b in iter(lambda:fh.read(1024*1024),b''):h.update(b)
    if h.hexdigest()!=meta['inputs']['series_sha256']:raise Refusal('attached series bytes do not match their recorded digest')
    return p

def _ledger(root):
    base=_base(root);meta=status(root);p=Path(contained_path(str(base),'ledger.jsonl.gz'))
    if p.stat().st_size>128*1024*1024:raise Refusal('workflow ledger exceeds compressed-size limit')
    h=hashlib.sha256()
    with p.open('rb') as fh:
        for b in iter(lambda:fh.read(1024*1024),b''):h.update(b)
    if h.hexdigest()!=meta.get('ledger_sha256'):raise Refusal('workflow ledger digest mismatch')
    return p

def check(root):
    base=_base(root);meta=status(root);source=_source(root)
    counts=Counter();components=Counter();seen=set();parents=set()
    with zipfile.ZipFile(source) as z,gzip.open(_ledger(root),'rb') as ledger:
        inspect_zip(z)
        with z.open('UCTODO/data/subtasks.jsonl') as tasks:
            original=_rows(tasks);applied=_rows(ledger)
            import itertools
            for left,right in itertools.zip_longest(original,applied):
                if left is None or right is None:raise Refusal('workflow source/ledger length mismatch')
                if not isinstance(left,dict) or not isinstance(right,dict):raise Refusal('workflow task must be an object')
                tid=left.get('id')
                if not isinstance(tid,str) or not TASK_ID.fullmatch(tid) or tid in seen:raise Refusal('invalid or duplicate workflow task ID')
                if right.get('id')!=tid or right.get('source_text_sha256')!=hashlib.sha256(left['text'].encode('utf-8')).hexdigest():
                    raise Refusal('workflow task trace mismatch',{'id':tid})
                state=right.get('status')
                if not isinstance(state,str) or state not in STATES:raise Refusal('unknown workflow task state')
                if state=='DONE':raise Refusal('this release has no individually promoted task; unexpected DONE record')
                if state=='NOT_APPLICABLE' and not right.get('reason'):raise Refusal('profile exclusion requires rationale')
                if right.get('component_id')!=left.get('component_id') or right.get('parent_id')!=left.get('parent_id'):
                    raise Refusal('workflow parent trace mismatch')
                seen.add(tid);parents.add(left['parent_id']);counts[state]+=1;components[left['component_id']]+=1
                if len(seen)>96000:raise Refusal('workflow task-count overflow')
    if len(seen)!=96000 or len(parents)!=9600 or len(components)!=96 or set(components.values())!={1000}:
        raise Refusal('incomplete workflow coverage')
    if dict(sorted(counts.items()))!=meta['task_status_counts']:raise Refusal('workflow status summary does not match task records')
    return {'schema':'UC/WORKFLOW_CHECK/1','valid':True,'tasks':len(seen),'parents':len(parents),
            'components':len(components),'status_counts':dict(counts),'source_sha256':meta['inputs']['series_sha256'],
            'engineering_completion_verified':False,
            'note':'Source integrity and task accounting only; no engineering task is completed by this check.'}

def show(root,task):
    if not TASK_ID.fullmatch(task):raise Refusal('invalid workflow task ID')
    base=_base(root);source=_source(root);original=None;progress=None
    with zipfile.ZipFile(source) as z:
        with z.open('UCTODO/data/subtasks.jsonl') as fh:
            for r in _rows(fh):
                if r['id']==task:original=r;break
    with gzip.open(_ledger(root),'rb') as fh:
        for r in _rows(fh):
            if r['id']==task:progress=r;break
    if original is None or progress is None:raise Refusal('task is missing from source or application ledger')
    if progress['source_text_sha256']!=hashlib.sha256(original['text'].encode('utf-8')).hexdigest():raise Refusal('task text identity mismatch')
    return {'schema':'UC/WORKFLOW_TASK/1','source':original,'application_pass':progress}
