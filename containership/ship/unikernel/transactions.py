"""Crash-recoverable managed-file snapshots for serialized trusted-local CLI use.

Before mutation: bounded inventory -> copied/fsynced/verified backup -> PREPARED
journal. A crash before COMMITTED leaves a blocking journal. Recovery replays
verified old roots and is repeatable. New/displaced files are retained, not
silently deleted. This is recovery atomicity for cooperating CLI consumers, NOT
simultaneous atomic visibility to direct filesystem readers, a guest snapshot,
or rollback of effects outside named resources. No automatic pruning occurs.
"""
from __future__ import annotations
import contextlib
import copy
import hashlib
import io
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path
from . import Refusal
from . import strictjson as J
from .safety import atomic_json, atomic_write, contained_path, reject_link, validate_name, ship_lock
from .control_store import ControlStore, now

SCHEMA='UC/MANAGED_TRANSACTION/1'
MAX_FILES=50000
MAX_SNAPSHOT=512*1024*1024
MAX_RETAINED=2*1024*1024*1024
MIN_FREE=64*1024*1024
MAX_TRANSACTIONS=256
ACTIVE={'PREPARED','EXECUTING','ROLLING_BACK','RECOVERY_FAILED'}
FINAL={'COMMITTED','ROLLED_BACK'}

def _valid_id(value):
    if not isinstance(value,str) or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):
        raise Refusal('invalid transaction ID')
    return value

def _resource(value):
    if isinstance(value,str) and value in {'registry','MANIFEST.json','SHA256SUMS.txt','_studio','berths'}: return value
    if isinstance(value,str) and value.startswith('berths/') and value.count('/')==1:
        validate_name(value.split('/')[1]); return value
    raise Refusal('journal resource is outside the managed allowlist',{'path':value})

def _sync_dir(path):
    if os.name!='nt':
        fd=os.open(str(path),os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)

def _sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''):
            if fh.tell()>MAX_SNAPSHOT: raise Refusal('snapshot hash input grew beyond budget')
            h.update(chunk)
    return h.hexdigest()

def inventory(path):
    """Includes empty directories; no links, FIFOs or unbounded file population."""
    path=Path(path); reject_link(str(path))
    if not path.exists(): return {'kind':'absent','entries':[],'bytes':0}
    entries=[]; total=0
    todo=[('',path)]
    while todo:
        rel,p=todo.pop(); reject_link(str(p)); info=p.lstat()
        if stat.S_ISDIR(info.st_mode):
            entries.append({'path':rel,'kind':'directory','mode':stat.S_IMODE(info.st_mode)})
            children=list(p.iterdir())
            if len(entries)+len(todo)+len(children)>MAX_FILES: raise Refusal('snapshot file-count budget exceeded')
            for child in sorted(children,reverse=True): todo.append((rel+'/'+child.name if rel else child.name,child))
        elif stat.S_ISREG(info.st_mode):
            total+=info.st_size
            if total>MAX_SNAPSHOT: raise Refusal('snapshot byte budget exceeded')
            entries.append({'path':rel,'kind':'file','bytes':info.st_size,'sha256':_sha(p),'mode':stat.S_IMODE(info.st_mode)})
        else: raise Refusal('snapshot refuses special filesystem objects',{'path':str(p)})
        if len(entries)>MAX_FILES: raise Refusal('snapshot file-count budget exceeded')
    return {'kind':'directory' if path.is_dir() else 'file','entries':sorted(entries,key=lambda r:r['path']),'bytes':total}

