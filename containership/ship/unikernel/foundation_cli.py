"""Operator surfaces for the UC-2.3.0 local foundation."""
from __future__ import annotations
import hashlib
from pathlib import Path
from . import Refusal
from . import engines as E, strictjson as J
from . import contracts, artifacts, transactions
from .control_store import ControlStore
from .safety import atomic_write, contained_path, reject_link

def configure(sp):
    p=sp.add_parser('capabilities',help='report actual backend and unimplemented assurance boundaries')
    p.add_argument('--require-isolation',choices=sorted(contracts.ISOLATIONS),default='host-process');p.add_argument('--out');p.set_defaults(fn=capabilities)
    p=sp.add_parser('contract-check',help='validate a versioned control request without executing it')
    p.add_argument('request');p.add_argument('--out');p.set_defaults(fn=contract_check)
    p=sp.add_parser('lifecycle',help='inspect generation-scoped local operation history')
    p.add_argument('name',nargs='?');p.add_argument('--limit',type=int,default=100);p.add_argument('--out');p.set_defaults(fn=lifecycle)
    p=sp.add_parser('recover',help='inspect or roll back pending managed-file transactions')
    p.add_argument('verb',choices=['list','inspect','rollback']);p.add_argument('transaction',nargs='?');p.add_argument('--out');p.set_defaults(fn=recover)
    p=sp.add_parser('graph',help='validate a typed artifact DAG or report affected descendants')
    p.add_argument('verb',choices=['validate','affected']);p.add_argument('file');p.add_argument('--changed',nargs='+');p.add_argument('--out');p.set_defaults(fn=graph)
    p=sp.add_parser('object',help='publish or verify a local content-addressed blob; not trust enrollment')
    p.add_argument('verb',choices=['put','verify']);p.add_argument('subject');p.add_argument('--out');p.set_defaults(fn=object_command)
    p=sp.add_parser('workflow',help='inspect the complete attached series and this release execution ledger')
    p.add_argument('verb',choices=['status','check','show']);p.add_argument('task',nargs='?');p.add_argument('--out');p.set_defaults(fn=workflow)

def emit(value,a,code=0):
    from .cli import _emit
    return _emit(value,code,out=getattr(a,'out',None))

def capabilities(a):return emit(contracts.require_backend(a.require_isolation),a)

def contract_check(a):
    value=contracts.validate_request(J.read(a.request));caps=contracts.require_backend(value['isolation'])
    executable=value['operation'] in {'inspect','invoke'}
    return emit({'schema':'UC/CONTROL_VALIDATION/1','valid':True,'request':value,
                 'canonical_sha256':hashlib.sha256(J.canonical_bytes(value)).hexdigest(),
                 'backend':caps['backend'],'executed':False,
                 'operation_implemented':executable,
                 'note':'No action was executed. Guest boot/stop/snapshot/restore are not implemented.'},a,0 if executable else 3)

def lifecycle(a):return emit(ControlStore(E.ship_root()).inspect(a.name,a.limit),a)

def recover(a):
    if a.verb=='list':return emit({'schema':'UC/TRANSACTION_LIST/1','transactions':transactions.list_transactions(E.ship_root())},a)
    if not a.transaction:raise Refusal('transaction ID is required')
    tx=transactions.Snapshot(E.ship_root(),a.transaction)
    if a.verb=='inspect':return emit(tx.read(),a)
    # An operator-requested recovery may only roll back unresolved transactions.
    return emit(tx.rollback(),a)

def graph(a):
    value=J.read(a.file);rec=artifacts.validate_graph(value)
    if a.verb=='affected':rec['affected']=artifacts.affected(value,a.changed)
    return emit(rec,a)

def object_command(a):
    store=artifacts.ObjectStore(E.ship_root())
    if a.verb=='verify':
        data=store.read(a.subject)
        return emit({'schema':'UC/OBJECT/1','sha256':a.subject,'bytes':len(data),'verified':True,'authenticity':'not_assessed'},a)
    transactions.ensure_clean(E.ship_root())
    reject_link(a.subject)
    with open(a.subject,'rb') as fh:data=fh.read(artifacts.MAX_BLOB+1)
    return emit({'schema':'UC/OBJECT/1',**store.put(data),'authenticity':'not_assessed'},a)

def workflow(a):
    from . import workflow as W
    if a.verb=='check':return emit(W.check(E.ship_root()),a)
    if a.verb=='show':
        if not a.task:raise Refusal('task ID is required')
        return emit(W.show(E.ship_root(),a.task),a)
    return emit(W.status(E.ship_root()),a)