def _copy(src,dst,_budget=None):
    # Enforce again during copying, not only in the earlier inventory.
    budget=_budget if _budget is not None else {'bytes':0,'entries':0}
    budget['entries']+=1
    if budget['entries']>MAX_FILES:raise Refusal('snapshot copy file-count budget exceeded')
    src=Path(src);dst=Path(dst);reject_link(str(src))
    if src.is_dir():
        dst.mkdir(parents=True,exist_ok=False)
        for child in sorted(src.iterdir()): _copy(child,dst/child.name,budget)
        os.chmod(dst,stat.S_IMODE(src.stat().st_mode));_sync_dir(dst)
    elif src.is_file():
        dst.parent.mkdir(parents=True,exist_ok=True)
        with src.open('rb') as fh,dst.open('xb') as out:
            for block in iter(lambda:fh.read(1024*1024),b''):
                budget['bytes']+=len(block)
                if budget['bytes']>MAX_SNAPSHOT:raise Refusal('snapshot copy byte budget exceeded')
                out.write(block)
            out.flush();os.fsync(out.fileno())
        os.chmod(dst,stat.S_IMODE(src.stat().st_mode))
    else: raise Refusal('copy refuses missing or special source')

def _fingerprint(plan): return hashlib.sha256(J.canonical_bytes(plan)).hexdigest()

class Snapshot:
    def __init__(self,root,tid=None):
        self.root=Path(root).absolute();self.tid=_valid_id(tid) if tid else uuid.uuid4().hex
        self.base=Path(contained_path(str(self.root),'_runs/managed_tx'))
        self.home=Path(contained_path(str(self.root),'_runs/managed_tx/'+self.tid))
        self.journal=self.home/'journal.json';self.record=None
    def prepare(self,resources,*,command,name=None,extra_bytes=0):
        resources=[_resource(r) for r in resources]
        if len(set(resources))!=len(resources) or any(a!=b and b.startswith(a+'/') for a in resources for b in resources):
            raise Refusal('overlapping or duplicate transaction resources')
        if type(extra_bytes) is not int or extra_bytes<0 or extra_bytes>2*MAX_SNAPSHOT: raise Refusal('invalid staging size estimate')
        ensure_clean(self.root)
        self.base.mkdir(parents=True,exist_ok=True)
        if sum(1 for _ in self.base.iterdir())>=MAX_TRANSACTIONS: raise Refusal('retained transaction-count budget exhausted; inspect backups')
        # Capacity checks are cooperative preflight, not an OS reservation.
        retained=0
        for dp,dns,fns in os.walk(self.base):
            for dn in dns: reject_link(str(Path(dp)/dn))
            for fn in fns:
                p=Path(dp)/fn;reject_link(str(p));retained+=p.stat().st_size
        plan=[]
        for i,resource in enumerate(resources):
            path=Path(contained_path(str(self.root),resource));inv=inventory(path)
            plan.append({'resource':resource,'backup':str(i),'inventory':inv})
        size=sum(x['inventory']['bytes'] for x in plan)
        if size>MAX_SNAPSHOT or retained+2*size+extra_bytes>MAX_RETAINED:
            raise Refusal('managed snapshot retention budget exceeded')
        required=2*size+extra_bytes+MIN_FREE
        if shutil.disk_usage(self.root).free<required:
            raise Refusal('insufficient free space before mutation',{'required_bytes':required})
        self.home.mkdir(exist_ok=False)
        self.record={'schema':SCHEMA,'id':self.tid,'command':command,'name':name,
                     'status':'PREPARING','created_utc':now(),'resources':plan,
                     'plan_sha256':_fingerprint(plan),'snapshot_bytes':size,'token':None,
                     'scope':'managed local files only; external/native side effects are not reversible'}
        self.save()
        for item in plan:
            src=Path(contained_path(str(self.root),item['resource']))
            if item['inventory']['kind']!='absent':
                dst=self.home/'backup'/item['backup'];_copy(src,dst)
                if inventory(dst)!=item['inventory']: raise Refusal('snapshot source changed while copying')
        self.record['status']='PREPARED';self.save();_sync_dir(self.base)
        return self.record
    def save(self):
        atomic_json(str(self.journal),self.record)
    def read(self):
        reject_link(str(self.home));record=J.read(self.journal)
        if not isinstance(record,dict) or record.get('schema')!=SCHEMA or record.get('id')!=self.tid or not isinstance(record.get('status'),str) or record.get('status') not in ACTIVE|FINAL|{'PREPARING'}:
            raise Refusal('invalid transaction journal identity/version/state')
        resources=record.get('resources')
        if not isinstance(resources,list) or len(resources)>10 or record.get('plan_sha256')!=_fingerprint(resources):
            raise Refusal('transaction recovery plan mismatch')
        found=[]
        for i,item in enumerate(resources):
            if not isinstance(item,dict) or set(item)!={'resource','backup','inventory'}: raise Refusal('invalid transaction resource record')
            inv=item['inventory']
            if not isinstance(inv,dict) or inv.get('kind') not in ('absent','file','directory') or type(inv.get('bytes')) is not int or not 0<=inv['bytes']<=MAX_SNAPSHOT or not isinstance(inv.get('entries'),list) or len(inv['entries'])>MAX_FILES:
                raise Refusal('invalid transaction backup inventory')
            _resource(item['resource']);found.append(item['resource'])
            if item['backup']!=str(i): raise Refusal('invalid backup ordinal')
        if len(set(found))!=len(found) or any(a!=b and b.startswith(a+'/') for a in found for b in found):
            raise Refusal('overlapping transaction recovery resources')
        if record.get('name') is not None: validate_name(record['name'])
        self.record=record;return record
    def commit(self):
        if self.record['status']!='EXECUTING':raise Refusal('cannot commit outside execution')
        self.record['status']='COMMITTED';self.record['finished_utc']=now();self.save()
    def rollback(self, *, allow_committed=False):
        self.read()
        if self.record['status']=='ROLLED_BACK':return self.record
        if self.record['status']=='PREPARING':
            # No managed action is allowed before PREPARED; incomplete backups cannot restore.
            self.record['status']='ROLLED_BACK';self.record['recovery_note']='preparation abandoned; mutation had not started';self.save();return self.record
        if self.record['status']=='COMMITTED' and not allow_committed: raise Refusal('committed historical rollback is unsupported; use pending recovery only')
        # Verify every backup before touching any live resource. Hashes are local integrity, not an external trust root.
        for item in self.record['resources']:
            if item['inventory']['kind']!='absent':
                src=Path(contained_path(str(self.home),'backup/'+item['backup']))
                if inventory(src)!=item['inventory']:raise Refusal('recovery backup integrity failure',{'resource':item['resource']})
        need=sum(i['inventory']['bytes'] for i in self.record['resources'])+MIN_FREE
        if shutil.disk_usage(self.root).free<need:raise Refusal('insufficient space for non-destructive recovery',{'required_bytes':need})
        self.record['status']='ROLLING_BACK';self.save()
        try:
            for item in self.record['resources']:
                resource=item['resource'];target=Path(contained_path(str(self.root),resource))
                if inventory(target)==item['inventory']:continue
                serial=uuid.uuid4().hex
                stage=Path(contained_path(str(self.home),'restore/'+serial))
                old=Path(contained_path(str(self.home),'displaced/'+serial))
                if item['inventory']['kind']!='absent':
                    _copy(self.home/'backup'/item['backup'],stage)
                    if inventory(stage)!=item['inventory']:raise Refusal('recovery staging mismatch')
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():
                    old.parent.mkdir(parents=True,exist_ok=True);os.replace(target,old);_sync_dir(target.parent);_sync_dir(old.parent)
                if item['inventory']['kind']!='absent':os.replace(stage,target);_sync_dir(target.parent)
                if inventory(target)!=item['inventory']:raise Refusal('post-recovery bytes differ')
            if self.record.get('name') and (self.record.get('token') or any(w.get('active_operation') for w in ControlStore(self.root).inspect(self.record['name'])['workloads'])):
                self.record['recovery_identity']=ControlStore(self.root).recover(self.record['name'],self.tid)
            self.record['status']='ROLLED_BACK';self.record['finished_utc']=now();self.save()
            return self.record
        except BaseException:
            self.record['status']='RECOVERY_FAILED';self.save();raise

def list_transactions(root):
    base=Path(contained_path(str(root),'_runs/managed_tx'));out=[]
    if not base.exists():return out
    for p in sorted(base.iterdir()):
        reject_link(str(p));_valid_id(p.name)
        if not p.is_dir():raise Refusal('unexpected transaction-root entry')
        if not (p/'journal.json').is_file():
            out.append({'id':p.name,'status':'PREPARATION_ORPHAN','note':'no journal; managed mutation cannot have started; retained for manual inspection'});continue
        record=Snapshot(root,p.name).read()
        out.append({k:record.get(k) for k in ('id','command','name','status','created_utc','finished_utc','snapshot_bytes')})
    return out

def ensure_clean(root):
    bad=[r for r in list_transactions(root) if r['status'] in ACTIVE|{'PREPARING'}]
    if bad:raise Refusal('pending managed-file recovery blocks mutation',{'transactions':bad,'action':'uc recover rollback ID'})

class BoundedText(io.StringIO):
    def write(self,text):
        if self.tell()+len(text)>4*1024*1024:raise Refusal('command output budget exceeded')
        return super().write(text)

def execute(root,args,fn):
    """Called while holding the ship lock. Public API callers must also serialize."""
    command=args.cmd;name=getattr(args,'name',None)
    paths=['registry','MANIFEST.json','SHA256SUMS.txt']
    if name:paths+=['berths/'+name,'_studio']
    elif command in {'build','verify','studio-test'}:paths+=['berths','_studio']
    report_target=getattr(args,'out',None)
    if report_target:
        report_target=Path(report_target).absolute()
        try:relative=report_target.relative_to(Path(root).absolute()).as_posix()
        except ValueError:relative=None
        if relative is not None:
            parts=relative.split('/')
            if len(parts)<2 or parts[0]!='_runs' or parts[1] in {'control','managed_tx','transactions','backups','objects'}:
                raise Refusal('explicit report output must be outside the workspace or in a non-control _runs path')
            contained_path(str(root),relative)
    snap=Snapshot(root);extra=0
    if command=='load':
        import zipfile
        source=Path(args.source)
        if source.is_file() and zipfile.is_zipfile(source):
            from .safety import inspect_zip
            with zipfile.ZipFile(source) as z:extra=sum(i.file_size for i in inspect_zip(z))
        elif source.is_dir():extra=inventory(source)['bytes']
    snap.prepare(paths,command=command,name=name,extra_bytes=extra)
    token=None;output=BoundedText();workargs=copy.copy(args)
    if report_target:workargs.out=str(snap.home/'operation_report.json')
    def publish_report(state):
        if not report_target:return
        report=snap.home/'operation_report.json'
        if report.exists():
            value=J.read(report)
            if isinstance(value,dict):value['managed_transaction']={'id':snap.tid,'status':state,'scope':snap.record['scope']}
            else:value={'operation_result':value,'managed_transaction':{'id':snap.tid,'status':state}}
            atomic_json(str(report_target),value)
    try:
        if name:
            token=ControlStore(root).begin(name,command,getattr(args,'generation',None),invalidate=command in {'load','unload'})
            snap.record['token']=token
        snap.record['status']='EXECUTING';snap.save()
        with contextlib.redirect_stdout(output):code=fn(workargs)
        if code!=0:
            snap.rollback()
            publish_report('ROLLED_BACK')
            print(output.getvalue(),end='')
            print(J.dumps({'schema':'UC/TRANSACTION_RESULT/1','id':snap.tid,'status':'ROLLED_BACK','command_exit':code,
                           'scope':snap.record['scope']}),file=sys.stderr)
            return code
        if token:
            observed='staged' if command=='load' else 'stopped' if command in {'unload','run','slot-run'} else None
            ControlStore(root).finish(token,True,observed=observed)
        snap.commit()
        try:publish_report('COMMITTED')
        except BaseException:
            print(J.dumps({'schema':'UC/TRANSACTION_RESULT/1','id':snap.tid,'status':'COMMITTED',
                           'report_publication_failed':True}),file=sys.stderr)
            raise
        print(output.getvalue(),end='')
        print(J.dumps({'schema':'UC/TRANSACTION_RESULT/1','id':snap.tid,'status':'COMMITTED',
                       'identity':token,'scope':snap.record['scope']}),file=sys.stderr)
        return code
    except BaseException:
        # Retain and report original exception unless rollback itself fails.
        if snap.record['status']!='COMMITTED':snap.rollback()
        raise
